#!/usr/bin/env python3
"""Full Wizardry VII PSX Korean disc rebuild including SCENARIJ.DBS names.

This is the production superset of build_korean_psx_disc.py. It reuses that
module's source-image verification, CHD/BIN/CUE extraction, mkpsxiso rebuild and
reporting helpers, but builds one shared native codepage across:
- merged MSG text
- korean/scenario/items.ko.tsv
- korean/scenario/monsters.ko.tsv

The same mapping is then used by MSGJ, FONT.MMT and SCENARIJ.DBS.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import build_korean_psx_disc as core

SCENARIO_NAME = "SCENARIJ.DBS"
DEFAULT_ITEMS = Path("korean/scenario/items.ko.tsv")
DEFAULT_MONSTERS = Path("korean/scenario/monsters.ko.tsv")


def add_full_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.description = (
        "Build Wizardry VII PSX Korean BIN/CUE with shared MSG/font/scenario codepage"
    )
    parser.add_argument(
        "--scenario-items",
        type=Path,
        default=DEFAULT_ITEMS,
        help="item-name Korean TSV",
    )
    parser.add_argument(
        "--scenario-monsters",
        type=Path,
        default=DEFAULT_MONSTERS,
        help="monster-name Korean TSV",
    )
    return parser


def resolve_asset_path(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return (root / path).resolve()


def build_full_assets(
    root: Path,
    work_dir: Path,
    original_font: Path,
    original_exe: Path,
    original_scenario: Path,
    items: Path,
    monsters: Path,
    bdf: Path | None,
) -> dict[str, Path]:
    assets = work_dir / "assets-full"
    msg_dir = assets / "msg"
    font_dir = assets / "font"
    merged = assets / "MSGHDR_indexText.ko.merged.txt"
    validation = assets / "MSGHDR_validation_report.txt"
    native_map = assets / "shared_native_hangul_map.tsv"
    patched_font = assets / "FONT.MMT"
    patched_exe = assets / "PSX.EXE"
    patched_scenario = assets / SCENARIO_NAME
    assets.mkdir(parents=True, exist_ok=True)

    for path in (items, monsters):
        if not path.is_file():
            raise ValueError(f"scenario translation table not found: {path}")

    py = sys.executable
    core.run_cmd(
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

    core.run_cmd(
        [
            py,
            str(root / "korean/tools/build_native_korean_msghdr_shared.py"),
            "--input",
            str(merged),
            "--output-dir",
            str(msg_dir),
            "--map",
            str(native_map),
            "--extra-charset",
            str(items),
            "--extra-charset",
            str(monsters),
        ],
        cwd=root,
    )

    font_cmd = [
        py,
        str(root / "Wiz7_Patching_Utilities/KoreanFontTools/build_korean_font.py"),
        "build",
        str(merged),
        str(items),
        str(monsters),
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
    core.run_cmd(font_cmd, cwd=root)

    core.verify_mapping_parity(native_map, font_dir / "korean_dbcs.tsv")

    core.patch_executable(root, original_exe, patched_exe)

    scenario_cmd = [
        py,
        str(root / "Wiz7_Patching_Utilities/KoreanFontTools/scenario_name_patcher.py"),
        "patch",
        "--psx",
        str(original_scenario),
        "--mapping",
        str(native_map),
        "--items",
        str(items),
        "--monsters",
        str(monsters),
        "--output",
        str(patched_scenario),
    ]
    core.run_cmd(scenario_cmd, cwd=root)

    required = {
        "FONT.MMT": patched_font,
        "MISCJ.HDR": msg_dir / "MISCJ.HDR",
        "MSGJ.HDR": msg_dir / "MSGJ.HDR",
        "MSGJ.DBS": msg_dir / "MSGJ.DBS",
        "PSX.EXE": patched_exe,
        SCENARIO_NAME: patched_scenario,
    }
    for name, path in required.items():
        if not path.is_file():
            raise RuntimeError(f"full asset build did not create {name}: {path}")
    return required


def install_full_assets(
    disc_files: dict[str, Path], assets: dict[str, Path]
) -> dict[str, tuple[str, str]]:
    changes: dict[str, tuple[str, str]] = {}
    for name, source in assets.items():
        target = disc_files[name]
        before = core.file_hashes(target).sha256
        shutil.copy2(source, target)
        after = core.file_hashes(target).sha256
        if after != core.file_hashes(source).sha256:
            raise RuntimeError(f"copy verification failed for {name}")
        changes[name] = (before, after)
        print(f"installed {name}: {target}")
    return changes


def write_full_report(
    path: Path,
    source: Path,
    source_hashes: core.Hashes,
    chd_hashes: core.Hashes | None,
    changes: dict[str, tuple[str, str]],
    output_bin: Path,
    output_cue: Path,
    output_chd: Path | None,
    items: Path,
    monsters: Path,
) -> None:
    output_hashes = core.file_hashes(output_bin)
    lines = [
        "Wizardry VII PSX Korean full disc build",
        "========================================",
        f"Source                    : {source}",
        f"Source BIN MD5            : {source_hashes.md5}",
        f"Source BIN CRC32          : {source_hashes.crc32}",
        f"Source BIN SHA256         : {source_hashes.sha256}",
        f"Verified upstream BIN     : {source_hashes.md5 == core.VERIFIED_BIN_MD5 and source_hashes.crc32 == core.VERIFIED_BIN_CRC32}",
        f"Scenario items table      : {items}",
        f"Scenario monsters table   : {monsters}",
    ]
    if chd_hashes:
        lines.extend(
            [
                f"Source CHD SHA256         : {chd_hashes.sha256}",
                f"Known reference CHD       : {chd_hashes.sha256 == core.VERIFIED_CHD_SHA256}",
            ]
        )
    lines.extend(["", "[Installed files]"])
    for name in sorted(changes):
        before, after = changes[name]
        lines.append(f"{name}: {before} -> {after}")
    lines.extend(
        [
            "",
            "[Output]",
            f"BIN                        : {output_bin}",
            f"CUE                        : {output_cue}",
            f"BIN MD5                    : {output_hashes.md5}",
            f"BIN CRC32                  : {output_hashes.crc32}",
            f"BIN SHA256                 : {output_hashes.sha256}",
        ]
    )
    if output_chd and output_chd.is_file():
        lines.extend(
            [
                f"CHD                        : {output_chd}",
                f"CHD SHA256                 : {core.file_hashes(output_chd).sha256}",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_parser() -> argparse.ArgumentParser:
    return add_full_args(core.make_parser())


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    root = core.repo_root()

    try:
        source = args.source.expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"source image not found: {source}")

        items = resolve_asset_path(root, args.scenario_items)
        monsters = resolve_asset_path(root, args.scenario_monsters)
        output_bin, output_cue, output_chd = core.normalize_output_paths(args)
        work_dir = args.work_dir.expanduser().resolve()
        core.ensure_clean_workspace(work_dir, args.reuse_work_dir)

        needs_chdman = source.suffix.lower() == ".chd" or output_chd is not None
        tools = core.resolve_tools(args, need_chdman=needs_chdman)

        input_for_dump, _source_bin, source_hashes, chd_hashes = core.prepare_source(
            source,
            work_dir / "source",
            tools,
            args.allow_unverified_source,
        )

        extracted = work_dir / "extracted"
        xml_path = work_dir / "disc.xml"
        core.extract_disc(input_for_dump, extracted, xml_path, tools)

        disc_files = core.locate_disc_files(extracted)
        disc_files[SCENARIO_NAME] = core.find_unique(extracted, SCENARIO_NAME)
        print("located full disc files:")
        for name in (*core.DISC_FILENAMES, SCENARIO_NAME):
            print(f"  {name}: {disc_files[name].relative_to(extracted)}")

        assets = build_full_assets(
            root,
            work_dir,
            original_font=disc_files["FONT.MMT"],
            original_exe=disc_files["PSX.EXE"],
            original_scenario=disc_files[SCENARIO_NAME],
            items=items,
            monsters=monsters,
            bdf=args.bdf,
        )
        changes = install_full_assets(disc_files, assets)
        core.rebuild_disc(xml_path, output_bin, output_cue, tools)

        if output_chd:
            if not tools.chdman:
                raise ValueError("--output-chd requires chdman")
            core.make_chd(output_cue, output_chd, tools.chdman)

        report = args.report.expanduser().resolve()
        write_full_report(
            report,
            source,
            source_hashes,
            chd_hashes,
            changes,
            output_bin,
            output_cue,
            output_chd,
            items,
            monsters,
        )
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("")
    print("Full build complete.")
    print(f"BIN: {output_bin}")
    print(f"CUE: {output_cue}")
    if output_chd:
        print(f"CHD: {output_chd}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
