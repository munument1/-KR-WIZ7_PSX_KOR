# PSX native font codepage reverse engineering

## Result

Wizardry VII PSX already has a 2-byte character path and its renderer maps a
2-byte character directly into one of the 2048 logical `FONT.MMT` bitplanes.
No custom glyph lookup table is required for Korean.

## Entry path

`FUN_ASCIItoZENKAKU` is at `0x8006CB80`.

For input lead bytes `0x80..0x9F`, it copies two input bytes to the output
unchanged. Relevant UI callers then pass that output into the normal text
renderer (`0x80076F50` path).

## Renderer disassembly

At `0x80074FD4` the renderer reads the second byte after recognizing the lead.
The decisive sequence is:

```text
80074FDC  sll   code, lead, 8
80074FE0  addu  code, code, trail
80074FE4  andi  tmp, code, 0x80
80074FE8  beqz  tmp, low_trail
80074FEC  andi  local, code, 0xff
80074FF4  addiu local, local, -0x60
80074FF8  addiu local, local, -0x30   # low-trail branch
80074FFC  sra   tmp, code, 1
80075000  andi  tmp, tmp, 0x1f80
80075004  addu  glyph, local, tmp
```

For leads `0x80..0x8F`, `(code >> 1) & 0x1F80` is equivalent to
`(lead - 0x80) * 128` in the 2048-slot font window.

## Canonical native Korean code space

```text
lead 0x80..0x8F

trail 0x30..0x6F -> local 0..63
trail 0xA0..0xDF -> local 64..127

slot = (lead - 0x80) * 128 + local
```

Boundary examples:

| Slot | Native code |
| ---: | :--- |
| 0 | 8030 |
| 63 | 806F |
| 64 | 80A0 |
| 127 | 80DF |
| 128 | 8130 |
| 2047 | 8FDF |

Every slot from 0 through 2047 has one deterministic canonical code.

## FONT.MMT geometry connection

The renderer subsequently uses:

```text
plane = glyph & 3
group = glyph >> 2
```

`FONT.MMT` has 512 physical 16x12 groups, each storing four logical glyphs as
four bits of each 4bpp pixel. Thus `512 * 4 = 2048`, exactly matching the native
code space above.

## Reservation policy

The current `ZENKAKU.TBL` is 404 bytes = 202 native code pairs. Applying the
verified formula yields 198 unique valid font slots. The Korean builder reserves
all of these by default when `--zenkaku` is supplied.

```text
2048 total slots
-198 existing ZENKAKU targets
=1850 available Korean slots
```

This is deliberately conservative: it preserves every glyph that the existing
ASCII/half-width conversion table may request. Korean glyphs are allocated from
slot 2047 downward because the original assets are concentrated in the low banks.
If the final Korean corpus ever exceeds 1850 unique glyphs, the reservation policy
can be narrowed after auditing which legacy slots are still used.

## Note about old A -> slot assumption

An earlier visual POC associated ASCII `A`, ZENKAKU code `80A5`, and logical
slot 65. The actual renderer formula maps `80A5` to slot 69. Therefore that old
three-way association must not be used as codepage evidence. It likely reflects
a mismatch between patched English assets/table expectations or the visual
identification step. The mapping documented here comes directly from the real
renderer instructions and is what the Korean pipeline now uses.
