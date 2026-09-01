# Wizardry VII PSX Korean font pipeline

This directory contains the first Korean-specific tooling for the PSX port.
It is intentionally separated from the original English patch utilities so the
encoding/font experiments can be reviewed and reverted independently.

## Why the 1-byte menus are not necessarily English-only

The decompiled `FUN_ASCIItoZENKAKU()` in this repository has a special path for
input bytes `0x80..0x9F`: it copies the current byte and the following byte to
the output without passing them through the ASCII lookup table. In other words,
the existing Japanese executable already has a two-byte ingress path before the
text renderer.

That makes the working Korean design:

```text
ASCII bytes              -> existing ASCII -> ZENKAKU mapping
Korean two-byte sequence -> existing 0x80..0x9F pass-through -> PSX renderer
```

This is useful for `SCENARIJ.DBS` and other byte-oriented menu/item strings: the
storage can remain a byte string while Korean characters occupy two bytes.
Whether every field has enough *length* for the expanded strings still has to be
checked per structure.

## Current status

`build_korean_font.py` currently provides only safe, reproducible intermediate
steps:

1. Scan UTF-8/CP949/EUC-KR translation files for the actually used Hangul.
2. Allocate a deterministic provisional two-byte code for each Hangul glyph.
3. Read the official Galmuri11 BDF and extract only the required glyphs.
4. Emit an 11x11 logical bitmap intermediate (`korean_glyphs.bin`).
5. Encode Unicode text using the generated mapping.

It does **not** yet patch `PSX.EXE` or produce a native game font file. The
repository documents `ZENKAKU.TBL` as a 16-bit character mapping table, but the
actual downstream two-byte-code -> glyph bitmap/index calculation has not yet
been documented. We should verify that formula before writing a native packer.

The generated DBCS values are therefore marked **PROVISIONAL**. Do not bulk
insert them into a ROM image until the renderer mapping has been verified with a
small one-glyph test.

## Galmuri11

Galmuri is maintained at `quiple/galmuri` and is licensed under the SIL Open Font
License 1.1. The font itself is not copied into this repository. Obtain the
official `dist/Galmuri11.bdf` and pass its local path to the tool.

## Usage

Build a charset/mapping from translation files:

```bash
python build_korean_font.py build path/to/translations --out build/korean-font
```

Also extract Galmuri11 glyphs:

```bash
python build_korean_font.py build path/to/translations \
  --bdf path/to/Galmuri11.bdf \
  --out build/korean-font
```

Encode a UTF-8 text file using the generated mapping:

```bash
python build_korean_font.py encode \
  --mapping build/korean-font/korean_dbcs.tsv \
  --input translated.txt \
  --output translated.dbcs
```

Run tests from this directory:

```bash
python -m unittest -v
```

## Generated files

- `charset.txt` - sorted Hangul character set.
- `korean_dbcs.tsv` - Unicode/code/frequency table.
- `build_info.json` - records that the allocation is provisional.
- `korean_glyphs.bin` - optional Galmuri11 logical bitmap stream; each glyph is
  11 rows of a 16-bit big-endian value (22 bytes/glyph). This is an intermediate
  representation, **not** the confirmed PSX native font format.
- `korean_glyphs.tsv` - offsets and code associations for the bitmap stream.

## Next reverse-engineering checkpoint

Before a real ROM patch is generated, trace the consumer of the two-byte output
from `FUN_ASCIItoZENKAKU()` and determine:

1. which lead/trail combinations are legal downstream,
2. how the two bytes select a Japanese glyph,
3. where that glyph bitmap is loaded from,
4. the native pixel dimensions/packing,
5. whether string-length and width calculations count bytes or characters.

Then replace one Japanese glyph slot with one Hangul glyph (for example `가`),
encode a single test label through the `0x80..0x9F` pass-through path, and verify
it in an emulator before scaling up the table.
