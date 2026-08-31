#!/usr/bin/env python3
"""Prototype a PSX-friendly Korean bytecode and estimate Huffman/DBS sizes.

Bytecode proposal v1
--------------------
- 0x00..0x7F: existing ASCII/control bytes are preserved verbatim.
- 0xC0..0xC7: eight two-byte Hangul lead codes.
- The remaining 120 bytes in 0x80..0xFF are direct tokens for the 120 most
  frequent Hangul syllables.
- Other Hangul syllables use [lead 0xC0..0xC7][trail 0x80..0xFF], providing
  1024 extended slots.

The mapping is deterministic for a given corpus. This script does not patch the
renderer yet; it proves whether the byte budget and one-byte decoded-length
field are viable before assembly work begins.
"""

from __future__ import annotations

import argparse
import collections
import heapq
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_INPUT = Path("korean/build/MSGHDR_indexText.ko.merged.txt")
DEFAULT_REPORT = Path("korean/build/MSGHDR_bytecode_plan.txt")
DEFAULT_MAP = Path("korean/build/MSGHDR_hangul_map.tsv")
RECORD_RE = re.compile(r"^(\d+)(\*)?\\(.*)$")

LEADS = tuple(range(0xC0, 0xC8))
DIRECT_BYTES = tuple(b for b in range(0x80, 0x100) if b not in LEADS)
TRAIL_BYTES = tuple(range(0x80, 0x100))

NORMALIZE = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",
}


@dataclass
class Record:
    message_id: int
    text: str


def is_hangul(ch: str) -> bool:
    return "\uac00" <= ch <= "\ud7a3"


def parse_records(raw: str) -> list[Record]:
    records: list[Record] = []
    current_id: int | None = None
    current: list[str] = []

    def flush() -> None:
        nonlocal current_id, current
        if current_id is not None:
            records.append(Record(current_id, "\n".join(current)))
        current_id = None
        current = []

    for line in raw.splitlines():
        m = RECORD_RE.match(line)
        if m:
            flush()
            current_id = int(m.group(1))
            current = [m.group(3)]
        elif current_id is not None:
            current.append(line)
    flush()
    return records


def normalized_chars(text: str) -> list[str]:
    out: list[str] = []
    for ch in text:
        replacement = NORMALIZE.get(ch)
        if replacement is None:
            out.append(ch)
        else:
            out.extend(replacement)
    return out


def build_mapping(records: list[Record]) -> tuple[dict[str, bytes], collections.Counter[str]]:
    freq: collections.Counter[str] = collections.Counter()
    for rec in records:
        freq.update(ch for ch in normalized_chars(rec.text) if is_hangul(ch))

    ordered = sorted(freq, key=lambda ch: (-freq[ch], ord(ch)))
    if len(ordered) > len(DIRECT_BYTES) + len(LEADS) * len(TRAIL_BYTES):
        raise RuntimeError(
            f"Hangul inventory {len(ordered)} exceeds bytecode capacity "
            f"{len(DIRECT_BYTES) + len(LEADS) * len(TRAIL_BYTES)}"
        )

    mapping: dict[str, bytes] = {}
    for ch, byte in zip(ordered[: len(DIRECT_BYTES)], DIRECT_BYTES):
        mapping[ch] = bytes([byte])

    extended = ordered[len(DIRECT_BYTES) :]
    for i, ch in enumerate(extended):
        lead = LEADS[i // len(TRAIL_BYTES)]
        trail = TRAIL_BYTES[i % len(TRAIL_BYTES)]
        mapping[ch] = bytes([lead, trail])

    return mapping, freq


def encode_text(text: str, mapping: dict[str, bytes]) -> bytes:
    out = bytearray()
    for ch in normalized_chars(text):
        cp = ord(ch)
        if cp <= 0x7F:
            out.append(cp)
        elif is_hangul(ch):
            out.extend(mapping[ch])
        else:
            raise RuntimeError(
                f"unsupported non-ASCII character U+{cp:04X} {ch!r} "
                f"({unicodedata.name(ch, '<unnamed>')})"
            )
    return bytes(out)


def huffman_code_lengths(freq: collections.Counter[int]) -> dict[int, int]:
    """Return optimal binary Huffman code lengths for the used byte symbols."""
    heap: list[tuple[int, int, tuple[int, ...]]] = []
    serial = 0
    for symbol, weight in sorted(freq.items()):
        heapq.heappush(heap, (weight, serial, (symbol,)))
        serial += 1

    if not heap:
        return {}
    if len(heap) == 1:
        return {heap[0][2][0]: 1}

    lengths: collections.Counter[int] = collections.Counter()
    while len(heap) > 1:
        w1, _, s1 = heapq.heappop(heap)
        w2, _, s2 = heapq.heappop(heap)
        merged = s1 + s2
        for symbol in merged:
            lengths[symbol] += 1
        heapq.heappush(heap, (w1 + w2, serial, merged))
        serial += 1
    return dict(lengths)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    args = parser.parse_args()

    records = parse_records(args.input.read_text(encoding="utf-8", errors="strict"))
    mapping, hangul_freq = build_mapping(records)

    encoded: list[tuple[Record, bytes]] = []
    byte_freq: collections.Counter[int] = collections.Counter()
    for rec in records:
        data = encode_text(rec.text, mapping)
        encoded.append((rec, data))
        byte_freq.update(data)

    code_lengths = huffman_code_lengths(byte_freq)

    raw_total = 0
    dbs_total = 0
    decoded_overflows: list[tuple[int, int]] = []
    compressed_overflows: list[tuple[int, int]] = []
    largest_decoded: list[tuple[int, int]] = []
    largest_compressed: list[tuple[int, int]] = []

    for rec, data in encoded:
        raw_len = len(data)
        bits = sum(code_lengths[b] for b in data)
        packed_len = math.ceil(bits / 8)
        dbs_record_len = packed_len + 2  # packed-size byte + decoded-size byte
        raw_total += raw_len
        dbs_total += dbs_record_len
        largest_decoded.append((raw_len, rec.message_id))
        largest_compressed.append((dbs_record_len, rec.message_id))
        if raw_len > 0xFF:
            decoded_overflows.append((rec.message_id, raw_len))
        if packed_len > 0xFE:
            compressed_overflows.append((rec.message_id, packed_len))

    direct_chars = sum(1 for value in mapping.values() if len(value) == 1)
    extended_chars = len(mapping) - direct_chars
    used_symbols = len(byte_freq)
    tree_bytes = max(0, (2 * used_symbols - 2) * 2)

    report = [
        "Wizardry VII PSX Korean bytecode/Huffman feasibility",
        "====================================================",
        f"Records                         : {len(records)}",
        f"Hangul syllables                : {len(mapping)}",
        f"Direct Hangul tokens            : {direct_chars}",
        f"Two-byte Hangul tokens          : {extended_chars}",
        f"Used decoded byte symbols       : {used_symbols} / 256",
        f"Estimated Huffman tree bytes    : {tree_bytes} (0x{tree_bytes:X})",
        f"Raw bytecode bytes              : {raw_total}",
        f"Estimated MSGJ.DBS bytes        : {dbs_total} (0x{dbs_total:X})",
        f"MSGJ.DBS address limit          : {0x3FFFF} (0x3FFFF)",
        f"DBS headroom                     : {0x3FFFF - dbs_total}",
        f"Decoded records >255 bytes      : {len(decoded_overflows)}",
        f"Compressed payloads >254 bytes  : {len(compressed_overflows)}",
        "",
        "[LARGEST DECODED RECORDS]",
    ]
    for size, message_id in sorted(largest_decoded, reverse=True)[:20]:
        report.append(f"ID {message_id:5d}\t{size:4d} bytes")

    report += ["", "[LARGEST COMPRESSED RECORDS]"]
    for size, message_id in sorted(largest_compressed, reverse=True)[:20]:
        report.append(f"ID {message_id:5d}\t{size:4d} DBS bytes")

    if decoded_overflows:
        report += ["", "[DECODED LENGTH OVERFLOW]"]
        for message_id, size in decoded_overflows:
            report.append(f"ID {message_id}\t{size}")

    if compressed_overflows:
        report += ["", "[COMPRESSED LENGTH OVERFLOW]"]
        for message_id, size in compressed_overflows:
            report.append(f"ID {message_id}\t{size}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")

    map_lines = ["unicode\tchar\tcount\tencoding"]
    ordered_map = sorted(mapping, key=lambda ch: (len(mapping[ch]), mapping[ch], ord(ch)))
    for ch in ordered_map:
        encoded_hex = " ".join(f"{b:02X}" for b in mapping[ch])
        map_lines.append(f"U+{ord(ch):04X}\t{ch}\t{hangul_freq[ch]}\t{encoded_hex}")
    args.map.write_text("\n".join(map_lines) + "\n", encoding="utf-8", newline="\n")

    print(
        f"hangul={len(mapping)} direct={direct_chars} extended={extended_chars} "
        f"dbs_est={dbs_total} decoded_overflow={len(decoded_overflows)} "
        f"compressed_overflow={len(compressed_overflows)}"
    )
    print(f"report: {args.report}")
    print(f"map: {args.map}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
