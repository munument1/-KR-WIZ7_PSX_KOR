#!/usr/bin/env python3
"""Audit merged Wizardry VII PSX Korean MSG records using the verified native DBCS.

Unlike the older prototype bytecode estimator, every Hangul character here is
encoded as the renderer-native two-byte sequence from korean_dbcs.tsv. This is
the correct byte-length audit for the current font/codepage design.
"""
from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

RECORD_RE = re.compile(r"^(\d+)(\*)?\\(.*)$")
NORMALIZE = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",
    "\u00d7": "x",
}
MAX_DECODED_RECORD = 0xFF


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
        m = RECORD_RE.match(line)
        if m:
            flush()
            current_id = int(m.group(1))
            current = [m.group(3)]
        elif current_id is not None:
            current.append(line)
    flush()
    return records


def load_mapping(path: Path) -> dict[str, bytes]:
    mapping: dict[str, bytes] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            ch = row["char"]
            mapping[ch] = bytes([int(row["lead"], 16), int(row["trail"], 16)])
    return mapping


def normalized_chars(text: str):
    for ch in text:
        replacement = NORMALIZE.get(ch)
        if replacement is None:
            yield ch
        else:
            yield from replacement


def encode_native(text: str, mapping: dict[str, bytes]) -> bytes:
    out = bytearray()
    for ch in normalized_chars(text):
        cp = ord(ch)
        if cp <= 0x7F:
            out.append(cp)
        elif ch in mapping:
            out.extend(mapping[ch])
        else:
            raise ValueError(
                f"unsupported/unmapped character U+{cp:04X} {ch!r} "
                f"({unicodedata.name(ch, '<unnamed>')})"
            )
    return bytes(out)


def audit(records: list[Record], mapping: dict[str, bytes]):
    rows = []
    for rec in records:
        encoded = encode_native(rec.text, mapping)
        hangul = sum(1 for ch in rec.text if ch in mapping)
        rows.append({
            "message_id": rec.message_id,
            "unicode_chars": len(rec.text),
            "hangul_chars": hangul,
            "native_bytes": len(encoded),
            "overflow_bytes": max(0, len(encoded) - MAX_DECODED_RECORD),
        })
    return rows


def write_report(path: Path, rows: list[dict], mapping_size: int) -> None:
    over = [row for row in rows if row["overflow_bytes"]]
    largest = sorted(rows, key=lambda row: (row["native_bytes"], row["message_id"]), reverse=True)
    total_bytes = sum(row["native_bytes"] for row in rows)
    max_row = largest[0] if largest else None
    lines = [
        "Wizardry VII PSX native Korean MSG byte-limit audit",
        "===================================================",
        f"Records                     : {len(rows)}",
        f"Native Hangul mappings      : {mapping_size}",
        f"Total decoded bytes         : {total_bytes}",
        f"Decoded record limit        : {MAX_DECODED_RECORD}",
        f"Records over 255 bytes      : {len(over)}",
        f"Maximum decoded record      : {max_row['native_bytes'] if max_row else 0} bytes"
        + (f" (ID {max_row['message_id']})" if max_row else ""),
        "",
        "[20 LARGEST RECORDS]",
        "ID\tbytes\toverflow\tunicode_chars\thangul_chars",
    ]
    for row in largest[:20]:
        lines.append(
            f"{row['message_id']}\t{row['native_bytes']}\t{row['overflow_bytes']}\t"
            f"{row['unicode_chars']}\t{row['hangul_chars']}"
        )
    if over:
        lines += ["", "[ALL OVERFLOW RECORDS]", "ID\tbytes\toverflow"]
        for row in sorted(over, key=lambda row: row["message_id"]):
            lines.append(
                f"{row['message_id']}\t{row['native_bytes']}\t{row['overflow_bytes']}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_tsv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["message_id", "unicode_chars", "hangul_chars", "native_bytes", "overflow_bytes"],
            delimiter="\t",
        )
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    p = argparse.ArgumentParser(description="Audit WIZ7 PSX merged Korean MSG with native 2-byte Hangul codes")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--mapping", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--tsv", type=Path)
    p.add_argument("--fail-on-overflow", action="store_true")
    args = p.parse_args()
    try:
        records = parse_records(args.input.read_text(encoding="utf-8", errors="strict"))
        mapping = load_mapping(args.mapping)
        rows = audit(records, mapping)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_report(args.output, rows, len(mapping))
        if args.tsv:
            args.tsv.parent.mkdir(parents=True, exist_ok=True)
            write_tsv(args.tsv, rows)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    overflow_count = sum(1 for row in rows if row["overflow_bytes"])
    max_bytes = max((row["native_bytes"] for row in rows), default=0)
    print(f"records={len(rows)} overflow={overflow_count} max_native_bytes={max_bytes}")
    print(f"report: {args.output}")
    if args.fail_on_overflow and overflow_count:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
