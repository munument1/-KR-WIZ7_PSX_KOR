import tempfile
import unittest
from pathlib import Path

import build_korean_font as kf


BDF = '''STARTFONT 2.1
FONT test
SIZE 11 75 75
FONTBOUNDINGBOX 11 11 0 0
CHARS 2
STARTCHAR AC00
ENCODING 44032
SWIDTH 1000 0
DWIDTH 11 0
BBX 11 11 0 0
BITMAP
FFE0
8020
8020
8020
8020
8020
8020
8020
8020
8020
FFE0
ENDCHAR
STARTCHAR B098
ENCODING 45208
SWIDTH 1000 0
DWIDTH 11 0
BBX 11 11 0 0
BITMAP
8020
8020
8020
8020
FFE0
0020
0020
0020
0020
0020
0020
ENDCHAR
ENDFONT
'''


class ToolTests(unittest.TestCase):
    def test_dbcs_allocation_is_stable(self):
        m = kf.allocate_dbcs(['가', '나'])
        self.assertEqual(m['가'], (0x80, 0x40))
        self.assertEqual(m['나'], (0x80, 0x41))

    def test_encoder_keeps_ascii_and_expands_hangul(self):
        m = {'가': (0x80, 0x40)}
        self.assertEqual(kf.encode_text('A가!', m), b'A\x80\x40!')

    def test_bdf_parser_and_glyph_emit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bdf = root / 'font.bdf'
            bdf.write_text(BDF, encoding='ascii')
            glyphs = kf.parse_bdf(bdf)
            self.assertIn(ord('가'), glyphs)
            self.assertEqual(glyphs[ord('가')].width, 11)
            mapping = kf.allocate_dbcs(['가', '나'])
            kf.emit_glyphs(root, ['가', '나'], mapping, glyphs)
            self.assertEqual((root / 'korean_glyphs.bin').stat().st_size, 2 * 11 * 2)


if __name__ == '__main__':
    unittest.main()
