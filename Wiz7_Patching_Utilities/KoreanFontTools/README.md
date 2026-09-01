# Wizardry VII PSX Korean font pipeline

This directory contains the Korean-specific font/encoding tooling for the PSX port.

## Native two-byte path is already present

`FUN_ASCIItoZENKAKU()` at PSX address `0x8006CB80` has an existing path for
lead bytes `0x80..0x9F`: it copies the lead byte and the following byte directly
to its output. Korean therefore does not need a new DBCS ingress parser for text
that reaches this routine.

```text
ASCII                -> existing ASCII -> ZENKAKU conversion -> renderer
Korean native 2-byte -> existing pass-through                 -> renderer
```

## Verified renderer code -> FONT.MMT slot formula

The consumer at `0x80074F0C` was disassembled from the real `PSX.EXE`. The
relevant instructions are at `0x80074FDC..0x80075004`.

For the 50,724-byte `FONT.MMT`, use only these canonical codes:

- lead: `0x80..0x8F`
- trail `0x30..0x6F`: local slot `0..63`
- trail `0xA0..0xDF`: local slot `64..127`

Formula:

```text
if trail bit7 == 0:
    local = trail - 0x30
else:
    local = trail - 0x60

slot = (lead - 0x80) * 128 + local
```

Inverse:

```text
lead = 0x80 + slot // 128
local = slot % 128
trail = 0x30 + local   if local < 64
        0x60 + local   otherwise
```

This gives exactly `16 * 128 = 2048` addressable glyphs, matching `FONT.MMT`.
Although the parser recognizes leads through `0x9F`, leads `0x90..0x9F` would
address glyph numbers beyond this `FONT.MMT`, so the Korean allocator does not
use them.

`ZENKAKU.TBL` contains 202 code pairs. On the current source set they reference
198 unique valid FONT.MMT slots, with the highest at slot 279. Reserving all of
those leaves **1850 slots** for Korean while preserving the existing ASCII and
half-width conversion table targets. Korean allocation proceeds from slot 2047
downward, keeping as much distance as possible from the legacy low-slot area.

For CI builds that intentionally do not contain game assets, the builder also
supports `--reserve-low-through 279`. This conservatively reserves every slot
from 0 through 279 and leaves **1768 high slots** for Korean.

## Galmuri11 extraction

The user does not need to create glyph images. `build_korean_font.py` reads the
official Galmuri11 BDF itself and parses each BDF `BITMAP` block into an 11x11
logical bitmap. By default it downloads `dist/Galmuri11.bdf` from
`quiple/galmuri`; `--bdf` is available for an offline copy.

Galmuri itself is not committed to this repository. Galmuri is licensed under
SIL Open Font License 1.1.

## Verified FONT.MMT layout

`font_mmt.py` reads/writes the actual PSX font texture:

- file size: 50,724 bytes
- header: 36 bytes
- pixel payload: 1024 x 99, 4bpp
- CLUT/palette: y=0..2
- glyph area: y=3..98
- physical cell: 16 x 12
- 64 x 8 physical cells = 512 groups
- 4 logical glyphs share each physical cell as four nibble bitplanes
- total logical slots: 2048

```text
physical_group = slot // 4
bitplane       = slot % 4
```

Replacing one glyph only changes its bitplane. The other three glyphs sharing
the cell remain intact. Extracting a real slot and writing the same bitmap back
produces a byte-identical file.

## Build Korean font

With the original table and font extracted from the PS1 disc:

```bash
python build_korean_font.py build path/to/korean/translations \
  --zenkaku path/to/ZENKAKU.TBL \
  --font path/to/FONT.MMT \
  --out build/korean-font
```

Outputs include:

- `charset.txt` - actually used Hangul characters
- `korean_dbcs.tsv` - Unicode, native code and FONT.MMT slot
- `build_info.json` - verified mapping/build metadata
- `korean_glyphs.bin` - extracted Galmuri11 11x11 bitmaps
- `korean_glyphs.tsv` - glyph/code/slot associations
- `FONT_KOR.MMT` - original font with allocated slots replaced by Galmuri11

Offline font source:

```bash
python build_korean_font.py build path/to/korean/translations \
  --zenkaku path/to/ZENKAKU.TBL \
  --font path/to/FONT.MMT \
  --bdf path/to/Galmuri11.bdf \
  --out build/korean-font
```

Encode a UTF-8 text file using the generated native mapping:

```bash
python build_korean_font.py encode \
  --mapping build/korean-font/korean_dbcs.tsv \
  --input translated.txt \
  --output translated.dbcs
```

Inspect the native mapping directly:

```bash
python build_korean_font.py code --slot 64   # -> 80A0
python build_korean_font.py code --code 8FDF # -> slot 2047
```

Run tests:

```bash
python -m unittest -v
```

The current tests cover all 2048 native code/slot round trips, the real
ZENKAKU.TBL reservation count, BDF extraction, real FONT.MMT geometry, bitplane
preservation, and patched-font generation.

## Automated current-translation build

`.github/workflows/build-psx-korean-font.yml` keeps the technical branch
separate from translation work. On the technical branch it checks out the latest
`korean-localization` branch, downloads the pinned official Galmuri11 BDF from
v2.40.4, reserves slots `0..279`, and generates a copyright-safe artifact:

- `charset.txt`
- `korean_dbcs.tsv`
- `build_info.json`
- `korean_glyphs.bin`
- `korean_glyphs.tsv`

The workflow never uploads `FONT.MMT`, `ZENKAKU.TBL`, `PSX.EXE`, or any disc
image. The generated mapping/bitmap artifact can later be combined locally with
the user's extracted original `FONT.MMT` to produce `FONT_KOR.MMT`.

## Remaining integration work

The font/codepage side no longer needs a speculative bytecode design. The next
integration points are the game data builders and fixed-size UI structures:

1. feed `korean_dbcs.tsv` into Korean MSGJ.DBS/SCENARIJ.DBS generation,
2. audit fields whose limits are measured in bytes because Korean is two bytes,
3. patch any width/length routines that still count raw bytes as characters,
4. rebuild the disc and run end-to-end emulator checks.
