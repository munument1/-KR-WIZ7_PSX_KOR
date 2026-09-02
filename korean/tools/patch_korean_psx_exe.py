#!/usr/bin/env python3
"""Patch Wizardry VII PSX.EXE for native Korean text.

The production patch keeps the Gertius PS1 English patch as its runtime base and
adds two independent Korean extensions:

1. DBCS-aware message line wrapping at 0x800C9800.
2. Direct-native item-name draw wrappers at 0x800C4070.

The item wrappers are important because SCENARIJ.DBS item names are already
encoded in the project's native Korean DBCS. The stock Japanese/English item
wrappers run their input through the original Shift-JIS -> native conversion
routine first; feeding already-native Korean bytes through that converter
corrupts them. The injected wrappers preserve the original cursor/font families
but skip Shift-JIS conversion and send the native bytes directly to the low-level
renderer.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

CALL_OFFSET = 0x4D028
CALL_ORIGINAL = bytes.fromhex("c2b5010c")
CALL_PATCHED = bytes.fromhex("0026030c")
LOWERCASE_OFFSET = 0x5D3F8

WRAP_INJECT_OFFSET = 0xBA000
WRAP_INJECT_RUNTIME = 0x800C9800
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

# Empty executable cave in the supported PS1 build / Gertius English patch.
ITEM_INJECT_OFFSET = 0xB4870
ITEM_INJECT_RUNTIME = 0x800C4070
ITEM_NATIVE_DRAW_CODE = bytes.fromhex(
    "d8ffbd272400bfaf2000b2af1c00b1af1800b0af25808000aa2a013cabaa21340d80023c981451340000328e000000001800"
    "410210180000c81442340000428c000000001800410010080000c2170300431803000e80043c343784340000878c1000b0af"
    "21286200c2170100430801000780033c21302200506f793409f82003ffff04240880013c243c393409f82003252000024008"
    "0200801002002108410021083200000021ae1800b08f1c00b18f2000b28f2400bf8f000000000800e0032800bd27e8ffbd27"
    "1400bfaf1000b0af258080000680013c84cd39342520a00009f820032528c0001c10030c252000021000b08f1400bf8f0000"
    "00000800e0031800bd27d8ffbd272400bfaf2000b2af1c00b1af1800b0af258080000d80013cd80431340000328eaa2a023c"
    "abaa4234dc0421340000218c00000000a0ff21241800220010080000d6ff432618006200101000000e80033c343763340000"
    "678c1000a4afc21f0200431002000780043c0c4f993421284300c2170100430801002130220009f82003010004240880013c"
    "243c393409f820032520000240080200801002002108410021083200000021ae1800b08f1c00b18f2000b28f2400bf8f0000"
    "00000800e0032800bd27e8ffbd271400bfaf1000b0af258080000680013cb4cc39342520a00009f820032528c0005d10030c"
    "252000021000b08f1400bf8f000000000800e0031800bd2701001704"
)
ITEM_NATIVE_DRAW_SHA256 = "60fdf9a2050126aaf46b78fcf01d12800cc419ff67c1471ad7ccf939c222ccba"
assert len(ITEM_NATIVE_DRAW_CODE) == 528
assert hashlib.sha256(ITEM_NATIVE_DRAW_CODE).hexdigest() == ITEM_NATIVE_DRAW_SHA256

# Runtime entry points within ITEM_NATIVE_DRAW_CODE.
DRAW_NATIVE_A = 0x800C4070
DRAW_NATIVE_A_AT = 0x800C4134
DRAW_NATIVE_B = 0x800C4174
DRAW_NATIVE_B_AT = 0x800C423C

# Each tuple is (file offset, accepted pre-v9 call bytes, v9 call bytes).
# We accept the original English-base call, the incorrect v8 experiment where
# applicable, and the v9 call itself so patching is guarded and idempotent.
ITEM_DRAW_CALL_PATCHES = (
    # Direct list draws, first cursor/font family.
    (0x102F0, (bytes.fromhex("01b4010c"), bytes.fromhex("66b4010c")), bytes.fromhex("1c10030c")),
    (0x10330, (bytes.fromhex("01b4010c"), bytes.fromhex("66b4010c")), bytes.fromhex("1c10030c")),
    # Slash-split item-name helper: first two draws use the second cursor family.
    (0x54030, (bytes.fromhex("bfb4010c"),), bytes.fromhex("8f10030c")),
    (0x5404C, (bytes.fromhex("bfb4010c"),), bytes.fromhex("8f10030c")),
    # Remaining split-name draws use the first cursor family.
    (0x54078, (bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")), bytes.fromhex("4d10030c")),
    (0x54094, (bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")), bytes.fromhex("4d10030c")),
    (0x540BC, (bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")), bytes.fromhex("4d10030c")),
    (0x540D8, (bytes.fromhex("28b4010c"), bytes.fromhex("bfb4010c")), bytes.fromhex("4d10030c")),
)

MIN_SIZE = max(
    WRAP_INJECT_OFFSET + len(KOREAN_WRAP_CODE),
    ITEM_INJECT_OFFSET + len(ITEM_NATIVE_DRAW_CODE),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inject_guarded(out: bytearray, offset: int, blob: bytes, label: str, notes: list[str]) -> None:
    current = bytes(out[offset : offset + len(blob)])
    if current == blob:
        notes.append(f"{label} already injected at 0x{offset:X}")
        return
    if any(current):
        first = next(i for i, b in enumerate(current) if b)
        raise ValueError(
            f"{label} code cave is not empty at PSX.EXE 0x{offset + first:X}: "
            f"0x{current[first]:02X}"
        )
    out[offset : offset + len(blob)] = blob
    notes.append(f"injected {label} at 0x{offset:X} ({len(blob)} bytes)")


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

    _inject_guarded(out, WRAP_INJECT_OFFSET, KOREAN_WRAP_CODE, "Korean line-wrap routine", notes)
    _inject_guarded(out, ITEM_INJECT_OFFSET, ITEM_NATIVE_DRAW_CODE, "native item draw wrappers", notes)

    for offset, accepted, patched in ITEM_DRAW_CALL_PATCHES:
        current = bytes(out[offset : offset + 4])
        if current == patched:
            notes.append(f"native item draw call at 0x{offset:X} already patched")
        elif current in accepted:
            out[offset : offset + 4] = patched
            notes.append(f"rerouted item-name draw call at 0x{offset:X} to direct-native wrapper")
        else:
            expected_text = ", ".join(x.hex(" ") for x in accepted)
            raise ValueError(
                f"unexpected bytes at item draw call 0x{offset:X}: {current.hex(' ')}; "
                f"expected one of [{expected_text}] or {patched.hex(' ')}"
            )

    return bytes(out), notes


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Patch Wizardry VII PSX.EXE for Korean DBCS rendering"
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
