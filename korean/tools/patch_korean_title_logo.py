#!/usr/bin/env python3
"""Replace the Japanese PSX title subtitle with Korean without shipping image assets.

The Japanese disc keeps ``ガーディアの宝珠`` baked into ``CDS/T/TITL.MMT``.
Gertius' PSX English patch leaves this MMT unchanged. The file is an 8-byte
wrapper followed by a standard 16bpp PSX TIM. This tool removes only the orange
subtitle pixels, fills the exposed background from nearby pixels, and draws
``가디아의 보주`` using glyphs already present in the generated Korean FONT.MMT.
"""
from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

FONT_HEADER = 36
FONT_WIDTH = 1024
FONT_BYTES_PER_ROW = FONT_WIDTH // 2
FONT_GLYPH_Y0 = 3
FONT_CELL_W = 16
FONT_CELL_H = 12
FONT_GROUP_COLS = 64
RENDERER_GLYPH_BIAS = 4

SUBTITLE = "가디아의 보주"
SUBTITLE_X = 202
SUBTITLE_Y = 121
SUBTITLE_ADVANCE = 13
SUBTITLE_SPACE = 7
SUBTITLE_RGB5 = (29, 19, 0)
MASK_X0, MASK_X1 = 154, 312
MASK_Y0, MASK_Y1 = 108, 146


def font_nibble(data: bytes, x: int, y: int) -> int:
    off = FONT_HEADER + y * FONT_BYTES_PER_ROW + x // 2
    value = data[off]
    return ((value >> 4) & 0x0F) if x & 1 else (value & 0x0F)


def renderer_glyph_rows(font: bytes, renderer_glyph: int) -> list[int]:
    slot = renderer_glyph - RENDERER_GLYPH_BIAS
    if not 0 <= slot < 2048:
        raise ValueError(f"renderer glyph is outside FONT.MMT after -4 bias: {renderer_glyph}")
    group = slot // 4
    plane = slot & 3
    x0 = (group % FONT_GROUP_COLS) * FONT_CELL_W
    y0 = FONT_GLYPH_Y0 + (group // FONT_GROUP_COLS) * FONT_CELL_H
    rows: list[int] = []
    for y in range(FONT_CELL_H):
        row = 0
        for x in range(FONT_CELL_W):
            if (font_nibble(font, x0 + x, y0 + y) >> plane) & 1:
                row |= 1 << (15 - x)
        rows.append(row)
    return rows


def load_renderer_mapping(path: Path) -> dict[str, int]:
    mapping: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            mapping[row["char"]] = int(row["slot"])
    missing = [ch for ch in SUBTITLE if ch != " " and ch not in mapping]
    if missing:
        raise ValueError("title subtitle mapping is missing: " + "".join(missing))
    return mapping


def rgb5(value: int) -> tuple[int, int, int]:
    return value & 31, (value >> 5) & 31, (value >> 10) & 31


def pack_rgb5(r: int, g: int, b: int, stp: int = 0) -> int:
    return (stp & 0x8000) | (r & 31) | ((g & 31) << 5) | ((b & 31) << 10)


def parse_direct16_tim(data: bytearray) -> tuple[int, int, int]:
    if len(data) < 28:
        raise ValueError("TITL.MMT is too small")
    off = 8
    magic, flags = struct.unpack_from("<II", data, off)
    off += 8
    if magic != 0x10 or flags != 2:
        raise ValueError(f"unexpected TITL.MMT TIM header: magic=0x{magic:X} flags={flags}")
    block_len, _x, _y, width, height = struct.unpack_from("<IHHHH", data, off)
    if width != 320 or height != 240:
        raise ValueError(f"unexpected TITL.MMT dimensions: {width}x{height}")
    if off + block_len > len(data):
        raise ValueError("truncated TITL.MMT image block")
    return off + 12, width, height


def build_subtitle_mask(values: list[int], width: int) -> set[tuple[int, int]]:
    mask: set[tuple[int, int]] = set()
    for y in range(MASK_Y0, MASK_Y1):
        for x in range(MASK_X0, MASK_X1):
            r, g, b = rgb5(values[y * width + x])
            if r >= 8 and g >= 3 and b <= 9 and r > g and r >= b * 2:
                mask.add((x, y))
    for _ in range(2):
        expanded = set(mask)
        for x, y in mask:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if MASK_X0 <= nx < MASK_X1 and MASK_Y0 <= ny < MASK_Y1:
                        expanded.add((nx, ny))
        mask = expanded
    return mask


def remove_japanese_subtitle(values: list[int], width: int, height: int) -> int:
    mask = build_subtitle_mask(values, width)
    original = values[:]
    for x, y in sorted(mask, key=lambda p: p[1]):
        candidates: list[int] = []
        for radius in range(1, 16):
            for nx, ny in ((x, y - radius), (x, y + radius), (x - radius, y), (x + radius, y)):
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in mask:
                    candidates.append(original[ny * width + nx])
            if len(candidates) >= 2:
                break
        if not candidates:
            candidates = [0]
        rs = gs = bs = 0
        for value in candidates:
            r, g, b = rgb5(value)
            rs += r
            gs += g
            bs += b
        count = len(candidates)
        stp = original[y * width + x] & 0x8000
        values[y * width + x] = pack_rgb5(round(rs / count), round(gs / count), round(bs / count), stp)
    return len(mask)


def draw_korean_subtitle(values: list[int], width: int, height: int, font: bytes, mapping: dict[str, int]) -> None:
    cursor = SUBTITLE_X
    orange = pack_rgb5(*SUBTITLE_RGB5)
    for ch in SUBTITLE:
        if ch == " ":
            cursor += SUBTITLE_SPACE
            continue
        rows = renderer_glyph_rows(font, mapping[ch])
        for gy, row in enumerate(rows):
            for gx in range(FONT_CELL_W):
                if not (row & (1 << (15 - gx))):
                    continue
                x = cursor + gx
                y = SUBTITLE_Y + gy
                if 0 <= x < width and 0 <= y < height:
                    values[y * width + x] = orange
        cursor += SUBTITLE_ADVANCE


def patch_title(title_path: Path, font_path: Path, mapping_path: Path, output_path: Path) -> int:
    data = bytearray(title_path.read_bytes())
    pixel_off, width, height = parse_direct16_tim(data)
    count = width * height
    values = list(struct.unpack_from("<" + "H" * count, data, pixel_off))
    removed = remove_japanese_subtitle(values, width, height)
    font = font_path.read_bytes()
    mapping = load_renderer_mapping(mapping_path)
    draw_korean_subtitle(values, width, height, font, mapping)
    struct.pack_into("<" + "H" * count, data, pixel_off, *values)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Replace WIZ7 PSX Japanese title subtitle with Korean")
    parser.add_argument("--title", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    removed = patch_title(args.title, args.font, args.mapping, args.output)
    print(f"patched title subtitle: removed_mask_pixels={removed} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
