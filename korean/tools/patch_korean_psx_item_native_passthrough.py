#!/usr/bin/env python3
"""Experimental PS1 Korean item-name renderer patch.

This deliberately does NOT inject a new renderer. It reuses the stock PS1 DBCS
path already present in Gertius' English-patched executable.

SCENARIJ.DBS Korean item names are already encoded in the project's native DBCS.
FUN_8006D198 detects high bytes, but normally converts its input through the
Japanese Shift-JIS -> native conversion buffer before handing it to the DBCS
renderer. Re-converting already-native Korean bytes is what made the v8 item
experiment render garbage.

The minimal experiment does two things:
1. NOP the instruction that replaces s0 (the original input pointer) with the
   temporary converted buffer pointer. The existing low-level DBCS call then
   receives the original native Korean bytes.
2. Redirect six item-name callsites to existing DBCS-capable wrappers already in
   the PS1 executable. No code cave, new MIPS routine, or calling convention is
   introduced.

This is intentionally separate from patch_korean_psx_exe.py until runtime play
validation confirms that inventory, item detail and appraisal screens are stable.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

# FUN_8006D198 runtime 0x8006D22C, payload 0x5D22C, PS-X EXE file +0x800.
PASSTHROUGH_OFFSET = 0x5DA2C
PASSTHROUGH_ORIGINAL = bytes.fromhex("1800b027")  # addiu s0,sp,0x18
PASSTHROUGH_PATCHED = bytes.fromhex("00000000")   # keep original s0 input pointer

# (file offset, English/stable call, existing PS1 DBCS-capable wrapper call)
ITEM_DRAW_CALL_PATCHES = (
    (0x102F0, bytes.fromhex("01b4010c"), bytes.fromhex("66b4010c")), # 8006D004 -> 8006D198
    (0x10330, bytes.fromhex("01b4010c"), bytes.fromhex("66b4010c")),
    (0x54078, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")), # 8006D0A0 -> 8006D2FC
    (0x54094, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")),
    (0x540BC, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")),
    (0x540D8, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")),
)
MIN_SIZE = max(PASSTHROUGH_OFFSET + 4, *(o + 4 for o, _, _ in ITEM_DRAW_CALL_PATCHES))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_exe(data: bytes) -> tuple[bytes, list[str]]:
    if len(data) < MIN_SIZE:
        raise ValueError(f"PSX.EXE is too small: {len(data)} bytes")
    out = bytearray(data)
    notes: list[str] = []

    current = bytes(out[PASSTHROUGH_OFFSET:PASSTHROUGH_OFFSET + 4])
    if current == PASSTHROUGH_ORIGINAL:
        out[PASSTHROUGH_OFFSET:PASSTHROUGH_OFFSET + 4] = PASSTHROUGH_PATCHED
        notes.append("kept original native DBCS input pointer in FUN_8006D198")
    elif current == PASSTHROUGH_PATCHED:
        notes.append("native DBCS input passthrough already enabled")
    else:
        raise ValueError(
            f"unexpected bytes at 0x{PASSTHROUGH_OFFSET:X}: {current.hex(' ')}; "
            f"expected {PASSTHROUGH_ORIGINAL.hex(' ')} or NOP"
        )

    for offset, original, patched in ITEM_DRAW_CALL_PATCHES:
        current = bytes(out[offset:offset + 4])
        if current == original:
            out[offset:offset + 4] = patched
            notes.append(f"item draw call 0x{offset:X}: existing DBCS wrapper enabled")
        elif current == patched:
            notes.append(f"item draw call 0x{offset:X}: already DBCS wrapper")
        else:
            raise ValueError(
                f"unexpected item call bytes at 0x{offset:X}: {current.hex(' ')}; "
                f"expected {original.hex(' ')} or {patched.hex(' ')}"
            )
    return bytes(out), notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Experimental native Korean PS1 item-name passthrough")
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    try:
        src = args.input.read_bytes()
        out, notes = patch_exe(src)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(f"input_sha256={sha256(src)}")
    print(f"output_sha256={sha256(out)}")
    for note in notes:
        print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
