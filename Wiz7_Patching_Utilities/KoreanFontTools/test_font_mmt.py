import unittest
from pathlib import Path

import font_mmt

FONT = Path('/mnt/data/wiz7_psx_core/FONT.MMT')


class FontMMTTests(unittest.TestCase):
    def test_renderer_bias_and_identity_planes(self):
        # Original ZENKAKU maps ASCII 'A' to 80A5. The renderer computes glyph
        # 69, while the original FONT.MMT bitmap for A is physical slot 65.
        self.assertEqual(font_mmt.renderer_glyph_to_font_slot(69), 65)
        self.assertEqual(font_mmt.renderer_glyph_to_font_slot(68), 64)
        self.assertEqual(font_mmt.font_slot_to_renderer_glyph(65), 69)

        # At a 64-cell texture-row boundary the one-cell-left relation wraps
        # inside the same row instead of spilling into the previous row.
        self.assertEqual(font_mmt.renderer_glyph_to_font_slot(1280), 1532)
        self.assertEqual(font_mmt.renderer_glyph_to_font_slot(1282), 1534)
        self.assertEqual(font_mmt.font_slot_to_renderer_glyph(1534), 1282)
        self.assertEqual(font_mmt.renderer_glyph_to_font_slot(1792), 2044)
        self.assertEqual(font_mmt.renderer_glyph_to_font_slot(2047), 2043)

        # Raw FONT.MMT bitplanes are in natural 0,1,2,3 order.
        x, y, plane = font_mmt.glyph_origin(64)
        self.assertEqual((x, y, plane), (16 * 16, 3, 0))
        self.assertEqual(font_mmt.glyph_origin(65)[2], 1)
        self.assertEqual(font_mmt.glyph_origin(66)[2], 2)
        self.assertEqual(font_mmt.glyph_origin(67)[2], 3)

    @unittest.skipUnless(FONT.exists(), 'PSX FONT.MMT fixture not present')
    def test_geometry_and_known_slot(self):
        data = FONT.read_bytes()
        font_mmt.validate_font(data)
        self.assertEqual(font_mmt.GLYPH_COUNT, 2048)
        self.assertEqual(font_mmt.glyph_origin(65), (16 * 16, 3, 1))
        glyph = font_mmt.extract_glyph(data, 65)
        self.assertTrue(any(glyph))

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
        # Renderer glyph 69 maps to physical FONT.MMT slot 65.
        modified = font_mmt.galmuri11_rows_to_mmt(data, 69, blank)
        after = [font_mmt.extract_glyph(modified, i) for i in (64, 66, 67)]
        self.assertEqual(before, after)
        self.assertFalse(any(font_mmt.extract_glyph(modified, 65)))


if __name__ == '__main__':
    unittest.main()
