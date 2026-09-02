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

The mapping TSV stores this `renderer_glyph` value. It is not the physical
bitplane number inside `FONT.MMT`.

## Verified one-cell-left mapping with row wrap

The original ASCII assets establish that the texture sampled by the renderer is
one 16-pixel cell to the left of the nominal renderer group. For example:

- ASCII `A` becomes native code `80A5`.
- the renderer formula yields glyph `69` (group 17, plane 1).
- the `A` bitmap in the original `FONT.MMT` is physical slot `65`
  (group 16, plane 1).

For ordinary columns this looks like `physical_slot = renderer_glyph - 4`, but
that shorthand is **wrong at the first cell of each 64-cell texture row**. The
one-cell-left relation wraps horizontally inside the same row instead of moving
to the previous row.

```text
renderer_group = renderer_glyph // 4
plane          = renderer_glyph & 3
row            = renderer_group // 64
column         = renderer_group % 64

physical_group = row * 64 + ((column - 1) % 64)
physical_slot  = physical_group * 4 + plane
```

This rule is a bijection across all 2048 physical slots. It also explains the
runtime report `없음 -> 없본`: `음` is renderer slot 1282, which is in the first
cell of a row. The old global `-4` rule wrote it to physical slot 1278, while the
renderer actually samples physical slot 1534 after horizontal wrap. That slot
contained `본` in the old build.

The affected Korean renderer slots in the current 1,133-character mapping were:

```text
1024..1027  퍼 팽 팬 팩
1280..1283  읏 읍 음 읊
1536..1539  봄 볼 본 복
1792..1795  되 됐 돼 동
```

All are fixed by the row-wrap mapping; no per-character exception table is used.

## Physical FONT.MMT geometry

The glyph area is arranged as 512 physical 16x12 cells, with four independent
1-bit glyphs stored in each cell's four nibble bits:

```text
physical_group = physical_slot // 4
physical_plane = physical_slot & 3
```

The physical plane order is the natural `0,1,2,3` order.

## Galmuri11 placement

Korean full-size glyphs use Galmuri11. Runtime screenshots established that
`x_offset=2` clips the rightmost Galmuri column, which contains the short arm of
`ㅏ` and made every `ㅏ` syllable resemble the corresponding `ㅣ` syllable.
Production placement is:

```text
x_offset = 1
y_offset = 0
```

Small 1-byte UI text is a separate problem and should not be solved by changing
this full-size mapping. The project is investigating `OFONT.MMT` + Galmuri7 for
compact UI labels, while item/monster names stay on the DBCS `FONT.MMT` path.

## Reservation policy

The project allocates Korean renderer glyphs from the high end down, while
reserving renderer glyphs through 279 for original ASCII/Japanese conversion
assets. MSG, FONT and SCENARIO names share one deterministic mapping.

## Regression history

- v1/v2: renderer glyph written directly to physical slot -> shifted glyphs.
- v3: incorrect 0/2 bitplane-swap theory -> still corrupt.
- v4: empirical one-cell-left relation applied as a global `-4` -> most glyphs fixed, row-boundary glyphs still wrong.
- v5+: Galmuri x offset 2 -> 1 -> `ㅏ` clipping fixed.
- v8: one-cell-left relation corrected to wrap inside each 64-cell texture row -> isolated substitutions such as `음 -> 본` fixed.
