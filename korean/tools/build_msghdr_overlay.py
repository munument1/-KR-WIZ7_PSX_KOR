#!/usr/bin/env python3
"""
Build and validate a Korean MSGHDR overlay for Wizardry VII PSX.

The PS1 English MSGHDR text is authoritative for record order, "*" flags,
control bytes and event tokens. Korean files are sparse overlays:
    <message id>\\<translated text>

Continuation lines that do not begin with an ID are part of the previous
record. Human-readable <0xNN> placeholders in Korean overlays are converted
back to raw control characters in the merged output.

A small declarative fixup file may correct known Gold-to-PS1 structural
mismatches without rewriting the translated prose. Fixups can:
- use the exact PS1 source record for control-only records,
- discard extra control bytes while retaining the PS1 control sequence,
- drop Gold-only IDs absent from the PS1 source,
- restore PS1 event-token prefixes omitted during translation transfer.

This tool intentionally does not translate or synthesize missing records.
Untranslated IDs remain the PS1 English source text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

RECORD_RE = re.compile(r"^(\d+)(\*)?\\(.*)$")
CONTROL_PLACEHOLDER_RE = re.compile(r"<0x([0-9A-Fa-f]{2})>")
EVENT_TOKEN_RE = re.compile(r"=[A-Za-z0-9.]+,")
LEADING_MARKUP_RE = re.compile(r"(?m)^(?:@)?(?:#!|!|@)")
REF_TOKEN_RE = re.compile(r"[\^\$%#]")

DEFAULT_SOURCE = Path("MSGHDR_indexText.txt")
DEFAULT_MAIN = Path("korean/MSGHDR_indexText.ko.txt")
DEFAULT_SEGMENTS = Path("korean/segments")
DEFAULT_FIXUPS = Path("korean/MSGHDR_structure_fixups.json")
DEFAULT_OUTPUT = Path("korean/build/MSGHDR_indexText.ko.merged.txt")
DEFAULT_REPORT = Path("korean/build/MSGHDR_validation_report.txt")


@dataclass(frozen=True)
class Record:
    message_id: int
    star: bool
    text: str
    source_name: str
    source_line: int


class ParseError(RuntimeError):
    pass


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def parse_records(text: str, source_name: str) -> list[Record]:
    """Parse MSGHDR-style ID records, preserving continuation lines."""
    records: list[Record] = []
    current_id: int | None = None
    current_star = False
    current_text: list[str] = []
    current_line = 0

    def flush() -> None:
        nonlocal current_id, current_star, current_text, current_line
        if current_id is None:
            return
        records.append(
            Record(
                message_id=current_id,
                star=current_star,
                text="\n".join(current_text),
                source_name=source_name,
                source_line=current_line,
            )
        )
        current_id = None
        current_star = False
        current_text = []
        current_line = 0

    for line_no, line in enumerate(text.splitlines(), start=1):
        match = RECORD_RE.match(line)
        if match:
            flush()
            current_id = int(match.group(1))
            current_star = bool(match.group(2))
            current_text = [match.group(3)]
            current_line = line_no
        else:
            if current_id is None:
                if line.strip():
                    raise ParseError(
                        f"{source_name}:{line_no}: continuation text before first ID: {line!r}"
                    )
                continue
            current_text.append(line)

    flush()
    return records


def decode_control_placeholders(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    return CONTROL_PLACEHOLDER_RE.sub(repl, text)


def control_signature(text: str) -> tuple[int, ...]:
    decoded = decode_control_placeholders(text)
    # Newlines separate continuation lines and are file structure, not MSGHDR
    # control bytes. Tabs and other C0 bytes may be real menu controls.
    return tuple(ord(ch) for ch in decoded if ord(ch) < 0x20 and ch not in "\r\n")


def event_signature(text: str) -> tuple[str, ...]:
    return tuple(EVENT_TOKEN_RE.findall(text))


def leading_markup_signature(text: str) -> tuple[str, ...]:
    return tuple(LEADING_MARKUP_RE.findall(text))


def ref_signature(text: str) -> tuple[str, ...]:
    return tuple(REF_TOKEN_RE.findall(text))


def load_overlay_files(main_file: Path, segments_dir: Path) -> list[Path]:
    paths: list[Path] = []
    if main_file.exists():
        paths.append(main_file)
    if segments_dir.exists():
        paths.extend(sorted(segments_dir.glob("*.ko.txt")))
    return paths


def records_by_id(records: Iterable[Record]) -> dict[int, Record]:
    out: dict[int, Record] = {}
    for record in records:
        if record.message_id in out:
            prev = out[record.message_id]
            raise ParseError(
                f"{record.source_name}:{record.source_line}: duplicate ID "
                f"{record.message_id}; first seen at "
                f"{prev.source_name}:{prev.source_line}"
            )
        out[record.message_id] = record
    return out


def collect_overlays(paths: Iterable[Path]) -> dict[int, Record]:
    out: dict[int, Record] = {}
    for path in paths:
        records = parse_records(read_utf8(path), str(path))
        for record in records:
            if record.message_id in out:
                prev = out[record.message_id]
                raise ParseError(
                    f"{path}:{record.source_line}: duplicate Korean overlay ID "
                    f"{record.message_id}; first seen at "
                    f"{prev.source_name}:{prev.source_line}"
                )
            out[record.message_id] = record
    return out


def reconcile_control_sequence(original: Record, overlay: Record) -> Record:
    """Remove overlay-only C0 bytes while preserving the PS1 control sequence.

    This is intentionally conservative: the PS1 control sequence must already
    appear as a subsequence of the Korean overlay. The function only deletes
    extras; it never invents or reorders controls.
    """
    wanted = list(control_signature(original.text))
    decoded = decode_control_placeholders(overlay.text)
    kept: list[str] = []
    wanted_index = 0

    for ch in decoded:
        code = ord(ch)
        if code < 0x20 and ch not in "\r\n":
            if wanted_index < len(wanted) and code == wanted[wanted_index]:
                kept.append(ch)
                wanted_index += 1
            # Any other control byte is a Gold-only extra and is discarded.
            continue
        kept.append(ch)

    if wanted_index != len(wanted):
        raise ParseError(
            f"cannot reconcile controls for ID {overlay.message_id}: "
            f"PS1={tuple(wanted)!r} overlay={control_signature(overlay.text)!r}"
        )

    return replace(
        overlay,
        text="".join(kept),
        source_name=f"{overlay.source_name} [PS1 structure fixup]",
    )


def apply_structure_fixups(
    source: dict[int, Record],
    overlays: dict[int, Record],
    fixups_path: Path,
) -> dict[int, Record]:
    if not fixups_path.exists():
        return overlays

    try:
        data = json.loads(read_utf8(fixups_path))
    except json.JSONDecodeError as exc:
        raise ParseError(f"{fixups_path}: invalid JSON: {exc}") from exc

    out = dict(overlays)

    for raw_id in data.get("drop_overlay_ids", []):
        out.pop(int(raw_id), None)

    for raw_id in data.get("use_source_record_ids", []):
        message_id = int(raw_id)
        original = source.get(message_id)
        if original is None:
            raise ParseError(
                f"{fixups_path}: use_source_record_ids contains missing PS1 ID {message_id}"
            )
        out[message_id] = replace(
            original,
            source_name=f"{fixups_path} [exact PS1 source record]",
            source_line=0,
        )

    for raw_id in data.get("reconcile_control_ids", []):
        message_id = int(raw_id)
        original = source.get(message_id)
        overlay = out.get(message_id)
        if original is None:
            raise ParseError(
                f"{fixups_path}: reconcile_control_ids contains missing PS1 ID {message_id}"
            )
        if overlay is None:
            raise ParseError(
                f"{fixups_path}: reconcile_control_ids contains missing overlay ID {message_id}"
            )
        out[message_id] = reconcile_control_sequence(original, overlay)

    for raw_id, prefix in data.get("prepend_event_tokens", {}).items():
        message_id = int(raw_id)
        original = source.get(message_id)
        overlay = out.get(message_id)
        if original is None:
            raise ParseError(
                f"{fixups_path}: prepend_event_tokens contains missing PS1 ID {message_id}"
            )
        if overlay is None:
            raise ParseError(
                f"{fixups_path}: prepend_event_tokens contains missing overlay ID {message_id}"
            )
        if not isinstance(prefix, str):
            raise ParseError(
                f"{fixups_path}: event prefix for ID {message_id} must be a string"
            )
        if not overlay.text.startswith(prefix):
            out[message_id] = replace(
                overlay,
                text=prefix + overlay.text,
                source_name=f"{overlay.source_name} [PS1 event fixup]",
            )

    return out


def validate(
    source: dict[int, Record],
    overlays: dict[int, Record],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for message_id, overlay in sorted(overlays.items()):
        original = source.get(message_id)
        where = f"{overlay.source_name}:{overlay.source_line} [ID {message_id}]"
        if original is None:
            errors.append(f"{where}: overlay ID does not exist in PS1 English source")
            continue

        source_controls = control_signature(original.text)
        overlay_controls = control_signature(overlay.text)
        if source_controls != overlay_controls:
            errors.append(
                f"{where}: control-byte sequence differs: "
                f"source={source_controls!r} overlay={overlay_controls!r}"
            )

        source_events = event_signature(original.text)
        overlay_events = event_signature(overlay.text)
        if source_events != overlay_events:
            errors.append(
                f"{where}: event-token sequence differs: "
                f"source={source_events!r} overlay={overlay_events!r}"
            )

        source_markup = leading_markup_signature(original.text)
        overlay_markup = leading_markup_signature(overlay.text)
        if source_markup != overlay_markup:
            warnings.append(
                f"{where}: leading display markup differs: "
                f"source={source_markup!r} overlay={overlay_markup!r}"
            )

        source_refs = ref_signature(original.text)
        overlay_refs = ref_signature(overlay.text)
        if source_refs != overlay_refs:
            warnings.append(
                f"{where}: ^/$/%/# marker sequence differs: "
                f"source={source_refs!r} overlay={overlay_refs!r}"
            )

    return errors, warnings


def write_merged(
    source_records: list[Record],
    overlays: dict[int, Record],
    output_path: Path,
) -> tuple[int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    translated = 0
    fallback = 0
    chunks: list[str] = []

    for original in source_records:
        overlay = overlays.get(original.message_id)
        if overlay is None:
            text = original.text
            fallback += 1
        else:
            text = decode_control_placeholders(overlay.text)
            translated += 1

        head = f"{original.message_id}{'*' if original.star else ''}\\"
        chunks.append(head + text)

    output_path.write_text("\n".join(chunks) + "\n", encoding="utf-8", newline="\n")
    return translated, fallback


def write_report(
    report_path: Path,
    source_count: int,
    overlay_count: int,
    translated_count: int,
    fallback_count: int,
    errors: list[str],
    warnings: list[str],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Wizardry VII PSX Korean MSGHDR validation",
        "==========================================",
        f"PS1 source records : {source_count}",
        f"Korean overlay IDs : {overlay_count}",
        f"Merged Korean IDs  : {translated_count}",
        f"English fallbacks   : {fallback_count}",
        f"Errors              : {len(errors)}",
        f"Warnings            : {len(warnings)}",
        "",
    ]
    if errors:
        lines.append("[ERRORS]")
        lines.extend(errors)
        lines.append("")
    if warnings:
        lines.append("[WARNINGS]")
        lines.extend(warnings)
        lines.append("")
    if not errors and not warnings:
        lines.append("OK: no validation issues found.")
    elif not errors:
        lines.append("OK: no blocking validation errors; review warnings before build.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Korean sparse overlays and build a merged PS1 MSGHDR text."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--segments-dir", type=Path, default=DEFAULT_SEGMENTS)
    parser.add_argument("--fixups", type=Path, default=DEFAULT_FIXUPS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation and report generation without writing merged output.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Return failure when non-blocking markup/reference warnings exist.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        source_records = parse_records(read_utf8(args.source), str(args.source))
        source = records_by_id(source_records)
        overlay_paths = load_overlay_files(args.main, args.segments_dir)
        overlays = collect_overlays(overlay_paths)
        overlays = apply_structure_fixups(source, overlays, args.fixups)
    except (OSError, UnicodeError, ParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate(source, overlays)

    translated = len(overlays)
    fallback = max(0, len(source_records) - len(overlays))
    if not args.validate_only and not errors:
        translated, fallback = write_merged(source_records, overlays, args.output)

    write_report(
        args.report,
        source_count=len(source_records),
        overlay_count=len(overlays),
        translated_count=translated,
        fallback_count=fallback,
        errors=errors,
        warnings=warnings,
    )

    print(
        f"source={len(source_records)} overlay={len(overlays)} "
        f"errors={len(errors)} warnings={len(warnings)}"
    )
    print(f"report: {args.report}")
    if not args.validate_only and not errors:
        print(f"merged: {args.output}")

    if errors:
        return 1
    if args.strict_warnings and warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
