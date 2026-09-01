#!/usr/bin/env python3
"""Dump and patch Wizardry VII PS1 item/monster names with native Korean DBCS.

Verified SCENARIJ.DBS layout for the supported Japanese PS1 build:
- file size: 368,320 bytes
- item table: 571 records at 0x380, stride 0x48
  - item name: record +0x00, 22-byte NUL-terminated field
- monster table: 250 records at 0x37038, stride 0xE8
  - four 16-byte NUL-terminated fields at record +0x08:
    specific singular/plural and generic singular/plural

The patcher consumes the same explicit native mapping TSV as FONT.MMT/MSGJ.
It never allocates a private codepage, preventing font/data mapping drift.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ITEM_START = 0x380
ITEM_STRIDE = 0x48
ITEM_COUNT = 571
ITEM_NAME_OFF = 0x00
ITEM_NAME_SIZE = 22

MON_START = 0x37038
MON_STRIDE = 0xE8
MON_COUNT = 250
MON_NAME_OFF = 0x08
MON_FIELD_SIZE = 16
MON_FIELDS = (
    "specific_singular",
    "specific_plural",
    "generic_singular",
    "generic_plural",
)

EXPECTED_SCENARIO_SIZE = 368320
NORMALIZE = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u00a0": " ",
    "\u00d7": "x",
}


@dataclass(frozen=True)
class Mapping:
    lead: int
    trail: int
    slot: int

    @property
    def encoded(self) -> bytes:
        return bytes((self.lead, self.trail))


def load_mapping(path: Path) -> dict[str, Mapping]:
    out: dict[str, Mapping] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"char", "lead", "trail", "slot"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"mapping missing columns: {sorted(required)}")
        for row in reader:
            out[row["char"]] = Mapping(
                lead=int(row["lead"], 16),
                trail=int(row["trail"], 16),
                slot=int(row["slot"]),
            )
    return out


def encode_text(text: str, mapping: dict[str, Mapping]) -> bytes:
    out = bytearray()
    for ch in text:
        replacement = NORMALIZE.get(ch, ch)
        for c in replacement:
            if ord(c) <= 0x7F:
                out.append(ord(c))
            elif c in mapping:
                out.extend(mapping[c].encoded)
            else:
                raise ValueError(
                    f"unmapped char U+{ord(c):04X} {c!r} "
                    f"({unicodedata.name(c, '<unnamed>')})"
                )
    return bytes(out)


def fixed_field(text: str, size: int, mapping: dict[str, Mapping], where: str) -> bytes:
    encoded = encode_text(text, mapping)
    if len(encoded) > size - 1:
        raise ValueError(
            f"{where}: encoded name is {len(encoded)} bytes; max is {size - 1}: {text!r}"
        )
    return encoded + b"\0" + bytes(size - len(encoded) - 1)


def read_cstr(field: bytes, encoding: str = "shift_jis") -> str:
    raw = field.split(b"\0", 1)[0]
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def validate_layout(data: bytes) -> None:
    if len(data) != EXPECTED_SCENARIO_SIZE:
        raise ValueError(
            f"unexpected SCENARIJ.DBS size {len(data)}; expected {EXPECTED_SCENARIO_SIZE}"
        )
    last_monster_end = (
        MON_START
        + (MON_COUNT - 1) * MON_STRIDE
        + MON_NAME_OFF
        + len(MON_FIELDS) * MON_FIELD_SIZE
    )
    if last_monster_end > len(data):
        raise ValueError("monster table is outside SCENARIJ.DBS")


def get_item_name(data: bytes, item_id: int) -> str:
    offset = ITEM_START + item_id * ITEM_STRIDE + ITEM_NAME_OFF
    return read_cstr(data[offset : offset + ITEM_NAME_SIZE])


def get_monster_names(data: bytes, monster_id: int) -> list[str]:
    base = MON_START + monster_id * MON_STRIDE + MON_NAME_OFF
    return [
        read_cstr(data[base + i * MON_FIELD_SIZE : base + (i + 1) * MON_FIELD_SIZE])
        for i in range(len(MON_FIELDS))
    ]


def dump_templates(psx_path: Path, dos_path: Path, out_dir: Path) -> None:
    psx = psx_path.read_bytes()
    dos = dos_path.read_bytes()
    validate_layout(psx)
    validate_layout(dos)
    out_dir.mkdir(parents=True, exist_ok=True)

    with (out_dir / "items.tsv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["id", "source_en", "source_jp", "ko_name"])
        for item_id in range(ITEM_COUNT):
            writer.writerow(
                [item_id, get_item_name(dos, item_id), get_item_name(psx, item_id), ""]
            )

    with (out_dir / "monsters.tsv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(
            ["id"]
            + [f"en_{name}" for name in MON_FIELDS]
            + [f"jp_{name}" for name in MON_FIELDS]
            + [f"ko_{name}" for name in MON_FIELDS]
        )
        for monster_id in range(MON_COUNT):
            writer.writerow(
                [monster_id]
                + get_monster_names(dos, monster_id)
                + get_monster_names(psx, monster_id)
                + [""] * len(MON_FIELDS)
            )


def apply_patch(
    psx_path: Path,
    mapping_path: Path,
    items_path: Path | None,
    monsters_path: Path | None,
    output_path: Path,
) -> None:
    original = psx_path.read_bytes()
    validate_layout(original)
    data = bytearray(original)
    mapping = load_mapping(mapping_path)
    changed: list[tuple[str, int, str, str]] = []

    if items_path:
        with items_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                text = (row.get("ko_name") or "").strip()
                if not text:
                    continue
                item_id = int(row["id"])
                if not 0 <= item_id < ITEM_COUNT:
                    raise ValueError(f"item id out of range: {item_id}")
                offset = ITEM_START + item_id * ITEM_STRIDE + ITEM_NAME_OFF
                data[offset : offset + ITEM_NAME_SIZE] = fixed_field(
                    text, ITEM_NAME_SIZE, mapping, f"item {item_id}"
                )
                changed.append(("item", item_id, "name", text))

    if monsters_path:
        with monsters_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                monster_id = int(row["id"])
                if not 0 <= monster_id < MON_COUNT:
                    raise ValueError(f"monster id out of range: {monster_id}")
                base = MON_START + monster_id * MON_STRIDE + MON_NAME_OFF
                for field_index, field_name in enumerate(MON_FIELDS):
                    text = (row.get("ko_" + field_name) or "").strip()
                    if not text:
                        continue
                    offset = base + field_index * MON_FIELD_SIZE
                    data[offset : offset + MON_FIELD_SIZE] = fixed_field(
                        text,
                        MON_FIELD_SIZE,
                        mapping,
                        f"monster {monster_id} {field_name}",
                    )
                    changed.append(("monster", monster_id, field_name, text))

    # Prove that every changed byte lies inside a requested name field.
    allowed = bytearray(len(data))
    for record_type, record_id, field_name, _ in changed:
        if record_type == "item":
            offset = ITEM_START + record_id * ITEM_STRIDE + ITEM_NAME_OFF
            allowed[offset : offset + ITEM_NAME_SIZE] = b"\1" * ITEM_NAME_SIZE
        else:
            field_index = MON_FIELDS.index(field_name)
            offset = MON_START + record_id * MON_STRIDE + MON_NAME_OFF + field_index * MON_FIELD_SIZE
            allowed[offset : offset + MON_FIELD_SIZE] = b"\1" * MON_FIELD_SIZE

    illegal = [
        i
        for i, (before, after) in enumerate(zip(original, data))
        if before != after and not allowed[i]
    ]
    if illegal:
        raise RuntimeError(f"change outside approved name field at 0x{illegal[0]:X}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    print(
        f"patched_fields={len(changed)} size={len(data)} "
        f"sha256={hashlib.sha256(data).hexdigest()}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dump/patch WIZ7 PS1 item and monster names with native Korean DBCS"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    dump = sub.add_parser("dump")
    dump.add_argument("--psx", type=Path, required=True)
    dump.add_argument("--dos", type=Path, required=True)
    dump.add_argument("--out-dir", type=Path, required=True)

    patch = sub.add_parser("patch")
    patch.add_argument("--psx", type=Path, required=True)
    patch.add_argument("--mapping", type=Path, required=True)
    patch.add_argument("--items", type=Path)
    patch.add_argument("--monsters", type=Path)
    patch.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "dump":
        dump_templates(args.psx, args.dos, args.out_dir)
    else:
        apply_patch(args.psx, args.mapping, args.items, args.monsters, args.output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
