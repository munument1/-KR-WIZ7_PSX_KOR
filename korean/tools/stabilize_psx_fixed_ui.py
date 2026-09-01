#!/usr/bin/env python3
"""Stabilize PSX character-sheet UI messages on the English-patch base.

Some Wizardry VII PSX character/status screens use fixed-width 1-byte draw paths.
Native Korean DBCS is not safe there yet. This tool replaces only those proven
fixed-width message IDs with the Gertius PSX English-patch bytes, rebuilds the
Huffman container, and optionally pads MSGJ.HDR/MSGJ.DBS back to the exact English
file sizes so every following file keeps the English patch's LBA.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import heapq
import struct
from dataclasses import dataclass
from pathlib import Path

TABLE_SIZE = 0x400
BLOCK_SIZE = 0x400
DBS_ADDRESS_LIMIT = 0x3FFFF
DEFAULT_FIXED_UI_RANGES = (
    (100, 110),
    (120, 134),
    (140, 141),
    (160, 162),
    (200, 219),
    (800, 937),
)


@dataclass
class Node:
    weight: int
    min_symbol: int
    symbol: int | None = None
    left: "Node | None" = None
    right: "Node | None" = None
    index: int | None = None

    @property
    def leaf(self) -> bool:
        return self.symbol is not None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_container(root: Path) -> tuple[bytes, bytes, bytes]:
    return (
        (root / "MISCJ.HDR").read_bytes(),
        (root / "MSGJ.HDR").read_bytes(),
        (root / "MSGJ.DBS").read_bytes(),
    )


def table_child(table: bytes, node: int, bit: int) -> int:
    off = node * 4 + bit * 2
    if off + 2 > len(table):
        raise RuntimeError(f"Huffman node outside table: {node}")
    return struct.unpack_from("<h", table, off)[0]


def decode_record(dbs: bytes, table: bytes, pos: int) -> tuple[bytes, int]:
    if pos >= len(dbs):
        raise RuntimeError(f"record offset outside DBS: 0x{pos:X}")
    size = dbs[pos] + 1
    rec = dbs[pos : pos + size]
    if len(rec) != size or len(rec) < 2:
        raise RuntimeError(f"truncated record at 0x{pos:X}")
    decoded_len = rec[1]
    if decoded_len == 0:
        return b"", size
    out = bytearray()
    node = 0
    for byte in rec[2:]:
        for shift in range(7, -1, -1):
            child = table_child(table, node, (byte >> shift) & 1)
            if child < 0:
                node = -child
            else:
                out.append(child & 0xFF)
                node = 0
                if len(out) == decoded_len:
                    return bytes(out), size
    raise RuntimeError(
        f"record at 0x{pos:X} ended after {len(out)} bytes; expected {decoded_len}"
    )


def load_records(root: Path) -> list[tuple[int, bytes]]:
    table, hdr, dbs = read_container(root)
    count = struct.unpack_from("<H", hdr, 0)[0]
    records: list[tuple[int, bytes]] = []
    for i in range(count):
        mid, off, subs, block = struct.unpack_from("<HHBB", hdr, 2 + i * 6)
        pos = block * BLOCK_SIZE + off
        for sub in range(subs + 1):
            decoded, rec_size = decode_record(dbs, table, pos)
            records.append((mid + sub, decoded))
            pos += rec_size
    return records


def make_record_getter(root: Path):
    table, hdr, dbs = read_container(root)
    count = struct.unpack_from("<H", hdr, 0)[0]
    entries = [struct.unpack_from("<HHBB", hdr, 2 + i * 6) for i in range(count)]

    def get(mid: int) -> bytes | None:
        for base_mid, off, subs, block in entries:
            if not (base_mid <= mid <= base_mid + subs):
                continue
            pos = block * BLOCK_SIZE + off
            for _ in range(mid - base_mid):
                if pos >= len(dbs):
                    return None
                pos += dbs[pos] + 1
            if pos >= len(dbs):
                return None
            try:
                decoded, _ = decode_record(dbs, table, pos)
            except RuntimeError:
                return None
            return decoded
        return None

    return get


def build_tree(freq: collections.Counter[int]) -> Node:
    if len(freq) < 2:
        raise RuntimeError("at least two Huffman symbols are required")
    heap: list[tuple[int, int, int, Node]] = []
    serial = 0
    for sym, weight in sorted(freq.items()):
        node = Node(weight, sym, symbol=sym)
        heapq.heappush(heap, (weight, sym, serial, node))
        serial += 1
    while len(heap) > 1:
        _, _, _, left = heapq.heappop(heap)
        _, _, _, right = heapq.heappop(heap)
        node = Node(left.weight + right.weight, min(left.min_symbol, right.min_symbol), left=left, right=right)
        heapq.heappush(heap, (node.weight, node.min_symbol, serial, node))
        serial += 1
    return heap[0][3]


def assign_indices(root: Node) -> list[Node]:
    nodes: list[Node] = []
    def walk(node: Node) -> None:
        if node.leaf:
            return
        node.index = len(nodes)
        nodes.append(node)
        assert node.left is not None and node.right is not None
        walk(node.left)
        walk(node.right)
    walk(root)
    return nodes


def serialize_tree(root: Node) -> bytes:
    nodes = assign_indices(root)
    if len(nodes) * 4 > TABLE_SIZE:
        raise RuntimeError(f"Huffman tree too large: {len(nodes)} internal nodes")
    out = bytearray()
    for node in nodes:
        assert node.left is not None and node.right is not None
        for child in (node.left, node.right):
            value = child.symbol if child.leaf else -child.index
            out += struct.pack("<h", value)
    out += b"\0" * (TABLE_SIZE - len(out))
    return bytes(out)


def build_codes(root: Node) -> dict[int, tuple[int, int]]:
    codes: dict[int, tuple[int, int]] = {}
    def walk(node: Node, bits: int = 0, length: int = 0) -> None:
        if node.leaf:
            assert node.symbol is not None
            codes[node.symbol] = (bits, max(1, length))
            return
        assert node.left is not None and node.right is not None
        walk(node.left, bits << 1, length + 1)
        walk(node.right, (bits << 1) | 1, length + 1)
    walk(root)
    return codes


def encode_record(data: bytes, codes: dict[int, tuple[int, int]], mid: int) -> bytes:
    if len(data) > 0xFF:
        raise RuntimeError(f"ID {mid}: decoded record exceeds 255 bytes")
    packed = bytearray()
    current = 0
    used = 0
    for sym in data:
        bits, length = codes[sym]
        for shift in range(length - 1, -1, -1):
            current = (current << 1) | ((bits >> shift) & 1)
            used += 1
            if used == 8:
                packed.append(current)
                current = 0
                used = 0
    if used:
        packed.append(current << (8 - used))
    following = len(packed) + 1
    if following > 0xFF:
        raise RuntimeError(f"ID {mid}: compressed record exceeds 255 bytes")
    return bytes((following, len(data))) + bytes(packed)


def build_header(blobs: list[tuple[int, bytes]]) -> bytes:
    entries: list[list[int]] = []
    current = 0
    previous_record_address = 0
    previous_id = 0
    subindices = 0
    for mid, blob in blobs:
        block_transition = previous_record_address // BLOCK_SIZE != current // BLOCK_SIZE
        new_index = block_transition or previous_id != mid - 1
        if new_index:
            if entries:
                entries[-1][2] = subindices
            entries.append([mid, current, 0])
            subindices = 0
        else:
            subindices += 1
        previous_id = mid
        previous_record_address = current
        current += len(blob)
    if entries:
        entries[-1][2] = subindices
    if current > DBS_ADDRESS_LIMIT:
        raise RuntimeError(f"MSGJ.DBS exceeds address space: 0x{current:X}")
    out = bytearray(struct.pack("<H", len(entries)))
    for mid, addr, subs in entries:
        if subs > 0xFF or addr // BLOCK_SIZE > 0xFF:
            raise RuntimeError(f"ID {mid}: header field overflow")
        out += struct.pack("<HHBB", mid, addr % BLOCK_SIZE, subs, addr // BLOCK_SIZE)
    return bytes(out)


def fixed_ids() -> set[int]:
    ids: set[int] = set()
    for first, last in DEFAULT_FIXED_UI_RANGES:
        ids.update(range(first, last + 1))
    return ids


def stabilize(korean_dir: Path, english_dir: Path, output_dir: Path, *, preserve_english_layout: bool = True) -> dict[str, object]:
    korean = load_records(korean_dir)
    get_english = make_record_getter(english_dir)
    fixed = fixed_ids()
    replaced: list[int] = []
    records: list[tuple[int, bytes]] = []
    for mid, data in korean:
        if mid in fixed:
            eng = get_english(mid)
            if eng is not None and data != eng:
                data = eng
                replaced.append(mid)
        records.append((mid, data))

    freq: collections.Counter[int] = collections.Counter()
    for _, data in records:
        freq.update(data)
    root = build_tree(freq)
    codes = build_codes(root)
    table = serialize_tree(root)
    blobs = [(mid, encode_record(data, codes, mid)) for mid, data in records]

    for (mid, original), (_, blob) in zip(records, blobs):
        decoded, _ = decode_record(blob, table, 0)
        if decoded != original:
            raise RuntimeError(f"ID {mid}: Huffman roundtrip mismatch")

    hdr = build_header(blobs)
    dbs = b"".join(blob for _, blob in blobs)
    raw_hdr_size = len(hdr)
    raw_dbs_size = len(dbs)

    if preserve_english_layout:
        target_hdr = (english_dir / "MSGJ.HDR").stat().st_size
        target_dbs = (english_dir / "MSGJ.DBS").stat().st_size
        if len(hdr) > target_hdr or len(dbs) > target_dbs:
            raise RuntimeError(
                "Korean MSG container no longer fits English layout: "
                f"HDR {len(hdr)}/{target_hdr}, DBS {len(dbs)}/{target_dbs}"
            )
        hdr += b"\0" * (target_hdr - len(hdr))
        dbs += b"\0" * (target_dbs - len(dbs))

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {"MISCJ.HDR": table, "MSGJ.HDR": hdr, "MSGJ.DBS": dbs}
    for name, data in outputs.items():
        (output_dir / name).write_bytes(data)

    report = {
        "fixed_ui_replacements": replaced,
        "raw_hdr_size": raw_hdr_size,
        "raw_dbs_size": raw_dbs_size,
        "final_hdr_size": len(hdr),
        "final_dbs_size": len(dbs),
        "hashes": {name: sha256(data) for name, data in outputs.items()},
    }
    lines = [
        "Wizardry VII PSX fixed-width UI stabilization",
        "==============================================",
        f"Replaced fixed-width IDs : {len(replaced)}",
        f"Raw MSGJ.HDR size        : {raw_hdr_size}",
        f"Raw MSGJ.DBS size        : {raw_dbs_size}",
        f"Final MSGJ.HDR size      : {len(hdr)}",
        f"Final MSGJ.DBS size      : {len(dbs)}",
        f"English layout preserved : {preserve_english_layout}",
        "",
        "Replaced IDs:",
        " ".join(map(str, replaced)),
        "",
    ]
    for name, digest in report["hashes"].items():
        lines.append(f"{name}\tSHA256 {digest}")
    (output_dir / "FIXED_UI_REPORT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--korean-dir", type=Path, required=True)
    parser.add_argument("--english-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--no-preserve-english-layout", action="store_true")
    args = parser.parse_args()
    report = stabilize(args.korean_dir, args.english_dir, args.output_dir, preserve_english_layout=not args.no_preserve_english_layout)
    print(f"fixed_ui_replacements={len(report['fixed_ui_replacements'])} hdr={report['final_hdr_size']} dbs={report['final_dbs_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
