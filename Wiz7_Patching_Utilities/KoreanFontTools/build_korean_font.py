#!/usr/bin/env python3
"""Wizardry VII PSX Korean native font/codepage builder.

The PSX renderer already understands a native two-byte font code.  Reverse-
engineering of PSX.EXE at 0x80074FDC..0x80075004 gives this exact mapping:

    slot = ((lead - 0x80) * 128) + local

where safe FONT.MMT codes are:
    lead  0x80..0x8F
    trail 0x30..0x6F -> local 0..63
    trail 0xA0..0xDF -> local 64..127

That address space is exactly 16 * 128 = 2048 slots, matching FONT.MMT.
The tool scans Korean translations, extracts required Galmuri11 bitmaps,
allocates native PSX codes while reserving existing ZENKAKU.TBL slots, and can
write a patched FONT_KOR.MMT directly from the original FONT.MMT.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple

import font_mmt

HANGUL_RE = re.compile(r"[\u3131-\u318E\uAC00-\uD7A3]")
DEFAULT_EXTS = {".txt", ".csv", ".tsv", ".md", ".json", ".xml", ".ini"}
GALMURI11_BDF_URL = "https://raw.githubusercontent.com/quiple/galmuri/main/dist/Galmuri11.bdf"

NATIVE_LEADS = tuple(range(0x80, 0x90))
LOW_TRAILS = tuple(range(0x30, 0x70))
HIGH_TRAILS = tuple(range(0xA0, 0xE0))
NATIVE_GLYPH_COUNT = 2048


@dataclass(frozen=True)
class Glyph:
    codepoint: int
    width: int
    height: int
    xoff: int
    yoff: int
    rows: Tuple[int, ...]


@dataclass(frozen=True)
class NativeMapping:
    lead: int
    trail: int
    slot: int


def native_code_to_slot(lead: int, trail: int) -> int:
    """Map a renderer-native 2-byte code to FONT.MMT logical slot 0..2047."""
    if lead not in NATIVE_LEADS:
        raise ValueError(f"native lead 0x{lead:02X} is outside safe FONT.MMT range 0x80..0x8F")
    if 0x30 <= trail <= 0x6F:
        local = trail - 0x30
    elif 0xA0 <= trail <= 0xDF:
        local = trail - 0x60
    else:
        raise ValueError(
            f"native trail 0x{trail:02X} is outside canonical ranges 0x30..0x6F/0xA0..0xDF"
        )
    slot = (lead - 0x80) * 128 + local
    if not 0 <= slot < NATIVE_GLYPH_COUNT:
        raise ValueError(f"native code maps outside FONT.MMT: {lead:02X}{trail:02X} -> {slot}")
    return slot


def slot_to_native_code(slot: int) -> Tuple[int, int]:
    """Inverse of native_code_to_slot for every FONT.MMT slot."""
    if not 0 <= slot < NATIVE_GLYPH_COUNT:
        raise ValueError(f"FONT.MMT slot out of range: {slot}")
    bank, local = divmod(slot, 128)
    lead = 0x80 + bank
    trail = (0x30 + local) if local < 64 else (0x60 + local)
    return lead, trail


def read_zenkaku_pairs(path: Path) -> List[Tuple[int, int]]:
    data = path.read_bytes()
    if len(data) % 2:
        raise ValueError(f"ZENKAKU.TBL has odd size: {len(data)}")
    return [(data[i], data[i + 1]) for i in range(0, len(data), 2)]


def zenkaku_reserved_slots(path: Path) -> set[int]:
    """Return safe FONT.MMT slots referenced by ZENKAKU.TBL.

    Some future/variant tables might contain codes outside the 2048-slot native
    FONT.MMT window; those are ignored rather than treated as allocatable.
    """
    reserved: set[int] = set()
    for lead, trail in read_zenkaku_pairs(path):
        try:
            reserved.add(native_code_to_slot(lead, trail))
        except ValueError:
            continue
    return reserved


def iter_text_files(paths: Sequence[Path], extensions: set[str]) -> Iterator[Path]:
    for path in paths:
        if path.is_file():
            yield path
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in extensions:
                    yield candidate


def read_text_lossy(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def collect_hangul(paths: Sequence[Path], extensions: set[str]) -> Tuple[List[str], Dict[str, int]]:
    counts: Dict[str, int] = {}
    for file in iter_text_files(paths, extensions):
        for ch in HANGUL_RE.findall(read_text_lossy(file)):
            counts[ch] = counts.get(ch, 0) + 1
    # Unicode order is deterministic across rebuilds and independent of text frequency changes.
    chars = sorted(counts)
    return chars, counts


def allocate_native_mapping(
    chars: Sequence[str], reserved_slots: set[int] | None = None
) -> Dict[str, NativeMapping]:
    reserved = set(reserved_slots or ())
    bad = sorted(slot for slot in reserved if not 0 <= slot < NATIVE_GLYPH_COUNT)
    if bad:
        raise ValueError(f"reserved slot outside FONT.MMT: {bad[0]}")
    # Allocate from the top down. Original Japanese/native assets occupy the low
    # banks heavily; high-slot allocation minimizes collateral risk from legacy
    # glyphs that are not explicitly referenced by ZENKAKU.TBL.
    free_slots = [slot for slot in range(NATIVE_GLYPH_COUNT - 1, -1, -1) if slot not in reserved]
    if len(chars) > len(free_slots):
        raise ValueError(
            f"charset has {len(chars)} chars but only {len(free_slots)} FONT.MMT slots remain "
            f"after reserving {len(reserved)} slots"
        )
    mapping: Dict[str, NativeMapping] = {}
    for ch, slot in zip(chars, free_slots):
        lead, trail = slot_to_native_code(slot)
        mapping[ch] = NativeMapping(lead, trail, slot)
    return mapping


# Backward-compatible name used by early tests/tools. It now allocates real native codes.
def allocate_dbcs(chars: Sequence[str]) -> Dict[str, Tuple[int, int]]:
    native = allocate_native_mapping(chars)
    return {ch: (m.lead, m.trail) for ch, m in native.items()}


def write_mapping(
    path: Path,
    chars: Sequence[str],
    counts: Dict[str, int],
    mapping: Dict[str, NativeMapping],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["char", "unicode", "lead", "trail", "code_hex", "slot", "count"])
        for ch in chars:
            m = mapping[ch]
            w.writerow(
                [
                    ch,
                    f"U+{ord(ch):04X}",
                    f"0x{m.lead:02X}",
                    f"0x{m.trail:02X}",
                    f"{m.lead:02X}{m.trail:02X}",
                    m.slot,
                    counts.get(ch, 0),
                ]
            )


def load_mapping(path: Path) -> Dict[str, Tuple[int, int]]:
    mapping: Dict[str, Tuple[int, int]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            ch = row["char"]
            mapping[ch] = (int(row["lead"], 16), int(row["trail"], 16))
    return mapping


def obtain_galmuri11_bdf(local_bdf: str | None, cache_dir: Path) -> Path:
    """Return Galmuri11 BDF, downloading the official file if needed."""
    if local_bdf:
        path = Path(local_bdf)
        if not path.is_file():
            raise ValueError(f"Galmuri11 BDF not found: {path}")
        return path

    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / "Galmuri11.bdf"
    if target.is_file() and target.stat().st_size > 0:
        return target

    try:
        print(f"fetching Galmuri11 BDF: {GALMURI11_BDF_URL}")
        urllib.request.urlretrieve(GALMURI11_BDF_URL, target)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise OSError(
            "could not download official Galmuri11.bdf; retry with network access "
            "or pass --bdf /path/to/Galmuri11.bdf"
        ) from exc
    return target


def parse_bdf(path: Path) -> Dict[int, Glyph]:
    glyphs: Dict[int, Glyph] = {}
    codepoint: int | None = None
    bbx: Tuple[int, int, int, int] | None = None
    bitmap_rows: List[str] = []
    in_bitmap = False

    def finish() -> None:
        nonlocal codepoint, bbx, bitmap_rows, in_bitmap
        if codepoint is None or codepoint < 0 or bbx is None or not bitmap_rows:
            codepoint = None
            bbx = None
            bitmap_rows = []
            in_bitmap = False
            return
        width, height, xoff, yoff = bbx
        rows: List[int] = []
        row_bits = ((width + 7) // 8) * 8
        for raw in bitmap_rows[:height]:
            val = int(raw, 16)
            pad = row_bits - width
            if pad > 0:
                val >>= pad
            rows.append(val & ((1 << width) - 1 if width else 0))
        while len(rows) < height:
            rows.append(0)
        glyphs[codepoint] = Glyph(codepoint, width, height, xoff, yoff, tuple(rows))
        codepoint = None
        bbx = None
        bitmap_rows = []
        in_bitmap = False

    with path.open("r", encoding="ascii", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if line.startswith("STARTCHAR"):
                finish()
            elif line.startswith("ENCODING "):
                try:
                    codepoint = int(line.split()[1])
                except (ValueError, IndexError):
                    codepoint = None
            elif line.startswith("BBX "):
                parts = line.split()
                if len(parts) >= 5:
                    bbx = tuple(map(int, parts[1:5]))  # type: ignore[assignment]
            elif line == "BITMAP":
                bitmap_rows = []
                in_bitmap = True
            elif line == "ENDCHAR":
                finish()
            elif in_bitmap and line:
                bitmap_rows.append(line)
    finish()
    return glyphs


def render_to_cell(glyph: Glyph, cell_w: int = 11, cell_h: int = 11) -> Tuple[int, ...]:
    """Place a BDF glyph in an 11x11 logical cell without scaling."""
    canvas = [0] * cell_h
    x0 = glyph.xoff
    y0 = cell_h - glyph.height - glyph.yoff
    for gy, row in enumerate(glyph.rows):
        cy = y0 + gy
        if not (0 <= cy < cell_h):
            continue
        for gx in range(glyph.width):
            if row & (1 << (glyph.width - 1 - gx)):
                cx = x0 + gx
                if 0 <= cx < cell_w:
                    canvas[cy] |= 1 << (cell_w - 1 - cx)
    return tuple(canvas)


def validate_required_glyphs(chars: Sequence[str], glyphs: Dict[int, Glyph]) -> None:
    missing = [ch for ch in chars if ord(ch) not in glyphs]
    if missing:
        preview = " ".join(f"{ch}(U+{ord(ch):04X})" for ch in missing[:20])
        raise ValueError(f"BDF is missing {len(missing)} required glyph(s): {preview}")


def emit_glyphs(
    out_dir: Path,
    chars: Sequence[str],
    mapping: Dict[str, NativeMapping],
    glyphs: Dict[int, Glyph],
) -> None:
    validate_required_glyphs(chars, glyphs)
    bin_path = out_dir / "korean_glyphs.bin"
    tsv_path = out_dir / "korean_glyphs.tsv"
    offset = 0
    with bin_path.open("wb") as bf, tsv_path.open("w", encoding="utf-8", newline="") as tf:
        w = csv.writer(tf, delimiter="\t")
        w.writerow(["char", "unicode", "code_hex", "slot", "offset", "bytes", "cell"])
        for ch in chars:
            rows = render_to_cell(glyphs[ord(ch)])
            payload = b"".join(row.to_bytes(2, "big") for row in rows)
            bf.write(payload)
            m = mapping[ch]
            w.writerow(
                [ch, f"U+{ord(ch):04X}", f"{m.lead:02X}{m.trail:02X}", m.slot, offset, len(payload), "11x11/16-bit-row-BE"]
            )
            offset += len(payload)


def build_patched_font(
    original_font: Path,
    output_font: Path,
    chars: Sequence[str],
    mapping: Dict[str, NativeMapping],
    glyphs: Dict[int, Glyph],
    *,
    x_offset: int = 2,
    y_offset: int = 0,
) -> None:
    """Insert all required Galmuri11 glyphs into allocated FONT.MMT slots."""
    validate_required_glyphs(chars, glyphs)
    data = original_font.read_bytes()
    font_mmt.validate_font(data)
    for ch in chars:
        rows11 = render_to_cell(glyphs[ord(ch)])
        data = font_mmt.galmuri11_rows_to_mmt(
            data, mapping[ch].slot, rows11, x_offset=x_offset, y_offset=y_offset
        )
    output_font.write_bytes(data)


def encode_text(text: str, mapping: Dict[str, Tuple[int, int]], strict: bool = True) -> bytes:
    out = bytearray()
    for ch in text:
        cp = ord(ch)
        if ch in mapping:
            out.extend(mapping[ch])
        elif cp < 0x80:
            out.append(cp)
        elif strict:
            raise ValueError(f"no mapping for {ch!r} U+{cp:04X}")
        else:
            out.extend(ch.encode("utf-8"))
    return bytes(out)


def parse_exts(value: str) -> set[str]:
    result = set()
    for ext in value.split(","):
        ext = ext.strip().lower()
        if ext:
            result.add(ext if ext.startswith(".") else "." + ext)
    return result


def cmd_build(args: argparse.Namespace) -> int:
    inputs = [Path(p) for p in args.inputs]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    extensions = parse_exts(args.extensions)
    chars, counts = collect_hangul(inputs, extensions)
    if not chars:
        raise ValueError("no Hangul characters found in inputs")

    reserved: set[int] = set()
    if args.zenkaku:
        reserved = zenkaku_reserved_slots(Path(args.zenkaku))
    mapping = allocate_native_mapping(chars, reserved)

    (out_dir / "charset.txt").write_text("".join(chars) + "\n", encoding="utf-8")
    write_mapping(out_dir / "korean_dbcs.tsv", chars, counts, mapping)

    metadata = {
        "charset_size": len(chars),
        "font_slots": NATIVE_GLYPH_COUNT,
        "reserved_slots": len(reserved),
        "free_slots_after_reserve": NATIVE_GLYPH_COUNT - len(reserved),
        "lead_range": ["0x80", "0x8F"],
        "trail_ranges": ["0x30-0x6F", "0xA0-0xDF"],
        "mapping_status": "VERIFIED from PSX.EXE renderer at 0x80074FDC..0x80075004",
        "slot_formula": "(lead-0x80)*128 + local; local=trail-0x30 if bit7=0 else trail-0x60",
    }
    (out_dir / "build_info.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    glyphs: Dict[int, Glyph] | None = None
    if not args.no_glyphs:
        bdf_path = obtain_galmuri11_bdf(args.bdf, out_dir / ".cache")
        glyphs = parse_bdf(bdf_path)
        emit_glyphs(out_dir, chars, mapping, glyphs)

    if args.font:
        if glyphs is None:
            raise ValueError("--font requires glyph extraction; remove --no-glyphs")
        output_font = Path(args.font_output) if args.font_output else out_dir / "FONT_KOR.MMT"
        build_patched_font(
            Path(args.font), output_font, chars, mapping, glyphs,
            x_offset=args.x_offset, y_offset=args.y_offset,
        )
        print(f"font:     {output_font}")

    print(f"charset:  {len(chars)} Hangul chars")
    print(f"reserved: {len(reserved)} slots")
    print(f"mapping:  {out_dir / 'korean_dbcs.tsv'}")
    if not args.no_glyphs:
        print(f"glyphs:   {out_dir / 'korean_glyphs.bin'}")
    else:
        print("glyphs:   skipped (--no-glyphs)")
    return 0


def cmd_encode(args: argparse.Namespace) -> int:
    mapping = load_mapping(Path(args.mapping))
    src = Path(args.input).read_text(encoding="utf-8")
    encoded = encode_text(src, mapping, strict=not args.allow_unmapped)
    Path(args.output).write_bytes(encoded)
    print(f"encoded {len(src)} Unicode chars -> {len(encoded)} bytes")
    return 0


def cmd_code(args: argparse.Namespace) -> int:
    if args.slot is not None:
        lead, trail = slot_to_native_code(args.slot)
        print(f"slot {args.slot} -> {lead:02X}{trail:02X}")
        return 0
    lead = int(args.code[:2], 16)
    trail = int(args.code[2:], 16)
    print(f"code {lead:02X}{trail:02X} -> slot {native_code_to_slot(lead, trail)}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Wiz7 PSX Korean native codepage/font builder")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="scan translations, allocate native PSX slots, extract Galmuri11, optionally patch FONT.MMT")
    b.add_argument("inputs", nargs="+", help="UTF-8/CP949 text files or directories")
    b.add_argument("--out", default="build/korean-font", help="output directory")
    b.add_argument("--zenkaku", help="original ZENKAKU.TBL; referenced slots are reserved")
    b.add_argument("--font", help="original FONT.MMT to patch")
    b.add_argument("--font-output", help="patched font output (default: <out>/FONT_KOR.MMT)")
    b.add_argument("--bdf", help="offline official Galmuri11.bdf (default: download automatically)")
    b.add_argument("--no-glyphs", action="store_true", help="only build charset/mapping; skip Galmuri bitmap extraction")
    b.add_argument("--x-offset", type=int, default=2, help="Galmuri11 x placement in 16x12 cell (default 2)")
    b.add_argument("--y-offset", type=int, default=0, help="Galmuri11 y placement in 16x12 cell (default 0)")
    b.add_argument("--extensions", default=",".join(sorted(DEFAULT_EXTS)), help="extensions scanned recursively")
    b.set_defaults(func=cmd_build)

    e = sub.add_parser("encode", help="encode UTF-8 text with generated native korean_dbcs.tsv")
    e.add_argument("--mapping", required=True)
    e.add_argument("--input", required=True)
    e.add_argument("--output", required=True)
    e.add_argument("--allow-unmapped", action="store_true", help="pass unmapped non-ASCII through as UTF-8 (diagnostic only)")
    e.set_defaults(func=cmd_encode)

    c = sub.add_parser("code", help="convert between native code and FONT.MMT slot")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--slot", type=int)
    g.add_argument("--code", help="4 hex digits, e.g. 80A0")
    c.set_defaults(func=cmd_code)
    return p


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
