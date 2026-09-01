#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_korean_psx_disc",
    HERE / "build_korean_psx_disc.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class DiscBuildTests(unittest.TestCase):
    def test_parse_cue_files_quoted_and_unquoted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cue = root / "game.cue"
            cue.write_text(
                'FILE "Track One.bin" BINARY\n'
                '  TRACK 01 MODE2/2352\n'
                'FILE track2.bin BINARY\n',
                encoding="utf-8",
            )
            got = mod.parse_cue_files(cue)
            self.assertEqual(
                got,
                [
                    (root / "Track One.bin").resolve(),
                    (root / "track2.bin").resolve(),
                ],
            )

    def test_find_unique_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "CDS" / "D" / "font.mmt"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"x")
            self.assertEqual(mod.find_unique(root, "FONT.MMT"), target)

    def test_find_unique_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for sub in ("A", "B"):
                path = root / sub / "PSX.EXE"
                path.parent.mkdir()
                path.write_bytes(sub.encode())
            with self.assertRaisesRegex(ValueError, "multiple PSX.EXE"):
                mod.find_unique(root, "PSX.EXE")

    def test_verify_bin_requires_known_hash_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "wrong.bin"
            path.write_bytes(b"not-the-game")
            with self.assertRaisesRegex(ValueError, "Unsupported source BIN"):
                mod.verify_bin(path, allow_unverified=False)
            hashes = mod.verify_bin(path, allow_unverified=True)
            self.assertEqual(hashes.md5, mod.file_hashes(path).md5)

    def test_install_assets_copies_all_required_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            extracted_files = {}
            assets = {}
            for index, name in enumerate(mod.DISC_FILENAMES):
                target = root / "disc" / "CDS" / "D" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(f"old-{index}".encode())
                source = root / "assets" / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(f"new-{index}".encode())
                extracted_files[name] = target
                assets[name] = source

            changes = mod.install_assets(extracted_files, assets)
            self.assertEqual(set(changes), set(mod.DISC_FILENAMES))
            for index, name in enumerate(mod.DISC_FILENAMES):
                self.assertEqual(
                    extracted_files[name].read_bytes(),
                    f"new-{index}".encode(),
                )
                self.assertNotEqual(changes[name][0], changes[name][1])

    def test_mapping_parity_accepts_column_order_difference(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            msg = root / "msg.tsv"
            font = root / "font.tsv"
            msg.write_text(
                "unicode\tchar\tcount\tlead\ttrail\tcode_hex\tslot\n"
                "U+AC00\t가\t1\t0x8F\t0xDF\t8FDF\t2047\n",
                encoding="utf-8",
            )
            font.write_text(
                "char\tunicode\tlead\ttrail\tcode_hex\tslot\tcount\n"
                "가\tU+AC00\t0x8F\t0xDF\t8FDF\t2047\t1\n",
                encoding="utf-8",
            )
            mod.verify_mapping_parity(msg, font)

    def test_mapping_parity_rejects_code_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            msg = root / "msg.tsv"
            font = root / "font.tsv"
            msg.write_text(
                "unicode\tchar\tcount\tlead\ttrail\tcode_hex\tslot\n"
                "U+AC00\t가\t1\t0x8F\t0xDF\t8FDF\t2047\n",
                encoding="utf-8",
            )
            font.write_text(
                "char\tunicode\tlead\ttrail\tcode_hex\tslot\tcount\n"
                "가\tU+AC00\t0x8F\t0xDE\t8FDE\t2046\t1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "codepage mismatch"):
                mod.verify_mapping_parity(msg, font)

    def test_normalize_output_derives_cue(self):
        parser = mod.make_parser()
        args = parser.parse_args(["source.bin", "--output-bin", "foo/bar.bin"])
        out_bin, out_cue, out_chd = mod.normalize_output_paths(args)
        self.assertEqual(out_bin.name, "bar.bin")
        self.assertEqual(out_cue.name, "bar.cue")
        self.assertIsNone(out_chd)


if __name__ == "__main__":
    unittest.main(verbosity=2)
