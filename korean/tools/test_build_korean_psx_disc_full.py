#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import build_korean_psx_disc as core
import build_korean_psx_disc_full as full


class FullDiscBuildTests(unittest.TestCase):
    def test_parser_defaults_to_repo_scenario_tables(self):
        parser = full.make_parser()
        args = parser.parse_args(["source.bin"])
        self.assertEqual(args.scenario_items, Path("korean/scenario/items.ko.tsv"))
        self.assertEqual(args.scenario_monsters, Path("korean/scenario/monsters.ko.tsv"))

    def test_install_full_assets_copies_six_core_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            names = (*core.DISC_FILENAMES, full.SCENARIO_NAME)
            disc = {}
            assets = {}
            for i, name in enumerate(names):
                target = root / "disc" / name
                source = root / "assets" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                source.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(f"old-{i}".encode())
                source.write_bytes(f"new-{i}".encode())
                disc[name] = target
                assets[name] = source

            changes = full.install_full_assets(disc, assets)
            self.assertEqual(set(changes), set(names))
            self.assertEqual(disc[full.SCENARIO_NAME].read_bytes(), b"new-5")

    def test_relative_scenario_path_resolves_from_repo_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            got = full.resolve_asset_path(root, Path("korean/scenario/items.ko.tsv"))
            self.assertEqual(got, (root / "korean/scenario/items.ko.tsv").resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
