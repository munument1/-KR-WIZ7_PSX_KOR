#!/usr/bin/env python3
"""Verified native Korean codepage for Wizardry VII PSX.

PSX.EXE's renderer maps two-byte native codes to FONT.MMT slots as:

    slot = (lead - 0x80) * 128 + local

Canonical codes for the 2048-slot FONT.MMT are:
- lead 0x80..0x8F
- trail 0x30..0x6F -> local 0..63
- trail 0xA0..0xDF -> local 64..127

For Korean we conservatively reserve slots 0..279 for the original Japanese /
ASCII conversion assets and allocate Hangul from slot 2047 downward. Characters
are sorted by Unicode code point so the mapping is deterministic and matches the
font pipeline on feat/korean-font-pipeline.
"""
from __future__ import annotations

import collections
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

HANGUL_RE = re.compile(r"[\u3131-\u318E\uAC00-\uD7A3]")
NATIVE_GLYPH_COUNT = 2048
RESERVE_LOW_THROUGH = 279
NATIVE_LEADS = tuple(range(0x80, 0x90))

NORMALIZE = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",
    "\u00d7": "x",
}


class TextRecord(Protocol):
    text: str


@dataclass(frozen=True)
class NativeMapping:
    lead: int
    trail: int
    slot: int

    @property
    def encoded(self) -> bytes:
        return bytes((self.lead, self.trail))


def is_hangul(ch: str) -> bool:
    return bool(HANGUL_RE.fullmatch(ch))


def normalized_chars(text: str) -> list[str]:
    out: list[str] = []
    for ch in text:
        replacement = NORMALIZE.get(ch)
        if replacement is None:
            out.append(ch)
        else:
            out.extend(replacement)
    return out


def native_code_to_slot(lead: int, trail: int) -> int:
    if lead not in NATIVE_LEADS:
        raise ValueError(f"native lead 0x{lead:02X} outside 0x80..0x8F")
    if 0x30 <= trail <= 0x6F:
        local = trail - 0x30
    elif 0xA0 <= trail <= 0xDF:
        local = trail - 0x60
    else:
        raise ValueError(
            f"native trail 0x{trail:02X} outside 0x30..0x6F/0xA0..0xDF"
        )
    slot = (lead - 0x80) * 128 + local
    if not 0 <= slot < NATIVE_GLYPH_COUNT:
        raise ValueError(f"native code maps outside FONT.MMT: {lead:02X}{trail:02X}")
    return slot


def slot_to_native_code(slot: int) -> tuple[int, int]:
    if not 0 <= slot < NATIVE_GLYPH_COUNT:
        raise ValueError(f"FONT.MMT slot outside 0..2047: {slot}")
    bank, local = divmod(slot, 128)
    lead = 0x80 + bank
    trail = 0x30 + local if local < 64 else 0x60 + local
    return lead, trail


def collect_inventory(records: Iterable[TextRecord]) -> collections.Counter[str]:
    freq: collections.Counter[str] = collections.Counter()
    for rec in records:
        freq.update(ch for ch in normalized_chars(rec.text) if is_hangul(ch))
    return freq


def allocate_native_mapping(chars: Iterable[str]) -> dict[str, NativeMapping]:
    ordered = sorted(set(chars))
    free_slots = list(range(NATIVE_GLYPH_COUNT - 1, RESERVE_LOW_THROUGH, -1))
    if len(ordered) > len(free_slots):
        raise RuntimeError(
            f"Hangul inventory {len(ordered)} exceeds conservative native capacity "
            f"{len(free_slots)} (slots {RESERVE_LOW_THROUGH + 1}..{NATIVE_GLYPH_COUNT - 1})"
        )
    mapping: dict[str, NativeMapping] = {}
    for ch, slot in zip(ordered, free_slots):
        lead, trail = slot_to_native_code(slot)
        mapping[ch] = NativeMapping(lead=lead, trail=trail, slot=slot)
    return mapping


def build_native_mapping(
    records: Iterable[TextRecord],
) -> tuple[dict[str, NativeMapping], collections.Counter[str]]:
    freq = collect_inventory(records)
    return allocate_native_mapping(freq), freq


def build_mapping(
    records: Iterable[TextRecord],
) -> tuple[dict[str, bytes], collections.Counter[str]]:
    """Compatibility shape used by the MSG Huffman builder."""
    native, freq = build_native_mapping(records)
    return {ch: m.encoded for ch, m in native.items()}, freq


def encode_text(text: str, mapping: dict[str, bytes] | dict[str, NativeMapping]) -> bytes:
    out = bytearray()
    for ch in normalized_chars(text):
        cp = ord(ch)
        if cp <= 0x7F:
            out.append(cp)
        elif is_hangul(ch):
            try:
                value = mapping[ch]
            except KeyError as exc:
                raise RuntimeError(f"no native mapping for Hangul {ch!r} U+{cp:04X}") from exc
            if isinstance(value, NativeMapping):
                out.extend(value.encoded)
            else:
                out.extend(value)
        else:
            raise RuntimeError(
                f"unsupported non-ASCII character U+{cp:04X} {ch!r} "
                f"({unicodedata.name(ch, '<unnamed>')})"
            )
    return bytes(out)


def write_mapping_tsv(
    path: Path,
    mapping: dict[str, NativeMapping],
    freq: collections.Counter[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["unicode\tchar\tcount\tlead\ttrail\tcode_hex\tslot"]
    for ch in sorted(mapping):
        m = mapping[ch]
        lines.append(
            f"U+{ord(ch):04X}\t{ch}\t{freq[ch]}\t0x{m.lead:02X}\t0x{m.trail:02X}\t"
            f"{m.lead:02X}{m.trail:02X}\t{m.slot}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
