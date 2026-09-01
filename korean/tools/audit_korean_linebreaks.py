#!/usr/bin/env python3
"""Simulate the injected PSX Korean line-wrap routine over merged MSG text.

This checks the actual native two-byte mapping and the 16-visible-glyph rule.
T'Rang Korean speech uses hyphens as word separators; the patched EXE accepts a
hyphen as a break candidate only after native DBCS has been observed, matching
`Assembler Injects/KoreanLineBreak16char.c`.

Slash-separated command/topic tables are reported but are not treated as normal
story text. Any native-Korean record that still exceeds 16 visible glyphs and is
not slash-token data is a blocking failure.
"""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

RECORD_RE = re.compile(r"^(\d+)(\*)?\\(.*)$")
SPECIAL = {ord(c) for c in "!%&]@#|"}
NORMALIZE = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",
    "\u00d7": "x",
}


@dataclass(frozen=True)
class Record:
    message_id: int
    text: str


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
        match = RECORD_RE.match(line)
        if match:
            flush()
            current_id = int(match.group(1))
            current = [match.group(3)]
        elif current_id is not None:
            current.append(line)
    flush()
    return records


def load_mapping(path: Path) -> dict[str, bytes]:
    mapping: dict[str, bytes] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            code = row["code_hex"].upper().replace("0X", "").replace(" ", "")
            mapping[row["char"]] = bytes.fromhex(code)
    return mapping


def encode_native(text: str, mapping: dict[str, bytes]) -> bytes:
    out = bytearray()
    for ch in text:
        replacement = NORMALIZE.get(ch, ch)
        for normalized in replacement:
            cp = ord(normalized)
            if cp <= 0x7F:
                out.append(cp)
            elif normalized in mapping:
                out.extend(mapping[normalized])
            else:
                raise ValueError(
                    f"unmapped non-ASCII {normalized!r} U+{cp:04X}"
                )
    return bytes(out)


def glyph_length(data: bytes) -> int:
    pos = 0
    glyphs = 0
    while pos < len(data):
        byte = data[pos]
        if 0x80 <= byte <= 0x8F and pos + 1 < len(data):
            pos += 2
        else:
            pos += 1
        glyphs += 1
    return glyphs


def find_break(data: bytes) -> int:
    """Python model of KoreanLineBreak16char.c; returns a byte offset or -1."""
    byte_pos = 0
    glyph_pos = 0
    previous = 0
    seen_dbcs = False

    while True:
        current = data[byte_pos] if byte_pos < len(data) else 0
        if current == 0:
            next_byte = (
                data[previous + 1]
                if previous and previous + 1 < len(data)
                else 0
            )
            if previous and (next_byte in SPECIAL or glyph_pos > 15):
                return previous
            return -1

        if current == 0x20 or (seen_dbcs and current == 0x2D):
            if glyph_pos > 15:
                return previous
            previous = byte_pos

        if (
            0x80 <= current <= 0x8F
            and byte_pos + 1 < len(data)
            and data[byte_pos + 1] != 0
        ):
            seen_dbcs = True
            byte_pos += 2
        else:
            byte_pos += 1
        glyph_pos += 1


def split_wrapped(data: bytes) -> list[bytes]:
    lines: list[bytes] = []
    current = data
    for _ in range(256):
        offset = find_break(current)
        if offset < 0:
            lines.append(current)
            return lines
        lines.append(current[:offset])
        current = current[offset + 1 :]
    raise RuntimeError("line split did not converge")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Korean PSX 16-glyph wrapping")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records = parse_records(args.input.read_text(encoding="utf-8"))
    mapping = load_mapping(args.mapping)
    oversized: list[tuple[int, int, str]] = []
    blocking: list[tuple[int, int, str]] = []
    hyphen_break_records = 0

    for record in records:
        data = encode_native(record.text, mapping)
        lines = split_wrapped(data)
        if b"-" in data and len(lines) > 1:
            hyphen_break_records += 1
        maximum = max((glyph_length(line) for line in lines), default=0)
        if maximum > 16:
            oversized.append((record.message_id, maximum, record.text))
            if any(0x80 <= byte <= 0x8F for byte in data) and b"/" not in data:
                blocking.append((record.message_id, maximum, record.text))

    report = [
        "Wizardry VII PSX Korean line-wrap audit",
        "========================================",
        f"Records: {len(records)}",
        f"Oversized after simulated wrapping: {len(oversized)}",
        f"Blocking Korean/story records: {len(blocking)}",
        f"Records using a hyphen break: {hyphen_break_records}",
        "",
    ]
    if oversized:
        report.append("[OVERSIZED / LIKELY MENU OR SCRIPT TOKENS]")
        for message_id, maximum, text in oversized:
            report.append(f"ID {message_id}\t{maximum} glyphs\t{text!r}")
    if blocking:
        report += ["", "[BLOCKING KOREAN/STORY RECORDS]"]
        for message_id, maximum, text in blocking:
            report.append(f"ID {message_id}\t{maximum} glyphs\t{text!r}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:6]))
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
