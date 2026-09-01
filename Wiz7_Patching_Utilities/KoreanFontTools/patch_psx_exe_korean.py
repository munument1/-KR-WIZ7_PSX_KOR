#!/usr/bin/env python3
"""Apply the verified Wizardry VII PS1 Korean executable patches.

Patches the supported Japanese PSX.EXE only:
1. keep the English patch's ASCII/lowercase ZENKAKU table range fix,
2. reroute the story line-wrap call to the reserved code area,
3. inject a DBCS-aware replacement that counts a native 2-byte glyph as one
   logical character while returning byte offsets to the original caller.

No original executable bytes are distributed by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

EXPECTED_SIZE = 763904
EXPECTED_SOURCE_SHA256 = "b4773240bb77436eb2f6e68094960985086f021949ca7ecd4b4b78d9212af117"
EXPECTED_OUTPUT_SHA256 = "bb046a535f18963eef6fc00f9d6039b3cae0b10dd9274d944a289621c50994c0"

LOWERCASE_OFFSET = 0x5D3F8
LINEBREAK_CALL_OFFSET = 0x4D028
INJECT_FILE_OFFSET = 0xBA000
INJECT_VA = 0x800C9800

SOURCE_LOWERCASE_INSN = bytes.fromhex("60 00 62 28")
PATCHED_LOWERCASE_INSN = bytes.fromhex("70 00 62 28")
SOURCE_LINEBREAK_CALL = bytes.fromhex("c2 b5 01 0c")

# Assembled from Assembler Injects/LineBreak_Korean_DBCS.s with clang 17,
# mipsel-none-elf, .text section only. SHA-256:
# 9709dce16cf00cddff2635e38f11f6e2900cc25eb6cbaa37c75a9ac2c659f284
LINEBREAK_DBCS = bytes.fromhex(
    "254000002548000025500000ff00a5302158880000006c911600801100000000"
    "080085150000000010002d290400a01500000000251040010800e00300000000"
    "2550000180ff8d252000ad2d0500a011000000000200082501002925ecff0010"
    "000000000100082501002925e8ff0010000000001b0040110000000010002d29"
    "1b00a0110000000021588a0001006c9121000d2416008d110000000025000d24"
    "13008d110000000026000d2410008d11000000005d000d240d008d1100000000"
    "40000d240a008d110000000023000d2407008d11000000007c000d2404008d11"
    "00000000ffff02240800e00300000000251040010800e00300000000"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def jal_bytes(target_va: int) -> bytes:
    instr = 0x0C000000 | ((target_va >> 2) & 0x03FFFFFF)
    return struct.pack("<I", instr)


def patch(source: bytes) -> bytes:
    if len(source) != EXPECTED_SIZE:
        raise ValueError(f"unexpected PSX.EXE size {len(source)}; expected {EXPECTED_SIZE}")
    digest = sha256(source)
    if digest != EXPECTED_SOURCE_SHA256:
        raise ValueError(
            f"unsupported PSX.EXE SHA-256 {digest}; expected {EXPECTED_SOURCE_SHA256}"
        )
    if source[LOWERCASE_OFFSET:LOWERCASE_OFFSET+4] != SOURCE_LOWERCASE_INSN:
        raise ValueError("lowercase patch site does not match supported executable")
    if source[LINEBREAK_CALL_OFFSET:LINEBREAK_CALL_OFFSET+4] != SOURCE_LINEBREAK_CALL:
        raise ValueError("linebreak call site does not match supported executable")
    inject_end = INJECT_FILE_OFFSET + len(LINEBREAK_DBCS)
    if any(source[INJECT_FILE_OFFSET:inject_end]):
        raise ValueError("reserved executable injection area is not empty")

    out = bytearray(source)
    out[LOWERCASE_OFFSET:LOWERCASE_OFFSET+4] = PATCHED_LOWERCASE_INSN
    out[LINEBREAK_CALL_OFFSET:LINEBREAK_CALL_OFFSET+4] = jal_bytes(INJECT_VA)
    out[INJECT_FILE_OFFSET:inject_end] = LINEBREAK_DBCS
    result = bytes(out)
    if sha256(result) != EXPECTED_OUTPUT_SHA256:
        raise RuntimeError("patched PSX.EXE hash differs from verified build")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch WIZ7 Japanese PSX.EXE for native Korean DBCS")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        result = patch(args.input.read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(result)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}")
        return 2
    print(f"output={args.output} size={len(result)} sha256={sha256(result)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
