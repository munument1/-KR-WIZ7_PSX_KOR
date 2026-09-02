# PSX v8 item / font boundary stabilization

## Runtime reports addressed

- item information screen contained garbled Korean text
- item names still appeared as Japanese/garbled 1-byte text even though Korean names were present in `SCENARIJ.DBS`
- isolated Korean syllables were substituted by other valid Korean syllables, e.g. `없음 -> 없본`

## 1. FONT.MMT row-boundary mapping

The old v4-v7 mapping used `physical_slot = renderer_glyph - 4` globally. That is only valid away from a texture-row boundary.

The renderer/texture relationship is one 16px cell to the left with horizontal wrap inside each 64-cell row:

```text
physical_group = row * 64 + ((renderer_column - 1) % 64)
physical_slot  = physical_group * 4 + plane
```

Current mapping boundary characters fixed by this rule:

- slots 1024..1027: `퍼 팽 팬 팩`
- slots 1280..1283: `읏 읍 음 읊`
- slots 1536..1539: `봄 볼 본 복`
- slots 1792..1795: `되 됐 돼 동`

The corrected font was regenerated for all 1,133 mapped Korean characters and every generated Galmuri11 bitmap matched its computed physical slot.

## 2. Item-name renderer calls

The English PS1 executable contains byte-oriented and DBCS-aware item-name draw wrappers. Korean `SCENARIJ.DBS` names must use the DBCS-aware variants.

Patched callsites:

```text
PSX.EXE 0x102F0: jal 0x8006D004 -> jal 0x8006D198
PSX.EXE 0x10330: jal 0x8006D004 -> jal 0x8006D198
PSX.EXE 0x54078: jal 0x8006D0A0 -> jal 0x8006D2FC
PSX.EXE 0x54094: jal 0x8006D0A0 -> jal 0x8006D2FC
PSX.EXE 0x540BC: jal 0x8006D0A0 -> jal 0x8006D2FC
PSX.EXE 0x540D8: jal 0x8006D0A0 -> jal 0x8006D2FC
```

These changes are guarded and idempotent in `patch_korean_psx_exe.py`.

## 3. Compact item UI stabilization

The following MSG ranges are still rendered by compact/byte-width UI paths and are restored to the upstream PSX English bytes until those individual widgets are made DBCS-safe:

- 300..309
- 350..358
- 400..413
- 450..487

This keeps labels such as USE/ASSAY/DAMAGE/SPECIAL/RESISTANCES readable while Korean item names remain DBCS through `FONT.MMT`.

## Verification

The v8 test image differs from the verified Gertius PS1 English base in exactly seven files:

```text
PSX.EXE
CDS/D/MISCJ.HDR
CDS/D/MSGJ.HDR
CDS/D/MSGJ.DBS
CDS/D/SCENARIJ.DBS
CDS/T/FONT.MMT
CDS/T/TITL.MMT
```

v8 test BIN after the row-wrap fix:

- MD5: `fcb5eb5d6d5db9ac511585b9d7e74033`
- SHA-256: `50237b8b2feb0ec9f30896fb93810d65307ebad9ae7df0295788389ea3371ed6`
- size: `324187920` bytes

xdelta roundtrip reproduced the v8 BIN byte-for-byte. BIN -> CHD -> BIN also reproduced it byte-for-byte.
