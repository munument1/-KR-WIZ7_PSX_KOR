# PSX native Korean codepage / FONT.MMT mapping

## Current verified result

Wizardry VII PSX already has a two-byte renderer path that can address 2048
renderer glyph numbers. The byte-code calculation in `PSX.EXE` is:

```text
lead  0x80..0x8F
trail 0x30..0x6F -> local 0..63
trail 0xA0..0xDF -> local 64..127

renderer_glyph = (lead - 0x80) * 128 + local
```

The important correction from the first Korean prototypes is that this renderer
glyph number is **not** the physical `FONT.MMT` bitplane number.

## Verified -4 FONT.MMT bias

Cross-checking the original Japanese `ZENKAKU.TBL`, the renderer code and known
ASCII glyphs proves a four-glyph bias:

```text
physical_font_slot = renderer_glyph - 4
renderer_glyph     = physical_font_slot + 4
```

Example:

- ASCII `A` is converted by the original game to native code `80A5`.
- The renderer formula yields glyph `69`.
- The actual `A` bitmap in the untouched `FONT.MMT` is physical slot `65`.
- Neighboring digits/letters follow the same offset continuously.

Therefore Korean mapping TSV `slot` values are renderer glyph numbers, while
font insertion must subtract 4 before selecting the physical bitplane.

The highest safe renderer glyph is 2047, which writes physical slot 2043.
Physical slots 2044..2047 are not reachable through this renderer window.

## Physical FONT.MMT geometry

`FONT.MMT` is an 8-byte wrapper around a TIM-like 1024x99 payload. The glyph
area is arranged as 512 physical 16x12 cells, with four independent 1-bit glyphs
stored in each cell's four nibble bits.

```text
physical_group = physical_slot // 4
physical_plane = physical_slot & 3
```

The physical plane order is the natural `0,1,2,3` order. The earlier v3 theory
that logical planes 0 and 2 were swapped was disproved by runtime testing and the
known ASCII glyph audit.

## Galmuri11 placement

Korean glyphs are packed from Galmuri11 into the 16x12 physical cell. Runtime
screenshots established that `x_offset=2` clips the rightmost Galmuri column.
That column contains the short right arm of `ㅏ`, making every syllable with
`ㅏ` appear as the corresponding `ㅣ` syllable (`가 -> 기`, `나 -> 니`, etc.).

Production placement is:

```text
x_offset = 1
y_offset = 0
```

`font_mmt.galmuri11_rows_to_mmt()` also normalizes the old x-offset 2 default to
1 so older build callers cannot accidentally recreate that corruption.

## Reservation policy

The project continues to allocate Korean renderer glyphs from the high end down,
while reserving the low region used by the original ASCII/Japanese conversion
paths. The full PS1 build currently reserves renderer glyphs through 279 and
uses one shared mapping for MSG, FONT and SCENARIO names.

## Regression history

- v1/v2: renderer glyph written directly to physical FONT slot -> four-slot shift.
- v3: incorrect 0/2 plane-swap theory -> still corrupt.
- v4: -4 physical-slot bias fixed -> most Hangul correct.
- v5+: Galmuri x offset 2 -> 1 -> `ㅏ` right-arm clipping fixed.
