import random
import unittest

import audit_korean_linebreaks as wrap
import patch_korean_psx_exe as exe_patch


class RuntimePatchTests(unittest.TestCase):
    def make_fixture(self, *, legacy_v8=False):
        data = bytearray(exe_patch.MIN_SIZE + 64)
        data[exe_patch.CALL_OFFSET : exe_patch.CALL_OFFSET + 4] = exe_patch.CALL_ORIGINAL
        data[exe_patch.LOWERCASE_OFFSET] = 0x60
        for offset, accepted, _ in exe_patch.ITEM_DRAW_CALL_PATCHES:
            value = accepted[-1] if legacy_v8 and len(accepted) > 1 else accepted[0]
            data[offset : offset + 4] = value
        return data

    def test_embedded_wrap_blob_is_stable(self):
        self.assertEqual(len(exe_patch.KOREAN_WRAP_CODE), 336)
        self.assertEqual(
            exe_patch.sha256(exe_patch.KOREAN_WRAP_CODE),
            exe_patch.KOREAN_WRAP_SHA256,
        )

    def test_embedded_item_native_blob_is_stable(self):
        self.assertEqual(len(exe_patch.ITEM_NATIVE_DRAW_CODE), 528)
        self.assertEqual(
            exe_patch.sha256(exe_patch.ITEM_NATIVE_DRAW_CODE),
            exe_patch.ITEM_NATIVE_DRAW_SHA256,
        )
        self.assertEqual(exe_patch.ITEM_INJECT_RUNTIME, 0x800C4070)
        self.assertEqual(exe_patch.DRAW_NATIVE_A, 0x800C4070)
        self.assertEqual(exe_patch.DRAW_NATIVE_A_AT, 0x800C4134)
        self.assertEqual(exe_patch.DRAW_NATIVE_B, 0x800C4174)
        self.assertEqual(exe_patch.DRAW_NATIVE_B_AT, 0x800C423C)

    def test_exe_patch_is_guarded_and_idempotent(self):
        data = self.make_fixture()
        patched, _ = exe_patch.patch_exe(bytes(data))

        self.assertEqual(
            patched[exe_patch.CALL_OFFSET : exe_patch.CALL_OFFSET + 4],
            exe_patch.CALL_PATCHED,
        )
        self.assertEqual(patched[exe_patch.LOWERCASE_OFFSET], 0x70)
        self.assertEqual(
            patched[
                exe_patch.WRAP_INJECT_OFFSET : exe_patch.WRAP_INJECT_OFFSET
                + len(exe_patch.KOREAN_WRAP_CODE)
            ],
            exe_patch.KOREAN_WRAP_CODE,
        )
        self.assertEqual(
            patched[
                exe_patch.ITEM_INJECT_OFFSET : exe_patch.ITEM_INJECT_OFFSET
                + len(exe_patch.ITEM_NATIVE_DRAW_CODE)
            ],
            exe_patch.ITEM_NATIVE_DRAW_CODE,
        )
        for offset, _, expected_patched in exe_patch.ITEM_DRAW_CALL_PATCHES:
            self.assertEqual(patched[offset : offset + 4], expected_patched)

        patched_again, _ = exe_patch.patch_exe(patched)
        self.assertEqual(patched_again, patched)

    def test_v8_wrong_item_calls_are_upgradable(self):
        data = self.make_fixture(legacy_v8=True)
        patched, _ = exe_patch.patch_exe(bytes(data))
        for offset, _, expected_patched in exe_patch.ITEM_DRAW_CALL_PATCHES:
            self.assertEqual(patched[offset : offset + 4], expected_patched)

    def test_nonempty_item_code_cave_is_rejected(self):
        data = self.make_fixture()
        data[exe_patch.ITEM_INJECT_OFFSET + 17] = 0x55
        with self.assertRaises(ValueError):
            exe_patch.patch_exe(bytes(data))

    def test_unexpected_callsite_is_rejected(self):
        data = self.make_fixture()
        data[exe_patch.ITEM_DRAW_CALL_PATCHES[0][0] : exe_patch.ITEM_DRAW_CALL_PATCHES[0][0] + 4] = b"BAD!"
        with self.assertRaises(ValueError):
            exe_patch.patch_exe(bytes(data))

    @staticmethod
    def old_ascii_find_break(data: bytes) -> int:
        pos = 0
        previous = 0
        while True:
            current = data[pos] if pos < len(data) else 0
            if current == 0:
                next_byte = (
                    data[previous + 1]
                    if previous and previous + 1 < len(data)
                    else 0
                )
                if previous and (next_byte in wrap.SPECIAL or pos > 15):
                    return previous
                return -1
            if current == 0x20:
                if pos > 15:
                    return previous
                previous = pos
            pos += 1

    def test_ascii_behavior_matches_english_patch(self):
        rng = random.Random(0x57495A37)
        alphabet = [0x20] + list(range(0x21, 0x7F))
        for _ in range(10000):
            data = bytes(rng.choice(alphabet) for _ in range(rng.randrange(0, 64)))
            self.assertEqual(
                wrap.find_break(data),
                self.old_ascii_find_break(data),
                data,
            )

    def test_dbcs_hyphen_can_be_break_candidate_without_affecting_ascii(self):
        korean = b"\x8f\xdf" * 8 + b"-" + b"\x8f\xde" * 9 + b"-END"
        self.assertEqual(wrap.find_break(korean), 16)

        ascii_text = b"ABCDEFGH-IJKLMNOP-QRSTUV"
        self.assertEqual(
            wrap.find_break(ascii_text),
            self.old_ascii_find_break(ascii_text),
        )


if __name__ == '__main__':
    unittest.main()
