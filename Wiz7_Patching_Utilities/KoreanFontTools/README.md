# Wizardry VII PSX Korean font pipeline

This directory contains the Korean-specific font/encoding work for the PSX port.

## Why the 1-byte menus are not necessarily English-only

The decompiled `FUN_ASCIItoZENKAKU()` has a special path for input bytes
`0x80..0x9F`: it copies the current byte and the following byte to the output.
That means the Japanese executable already accepts a two-byte text path before
the renderer.

Working design:

```text
ASCII bytes              -> existing ASCII -> ZENKAKU mapping
Korean two-byte sequence -> existing 0x80..0x9F pass-through -> PSX renderer
```

This can be used for `SCENARIJ.DBS` and other byte-oriented menu/item strings.
Individual field lengths still have to be checked because one Korean character
uses two bytes.

## Galmuri11 bitmap extraction

The user does not need to pre-extract Galmuri glyph images.

`build_korean_font.py` does the extraction itself:

1. scans translation files for the actually used Hangul,
2. creates a deterministic provisional DBCS table,
3. downloads the official `Galmuri11.bdf` from `quiple/galmuri` by default,
4. parses each BDF `BITMAP` block directly,
5. emits only the required 11x11 logical glyphs.

For offline use, `--bdf path/to/Galmuri11.bdf` can be supplied. The Galmuri font
file itself is not committed to this repository.

Galmuri is licensed under SIL Open Font License 1.1.

## Verified FONT.MMT layout

`font_mmt.py` reads and writes the actual PSX `FONT.MMT` structure.

Verified geometry:

- file size: 50,724 bytes
- header: 36 bytes
- pixel payload: 1024 x 99, 4bpp
- CLUT/palette area: y=0..2
- glyph area: y=3..98
- physical glyph cell: 16 x 12
- 64 x 8 physical cells = 512 physical groups
- four logical glyphs share each physical cell as four nibble bitplanes
- total logical glyph slots: 2048

A logical glyph index uses:

```text
physical_group = glyph_index // 4
bitplane       = glyph_index % 4
```

The packer preserves the other three glyph bitplanes when replacing one glyph.
Round-trip testing against the real Japanese `FONT.MMT` confirms that extracting
ASCII `A` (logical slot 65) and writing it back produces a byte-identical file.
Blanking only slot 65 leaves the neighboring `9`, `B`, and `C` bitplanes intact.

## Usage

Build charset + DBCS + Galmuri11 bitmap intermediates:

```bash
python build_korean_font.py build path/to/translations --out build/korean-font
```

Offline Galmuri source:

```bash
python build_korean_font.py build path/to/translations \
  --bdf path/to/Galmuri11.bdf \
  --out build/korean-font
```

Encode a Unicode text file with the generated mapping:

```bash
python build_korean_font.py encode \
  --mapping build/korean-font/korean_dbcs.tsv \
  --input translated.txt \
  --output translated.dbcs
```

Run tests:

```bash
python -m unittest -v
```

## Generated files

- `charset.txt` - used Hangul characters
- `korean_dbcs.tsv` - Unicode/provisional code mapping
- `build_info.json` - build metadata
- `korean_glyphs.bin` - 11x11 Galmuri bitmap rows, 22 bytes per glyph
- `korean_glyphs.tsv` - glyph offsets and code associations

## Remaining reverse-engineering checkpoint

The font container itself is now understood. The remaining important step is to
determine the complete formula used by the renderer to turn a passed-through
2-byte code into one of the 2048 logical glyph indices.

One confirmed point is:

```text
ASCII 'A' -> ZENKAKU.TBL 0x80A5 -> FONT.MMT logical slot 65
```

Once the complete code-to-slot mapping is recovered, the provisional Korean
DBCS allocator can be replaced with the real renderer-compatible allocator and
the tool can automatically pack all required Galmuri11 glyphs into `FONT.MMT`.
