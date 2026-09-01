#!/usr/bin/env python3
"""Wizardry VII PSX Korean font/encoding preparation tool.

This tool deliberately stops before packing glyphs into the game's native
font storage.  The PSX executable's FUN_ASCIItoZENKAKU routine already passes
0x80..0x9F lead-byte sequences through as two bytes; the exact downstream
glyph-index mapping still needs to be verified from the game executable/assets.

Outputs are therefore reproducible intermediate assets:
  * charset.txt          sorted Korean characters
  * korean_dbcs.tsv      Unicode <-> provisional two-byte code mapping
  * korean_glyphs.bin    11x11 glyph rows, 16-bit big-endian per row
  * korean_glyphs.tsv    glyph offsets/metrics

Galmuri11 is not bundled. By default the tool downloads the official Galmuri11.bdf
from quiple/galmuri and extracts the required bitmap glyphs itself. Use --bdf only
when an offline/local copy should be used.
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
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

HANGUL_RE = re.compile(r"[\u3131-\u318E\uAC00-\uD7A3]")
DEFAULT_EXTS = {".txt", ".csv", ".tsv", ".md", ".json", ".xml", ".ini"}
LEADS = tuple(range(0x80, 0xA0))
TRAILS = tuple(range(0x40, 0x7F)) + tuple(range(0x80, 0xFD))
GALMURI11_BDF_URL = "https://raw.githubusercontent.com/quiple/galmuri/main/dist/Galmuri11.bdf"


@dataclass(frozen=True)
class Glyph:
    codepoint: int
    width: int
    height: int
    xoff: int
    yoff: int
    rows: Tuple[int, ...]


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
    chars = sorted(counts)
    return chars, counts


def allocate_dbcs(chars: Sequence[str]) -> Dict[str, Tuple[int, int]]:
    capacity = len(LEADS) * len(TRAILS)
    if len(chars) > capacity:
        raise ValueError(f"charset has {len(chars)} chars; provisional DBCS capacity is {capacity}")
    mapping: Dict[str, Tuple[int, int]] = {}
    i = 0
    for lead in LEADS:
        for trail in TRAILS:
            if i >= len(chars):
                return mapping
            mapping[chars[i]] = (lead, trail)
            i += 1
    return mapping


def write_mapping(path: Path, chars: Sequence[str], counts: Dict[str, int], mapping: Dict[str, Tuple[int, int]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["char", "unicode", "lead", "trail", "code_hex", "count"])
        for ch in chars:
            lead, trail = mapping[ch]
            w.writerow([ch, f"U+{ord(ch):04X}", f"0x{lead:02X}", f"0x{trail:02X}", f"{lead:02X}{trail:02X}", counts.get(ch, 0)])


def load_mapping(path: Path) -> Dict[str, Tuple[int, int]]:
    mapping: Dict[str, Tuple[int, int]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            ch = row["char"]
            mapping[ch] = (int(row["lead"], 16), int(row["trail"], 16))
    return mapping


def obtain_galmuri11_bdf(local_bdf: str | None, cache_dir: Path) -> Path:
    """Return a local Galmuri11 BDF path, downloading the official file if needed.

    The font file is kept only as a local build cache and is not copied into the
    repository or generated outputs.
    """
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
            "could not download official Galmuri11.bdf; "
            "retry with network access or pass --bdf /path/to/Galmuri11.bdf"
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
                    bbx = tuple(map(int, parts[1:5]))
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


def emit_glyphs(out_dir: Path, chars: Sequence[str], mapping: Dict[str, Tuple[int, int]], glyphs: Dict[int, Glyph]) -> None:
    missing = [ch for ch in chars if ord(ch) not in glyphs]
    if missing:
        preview = " ".join(f"{ch}(U+{ord(ch):04X})" for ch in missing[:20])
        raise ValueError(f"BDF is missing {len(missing)} required glyph(s): {preview}")

    bin_path = out_dir / "korean_glyphs.bin"
    tsv_path = out_dir / "korean_glyphs.tsv"
    offset = 0
    with bin_path.open("wb") as bf, tsv_path.open("w", encoding="utf-8", newline="") as tf:
        w = csv.writer(tf, delimiter="\t")
        w.writerow(["char", "unicode", "code_hex", "offset", "bytes", "cell"])
        for ch in chars:
            rows = render_to_cell(glyphs[ord(ch)])
            payload = b"".join(row.to_bytes(2, "big") for row in rows)
            bf.write(payload)
            lead, trail = mapping[ch]
            w.writerow([ch, f"U+{ord(ch):04X}", f"{lead:02X}{trail:02X}", offset, len(payload), "11x11/16-bit-row-BE"])
            offset += len(payload)


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
        if not ext:
            continue
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
    mapping = allocate_dbcs(chars)
    (out_dir / "charset.txt").write_text("".join(chars) + "\n", encoding="utf-8")
    write_mapping(out_dir / "korean_dbcs.tsv", chars, counts, mapping)

    metadata = {
        "charset_size": len(chars),
        "lead_range": ["0x80", "0x9F"],
        "trail_policy": "0x40-0x7E, 0x80-0xFC (0x7F excluded)",
        "mapping_status": "PROVISIONAL: downstream PSX glyph-index mapping not yet verified",
    }
    (out_dir / "build_info.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.no_glyphs:
        bdf_path = obtain_galmuri11_bdf(args.bdf, out_dir / ".cache")
        glyphs = parse_bdf(bdf_path)
        emit_glyphs(out_dir, chars, mapping, glyphs)

    print(f"charset: {len(chars)} Hangul chars")
    print(f"mapping: {out_dir / 'korean_dbcs.tsv'}")
    if not args.no_glyphs:
        print(f"glyphs:  {out_dir / 'korean_glyphs.bin'}")
    else:
        print("glyphs:  skipped (--no-glyphs)")
    return 0


def cmd_encode(args: argparse.Namespace) -> int:
    mapping = load_mapping(Path(args.mapping))
    src = Path(args.input).read_text(encoding="utf-8")
    encoded = encode_text(src, mapping, strict=not args.allow_unmapped)
    Path(args.output).write_bytes(encoded)
    print(f"encoded {len(src)} Unicode chars -> {len(encoded)} bytes")
    return 0


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Wiz7 PSX Korean DBCS/font preparation")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="scan translations, allocate DBCS, and extract Galmuri11 bitmaps")
    b.add_argument("inputs", nargs="+", help="UTF-8/CP949 text files or directories")
    b.add_argument("--out", default="build/korean-font", help="output directory")
    b.add_argument("--bdf", help="offline path to official Galmuri11.bdf (default: download official BDF automatically)")
    b.add_argument("--no-glyphs", action="store_true", help="only build charset/mapping; skip Galmuri11 bitmap extraction")
    b.add_argument("--extensions", default=",".join(sorted(DEFAULT_EXTS)), help="extensions scanned recursively")
    b.set_defaults(func=cmd_build)

    e = sub.add_parser("encode", help="encode a UTF-8 text file using generated korean_dbcs.tsv")
    e.add_argument("--mapping", required=True)
    e.add_argument("--input", required=True)
    e.add_argument("--output", required=True)
    e.add_argument("--allow-unmapped", action="store_true", help="pass unmapped non-ASCII through as UTF-8 (diagnostic only)")
    e.set_defaults(func=cmd_encode)
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
