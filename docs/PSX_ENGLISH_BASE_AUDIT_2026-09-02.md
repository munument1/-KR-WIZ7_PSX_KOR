# Wizardry VII PSX Korean - English-base audit (2026-09-02)

## Decision

The production Korean build is based on **Gertius' Wizardry 7 PSX English Patch V1.0**, not the DOS or Wizardry Gold executable/assets.

```text
verified Japanese PS1 BIN/CHD
  -> Gertius WIZ7_PSX_ENG V1.0 xdelta
  -> exact English PS1 BIN
  -> Korean MSG/FONT/EXE/SCENARIO overlay
  -> fixed-width UI English fallback
  -> Korean title subtitle
  -> final Korean BIN/CUE/CHD or one xdelta against the Japanese BIN
```

Gold/DOS material remains translation-reference data only.

## Verified source images

Japanese raw BIN:
- MD5: `188d3ee5a2a2242a719f290ea595e5ec`
- CRC32: `bab5dd73`

Gertius PSX English V1.0 result:
- MD5: `7fb464147ab7144facae337226c91aa5`
- SHA-256: `6d61aaccf5a21853077f96b66e5fea4a2859611d89b5a93358e79d2f504c1683`

The English BIN can be extracted and rebuilt with dumpsxiso/mkpsxiso byte-for-byte identically.

## Files changed by the upstream PSX English patch

A full Japanese-vs-English filesystem hash comparison finds exactly 12 changed files:

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

Current Korean overlay files are:

```text
CDS/D/MISCJ.HDR
CDS/D/MSGJ.DBS
CDS/D/MSGJ.HDR
CDS/D/SCENARIJ.DBS
CDS/T/FONT.MMT
CDS/T/TITL.MMT
PSX.EXE
```

Therefore the English `PCFILE.`, `SCENARIO.HDR`, `TALK.SCR`, `BOOK.STR`, `OPEN.STR`, `OPEN.TXT` and `AD.XA` remain byte-identical to Gertius V1.0.

## Fixed-width character/status UI

Some character-sheet/status text paths are still 1-byte/fixed-width. Native Korean DBCS in these records caused omitted words and garbled glyph streams. Until those renderers are patched for DBCS, these ranges are deliberately restored from the PSX English patch before Huffman rebuild:

- 100..110 - race names
- 120..134 - profession names
- 140..141 - sex labels
- 160..162 - controller/pad hints
- 200..219 - LVL/RNK/EXP/attributes/status labels
- 800..937 - profession rank/title names

157 records differ from the Korean build and are replaced by their English PSX bytes in the stabilized output.

## MSG size / LBA preservation

The stabilized build pads the rebuilt Korean files to exactly the English sizes:

```text
MSGJ.HDR = 11,408 bytes
MSGJ.DBS = 254,969 bytes
```

This preserves the downstream English layout. `PCFILE.` remains at the English patch position and contains the English preset characters (`THESUS`, `TEMPEST`, `LYSAND`, `NOBAL`, `TREON`, `PENTAS`, ...).

## Visual asset audit

All 52 `.MMT` assets in the PS1 disc were decoded/rendered for inspection. The obvious remaining Japanese text in normal MMT image assets is `CDS/T/TITL.MMT`, whose title screen contains the baked subtitle `ガーディアの宝珠`.

Gertius V1.0 leaves this MMT byte-identical to the Japanese disc. The Korean build now removes that baked subtitle and draws `가디아의 보주` using glyphs from the already-generated Korean `FONT.MMT`; no font file or original game image is committed to git.

Other inspected logo MMTs are already non-Japanese:
- `CDS/M/TITLE.MMT` - PC version credits in English
- `CDS/M/SCELOGO.MMT` - `Sony Computer Entertainment Inc. Presents`

Opening/book/audio-stream assets modified by Gertius (`OPEN.STR`, `BOOK.STR`, `AD.XA`) are preserved rather than regenerated.

## v7 verified test image

Final raw BIN:
- MD5: `381cf7ff7509f35b5fbc423791ed689d`
- SHA-256: `7dc0fb63ccd4565542e07c134881d54c4faa84c7145b73c67d6d5708f5d67df1`

Final xdelta SHA-256:
- `b421320fa47264b185be5e8fb95417d639e656cd0a52750f4cbeb61edd0f896a`

Validation:
- Japanese source BIN -> final xdelta -> v7 BIN: byte-identical
- v7 BIN -> CHD -> BIN: byte-identical
- `chdman verify`: raw and overall SHA1 successful
- English filesystem -> v7 filesystem: exactly 7 intended files differ
- all other Gertius English-patch assets remain byte-identical

## Remaining runtime QA

1. preset character names becoming English instead of Japanese,
2. character info/status panel no longer emitting garbled lower-screen glyphs,
3. title screen showing `가디아의 보주`,
4. any PS1-specific fixed-width screen not covered by the current fallback ranges.
