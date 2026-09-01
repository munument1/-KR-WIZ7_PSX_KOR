#!/usr/bin/env python3
"""Build a Wizardry VII PSX Korean BIN/CUE from a user-owned source image.

Pipeline:
  CHD (optional) -> BIN/CUE -> dumpsxiso extraction/XML
  -> merged Korean MSG source
  -> native Korean MISCJ.HDR / MSGJ.HDR / MSGJ.DBS
  -> Galmuri11-backed FONT.MMT
  -> DBCS-aware PSX.EXE patch
  -> install into extracted disc tree
  -> mkpsxiso rebuild
  -> optional CHD output

No original game data is stored in this repository. The source-image gate defaults
to the verified Japanese raw BIN used by the upstream WIZ7_PSX_ENG patch.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

VERIFIED_BIN_MD5 = "188d3ee5a2a2242a719f290ea595e5ec"
VERIFIED_BIN_CRC32 = "bab5dd73"
VERIFIED_CHD_SHA256 = "a1d45439c8e38e9a9c106c7735d725f79a22596497ce0690442a8e33c1ecf4b0"

DISC_FILENAMES = (
    "FONT.MMT",
    "MISCJ.HDR",
    "MSGJ.HDR",
    "MSGJ.DBS",
    "PSX.EXE",
)

CUE_FILE_RE = re.compile(
    r'^\s*FILE\s+(?:"([^"]+)"|(\S+))\s+(\S+)\s*$',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Hashes:
    md5: str
    sha256: str
    crc32: str


@dataclass(frozen=True)
class Tools:
    dumpsxiso: str
    mkpsxiso: str
    chdman: str | None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def file_hashes(path: Path, chunk_size: int = 1024 * 1024) -> Hashes:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    crc = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
            sha256.update(chunk)
            crc = zlib.crc32(chunk, crc)
    return Hashes(
        md5=md5.hexdigest(),
        sha256=sha256.hexdigest(),
        crc32=f"{crc & 0xFFFFFFFF:08x}",
    )


def parse_cue_files(cue: Path) -> list[Path]:
    try:
        text = cue.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = cue.read_text(encoding="latin-1")

    files: list[Path] = []
    for line in text.splitlines():
        match = CUE_FILE_RE.match(line)
        if not match:
            continue
        name = match.group(1) or match.group(2)
        assert name is not None
        path = (cue.parent / name).resolve()
        if path not in files:
            files.append(path)
    return files


def select_bin_from_cue(cue: Path, allow_unverified: bool) -> Path:
    candidates = parse_cue_files(cue)
    if not candidates:
        raise ValueError(f"CUE has no FILE entry: {cue}")

    existing = [p for p in candidates if p.is_file()]
    if not existing:
        joined = ", ".join(str(p) for p in candidates)
        raise ValueError(f"CUE references missing file(s): {joined}")

    for path in existing:
        hashes = file_hashes(path)
        if (
            hashes.md5.lower() == VERIFIED_BIN_MD5
            and hashes.crc32.lower() == VERIFIED_BIN_CRC32
        ):
            return path

    if allow_unverified:
        return existing[0]

    details = "; ".join(
        f"{p.name}: md5={file_hashes(p).md5} crc32={file_hashes(p).crc32}"
        for p in existing
    )
    raise ValueError(
        "CUE does not reference the verified Wizardry VII Japanese BIN. "
        f"Expected md5={VERIFIED_BIN_MD5} crc32={VERIFIED_BIN_CRC32}; {details}"
    )


def verify_bin(path: Path, allow_unverified: bool) -> Hashes:
    hashes = file_hashes(path)
    verified = (
        hashes.md5.lower() == VERIFIED_BIN_MD5
        and hashes.crc32.lower() == VERIFIED_BIN_CRC32
    )
    if not verified and not allow_unverified:
        raise ValueError(
            "Unsupported source BIN. "
            f"Expected md5={VERIFIED_BIN_MD5} crc32={VERIFIED_BIN_CRC32}, "
            f"got md5={hashes.md5} crc32={hashes.crc32}. "
            "Use --allow-unverified-source only for deliberate research builds."
        )
    return hashes


def resolve_tool(explicit: str | None, names: Iterable[str], tool_dir: Path | None) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise ValueError(f"tool not found: {explicit}")

    if tool_dir:
        for name in names:
            for candidate_name in (name, name + ".exe"):
                candidate = tool_dir / candidate_name
                if candidate.is_file():
                    return str(candidate.resolve())

    for name in names:
        found = shutil.which(name)
        if found:
            return found

    raise ValueError(
        f"required tool not found ({'/'.join(names)}). "
        "Use --tool-dir or the corresponding explicit tool option."
    )


def resolve_tools(args: argparse.Namespace, need_chdman: bool) -> Tools:
    tool_dir = args.tool_dir.resolve() if args.tool_dir else None
    dumpsxiso = resolve_tool(args.dumpsxiso, ("dumpsxiso",), tool_dir)
    mkpsxiso = resolve_tool(args.mkpsxiso, ("mkpsxiso",), tool_dir)
    chdman = None
    if need_chdman:
        chdman = resolve_tool(args.chdman, ("chdman",), tool_dir)
    elif args.chdman:
        chdman = resolve_tool(args.chdman, ("chdman",), tool_dir)
    return Tools(dumpsxiso=dumpsxiso, mkpsxiso=mkpsxiso, chdman=chdman)


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    shown = " ".join(f'"{part}"' if " " in part else part for part in cmd)
    print(f"+ {shown}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def find_unique(root: Path, basename: str) -> Path:
    matches = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.name.upper() == basename.upper()
    ]
    if not matches:
        raise ValueError(f"{basename} not found under extracted disc tree: {root}")
    if len(matches) > 1:
        preview = ", ".join(str(p.relative_to(root)) for p in matches[:10])
        raise ValueError(f"multiple {basename} files found: {preview}")
    return matches[0]


def locate_disc_files(extracted: Path) -> dict[str, Path]:
    return {name: find_unique(extracted, name) for name in DISC_FILENAMES}


def ensure_clean_workspace(work_dir: Path, reuse: bool) -> None:
    if work_dir.exists():
        if not reuse:
            raise ValueError(
                f"work directory already exists: {work_dir}. "
                "Remove it or pass --reuse-work-dir."
            )
    else:
        work_dir.mkdir(parents=True)


def normalize_output_paths(args: argparse.Namespace) -> tuple[Path, Path, Path | None]:
    output_bin = args.output_bin.resolve()
    output_cue = (
        args.output_cue.resolve()
        if args.output_cue
        else output_bin.with_suffix(".cue")
    )
    output_chd = args.output_chd.resolve() if args.output_chd else None
    if output_bin == output_cue:
        raise ValueError("BIN and CUE output paths must differ")
    return output_bin, output_cue, output_chd


def extract_chd(
    source_chd: Path,
    work_source_dir: Path,
    chdman: str,
) -> tuple[Path, Path]:
    cue = work_source_dir / "source.cue"
    bin_path = work_source_dir / "source.bin"
    work_source_dir.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            chdman,
            "extractcd",
            "-i",
            str(source_chd),
            "-o",
            str(cue),
            "-ob",
            str(bin_path),
            "-f",
        ]
    )
    if not cue.is_file() or not bin_path.is_file():
        raise RuntimeError("chdman completed but did not create source.cue/source.bin")
    return cue, bin_path


def prepare_source(
    source: Path,
    work_source_dir: Path,
    tools: Tools,
    allow_unverified: bool,
) -> tuple[Path, Path, Hashes, Hashes | None]:
    suffix = source.suffix.lower()
    chd_hashes: Hashes | None = None

    if suffix == ".chd":
        if not tools.chdman:
            raise ValueError("CHD input requires chdman")
        chd_hashes = file_hashes(source)
        print(
            f"source CHD sha256={chd_hashes.sha256}"
            + (
                " (known verified CHD)"
                if chd_hashes.sha256.lower() == VERIFIED_CHD_SHA256
                else " (different CHD container; reconstructed BIN will be authoritative)"
            )
        )
        input_for_dump, bin_path = extract_chd(source, work_source_dir, tools.chdman)
    elif suffix == ".cue":
        input_for_dump = source
        bin_path = select_bin_from_cue(source, allow_unverified)
    elif suffix == ".bin":
        input_for_dump = source
        bin_path = source
    else:
        raise ValueError("source must be .chd, .cue or .bin")

    hashes = verify_bin(bin_path, allow_unverified)
    print(
        f"source BIN md5={hashes.md5} crc32={hashes.crc32} "
        f"sha256={hashes.sha256}"
    )
    return input_for_dump, bin_path, hashes, chd_hashes


def extract_disc(input_for_dump: Path, extracted: Path, xml_path: Path, tools: Tools) -> None:
    extracted.mkdir(parents=True, exist_ok=True)
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            tools.dumpsxiso,
            "-x",
            str(extracted),
            "-s",
            str(xml_path),
            str(input_for_dump),
        ]
    )
    if not xml_path.is_file():
        raise RuntimeError(f"dumpsxiso did not create XML project: {xml_path}")


def build_korean_assets(
    root: Path,
    work_dir: Path,
    original_font: Path,
    bdf: Path | None,
) -> dict[str, Path]:
    assets = work_dir / "assets"
    msg_dir = assets / "msg"
    font_dir = assets / "font"
    merged = assets / "MSGHDR_indexText.ko.merged.txt"
    validation = assets / "MSGHDR_validation_report.txt"
    native_map = assets / "MSGHDR_native_hangul_map.tsv"
    patched_font = assets / "FONT.MMT"
    patched_exe = assets / "PSX.EXE"

    assets.mkdir(parents=True, exist_ok=True)

    py = sys.executable
    run_cmd(
        [
            py,
            str(root / "korean/tools/build_msghdr_overlay.py"),
            "--output",
            str(merged),
            "--report",
            str(validation),
        ],
        cwd=root,
    )
    run_cmd(
        [
            py,
            str(root / "korean/tools/build_native_korean_msghdr_binary.py"),
            "--input",
            str(merged),
            "--output-dir",
            str(msg_dir),
            "--map",
            str(native_map),
        ],
        cwd=root,
    )

    font_cmd = [
        py,
        str(root / "Wiz7_Patching_Utilities/KoreanFontTools/build_korean_font.py"),
        "build",
        str(merged),
        "--reserve-low-through",
        "279",
        "--font",
        str(original_font),
        "--font-output",
        str(patched_font),
        "--out",
        str(font_dir),
    ]
    if bdf:
        font_cmd.extend(["--bdf", str(bdf.resolve())])
    run_cmd(font_cmd, cwd=root)

    required = {
        "FONT.MMT": patched_font,
        "MISCJ.HDR": msg_dir / "MISCJ.HDR",
        "MSGJ.HDR": msg_dir / "MSGJ.HDR",
        "MSGJ.DBS": msg_dir / "MSGJ.DBS",
        "PSX.EXE": patched_exe,
    }
    for name, path in required.items():
        if name == "PSX.EXE":
            continue
        if not path.is_file():
            raise RuntimeError(f"asset build did not create {name}: {path}")

    verify_mapping_parity(native_map, font_dir / "korean_dbcs.tsv")
    return required


def load_mapping_tsv(path: Path) -> dict[str, tuple[str, int]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        rows = csv.DictReader(fh, delimiter="\t")
        mapping: dict[str, tuple[str, int]] = {}
        for row in rows:
            ch = row["char"]
            mapping[ch] = (row["code_hex"].upper(), int(row["slot"]))
    return mapping


def verify_mapping_parity(msg_map: Path, font_map: Path) -> None:
    msg = load_mapping_tsv(msg_map)
    font = load_mapping_tsv(font_map)
    if msg != font:
        missing_msg = sorted(set(font) - set(msg))
        missing_font = sorted(set(msg) - set(font))
        mismatched = sorted(
            ch for ch in set(msg) & set(font) if msg[ch] != font[ch]
        )
        preview = []
        if missing_msg:
            preview.append(f"missing in MSG map: {missing_msg[:5]}")
        if missing_font:
            preview.append(f"missing in font map: {missing_font[:5]}")
        if mismatched:
            preview.append(
                "mismatch: "
                + ", ".join(
                    f"{ch} msg={msg[ch]} font={font[ch]}" for ch in mismatched[:5]
                )
            )
        raise RuntimeError(
            "font/MSG native codepage mismatch; " + "; ".join(preview)
        )
    print(f"native mapping parity OK: {len(msg)} characters")


def patch_executable(root: Path, original_exe: Path, patched_exe: Path) -> None:
    run_cmd(
        [
            sys.executable,
            str(root / "korean/tools/patch_korean_psx_exe.py"),
            str(original_exe),
            str(patched_exe),
        ],
        cwd=root,
    )
    if not patched_exe.is_file():
        raise RuntimeError(f"EXE patcher did not create {patched_exe}")


def install_assets(
    extracted_files: dict[str, Path],
    assets: dict[str, Path],
) -> dict[str, tuple[str, str]]:
    changes: dict[str, tuple[str, str]] = {}
    for name in DISC_FILENAMES:
        target = extracted_files[name]
        source = assets[name]
        before = file_hashes(target).sha256
        shutil.copy2(source, target)
        after = file_hashes(target).sha256
        if after != file_hashes(source).sha256:
            raise RuntimeError(f"copy verification failed for {name}")
        changes[name] = (before, after)
        print(f"installed {name}: {target}")
    return changes


def rebuild_disc(
    xml_path: Path,
    output_bin: Path,
    output_cue: Path,
    tools: Tools,
) -> None:
    output_bin.parent.mkdir(parents=True, exist_ok=True)
    output_cue.parent.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            tools.mkpsxiso,
            "-y",
            "-o",
            str(output_bin),
            "-c",
            str(output_cue),
            str(xml_path),
        ]
    )
    if not output_bin.is_file() or not output_cue.is_file():
        raise RuntimeError("mkpsxiso completed but BIN/CUE output is missing")


def make_chd(output_cue: Path, output_chd: Path, chdman: str) -> None:
    output_chd.parent.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            chdman,
            "createcd",
            "-i",
            str(output_cue),
            "-o",
            str(output_chd),
            "-f",
        ]
    )
    if not output_chd.is_file():
        raise RuntimeError(f"chdman did not create {output_chd}")


def write_report(
    report: Path,
    source: Path,
    source_hashes: Hashes,
    chd_hashes: Hashes | None,
    changes: dict[str, tuple[str, str]],
    output_bin: Path,
    output_cue: Path,
    output_chd: Path | None,
) -> None:
    out_hashes = file_hashes(output_bin)
    lines = [
        "Wizardry VII PSX Korean disc build",
        "===================================",
        f"Source                    : {source}",
        f"Source BIN MD5            : {source_hashes.md5}",
        f"Source BIN CRC32          : {source_hashes.crc32}",
        f"Source BIN SHA256         : {source_hashes.sha256}",
        f"Verified upstream BIN     : {source_hashes.md5 == VERIFIED_BIN_MD5 and source_hashes.crc32 == VERIFIED_BIN_CRC32}",
    ]
    if chd_hashes:
        lines.extend(
            [
                f"Source CHD SHA256         : {chd_hashes.sha256}",
                f"Known reference CHD       : {chd_hashes.sha256 == VERIFIED_CHD_SHA256}",
            ]
        )
    lines.extend(["", "[Installed files]"])
    for name in DISC_FILENAMES:
        before, after = changes[name]
        lines.append(f"{name}: {before} -> {after}")
    lines.extend(
        [
            "",
            "[Output]",
            f"BIN                        : {output_bin}",
            f"CUE                        : {output_cue}",
            f"BIN MD5                    : {out_hashes.md5}",
            f"BIN CRC32                  : {out_hashes.crc32}",
            f"BIN SHA256                 : {out_hashes.sha256}",
        ]
    )
    if output_chd and output_chd.is_file():
        chd_out_hashes = file_hashes(output_chd)
        lines.extend(
            [
                f"CHD                        : {output_chd}",
                f"CHD SHA256                 : {chd_out_hashes.sha256}",
            ]
        )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build Wizardry VII PSX Korean BIN/CUE from a user-owned Japanese source"
    )
    parser.add_argument("source", type=Path, help="verified Japanese .chd, .cue or raw .bin")
    parser.add_argument(
        "--output-bin",
        type=Path,
        default=Path("build/Wizardry7_PSX_KOR.bin"),
        help="rebuilt BIN output",
    )
    parser.add_argument("--output-cue", type=Path, help="rebuilt CUE output (default: BIN with .cue)")
    parser.add_argument("--output-chd", type=Path, help="optional CHD output")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("build/psx-korean-disc-work"),
        help="extraction/build workspace",
    )
    parser.add_argument("--reuse-work-dir", action="store_true")
    parser.add_argument(
        "--allow-unverified-source",
        action="store_true",
        help="allow a BIN whose MD5/CRC32 differs from the verified Japanese dump",
    )
    parser.add_argument("--bdf", type=Path, help="offline Galmuri11.bdf; otherwise font tool downloads it")
    parser.add_argument("--tool-dir", type=Path, help="directory containing dumpsxiso/mkpsxiso/chdman")
    parser.add_argument("--dumpsxiso", help="explicit dumpsxiso executable")
    parser.add_argument("--mkpsxiso", help="explicit mkpsxiso executable")
    parser.add_argument("--chdman", help="explicit chdman executable")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("build/Wizardry7_PSX_KOR_BUILD_REPORT.txt"),
        help="build report path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    root = repo_root()

    try:
        source = args.source.expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"source image not found: {source}")

        output_bin, output_cue, output_chd = normalize_output_paths(args)
        work_dir = args.work_dir.expanduser().resolve()
        ensure_clean_workspace(work_dir, args.reuse_work_dir)

        needs_chdman = source.suffix.lower() == ".chd" or output_chd is not None
        tools = resolve_tools(args, need_chdman=needs_chdman)

        input_for_dump, _source_bin, source_hashes, chd_hashes = prepare_source(
            source,
            work_dir / "source",
            tools,
            args.allow_unverified_source,
        )

        extracted = work_dir / "extracted"
        xml_path = work_dir / "disc.xml"
        extract_disc(input_for_dump, extracted, xml_path, tools)

        disc_files = locate_disc_files(extracted)
        print("located disc files:")
        for name in DISC_FILENAMES:
            print(f"  {name}: {disc_files[name].relative_to(extracted)}")

        assets = build_korean_assets(
            root,
            work_dir,
            original_font=disc_files["FONT.MMT"],
            bdf=args.bdf,
        )
        patch_executable(root, disc_files["PSX.EXE"], assets["PSX.EXE"])

        changes = install_assets(disc_files, assets)
        rebuild_disc(xml_path, output_bin, output_cue, tools)

        if output_chd:
            if not tools.chdman:
                raise ValueError("--output-chd requires chdman")
            make_chd(output_cue, output_chd, tools.chdman)

        write_report(
            args.report.expanduser().resolve(),
            source,
            source_hashes,
            chd_hashes,
            changes,
            output_bin,
            output_cue,
            output_chd,
        )
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("")
    print("Build complete.")
    print(f"BIN: {output_bin}")
    print(f"CUE: {output_cue}")
    if output_chd:
        print(f"CHD: {output_chd}")
    print(f"Report: {args.report.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
