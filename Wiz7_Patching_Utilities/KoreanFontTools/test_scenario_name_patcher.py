import tempfile
import unittest
from pathlib import Path

import scenario_name_patcher as s


class ScenarioNamePatcherTests(unittest.TestCase):
    def make_mapping(self, root: Path) -> Path:
        path = root / "map.tsv"
        path.write_text(
            "char\tlead\ttrail\tslot\n"
            "가\t0x8F\t0xDF\t2047\n"
            "나\t0x8F\t0xDE\t2046\n"
            "다\t0x8F\t0xDD\t2045\n"
            "라\t0x8F\t0xDC\t2044\n"
            "마\t0x8F\t0xDB\t2043\n"
            "바\t0x8F\t0xDA\t2042\n"
            "사\t0x8F\t0xD9\t2041\n"
            "아\t0x8F\t0xD8\t2040\n",
            encoding="utf-8",
        )
        return path

    def make_scenario(self, root: Path) -> Path:
        data = bytearray(s.EXPECTED_SCENARIO_SIZE)
        item = s.ITEM_START
        data[item:item + s.ITEM_NAME_SIZE] = b"DAGGER\0" + bytes(s.ITEM_NAME_SIZE - 7)
        mon = s.MON_START + s.MON_NAME_OFF
        for i, name in enumerate((b"DANDIPHOOT", b"DANDIPHOOTS", b"PHOOT", b"PHOOTS")):
            field = name + b"\0" + bytes(s.MON_FIELD_SIZE - len(name) - 1)
            data[mon + i*s.MON_FIELD_SIZE:mon + (i+1)*s.MON_FIELD_SIZE] = field
        path = root / "SCENARIJ.DBS"
        path.write_bytes(data)
        return path

    def test_item_and_monster_patch_stay_inside_verified_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self.make_scenario(root)
            mapping = self.make_mapping(root)
            items = root / "items.tsv"
            items.write_text("id\tko_name\n0\t가나다\n", encoding="utf-8")
            monsters = root / "monsters.tsv"
            monsters.write_text(
                "id\tko_specific_singular\tko_specific_plural\tko_generic_singular\tko_generic_plural\n"
                "0\t가나다\t가나다라\t가\t가나\n",
                encoding="utf-8",
            )
            output = root / "out.DBS"
            s.apply_patch(source, mapping, items, monsters, output)
            before = source.read_bytes()
            after = output.read_bytes()
            changed = {i for i, (a, b) in enumerate(zip(before, after)) if a != b}
            allowed = set(range(s.ITEM_START, s.ITEM_START + s.ITEM_NAME_SIZE))
            mon0 = s.MON_START + s.MON_NAME_OFF
            allowed.update(range(mon0, mon0 + 4*s.MON_FIELD_SIZE))
            self.assertTrue(changed)
            self.assertTrue(changed <= allowed)

    def test_monster_eight_hangul_syllables_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mapping = self.make_mapping(root)
            m = s.load_mapping(mapping)
            with self.assertRaisesRegex(ValueError, "max is 15"):
                s.fixed_field("가나다라마바사아", s.MON_FIELD_SIZE, m, "monster 0")

    def test_item_ten_hangul_syllables_fit_but_eleven_do_not(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mapping = self.make_mapping(root)
            with mapping.open("a", encoding="utf-8") as f:
                f.write("자\t0x8F\t0xD7\t2039\n차\t0x8F\t0xD6\t2038\n카\t0x8F\t0xD5\t2037\n")
            m = s.load_mapping(mapping)
            ten = "가나다라마바사아자차"
            self.assertEqual(len(s.fixed_field(ten, s.ITEM_NAME_SIZE, m, "item 0")), s.ITEM_NAME_SIZE)
            with self.assertRaisesRegex(ValueError, "max is 21"):
                s.fixed_field(ten + "카", s.ITEM_NAME_SIZE, m, "item 0")


if __name__ == "__main__":
    unittest.main()
