import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from native_psx_codepage import build_native_mapping, encode_text


@dataclass(frozen=True)
class R:
    text: str


class SharedCodepageTests(unittest.TestCase):
    def test_extra_asset_hangul_joins_msg_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            extra = Path(td) / "items.tsv"
            extra.write_text("id\tko_name\n1\t힣\n", encoding="utf-8")
            mapping, freq = build_native_mapping([R("가나다")], [extra])
            self.assertEqual(set(mapping), set("가나다힣"))
            self.assertEqual(freq["힣"], 1)
            self.assertEqual(mapping["가"].slot, 2047)
            self.assertEqual(mapping["힣"].slot, 2044)

    def test_extra_asset_changes_mapping_deterministically(self):
        base, _ = build_native_mapping([R("나다")])
        with tempfile.TemporaryDirectory() as td:
            extra = Path(td) / "monsters.tsv"
            extra.write_text("id\tko_specific_singular\n0\t가\n", encoding="utf-8")
            shared, _ = build_native_mapping([R("나다")], [extra])
            self.assertEqual(shared["가"].slot, 2047)
            self.assertEqual(shared["나"].slot, 2046)
            self.assertEqual(shared["다"].slot, 2045)
            self.assertNotEqual(base["나"].slot, shared["나"].slot)

    def test_shared_mapping_encodes_msg_and_extra_chars(self):
        with tempfile.TemporaryDirectory() as td:
            extra = Path(td) / "items.tsv"
            extra.write_text("id\tko_name\n1\t힣\n", encoding="utf-8")
            mapping, _ = build_native_mapping([R("가")], [extra])
            encoded = encode_text("가힣", mapping)
            self.assertEqual(len(encoded), 4)
            self.assertEqual(encoded[:2], mapping["가"].encoded)
            self.assertEqual(encoded[2:], mapping["힣"].encoded)


if __name__ == "__main__":
    unittest.main(verbosity=2)
