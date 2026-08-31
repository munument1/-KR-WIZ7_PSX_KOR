#!/usr/bin/env python3
"""Analyze the character inventory required by the merged Korean MSGHDR text."""

from __future__ import annotations

import argparse
import collections
import re
import unicodedata
from pathlib import Path

DEFAULT_INPUT = Path("korean/build/MSGHDR_indexText.ko.merged.txt")
DEFAULT_REPORT = Path("korean/build/MSGHDR_charset_report.txt")
RECORD_RE = re.compile(r"^\d+\*?\\")


def is_hangul_syllable(ch: str) -> bool:
    return "\uac00" <= ch <= "\ud7a3"


def is_hangul_jamo(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x1100 <= cp <= 0x11FF
        or 0x3130 <= cp <= 0x318F
        or 0xA960 <= cp <= 0xA97F
        or 0xD7B0 <= cp <= 0xD7FF
    )


def extract_message_text(raw: str) -> str:
    out: list[str] = []
    for line in raw.splitlines():
        out.append(RECORD_RE.sub("", line, count=1))
    return "\n".join(out)


def fmt_char(ch: str) -> str:
    cp = ord(ch)
    name = unicodedata.name(ch, "<unnamed>")
    visible = ch if not ch.isspace() and cp >= 0x20 else repr(ch)
    return f"U+{cp:04X}\t{visible}\t{name}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    raw = args.input.read_text(encoding="utf-8", errors="strict")
    text = extract_message_text(raw)
    counts = collections.Counter(text)

    hangul = sorted(ch for ch in counts if is_hangul_syllable(ch))
    jamo = sorted(ch for ch in counts if is_hangul_jamo(ch))
    non_ascii = sorted(ch for ch in counts if ord(ch) >= 0x80)
    controls = sorted(ch for ch in counts if ord(ch) < 0x20 and ch not in "\n\r")

    lines = [
        "Wizardry VII PSX Korean MSGHDR character inventory",
        "=================================================",
        f"Total text characters        : {len(text)}",
        f"Unique characters            : {len(counts)}",
        f"Hangul syllable occurrences  : {sum(counts[ch] for ch in hangul)}",
        f"Unique Hangul syllables      : {len(hangul)}",
        f"Unique Hangul Jamo           : {len(jamo)}",
        f"Unique non-ASCII characters  : {len(non_ascii)}",
        f"Unique C0 controls            : {len(controls)}",
        "",
        "[MOST COMMON HANGUL SYLLABLES]",
    ]
    for ch, count in collections.Counter({ch: counts[ch] for ch in hangul}).most_common(100):
        lines.append(f"{count:7d}\t{fmt_char(ch)}")

    lines += ["", "[ALL UNIQUE HANGUL SYLLABLES]"]
    for ch in hangul:
        lines.append(f"{counts[ch]:7d}\t{fmt_char(ch)}")

    if jamo:
        lines += ["", "[HANGUL JAMO]"]
        for ch in jamo:
            lines.append(f"{counts[ch]:7d}\t{fmt_char(ch)}")

    lines += ["", "[NON-ASCII NON-HANGUL]"]
    for ch in non_ascii:
        if ch not in hangul and ch not in jamo:
            lines.append(f"{counts[ch]:7d}\t{fmt_char(ch)}")

    lines += ["", "[C0 CONTROLS]"]
    for ch in controls:
        lines.append(f"{counts[ch]:7d}\tU+{ord(ch):04X}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"unique_hangul={len(hangul)} non_ascii={len(non_ascii)} unique_total={len(counts)}")
    print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
