# Wizardry VII PSX Korean v9 - item native renderer fix

Date: 2026-09-02

## Reported regression

The v8 test build changed item-name draw calls from the byte-oriented wrappers to
existing Japanese DBCS wrappers. In game this made the entire item-name area turn
into control-looking glyphs/icons instead of Korean text.

## Root cause

`SCENARIJ.DBS` item fields are already encoded with the project's shared native
Korean DBCS mapping. The existing Japanese full-width wrappers are not generic
"already-native DBCS" renderers: they first run the input through the original
Shift-JIS -> native conversion routine. Feeding Korean native bytes into that
converter corrupts the byte stream before drawing.

v8 therefore used the wrong abstraction even though the target renderer itself
was capable of displaying the Korean FONT.MMT glyphs.

## v9 fix

A new 528-byte MIPS-I code blob is injected into a verified empty PSX.EXE cave:

- file offset: `0xB4870`
- runtime: `0x800C4070`
- SHA-256: `60fdf9a2050126aaf46b78fcf01d12800cc419ff67c1471ad7ccf939c222ccba`

The blob provides four wrappers:

- `0x800C4070` direct-native draw, cursor/font family A
- `0x800C4134` direct-native draw-at, family A
- `0x800C4174` direct-native draw, cursor/font family B
- `0x800C423C` direct-native draw-at, family B

These wrappers preserve the original screen-coordinate and font-family behavior,
but skip Shift-JIS conversion and pass the already-native Korean bytes directly
to the low-level PS1 text renderer.

Eight item-name call sites are redirected:

- `0x102F0`, `0x10330` -> family A direct-native draw
- `0x54030`, `0x5404C` -> family B direct-native draw-at
- `0x54078`, `0x54094`, `0x540BC`, `0x540D8` -> family A direct-native draw-at

The earlier v8 calls are accepted by the patcher only as an upgrade input; they
are not emitted by v9.

Reproducible C source is stored at:

`Assembler Injects/KoreanItemNativeDraw.c`

## Other retained fixes

v9 retains the v8 `FONT.MMT` row-boundary correction that fixed isolated valid
Hangul substitutions such as `없음 -> 없본`. It also retains the English-base
fixed-width UI stabilization while the separate `OFONT.MMT` / Galmuri7 small-UI
work is pending.

## Full-disc verification

Candidate v9 raw BIN:

- MD5: `3b3f08395e545e9d42930bd0f780491e`
- SHA-256: `9af89f1545cbfd5e17b6b8cdeef482ddc473d0ffc2fbc40375283ade727a6adc`
- size: `324187920` bytes

v9 xdelta:

- MD5: `997bb307fde02c6e9e48f51068418d79`
- SHA-256: `89c1c88a88495460442d6e5c6492ddee9d5017372e7d9466a1683f3759c78d66`
- size: `405631` bytes

Verified:

1. source BIN -> v9 xdelta -> v9 BIN is byte-identical.
2. v9 BIN -> CHD -> BIN is byte-identical.
3. `chdman verify` reports successful raw and overall SHA1 verification.
4. Re-extracted v9 and v8 have identical file sets; only `PSX.EXE` differs.
5. Re-extracted v9 vs Gertius PS1 English base differs in exactly seven intended files:
   `MISCJ.HDR`, `MSGJ.DBS`, `MSGJ.HDR`, `SCENARIJ.DBS`, `FONT.MMT`, `TITL.MMT`, `PSX.EXE`.

## Runtime test focus

- inventory item-name list
- item detail/assay screens
- slash-split two-line item names
- `특이한 것은 없음` and other previously mis-mapped boundary Hangul

The compact one-byte UI remains intentionally English until the separate
Galmuri7/OFONT path is implemented.
