import unittest

import patch_korean_psx_item_native_passthrough as item_patch


class ItemNativePassthroughTests(unittest.TestCase):
    def make_fixture(self):
        data = bytearray(item_patch.MIN_SIZE + 32)
        data[item_patch.PASSTHROUGH_OFFSET:item_patch.PASSTHROUGH_OFFSET + 4] = item_patch.PASSTHROUGH_ORIGINAL
        for off, original, _ in item_patch.ITEM_DRAW_CALL_PATCHES:
            data[off:off + 4] = original
        return bytes(data)

    def test_patch_is_minimal_and_idempotent(self):
        src = self.make_fixture()
        out, _ = item_patch.patch_exe(src)
        self.assertEqual(
            out[item_patch.PASSTHROUGH_OFFSET:item_patch.PASSTHROUGH_OFFSET + 4],
            item_patch.PASSTHROUGH_PATCHED,
        )
        for off, _, patched in item_patch.ITEM_DRAW_CALL_PATCHES:
            self.assertEqual(out[off:off + 4], patched)

        changed = [i for i, (a, b) in enumerate(zip(src, out)) if a != b]
        # NOP changes three non-zero bytes of addiu s0,sp,0x18 plus one byte in
        # each JAL target, so the supported fixture has exactly nine byte deltas.
        self.assertEqual(len(changed), 9)
        out2, _ = item_patch.patch_exe(out)
        self.assertEqual(out2, out)

    def test_unexpected_passthrough_instruction_rejected(self):
        data = bytearray(self.make_fixture())
        data[item_patch.PASSTHROUGH_OFFSET:item_patch.PASSTHROUGH_OFFSET + 4] = b"BAD!"
        with self.assertRaises(ValueError):
            item_patch.patch_exe(bytes(data))

    def test_unexpected_callsite_rejected(self):
        data = bytearray(self.make_fixture())
        off = item_patch.ITEM_DRAW_CALL_PATCHES[0][0]
        data[off:off + 4] = b"BAD!"
        with self.assertRaises(ValueError):
            item_patch.patch_exe(bytes(data))


if __name__ == "__main__":
    unittest.main()
