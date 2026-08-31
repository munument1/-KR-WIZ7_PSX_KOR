#!/usr/bin/env python3
"""Wizardry VII PSX FONT.MMT single-glyph proof of concept.

Replaces the glyph selected for ASCII 'A' (ZENKAKU 0x80A5) with a
pre-rendered 16x12 bitmap for Korean '한', while preserving the other three
glyph bitplanes packed into the same 4bpp texture cell.

This script intentionally contains no original game data and no font file.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED_SIZE = 50_724
HEADER_SIZE = 36
WIDTH = 1024
HEIGHT = 99
ROW_BYTES = WIDTH // 2

# Confirmed by renderer analysis and visual bitplane verification:
# physical FONT.MMT group 16, first glyph row (texture y=3..14), bitplane 1 = 'A'.
TARGET_GROUP = 16
TARGET_GLYPH_ROW = 0
TARGET_BIT = 1
TARGET_CODE = 0x80A5
TARGET_ASCII = "A"

# Temporary POC bitmap for '한'. 16 columns x 12 rows.
# Generated once from an installed Korean UI font, then embedded as pixels;
# no font binary is distributed or required by this script.
HAN_MASK = [
    "................",
    "..........#.....",
    "....####..#.....",
    "...######.#.....",
    "..........#.....",
    "....####..###...",
    "...##..##.#.....",
    "....####..#.....",
    "....#.....#.....",
    "....#...........",
    "....########....",
    "................",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unpack_4bpp(payload: bytes) -> list[int]:
    pixels: list[int] = []
    for value in payload:
        pixels.append(value & 0x0F)
        pixels.append(value >> 4)
    if len(pixels) != WIDTH * HEIGHT:
        raise ValueError(f"unexpected pixel count: {len(pixels)}")
    return pixels


def pack_4bpp(pixels: list[int]) -> bytes:
    if len(pixels) != WIDTH * HEIGHT:
        raise ValueError("unexpected pixel count")
    out = bytearray(len(pixels) // 2)
    for i in range(0, len(pixels), 2):
        lo = pixels[i] & 0x0F
        hi = pixels[i + 1] & 0x0F
        out[i // 2] = lo | (hi << 4)
    return bytes(out)


def glyph_mask(pixels: list[int], group: int, glyph_row: int, bit: int) -> list[str]:
    x0 = group * 16
    y0 = 3 + glyph_row * 12
    rows = []
    for y in range(y0, y0 + 12):
        rows.append("".join("#" if ((pixels[y * WIDTH + x] >> bit) & 1) else "."
                            for x in range(x0, x0 + 16)))
    return rows


def patch_font(data: bytes) -> tuple[bytes, list[str], list[str]]:
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"FONT.MMT size must be {EXPECTED_SIZE}, got {len(data)}")

    header = data[:HEADER_SIZE]
    payload = data[HEADER_SIZE:]
    if len(payload) != WIDTH * HEIGHT // 2:
        raise ValueError("FONT.MMT payload size does not match 1024x99 4bpp")

    pixels = unpack_4bpp(payload)
    before = glyph_mask(pixels, TARGET_GROUP, TARGET_GLYPH_ROW, TARGET_BIT)

    x0 = TARGET_GROUP * 16
    y0 = 3 + TARGET_GLYPH_ROW * 12
    clear_mask = 0x0F ^ (1 << TARGET_BIT)

    for dy, row in enumerate(HAN_MASK):
        if len(row) != 16:
            raise ValueError("HAN_MASK must be exactly 16 pixels wide")
        for dx, mark in enumerate(row):
            idx = (y0 + dy) * WIDTH + (x0 + dx)
            pixels[idx] &= clear_mask
            if mark == "#":
                pixels[idx] |= (1 << TARGET_BIT)
            elif mark != ".":
                raise ValueError(f"bad bitmap character: {mark!r}")

    after = glyph_mask(pixels, TARGET_GROUP, TARGET_GLYPH_ROW, TARGET_BIT)
    patched = header + pack_4bpp(pixels)
    return patched, before, after


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="original FONT.MMT")
    ap.add_argument("output", type=Path, help="patched FONT.MMT")
    args = ap.parse_args()

    original = args.input.read_bytes()
    patched, before, after = patch_font(original)
    args.output.write_bytes(patched)

    print(f"input_size={len(original)} output_size={len(patched)}")
    print(f"input_sha256={sha256(original)}")
    print(f"output_sha256={sha256(patched)}")
    print(f"target_ascii={TARGET_ASCII} target_zenkaku=0x{TARGET_CODE:04X}")
    print(f"physical_group={TARGET_GROUP} glyph_row={TARGET_GLYPH_ROW} bitplane={TARGET_BIT}")
    print("before:")
    print("\n".join(before))
    print("after:")
    print("\n".join(after))


if __name__ == "__main__":
    main()
