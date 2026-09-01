import csv
import json
import tempfile
import unittest
from pathlib import Path

import apply_font_assets as afa
import font_mmt


@unittest.skipUnless(
    Path('/mnt/data/wiz7_psx_core/FONT.MMT').exists(),
    'PSX FONT.MMT fixture not present',
)
class ApplyAssetsTests(unittest.TestCase):
    def make_assets(self, root: Path) -> Path:
        assets = root / 'assets'
        assets.mkdir()
        with (assets / 'korean_dbcs.tsv').open('w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['char','unicode','lead','trail','code_hex','slot','count'])
            w.writerow(['가','U+AC00','0x8F','0xDF','8FDF','2047','1'])
        rows = [0x7FF] * 11
        (assets / 'korean_glyphs.bin').write_bytes(b''.join(x.to_bytes(2,'big') for x in rows))
        (assets / 'build_info.json').write_text(json.dumps({'reserve_low_through':279}), encoding='utf-8')
        return assets

    def test_apply_and_preserve_untargeted_slots(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            assets = self.make_assets(root)
            out = root / 'FONT_KOR.MMT'
            report = afa.apply_assets(
                Path('/mnt/data/wiz7_psx_core/FONT.MMT'), assets, out
            )
            self.assertEqual(report['charset_size'], 1)
            self.assertEqual(report['target_slot_min'], 2047)
            before = Path('/mnt/data/wiz7_psx_core/FONT.MMT').read_bytes()
            after = out.read_bytes()
            self.assertEqual(font_mmt.extract_glyph(before, 0), font_mmt.extract_glyph(after, 0))
            self.assertNotEqual(font_mmt.extract_glyph(before, 2047), font_mmt.extract_glyph(after, 2047))


if __name__ == '__main__':
    unittest.main()
