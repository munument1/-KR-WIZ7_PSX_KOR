#!/usr/bin/env python3
"""Read/write Wizardry VII PSX FONT.MMT glyph bitplanes.

The FONT.MMT bitmap contains 2048 physical glyph bitplanes arranged as 512
16x12 cells with four independent 1-bit glyphs per 4bpp cell. Physical bitplane
order is the natural order 0,1,2,3.

A renderer-native glyph number is NOT the same number as the physical FONT.MMT
slot. Comparison against the original ZENKAKU.TBL and known ASCII glyphs proves
that the renderer is biased by four glyphs:

    physical_font_slot = renderer_glyph - 4

For example ASCII 'A' is converted by the game to native code 80A5. The renderer
calculates glyph 69, while the actual 'A' bitmap is physical FONT.MMT slot 65.
The Korean codepage stores renderer glyph numbers, so Korean insertion must apply
this -4 bias before touching FONT.MMT.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple

HEADER_SIZE = 36
WIDTH = 1024
HEIGHT = 99
BYTES_PER_ROW = WIDTH // 2
GLYPH_Y0 = 3
CELL_W = 16
CELL_H = 12
GROUP_COLS = WIDTH // CELL_W
GROUP_ROWS = (HEIGHT - GLYPH_Y0) // CELL_H
GLYPH_COUNT = GROUP_COLS * GROUP_ROWS * 4
EXPECTED_SIZE = HEADER_SIZE + BYTES_PER_ROW * HEIGHT
RENDERER_GLYPH_BIAS = 4


@dataclass(frozen=True)
class FontGeometry:
    width: int = WIDTH
    height: int = HEIGHT
    header_size: int = HEADER_SIZE
    glyph_y0: int = GLYPH_Y0
    cell_w: int = CELL_W
    cell_h: int = CELL_H
    glyph_count: int = GLYPH_COUNT


def renderer_glyph_to_font_slot(renderer_glyph: int) -> int:
    """Convert the renderer's glyph number to a physical FONT.MMT slot."""
    slot = renderer_glyph - RENDERER_GLYPH_BIAS
    if not 0 <= slot < GLYPH_COUNT:
        raise ValueError(
            f"renderer glyph {renderer_glyph} has no physical FONT.MMT slot "
            f"after -{RENDERER_GLYPH_BIAS} bias"
        )
    return slot


def font_slot_to_renderer_glyph(slot: int) -> int:
    """Convert a physical FONT.MMT slot to the renderer glyph number."""
    if not 0 <= slot < GLYPH_COUNT:
        raise ValueError(f"FONT.MMT slot out of range: {slot}")
    renderer_glyph = slot + RENDERER_GLYPH_BIAS
    if renderer_glyph >= GLYPH_COUNT:
        raise ValueError(
            f"FONT.MMT slot {slot} is not addressable by the 0..{GLYPH_COUNT - 1} renderer window"
        )
    return renderer_glyph


def validate_font(data: bytes | bytearray) -> None:
    if len(data) != EXPECTED_SIZE:
        raise ValueError(f"unexpected FONT.MMT size: {len(data)} (expected {EXPECTED_SIZE})")


def _pixel_offset(x: int, y: int) -> Tuple[int, bool]:
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        raise ValueError(f"pixel outside FONT.MMT texture: {x},{y}")
    return HEADER_SIZE + y * BYTES_PER_ROW + x // 2, bool(x & 1)


def get_nibble(data: bytes | bytearray, x: int, y: int) -> int:
    off, high = _pixel_offset(x, y)
    value = data[off]
    return (value >> 4) & 0x0F if high else value & 0x0F


def set_nibble(data: bytearray, x: int, y: int, nibble: int) -> None:
    if not 0 <= nibble <= 0x0F:
        raise ValueError("nibble must be 0..15")
    off, high = _pixel_offset(x, y)
    old = data[off]
    data[off] = ((old & 0x0F) | (nibble << 4)) if high else ((old & 0xF0) | nibble)


def glyph_origin(index: int) -> Tuple[int, int, int]:
    """Return raw texture origin/bit for a physical FONT.MMT slot."""
    if not 0 <= index < GLYPH_COUNT:
        raise ValueError(f"glyph index out of range: {index} (0..{GLYPH_COUNT - 1})")
    group = index // 4
    plane = index & 3
    x0 = (group % GROUP_COLS) * CELL_W
    y0 = GLYPH_Y0 + (group // GROUP_COLS) * CELL_H
    return x0, y0, plane


def extract_glyph(data: bytes | bytearray, index: int) -> Tuple[int, ...]:
    """Return one physical 16x12 FONT.MMT glyph as row bitfields."""
    validate_font(data)
    x0, y0, plane = glyph_origin(index)
    rows = []
    for y in range(CELL_H):
        row = 0
        for x in range(CELL_W):
            if (get_nibble(data, x0 + x, y0 + y) >> plane) & 1:
                row |= 1 << (CELL_W - 1 - x)
        rows.append(row)
    return tuple(rows)


def replace_glyph(
    data: bytes | bytearray,
    index: int,
    rows: Sequence[int],
    *,
    glyph_w: int,
    glyph_h: int,
    x_offset: int = 0,
    y_offset: int = 0,
) -> bytes:
    """Replace one physical FONT.MMT bitplane and preserve its neighbors."""
    validate_font(data)
    if glyph_w <= 0 or glyph_h <= 0 or glyph_w > CELL_W or glyph_h > CELL_H:
        raise ValueError("glyph dimensions must fit inside 16x12")
    if len(rows) < glyph_h:
        raise ValueError("not enough bitmap rows")
    if x_offset < 0 or y_offset < 0 or x_offset + glyph_w > CELL_W or y_offset + glyph_h > CELL_H:
        raise ValueError("glyph placement does not fit inside 16x12")

    out = bytearray(data)
    x0, y0, plane = glyph_origin(index)
    mask = 1 << plane

    for cy in range(CELL_H):
        for cx in range(CELL_W):
            on = False
            sx = cx - x_offset
            sy = cy - y_offset
            if 0 <= sx < glyph_w and 0 <= sy < glyph_h:
                on = bool(rows[sy] & (1 << (glyph_w - 1 - sx)))
            nib = get_nibble(out, x0 + cx, y0 + cy)
            nib = (nib | mask) if on else (nib & ~mask)
            set_nibble(out, x0 + cx, y0 + cy, nib)
    return bytes(out)


def galmuri11_rows_to_mmt(
    data: bytes | bytearray,
    renderer_glyph: int,
    rows11: Sequence[int],
    *,
    x_offset: int = 1,
    y_offset: int = 0,
) -> bytes:
    """Pack Galmuri11 for a renderer glyph into its biased FONT.MMT slot.

    Runtime testing showed x_offset=2 clips the Galmuri11 rightmost column;
    that single column carries the ㅏ arm, making every ㅏ syllable look like ㅣ.
    x_offset=1 keeps all 11 columns visible.
    """
    # Compatibility with older callers whose CLI default was x_offset=2.
    # Normalize that legacy value so existing build scripts also produce the
    # corrected font until their CLI default is migrated to 1.
    if x_offset == 2:
        x_offset = 1
    slot = renderer_glyph_to_font_slot(renderer_glyph)
    return replace_glyph(data, slot, rows11, glyph_w=11, glyph_h=11, x_offset=x_offset, y_offset=y_offset)


def save_replaced_glyph(
    font_path: Path,
    output_path: Path,
    renderer_glyph: int,
    rows11: Sequence[int],
    *,
    x_offset: int = 1,
    y_offset: int = 0,
) -> None:
    data = font_path.read_bytes()
    output_path.write_bytes(
        galmuri11_rows_to_mmt(
            data, renderer_glyph, rows11, x_offset=x_offset, y_offset=y_offset
        )
    )
