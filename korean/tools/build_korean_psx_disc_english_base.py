#!/usr/bin/env python3
"""Build Wizardry VII PSX Korean on top of Gertius' PSX English patch.

Production order:
  verified Japanese PS1 BIN/CHD
  -> apply Gertius WIZ7_PSX_ENG V1.0 xdelta
  -> verify exact English-patch BIN
  -> extract that English BIN
  -> Korean MSG/FONT/EXE/SCENARIO overlays
  -> fixed-width character/status UI English fallback
  -> preserve English MSG file sizes/LBA layout
  -> replace remaining Japanese title subtitle with Korean
  -> rebuild BIN/CUE, optional CHD and optional final xdelta against Japanese BIN
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import build_korean_psx_disc as core
import build_korean_psx_disc_full as full
import patch_korean_title_logo as title_logo
import stabilize_psx_fixed_ui as stable_ui

ENGLISH_BIN_MD5 = "7fb464147ab7144facae337226c91aa5"
ENGLISH_BIN_SHA256 = "6d61aaccf5a21853077f96b66e5fea4a2859611d89b5a93358e79d2f504c1683"
TITLE_NAME = "TITL.MMT"

ITEM_START = 0x380
ITEM_STRIDE = 0x48
ITEM_COUNT = 571
ITEM_NAME_SIZE = 22

def restore_english_item_names(korean_scenario: Path, english_scenario: Path) -> None:
    """Keep PS1 English item names until the small-font DBCS path is safe."""
    data = bytearray(korean_scenario.read_bytes())
    english = english_scenario.read_bytes()
    if len(data) != len(english):
        raise RuntimeError(f"SCENARIJ size mismatch: korean={len(data)} english={len(english)}")
    for item_id in range(ITEM_COUNT):
        off = ITEM_START + item_id * ITEM_STRIDE
        data[off:off + ITEM_NAME_SIZE] = english[off:off + ITEM_NAME_SIZE]
    korean_scenario.write_bytes(data)



def verify_english_bin(path: Path) -> core.Hashes:
    hashes = core.file_hashes(path)
    if hashes.md5.lower() != ENGLISH_BIN_MD5 or hashes.sha256.lower() != ENGLISH_BIN_SHA256:
        raise RuntimeError(
            "upstream English xdelta output mismatch: "
            f"md5={hashes.md5} sha256={hashes.sha256}; "
            f"expected md5={ENGLISH_BIN_MD5} sha256={ENGLISH_BIN_SHA256}"
        )
    return hashes


def apply_english_patch(source_bin: Path, patch: Path, output_bin: Path, xdelta3: str) -> core.Hashes:
    if not patch.is_file():
        raise ValueError(f"upstream English xdelta not found: {patch}")
    output_bin.parent.mkdir(parents=True, exist_ok=True)
    core.run_cmd([xdelta3, "-d", "-f", "-s", str(source_bin), str(patch), str(output_bin)])
    if not output_bin.is_file():
        raise RuntimeError("xdelta3 did not create the English base BIN")
    return verify_english_bin(output_bin)


def create_final_xdelta(source_bin: Path, output_bin: Path, output_xdelta: Path, xdelta3: str, work_dir: Path) -> None:
    output_xdelta.parent.mkdir(parents=True, exist_ok=True)
    core.run_cmd([xdelta3, "-e", "-f", "-s", str(source_bin), str(output_bin), str(output_xdelta)])
    verify_bin = work_dir / "final-xdelta-verify.bin"
    core.run_cmd([xdelta3, "-d", "-f", "-s", str(source_bin), str(output_xdelta), str(verify_bin)])
    expected = core.file_hashes(output_bin).sha256
    actual = core.file_hashes(verify_bin).sha256
    if expected != actual:
        raise RuntimeError(f"final xdelta roundtrip mismatch: {actual} != {expected}")


def make_parser() -> argparse.ArgumentParser:
    parser = full.make_parser()
    parser.description = "Build WIZ7 PSX Korean strictly on Gertius PSX English V1.0 base"
    parser.add_argument("--upstream-english-xdelta", type=Path, required=True, help="Gertius WIZ7_PSX_ENG V1.0 Wiz7_patch.xdelta")
    parser.add_argument("--xdelta3", help="explicit xdelta3 executable")
    parser.add_argument("--output-xdelta", type=Path, help="optional final Korean xdelta against the verified Japanese raw BIN")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    root = core.repo_root()

    try:
        source = args.source.expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"source image not found: {source}")

        items = full.resolve_asset_path(root, args.scenario_items)
        monsters = full.resolve_asset_path(root, args.scenario_monsters)
        output_bin, output_cue, output_chd = core.normalize_output_paths(args)
        work_dir = args.work_dir.expanduser().resolve()
        core.ensure_clean_workspace(work_dir, args.reuse_work_dir)

        need_chdman = source.suffix.lower() == ".chd" or output_chd is not None
        tools = core.resolve_tools(args, need_chdman=need_chdman)
        tool_dir = args.tool_dir.resolve() if args.tool_dir else None
        xdelta3 = core.resolve_tool(args.xdelta3, ("xdelta3",), tool_dir)

        _input_for_dump, source_bin, source_hashes, chd_hashes = core.prepare_source(
            source,
            work_dir / "source",
            tools,
            False,
        )

        english_bin = work_dir / "english-base" / "Wizardry7_PSX_ENG_V1_0.bin"
        english_hashes = apply_english_patch(
            source_bin,
            args.upstream_english_xdelta.expanduser().resolve(),
            english_bin,
            xdelta3,
        )
        print(f"English base verified: md5={english_hashes.md5} sha256={english_hashes.sha256}")

        extracted = work_dir / "english-extracted"
        xml_path = work_dir / "english-base.xml"
        core.extract_disc(english_bin, extracted, xml_path, tools)

        disc_files = core.locate_disc_files(extracted)
        disc_files[full.SCENARIO_NAME] = core.find_unique(extracted, full.SCENARIO_NAME)
        disc_files[TITLE_NAME] = core.find_unique(extracted, TITLE_NAME)

        assets = full.build_full_assets(
            root,
            work_dir,
            original_font=disc_files["FONT.MMT"],
            original_exe=disc_files["PSX.EXE"],
            original_scenario=disc_files[full.SCENARIO_NAME],
            items=items,
            monsters=monsters,
            bdf=args.bdf,
        )

        # v9 proved the PS1 inventory/item-info small-font path is not
        # safe for native two-byte Korean item names yet. Preserve Korean
        # monster fields but restore all item-name fields from the PS1 English base.
        restore_english_item_names(assets[full.SCENARIO_NAME], disc_files[full.SCENARIO_NAME])

        assets_root = work_dir / "assets-full"
        msg_dir = assets_root / "msg"
        english_msg_dir = disc_files["MSGJ.DBS"].parent
        stable_ui.stabilize(msg_dir, english_msg_dir, msg_dir, preserve_english_layout=True)

        title_out = assets_root / TITLE_NAME
        title_logo.patch_title(
            disc_files[TITLE_NAME],
            assets["FONT.MMT"],
            assets_root / "shared_native_hangul_map.tsv",
            title_out,
        )
        assets[TITLE_NAME] = title_out

        changes = full.install_full_assets(disc_files, assets)
        core.rebuild_disc(xml_path, output_bin, output_cue, tools)

        if output_chd:
            if not tools.chdman:
                raise ValueError("--output-chd requires chdman")
            core.make_chd(output_cue, output_chd, tools.chdman)

        output_xdelta = args.output_xdelta.expanduser().resolve() if args.output_xdelta else None
        if output_xdelta:
            create_final_xdelta(source_bin, output_bin, output_xdelta, xdelta3, work_dir)

        report = args.report.expanduser().resolve()
        full.write_full_report(
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
        with report.open("a", encoding="utf-8") as fh:
            fh.write("\n[English base]\n")
            fh.write(f"Upstream English BIN MD5    : {english_hashes.md5}\n")
            fh.write(f"Upstream English BIN SHA256 : {english_hashes.sha256}\n")
            fh.write("Fixed-width UI              : English fallback applied\n")
            fh.write("MSG layout                  : padded to English HDR/DBS sizes\n")
            fh.write("Title subtitle              : 가디아의 보주\n")
            fh.write("Item names                  : PS1 English fallback (v10 stability)\n")
            fh.write("Monster names               : Korean overlay retained\n")
            if output_xdelta:
                fh.write(f"Final xdelta                : {output_xdelta}\n")

    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("")
    print("English-base Korean build complete.")
    print(f"BIN: {output_bin}")
    print(f"CUE: {output_cue}")
    if output_chd:
        print(f"CHD: {output_chd}")
    if args.output_xdelta:
        print(f"xdelta: {args.output_xdelta.expanduser().resolve()}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
