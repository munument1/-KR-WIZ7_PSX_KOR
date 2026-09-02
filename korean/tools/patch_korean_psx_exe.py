#!/usr/bin/env python3
"""Patch Wizardry VII Japanese PSX.EXE for native Korean text.

The patch is deliberately small and guarded by expected-byte checks:
- 0x4D028: reroute the original strchr-based line-wrap call to 0x800C9800
- 0x5D3F8: preserve the English patch's widened ASCII/ZENKAKU range (0x60->0x70)
- 0xBA000: inject the DBCS-aware 16-visible-glyph line-wrap routine

The embedded MIPS-I blob is generated from
`Assembler Injects/KoreanLineBreak16char.c`, linked at runtime address
0x800C9800. It is embedded here so end users do not need a MIPS compiler.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

CALL_OFFSET = 0x4D028
CALL_ORIGINAL = bytes.fromhex("c2b5010c")
CALL_PATCHED = bytes.fromhex("0026030c")
LOWERCASE_OFFSET = 0x5D3F8
INJECT_OFFSET = 0xBA000
INJECT_RUNTIME = 0x800C9800

KOREAN_WRAP_CODE = bytes.fromhex(
    "f8ffbd270400bfaf0000beaf25f0a003000007242d000224000003240000092400000624ffffe1302108810000002a80"
    "0000000021004011ffff6830ff00413105002510000000001a00c0100000000016004215000000001000012d35002010"
    "2540e00090ff41290c0020100100e924ffff213121088100000021900000000001002a2c020040150000000001000624"
    "02004015000000000200e9240100632425382001092603082548000119260308254020011926030825402001ffff2231"
    "1a0040100000000001002125ffff2130210881000000239000000000dfff64242000812c080020100000000001000124"
    "040881000080043c35008434240824000d002014000000005d0001240a006110000000007c0001240700611000000000"
    "1000012d04002010000000004e260308ffff0224ffff223125e8c0030000be8f0400bf8f000000000800e0030800bd27"
)
KOREAN_WRAP_SHA256 = "f91ae18e51f44a2fad28e1d0620891b2b03af6172b2ac9932b39d3972718d52c"
assert len(KOREAN_WRAP_CODE) == 336
assert hashlib.sha256(KOREAN_WRAP_CODE).hexdigest() == KOREAN_WRAP_SHA256
MIN_SIZE = INJECT_OFFSET + len(KOREAN_WRAP_CODE)

# Item-name draw callsites. The English patch has both byte-oriented and
# DBCS-aware wrappers. Korean SCENARIJ.DBS names must use the DBCS-aware
# variants or each two-byte native code is treated as two independent glyphs.
ITEM_DRAW_CALL_PATCHES = (
    # jal 0x8006D004 -> jal 0x8006D198
    (0x102F0, bytes.fromhex("01b4010c"), bytes.fromhex("66b4010c")),
    (0x10330, bytes.fromhex("01b4010c"), bytes.fromhex("66b4010c")),
    # jal 0x8006D0A0 -> jal 0x8006D2FC
    (0x54078, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")),
    (0x54094, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")),
    (0x540BC, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")),
    (0x540D8, bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_exe(data: bytes) -> tuple[bytes, list[str]]:
    if len(data) < MIN_SIZE:
        raise ValueError(
            f"PSX.EXE is too small: {len(data)} bytes; need at least {MIN_SIZE}"
        )

    out = bytearray(data)
    notes: list[str] = []

    call = bytes(out[CALL_OFFSET : CALL_OFFSET + 4])
    if call == CALL_ORIGINAL:
        out[CALL_OFFSET : CALL_OFFSET + 4] = CALL_PATCHED
        notes.append("rerouted line-wrap call to 0x800C9800")
    elif call == CALL_PATCHED:
        notes.append("line-wrap call already rerouted")
    else:
        raise ValueError(
            f"unexpected bytes at PSX.EXE 0x{CALL_OFFSET:X}: {call.hex(' ')}; "
            f"expected {CALL_ORIGINAL.hex(' ')} or {CALL_PATCHED.hex(' ')}"
        )

    value = out[LOWERCASE_OFFSET]
    if value == 0x60:
        out[LOWERCASE_OFFSET] = 0x70
        notes.append("enabled full ASCII/ZENKAKU conversion range (0x60 -> 0x70)")
    elif value == 0x70:
        notes.append("ASCII/ZENKAKU range patch already present")
    else:
        raise ValueError(
            f"unexpected byte at PSX.EXE 0x{LOWERCASE_OFFSET:X}: 0x{value:02X}; "
            "expected 0x60 or 0x70"
        )

    out[INJECT_OFFSET : INJECT_OFFSET + len(KOREAN_WRAP_CODE)] = KOREAN_WRAP_CODE
    notes.append(
        f"injected DBCS-aware 16-glyph wrap routine at 0x{INJECT_OFFSET:X} "
        f"({len(KOREAN_WRAP_CODE)} bytes, runtime 0x{INJECT_RUNTIME:08X})"
    )

    for offset, expected, patched in ITEM_DRAW_CALL_PATCHES:
        current = bytes(out[offset : offset + 4])
        if current == expected:
            out[offset : offset + 4] = patched
            notes.append(f"rerouted item-name draw call at 0x{offset:X} to DBCS-aware path")
        elif current == patched:
            notes.append(f"item-name draw call at 0x{offset:X} already DBCS-aware")
        else:
            raise ValueError(
                f"unexpected bytes at item draw call 0x{offset:X}: {current.hex(' ')}; "
                f"expected {expected.hex(' ')} or {patched.hex(' ')}"
            )

    return bytes(out), notes


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Patch Wizardry VII PSX.EXE for native Korean DBCS line wrapping"
    )
    parser.add_argument("input", type=Path, help="Japanese or English-patched PSX.EXE")
    parser.add_argument("output", type=Path, help="patched PSX.EXE output path")
    return parser


def main() -> int:
    args = make_parser().parse_args()
    try:
        source = args.input.read_bytes()
        patched, notes = patch_exe(source)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(patched)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    print(f"input_sha256={sha256(source)}")
    print(f"output_sha256={sha256(patched)}")
    for note in notes:
        print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
