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
    def test_native_slot_code_boundaries(self):
        known = {
            0: (0x80, 0x30),
            63: (0x80, 0x6F),
            64: (0x80, 0xA0),
            127: (0x80, 0xDF),
            128: (0x81, 0x30),
            2047: (0x8F, 0xDF),
        }
        for slot, code in known.items():
            self.assertEqual(kf.slot_to_native_code(slot), code)
            self.assertEqual(kf.native_code_to_slot(*code), slot)

    def test_all_2048_native_codes_roundtrip_uniquely(self):
        seen = set()
        for slot in range(2048):
            code = kf.slot_to_native_code(slot)
            self.assertNotIn(code, seen)
            seen.add(code)
            self.assertEqual(kf.native_code_to_slot(*code), slot)
        self.assertEqual(len(seen), 2048)

    def test_native_allocation_skips_reserved(self):
        mapping = kf.allocate_native_mapping(['가', '나'], {2047})
        self.assertEqual(mapping['가'].slot, 2046)
        self.assertEqual((mapping['가'].lead, mapping['가'].trail), (0x8F, 0xDE))
        self.assertEqual(mapping['나'].slot, 2045)

    def test_conservative_low_bank_reservation_capacity(self):
        reserved = set(range(280))
        mapping = kf.allocate_native_mapping(['가', '나'], reserved)
        self.assertEqual(mapping['가'].slot, 2047)
        self.assertEqual(mapping['나'].slot, 2046)
        self.assertEqual(2048 - len(reserved), 1768)

    def test_encoder_keeps_ascii_and_expands_hangul(self):
        m = {'가': (0x80, 0x30)}
        self.assertEqual(kf.encode_text('A가!', m), b'A\x80\x30!')

    def test_bdf_parser_and_glyph_emit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bdf = root / 'font.bdf'
            bdf.write_text(BDF, encoding='ascii')
            glyphs = kf.parse_bdf(bdf)
            self.assertIn(ord('가'), glyphs)
            self.assertEqual(glyphs[ord('가')].width, 11)
            mapping = kf.allocate_native_mapping(['가', '나'])
            kf.emit_glyphs(root, ['가', '나'], mapping, glyphs)
            self.assertEqual((root / 'korean_glyphs.bin').stat().st_size, 2 * 11 * 2)

    @unittest.skipUnless(Path('/mnt/data/wiz7_psx_core/ZENKAKU.TBL').exists(), 'PSX ZENKAKU.TBL fixture not present')
    def test_real_zenkaku_reserved_slots(self):
        reserved = kf.zenkaku_reserved_slots(Path('/mnt/data/wiz7_psx_core/ZENKAKU.TBL'))
        self.assertEqual(len(reserved), 198)
        self.assertLessEqual(max(reserved), 279)
        self.assertEqual(2048 - len(reserved), 1850)

    @unittest.skipUnless(
        Path('/mnt/data/wiz7_psx_core/FONT.MMT').exists(),
        'PSX FONT.MMT fixture not present',
    )
    def test_build_patched_font_changes_only_allocated_plane(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bdf = root / 'font.bdf'
            bdf.write_text(BDF, encoding='ascii')
            glyphs = kf.parse_bdf(bdf)
            mapping = kf.allocate_native_mapping(['가'], {0, 1, 2})
            out = root / 'FONT_KOR.MMT'
            kf.build_patched_font(
                Path('/mnt/data/wiz7_psx_core/FONT.MMT'), out,
                ['가'], mapping, glyphs,
            )
            self.assertEqual(out.stat().st_size, Path('/mnt/data/wiz7_psx_core/FONT.MMT').stat().st_size)
            self.assertNotEqual(out.read_bytes(), Path('/mnt/data/wiz7_psx_core/FONT.MMT').read_bytes())


if __name__ == '__main__':
    unittest.main()
