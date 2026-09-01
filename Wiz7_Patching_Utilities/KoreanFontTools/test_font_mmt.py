import unittest
from pathlib import Path

import font_mmt

FONT = Path('/mnt/data/wiz7_psx_core/FONT.MMT')


class FontMMTTests(unittest.TestCase):
    @unittest.skipUnless(FONT.exists(), 'PSX FONT.MMT fixture not present')
    def test_geometry_and_known_ascii_slots(self):
        data = FONT.read_bytes()
        font_mmt.validate_font(data)
        self.assertEqual(font_mmt.GLYPH_COUNT, 2048)
        self.assertEqual(font_mmt.glyph_origin(65), (16 * 16, 3, 1))
        a = font_mmt.extract_glyph(data, 65)
        self.assertTrue(any(a))

    @unittest.skipUnless(FONT.exists(), 'PSX FONT.MMT fixture not present')
    def test_roundtrip_same_glyph_is_byte_identical(self):
        data = FONT.read_bytes()
        rows = font_mmt.extract_glyph(data, 65)
        rebuilt = font_mmt.replace_glyph(data, 65, rows, glyph_w=16, glyph_h=12)
        self.assertEqual(rebuilt, data)

    @unittest.skipUnless(FONT.exists(), 'PSX FONT.MMT fixture not present')
    def test_replacement_preserves_neighbor_planes(self):
        data = FONT.read_bytes()
        before = [font_mmt.extract_glyph(data, i) for i in (64, 66, 67)]
        blank = [0] * 11
        modified = font_mmt.galmuri11_rows_to_mmt(data, 65, blank)
        after = [font_mmt.extract_glyph(modified, i) for i in (64, 66, 67)]
        self.assertEqual(before, after)
        self.assertFalse(any(font_mmt.extract_glyph(modified, 65)))


if __name__ == '__main__':
    unittest.main()
