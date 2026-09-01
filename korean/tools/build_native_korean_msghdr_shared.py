#!/usr/bin/env python3
"""Build native Korean MSGJ using a codepage shared with optional PSX assets.

The base MSGJ builder originally allocated its codepage only from MSG text. This
wrapper extends the inventory with arbitrary UTF-8 text/TSV assets (for example
SCENARIJ.DBS item/monster translation tables), then runs the same Huffman and
header logic. The output mapping can therefore be reused verbatim by FONT.MMT
and fixed-field scenario patchers.
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

import build_native_korean_msghdr_binary as base
from native_psx_codepage import (
    allocate_native_mapping,
    collect_inventory,
    collect_text_inventory,
    encode_text,
    write_mapping_tsv,
)


def build(
    input_path: Path,
    output_dir: Path,
    map_path: Path,
    extra_charset: list[Path],
) -> None:
    records = base.parse_records(input_path.read_text(encoding="utf-8", errors="strict"))

    hangul_freq = collect_inventory(records)
    extra_freq = collect_text_inventory(extra_charset)
    hangul_freq.update(extra_freq)
    native_mapping = allocate_native_mapping(hangul_freq)
    byte_mapping = {ch: m.encoded for ch, m in native_mapping.items()}
    write_mapping_tsv(map_path, native_mapping, hangul_freq)

    decoded_records: list[tuple[int, bytes]] = []
    freq: collections.Counter[int] = collections.Counter()
    overflow_rows: list[tuple[int, int]] = []
    max_decoded = (0, 0)

    for rec in records:
        decoded = encode_text(rec.text, byte_mapping)
        decoded_records.append((rec.message_id, decoded))
        freq.update(decoded)
        if len(decoded) > base.MAX_DECODED_RECORD:
            overflow_rows.append((rec.message_id, len(decoded)))
        if len(decoded) > max_decoded[1]:
            max_decoded = (rec.message_id, len(decoded))

    if overflow_rows:
        preview = ", ".join(f"ID {mid}={size}" for mid, size in overflow_rows[:20])
        raise RuntimeError(
            f"{len(overflow_rows)} native decoded record(s) exceed 255 bytes; {preview}"
        )

    root = base.build_huffman_tree(freq)
    codes = base.build_codes(root)
    table = base.serialize_huffman_tree(root)

    blobs: list[tuple[int, bytes]] = []
    roundtrip_failures = 0
    max_blob = (0, 0)
    for message_id, decoded in decoded_records:
        blob = base.encode_huffman(decoded, codes, message_id)
        if base.decode_huffman_record(blob, table) != decoded:
            roundtrip_failures += 1
            raise RuntimeError(f"ID {message_id}: Huffman roundtrip mismatch")
        blobs.append((message_id, blob))
        if len(blob) > max_blob[1]:
            max_blob = (message_id, len(blob))

    dbs = b"".join(blob for _, blob in blobs)
    hdr, entries = base.build_header(blobs)
    if len(dbs) > base.DBS_ADDRESS_LIMIT:
        raise RuntimeError(
            f"MSGJ.DBS size 0x{len(dbs):X} exceeds address limit 0x{base.DBS_ADDRESS_LIMIT:X}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {"MISCJ.HDR": table, "MSGJ.HDR": hdr, "MSGJ.DBS": dbs}
    for name, data in outputs.items():
        (output_dir / name).write_bytes(data)

    msg_only = collect_inventory(records)
    extra_only_chars = sorted(set(extra_freq) - set(msg_only))
    report_lines = [
        "Wizardry VII PSX shared-codepage Korean MSG build",
        "================================================",
        f"Source records          : {len(records)}",
        f"MSG Hangul              : {len(msg_only)}",
        f"Extra asset Hangul      : {len(extra_freq)}",
        f"Extra-only Hangul       : {len(extra_only_chars)}",
        f"Native Hangul mappings  : {len(native_mapping)}",
        f"Korean slot range used  : {min((m.slot for m in native_mapping.values()), default=0)}.."
        f"{max((m.slot for m in native_mapping.values()), default=0)}",
        f"Huffman symbols         : {len(freq)}",
        f"MISCJ.HDR size          : {len(table)} (0x{len(table):X})",
        f"MSGJ.HDR entries        : {len(entries)}",
        f"MSGJ.HDR size           : {len(hdr)} (0x{len(hdr):X})",
        f"MSGJ.DBS size           : {len(dbs)} (0x{len(dbs):X})",
        f"DBS headroom            : {base.DBS_ADDRESS_LIMIT - len(dbs)}",
        f"Max native record       : ID {max_decoded[0]} / {max_decoded[1]} bytes",
        f"Max compressed record   : ID {max_blob[0]} / {max_blob[1]} bytes incl. header",
        f"Roundtrip failures      : {roundtrip_failures}",
        "",
    ]
    if extra_only_chars:
        report_lines.append("Extra-only characters: " + "".join(extra_only_chars))
        report_lines.append("")
    for name, data in outputs.items():
        report_lines.append(f"{name}\tSHA256 {base.sha256(data)}")

    report_path = output_dir / "BUILD_REPORT.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")

    print(
        f"records={len(records)} msg_hangul={len(msg_only)} extra_hangul={len(extra_freq)} "
        f"native_hangul={len(native_mapping)} dbs={len(dbs)}"
    )
    print(f"mapping: {map_path}")
    print(f"output: {output_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build WIZ7 PSX MSGJ with a codepage shared across Korean assets"
    )
    parser.add_argument("--input", type=Path, default=base.DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=base.DEFAULT_DIR)
    parser.add_argument("--map", type=Path, default=base.DEFAULT_MAP)
    parser.add_argument(
        "--extra-charset",
        type=Path,
        action="append",
        default=[],
        help="UTF-8 text/TSV asset whose Hangul must share the native codepage; repeatable",
    )
    args = parser.parse_args()
    build(args.input, args.output_dir, args.map, args.extra_charset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
