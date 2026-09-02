import random
import unittest

import audit_korean_linebreaks as wrap
import patch_korean_psx_exe as exe_patch


class RuntimePatchTests(unittest.TestCase):
    def test_embedded_wrap_blob_is_stable(self):
        self.assertEqual(len(exe_patch.KOREAN_WRAP_CODE), 336)
        self.assertEqual(
            exe_patch.sha256(exe_patch.KOREAN_WRAP_CODE),
            exe_patch.KOREAN_WRAP_SHA256,
        )

    def test_exe_patch_is_guarded_and_idempotent(self):
        data = bytearray(exe_patch.MIN_SIZE + 64)
        data[exe_patch.CALL_OFFSET : exe_patch.CALL_OFFSET + 4] = exe_patch.CALL_ORIGINAL
        data[exe_patch.LOWERCASE_OFFSET] = 0x60
        for offset, expected, _ in exe_patch.ITEM_DRAW_CALL_PATCHES:
            data[offset : offset + 4] = expected

        patched, _ = exe_patch.patch_exe(bytes(data))
        self.assertEqual(
            patched[exe_patch.CALL_OFFSET : exe_patch.CALL_OFFSET + 4],
            exe_patch.CALL_PATCHED,
        )
        self.assertEqual(patched[exe_patch.LOWERCASE_OFFSET], 0x70)
        self.assertEqual(
            patched[
                exe_patch.INJECT_OFFSET : exe_patch.INJECT_OFFSET
                + len(exe_patch.KOREAN_WRAP_CODE)
            ],
            exe_patch.KOREAN_WRAP_CODE,
        )
        for offset, _, expected_patched in exe_patch.ITEM_DRAW_CALL_PATCHES:
            self.assertEqual(patched[offset : offset + 4], expected_patched)

        patched_again, _ = exe_patch.patch_exe(patched)
        self.assertEqual(patched_again, patched)

    def test_unexpected_callsite_is_rejected(self):
        data = bytearray(exe_patch.MIN_SIZE + 64)
        data[exe_patch.CALL_OFFSET : exe_patch.CALL_OFFSET + 4] = b"BAD!"
        data[exe_patch.LOWERCASE_OFFSET] = 0x60
        for offset, expected, _ in exe_patch.ITEM_DRAW_CALL_PATCHES:
            data[offset : offset + 4] = expected
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
        # Native DBCS is present before '-', so the Korean separator is eligible.
        korean = b"\x8f\xdf" * 8 + b"-" + b"\x8f\xde" * 9 + b"-END"
        self.assertEqual(wrap.find_break(korean), 16)

        # Pure ASCII hyphens retain the old English-patch behavior.
        ascii_text = b"ABCDEFGH-IJKLMNOP-QRSTUV"
        self.assertEqual(
            wrap.find_break(ascii_text),
            self.old_ascii_find_break(ascii_text),
        )


if __name__ == "__main__":
    unittest.main()
