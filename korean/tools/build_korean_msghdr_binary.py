#!/usr/bin/env python3
"""Build PSX-ready Korean MISCJ.HDR, MSGJ.HDR and MSGJ.DBS prototypes.

This reproduces the data layout used by the original English-patch JUCE tools,
but accepts the custom Korean bytecode planned by plan_korean_bytecode.py.

Outputs are prototypes until the PSX renderer/font patch understands the same
Korean bytecode. Every compressed record is decoded again with an emulation of
the game's Huffman tree traversal before the files are written.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import heapq
import struct
from dataclasses import dataclass
from pathlib import Path

from plan_korean_bytecode import build_mapping, encode_text, parse_records

DEFAULT_INPUT = Path("korean/build/MSGHDR_indexText.ko.merged.txt")
DEFAULT_DIR = Path("korean/build/psx")
HUFFMAN_TABLE_SIZE = 0x400
DBS_ADDRESS_LIMIT = 0x3FFFF
BLOCK_SIZE = 0x400


@dataclass
class HuffNode:
    weight: int
    min_symbol: int
    symbol: int | None = None
    left: "HuffNode | None" = None
    right: "HuffNode | None" = None
    index: int | None = None

    @property
    def leaf(self) -> bool:
        return self.symbol is not None


@dataclass
class HeaderEntry:
    message_id: int
    address: int
    subindices: int = 0


def build_huffman_tree(freq: collections.Counter[int]) -> HuffNode:
    if len(freq) < 2:
        raise RuntimeError("at least two Huffman symbols are required")

    heap: list[tuple[int, int, int, HuffNode]] = []
    serial = 0
    for symbol, weight in sorted(freq.items()):
        node = HuffNode(weight=weight, min_symbol=symbol, symbol=symbol)
        heapq.heappush(heap, (weight, symbol, serial, node))
        serial += 1

    while len(heap) > 1:
        _, _, _, left = heapq.heappop(heap)
        _, _, _, right = heapq.heappop(heap)
        node = HuffNode(
            weight=left.weight + right.weight,
            min_symbol=min(left.min_symbol, right.min_symbol),
            left=left,
            right=right,
        )
        heapq.heappush(heap, (node.weight, node.min_symbol, serial, node))
        serial += 1

    return heap[0][3]


def assign_internal_indices(root: HuffNode) -> list[HuffNode]:
    nodes: list[HuffNode] = []

    def walk(node: HuffNode) -> None:
        if node.leaf:
            return
        node.index = len(nodes)
        nodes.append(node)
        assert node.left is not None and node.right is not None
        walk(node.left)
        walk(node.right)

    walk(root)
    if not nodes or nodes[0] is not root or root.index != 0:
        raise RuntimeError("invalid Huffman root assignment")
    return nodes


def build_codes(root: HuffNode) -> dict[int, tuple[int, int]]:
    codes: dict[int, tuple[int, int]] = {}

    def walk(node: HuffNode, bits: int, length: int) -> None:
        if node.leaf:
            assert node.symbol is not None
            codes[node.symbol] = (bits, max(1, length))
            return
        assert node.left is not None and node.right is not None
        walk(node.left, bits << 1, length + 1)
        walk(node.right, (bits << 1) | 1, length + 1)

    walk(root, 0, 0)
    return codes


def serialize_huffman_tree(root: HuffNode) -> bytes:
    nodes = assign_internal_indices(root)
    used_bytes = len(nodes) * 4
    if used_bytes > HUFFMAN_TABLE_SIZE:
        raise RuntimeError(
            f"Huffman tree needs 0x{used_bytes:X} bytes, exceeds 0x{HUFFMAN_TABLE_SIZE:X}"
        )

    out = bytearray()
    for node in nodes:
        assert node.left is not None and node.right is not None
        for child in (node.left, node.right):
            if child.leaf:
                assert child.symbol is not None
                value = child.symbol
            else:
                if child.index is None or child.index == 0:
                    raise RuntimeError("invalid internal Huffman child index")
                value = -child.index
            out += struct.pack("<h", value)

    out.extend(b"\x00" * (HUFFMAN_TABLE_SIZE - len(out)))
    return bytes(out)


def encode_huffman(decoded: bytes, codes: dict[int, tuple[int, int]]) -> bytes:
    if len(decoded) > 0xFF:
        raise RuntimeError(f"decoded record length {len(decoded)} exceeds 255 bytes")

    packed = bytearray()
    current = 0
    used = 0

    for symbol in decoded:
        try:
            bits, length = codes[symbol]
        except KeyError as exc:
            raise RuntimeError(f"missing Huffman code for byte 0x{symbol:02X}") from exc

        for shift in range(length - 1, -1, -1):
            current = (current << 1) | ((bits >> shift) & 1)
            used += 1
            if used == 8:
                packed.append(current)
                current = 0
                used = 0

    if used:
        packed.append(current << (8 - used))

    # Existing format: byte 0 = number of following bytes (decoded-length byte
    # plus packed data), byte 1 = decoded byte count.
    following = len(packed) + 1
    if following > 0xFF:
        raise RuntimeError(f"compressed record payload {following} exceeds 255 bytes")
    return bytes([following, len(decoded)]) + bytes(packed)


def table_child(table: bytes, node_index: int, bit: int) -> int:
    offset = node_index * 4 + bit * 2
    if offset + 2 > len(table):
        raise RuntimeError(f"Huffman node {node_index} is outside table")
    return struct.unpack_from("<h", table, offset)[0]


def decode_huffman_record(record: bytes, table: bytes) -> bytes:
    if len(record) < 2:
        raise RuntimeError("truncated Huffman record")
    following = record[0]
    decoded_length = record[1]
    if following + 1 != len(record):
        raise RuntimeError(
            f"Huffman record size mismatch: header={following + 1} actual={len(record)}"
        )

    out = bytearray()
    node = 0
    for byte in record[2:]:
        for shift in range(7, -1, -1):
            bit = (byte >> shift) & 1
            child = table_child(table, node, bit)
            if child < 0:
                node = -child
            else:
                if not 0 <= child <= 0xFF:
                    raise RuntimeError(f"invalid Huffman leaf {child}")
                out.append(child)
                node = 0
                if len(out) == decoded_length:
                    return bytes(out)
    raise RuntimeError(
        f"compressed record ended after {len(out)} decoded bytes; expected {decoded_length}"
    )


def build_header(records_and_blobs: list[tuple[int, bytes]]) -> tuple[bytes, list[HeaderEntry]]:
    entries: list[HeaderEntry] = []
    current_address = 0
    previous_record_address = 0
    previous_id = 0
    current_subindices = 0

    for message_id, blob in records_and_blobs:
        block_transition = (
            previous_record_address // BLOCK_SIZE != current_address // BLOCK_SIZE
        )
        write_new_index = block_transition or previous_id != message_id - 1

        if write_new_index:
            if entries:
                entries[-1].subindices = current_subindices
            entries.append(HeaderEntry(message_id=message_id, address=current_address))
            current_subindices = 0
        else:
            current_subindices += 1

        previous_id = message_id
        previous_record_address = current_address
        current_address += len(blob)

    if entries:
        entries[-1].subindices = current_subindices

    if current_address > DBS_ADDRESS_LIMIT:
        raise RuntimeError(
            f"MSGJ.DBS size 0x{current_address:X} exceeds 0x{DBS_ADDRESS_LIMIT:X}"
        )
    if len(entries) > 0xFFFF:
        raise RuntimeError("MSGJ.HDR has more than 65535 main indices")

    out = bytearray(struct.pack("<H", len(entries)))
    for entry in entries:
        if entry.subindices > 0xFF:
            raise RuntimeError(
                f"ID {entry.message_id}: {entry.subindices} subindices exceeds 255"
            )
        block = entry.address // BLOCK_SIZE
        offset = entry.address % BLOCK_SIZE
        if block > 0xFF:
            raise RuntimeError(
                f"ID {entry.message_id}: DBS block {block} exceeds one-byte field"
            )
        out += struct.pack("<HHBB", entry.message_id, offset, entry.subindices, block)

    return bytes(out), entries


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()

    records = parse_records(args.input.read_text(encoding="utf-8", errors="strict"))
    mapping, _ = build_mapping(records)

    decoded_records: list[tuple[int, bytes]] = []
    freq: collections.Counter[int] = collections.Counter()
    for rec in records:
        decoded = encode_text(rec.text, mapping)
        decoded_records.append((rec.message_id, decoded))
        freq.update(decoded)

    root = build_huffman_tree(freq)
    codes = build_codes(root)
    table = serialize_huffman_tree(root)

    blobs: list[tuple[int, bytes]] = []
    roundtrip_failures = 0
    max_decoded = (0, 0)
    max_blob = (0, 0)

    for message_id, decoded in decoded_records:
        blob = encode_huffman(decoded, codes)
        roundtrip = decode_huffman_record(blob, table)
        if roundtrip != decoded:
            roundtrip_failures += 1
            raise RuntimeError(f"ID {message_id}: Huffman roundtrip mismatch")
        blobs.append((message_id, blob))
        if len(decoded) > max_decoded[1]:
            max_decoded = (message_id, len(decoded))
        if len(blob) > max_blob[1]:
            max_blob = (message_id, len(blob))

    dbs = b"".join(blob for _, blob in blobs)
    hdr, entries = build_header(blobs)

    if len(dbs) > DBS_ADDRESS_LIMIT:
        raise RuntimeError(
            f"MSGJ.DBS size 0x{len(dbs):X} exceeds address limit 0x{DBS_ADDRESS_LIMIT:X}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "MISCJ.HDR": table,
        "MSGJ.HDR": hdr,
        "MSGJ.DBS": dbs,
    }
    for name, data in paths.items():
        (args.output_dir / name).write_bytes(data)

    internal_nodes = (len(freq) - 1) if freq else 0
    report_lines = [
        "Wizardry VII PSX Korean binary MSG build",
        "========================================",
        f"Source records          : {len(records)}",
        f"Hangul mapping entries  : {len(mapping)}",
        f"Huffman symbols         : {len(freq)}",
        f"Huffman internal nodes  : {internal_nodes}",
        f"MISCJ.HDR size          : {len(table)} (0x{len(table):X})",
        f"MSGJ.HDR entries        : {len(entries)}",
        f"MSGJ.HDR size           : {len(hdr)} (0x{len(hdr):X})",
        f"MSGJ.DBS size           : {len(dbs)} (0x{len(dbs):X})",
        f"DBS headroom            : {DBS_ADDRESS_LIMIT - len(dbs)}",
        f"Max decoded record      : ID {max_decoded[0]} / {max_decoded[1]} bytes",
        f"Max compressed record   : ID {max_blob[0]} / {max_blob[1]} bytes incl. header",
        f"Roundtrip failures      : {roundtrip_failures}",
        "",
    ]
    for name, data in paths.items():
        report_lines.append(f"{name}\tSHA256 {sha256(data)}")

    report_path = args.output_dir / "BUILD_REPORT.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")

    print(
        f"records={len(records)} symbols={len(freq)} hdr_entries={len(entries)} "
        f"dbs={len(dbs)} roundtrip_failures={roundtrip_failures}"
    )
    print(f"output: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
