# PSX v3 English-base + FONT bitplane verification (2026-09-01)

## Why v3 was needed

Runtime testing exposed two separate issues in the first Korean full-disc build:

1. Korean glyphs were readable shapes but the wrong Hangul was selected for many characters.
2. Several PS1-only menus/media assets were still Japanese because the Korean build had been layered directly onto the Japanese disc instead of preserving the complete upstream English ROMhack changes.

## FONT.MMT renderer plane fix

Runtime screenshots proved that four logical glyph slots sharing one physical 16x12 FONT.MMT cell do not use identity bitplane order.

Verified logical -> physical nibble-bit mapping:

```text
0 -> 2
1 -> 1
2 -> 0
3 -> 3
```

Therefore the renderer plane permutation is:

```text
(2, 1, 0, 3)
```

Using `(0, 1, 2, 3)` caused logical planes 0 and 2 to display the other Korean glyph stored in the same physical cell. `font_mmt.py` and its unit tests now encode this verified permutation.

Corrected Korean FONT.MMT internal build SHA-256:

```text
e34584f0f18934302ee144a4fa2ae3725c6d55ccc079dd5124a19af6ff692178
```

The font binary itself is not distributed or committed.

## Upstream English base

Upstream:

```text
Gertius / WIZ7_PSX_ENG V1.0
```

Verified Japanese raw source BIN:

```text
MD5    188d3ee5a2a2242a719f290ea595e5ec
CRC32  bab5dd73
```

Verified upstream `Wiz7_patch.xdelta`:

```text
SHA-256 c689d37560dbe3cccc096d7fccfb288f0fc9edd0de9879557e048f42e580764a
```

Resulting upstream English V1.0 BIN:

```text
MD5     7fb464147ab7144facae337226c91aa5
CRC32   a24a7e4a
SHA-256 6d61aaccf5a21853077f96b66e5fea4a2859611d89b5a93358e79d2f504c1683
```

`korean/tools/apply_upstream_english_base.py` reproduces this BIN byte-for-byte from the verified Japanese source + separately supplied upstream xdelta.

## Files changed by upstream English V1.0

Compared with the Japanese source filesystem, upstream English V1.0 changes exactly 12 game files:

```text
CDS/D/MISCJ.HDR
CDS/D/MSGJ.DBS
CDS/D/MSGJ.HDR
CDS/D/PCFILE.
CDS/D/SCENARIJ.DBS
CDS/D/SCENARIO.HDR
CDS/D/TALK.SCR
CDS/M/BOOK.STR
CDS/M/OPEN.STR
CDS/M/OPEN.TXT
CDS/S1/AD.XA
PSX.EXE
```

This is why building Korean directly on top of the Japanese disc left some menus/media in Japanese.

## v3 layering strategy

v3 starts from the complete upstream English V1.0 disc and then layers Korean assets on top:

- Korean `MISCJ.HDR / MSGJ.HDR / MSGJ.DBS`
- corrected Korean `FONT.MMT`
- Korean-aware `PSX.EXE`
- Korean item/monster names applied to the **English-base** `SCENARIJ.DBS`

All other upstream English changes are preserved, including menu/media/script fixes.

Compared with the original Japanese disc, v3 changes exactly 13 files:

```text
CDS/D/MISCJ.HDR
CDS/D/MSGJ.DBS
CDS/D/MSGJ.HDR
CDS/D/PCFILE.
CDS/D/SCENARIJ.DBS
CDS/D/SCENARIO.HDR
CDS/D/TALK.SCR
CDS/M/BOOK.STR
CDS/M/OPEN.STR
CDS/M/OPEN.TXT
CDS/S1/AD.XA
CDS/T/FONT.MMT
PSX.EXE
```

No unexpected file-set changes were found after rebuilding and re-extracting the disc.

## v3 output verification

Internal v3 BIN:

```text
MD5     7b94f5ccb6cfcbd0c87a856d8c60056a
SHA-256 80781023cae9e3c96d72f4d090995931f1f8df0f87bb40ff2eaf200827eb38f9
Size    324150288 bytes
```

Distribution xdelta:

```text
SHA-256 09a73307a9c73c46dd86e2ab7dee1eb5d60aa6e3141a93cedb2b7f3588268264
```

Validation completed:

- source Japanese BIN -> v3 xdelta -> v3 BIN: byte-identical
- v3 BIN -> CHD -> BIN: byte-identical
- CHD verification: successful
- rebuilt v3 filesystem vs original Japanese filesystem: exactly 13 changed files

The full BIN/CHD and extracted game assets are verification-only and are not committed or distributed.

## Remaining validation

The binary pipeline is verified. Actual gameplay testing is still required, especially:

- the previously corrupted Korean menu text
- formerly Japanese PS1-specific menus
- new game / starter party screens
- NPC topics and event progression
- intro/media text
- item/monster names and scenario events
