#!/usr/bin/env python3
"""Apply generated Wizardry VII PSX Korean glyph assets to an original FONT.MMT.

The GitHub Actions artifact intentionally contains no copyrighted game data.
This tool combines that artifact locally with the user's extracted FONT.MMT.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import build_korean_font as kf
import font_mmt

ROWS_PER_GLYPH = 11
BYTES_PER_ROW = 2
BYTES_PER_GLYPH = ROWS_PER_GLYPH * BYTES_PER_ROW


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_assets(asset_dir: Path):
    map_path = asset_dir / "korean_dbcs.tsv"
    glyph_path = asset_dir / "korean_glyphs.bin"
    info_path = asset_dir / "build_info.json"
    if not map_path.is_file() or not glyph_path.is_file():
        raise ValueError("asset directory must contain korean_dbcs.tsv and korean_glyphs.bin")

    with map_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    raw = glyph_path.read_bytes()
    if len(raw) != len(rows) * BYTES_PER_GLYPH:
        raise ValueError(
            f"glyph stream size mismatch: {len(raw)} bytes for {len(rows)} mappings "
            f"(expected {len(rows) * BYTES_PER_GLYPH})"
        )

    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.is_file() else {}
    result = []
    seen_slots: set[int] = set()
    for i, row in enumerate(rows):
        lead = int(row["lead"], 16)
        trail = int(row["trail"], 16)
        slot = int(row["slot"])
        calculated = kf.native_code_to_slot(lead, trail)
        if calculated != slot:
            raise ValueError(
                f"mapping mismatch for {row['char']!r}: {lead:02X}{trail:02X} -> "
                f"slot {calculated}, TSV says {slot}"
            )
        if slot in seen_slots:
            raise ValueError(f"duplicate FONT.MMT slot in mapping: {slot}")
        seen_slots.add(slot)
        chunk = raw[i * BYTES_PER_GLYPH:(i + 1) * BYTES_PER_GLYPH]
        bitmap = tuple(
            int.from_bytes(chunk[j:j + 2], "big")
            for j in range(0, BYTES_PER_GLYPH, 2)
        )
        result.append((row["char"], slot, bitmap))

    reserve_low = info.get("reserve_low_through")
    if reserve_low is not None:
        bad = [slot for _, slot, _ in result if slot <= int(reserve_low)]
        if bad:
            raise ValueError(
                f"artifact uses slot {min(bad)} inside reserved range 0..{reserve_low}"
            )
    return result, info


def apply_assets(
    original_font: Path,
    asset_dir: Path,
    output_font: Path,
    *,
    x_offset: int = 2,
    y_offset: int = 0,
    verify: bool = True,
) -> dict:
    entries, info = load_assets(asset_dir)
    original = original_font.read_bytes()
    font_mmt.validate_font(original)
    data = original

    targets: set[int] = set()
    for _, slot, rows11 in entries:
        targets.add(slot)
        data = font_mmt.galmuri11_rows_to_mmt(
            data, slot, rows11, x_offset=x_offset, y_offset=y_offset
        )

    if verify:
        for slot in range(font_mmt.GLYPH_COUNT):
            before = font_mmt.extract_glyph(original, slot)
            after = font_mmt.extract_glyph(data, slot)
            if slot not in targets and before != after:
                raise ValueError(f"verification failed: untargeted glyph slot {slot} changed")

    output_font.parent.mkdir(parents=True, exist_ok=True)
    output_font.write_bytes(data)
    return {
        "charset_size": len(entries),
        "target_slot_min": min(targets) if targets else None,
        "target_slot_max": max(targets) if targets else None,
        "untouched_slot_count": font_mmt.GLYPH_COUNT - len(targets),
        "changed_bytes": sum(a != b for a, b in zip(original, data)),
        "original_sha256": sha256(original),
        "output_sha256": sha256(data),
        "output_size": len(data),
        "build_info": info,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Apply WIZ7 PSX Korean font artifact to FONT.MMT")
    p.add_argument("--font", required=True, type=Path, help="original FONT.MMT")
    p.add_argument("--assets", required=True, type=Path, help="extracted CI artifact directory")
    p.add_argument("--output", required=True, type=Path, help="output FONT_KOR.MMT")
    p.add_argument("--x-offset", type=int, default=2)
    p.add_argument("--y-offset", type=int, default=0)
    p.add_argument("--no-verify", action="store_true")
    args = p.parse_args()
    try:
        report = apply_assets(
            args.font,
            args.assets,
            args.output,
            x_offset=args.x_offset,
            y_offset=args.y_offset,
            verify=not args.no_verify,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
