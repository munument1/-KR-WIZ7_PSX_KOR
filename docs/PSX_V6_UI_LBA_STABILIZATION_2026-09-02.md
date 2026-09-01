# PSX v6 UI/LBA stabilization verification

## Runtime reports addressed

v5 runtime testing showed:

- Korean main text/font mostly rendered correctly after the renderer-slot and Galmuri placement fixes.
- Premade character names still appeared in Japanese even with an empty memory-card test.
- Character-sheet race/class/status labels were missing or rendered as garbage.

## Root causes

### 1. Compact character-sheet UI is not DBCS-safe

MSG IDs used by the character creation/sheet UI are handled by compact/fixed-width paths. Replacing short ASCII labels with multi-byte Korean expanded the byte count and caused missing/garbled labels.

v6 temporarily restores upstream PSX English ASCII for these proven compact ranges:

- 100..110 race names
- 120..134 class names/cancel
- 140..141 gender
- 160..162 shoulder-button strings including original control bytes
- 200..219 LVL/RNK/EXP/MKS/stats/AGE/LIFE/NEXT LVL
- 800..937 profession rank titles

This is a stability fallback until those specific UI render/copy routines are patched for DBCS.

### 2. Rebuilding with a smaller Korean MSGJ.DBS moved downstream LBAs

Upstream PSX English V1.0:

- MSGJ.DBS starts at LBA 605
- MSGJ.HDR starts at LBA 730
- PCFILE. starts at LBA 742
- SCENARIJ.DBS starts at LBA 747

v5 Korean MSGJ.DBS was smaller, moving PCFILE. to LBA 726 and SCENARIJ.DBS to 731.

v6 rebuilds with the upstream English LBA layout and pads the generated Korean MSG files to the upstream file sizes:

- MISCJ.HDR: 1024
- MSGJ.HDR: 11408
- MSGJ.DBS: 254969

The padding is outside all generated record addresses and is ignored by the message header. It exists only to preserve downstream disc placement.

v6 verified LBAs:

- MSGJ.DBS: 605
- MSGJ.HDR: 730
- PCFILE.: 742
- SCENARIJ.DBS: 747

The first user-data bytes at v6 LBA 742 are the upstream English PCFILE record and contain `THESUS`.

## v6 image verification

Source raw BIN MD5:

`188d3ee5a2a2242a719f290ea595e5ec`

v6 BIN:

- MD5: `38045b4a8629343c32b090f4f837ba7e`
- SHA-256: `a531ca24bb0d70ed7989dfe72a9fb571706176a36165fd392fb07a649db3c342`
- size: 324185568 bytes (same as upstream PSX English V1.0 image)

v6 xdelta SHA-256:

`25138af8fd60c50d7decded07c6d9c53c6dfe6870ec79e6e20c1e5c419e1af3a`

Checks performed:

- source BIN -> v6 xdelta -> output is byte-identical to v6 BIN
- v6 BIN -> CHD -> BIN roundtrip is byte-identical
- re-extracted v6 differs from upstream English base in exactly six intended files: PSX.EXE, FONT.MMT, SCENARIJ.DBS, MISCJ.HDR, MSGJ.HDR, MSGJ.DBS
- PCFILE., SCENARIO.HDR, TALK.SCR and all English PSX media/menu assets remain byte-identical to upstream English V1.0

## Font state carried into v6

- physical FONT.MMT bitplanes use identity order 0,1,2,3
- physical FONT.MMT slot = renderer glyph - 4
- Galmuri11 x placement normalized to 1 pixel; legacy x-offset 2 is treated as 1 to prevent clipping the rightmost column used by ㅏ
