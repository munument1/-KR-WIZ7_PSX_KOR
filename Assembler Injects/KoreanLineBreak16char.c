/* Wizardry VII PSX Korean 16-glyph line-break replacement.
 *
 * Runtime address: 0x800C9800
 * PSX.EXE file offset: 0xBA000
 * Caller: 0x8005C828 / file offset 0x4D028
 *
 * The original English patch counts bytes, which makes every native two-byte
 * Korean glyph consume two of the 16 positions. This replacement keeps the
 * returned value as a byte offset (required by the caller) but counts native
 * 0x80..0x8F two-byte codes as one visible glyph.
 *
 * Korean T'Rang speech in the current translation deliberately uses '-' as a
 * word separator. Once a native DBCS glyph has been seen, '-' is therefore
 * accepted as an additional break candidate. The caller replaces the returned
 * delimiter with NUL and resumes after it, so a selected '-' behaves like a
 * space and is not rendered. Pure ASCII strings retain the exact English-patch
 * behavior because hyphens are ignored until native DBCS is observed.
 */
typedef unsigned char u8;

static int is_special(u8 c) {
    return c == '!' || c == '%' || c == '&' || c == ']' ||
           c == '@' || c == '#' || c == '|';
}

int wiz7_korean_wrap(const u8 *s, u8 character) {
    unsigned short byte_pos = 0;
    unsigned short glyph_pos = 0;
    unsigned short prev_pos = 0;
    int seen_dbcs = 0;

    for (;;) {
        u8 c = s[byte_pos];

        if (c == 0) {
            if (prev_pos &&
                (is_special(s[(unsigned short)(prev_pos + 1)]) ||
                 glyph_pos > 15)) {
                return (int)prev_pos;
            }
            return -1;
        }

        if (c == character || (seen_dbcs && c == '-')) {
            if (glyph_pos > 15)
                return (int)prev_pos;
            prev_pos = byte_pos;
        }

        if (c >= 0x80 && c <= 0x8f &&
            s[(unsigned short)(byte_pos + 1)] != 0) {
            seen_dbcs = 1;
            byte_pos = (unsigned short)(byte_pos + 2);
        } else {
            byte_pos = (unsigned short)(byte_pos + 1);
        }

        glyph_pos = (unsigned short)(glyph_pos + 1);
    }
}

/* Reproducible build used for the committed patch blob:
 *
 * clang --target=mipsel-none-elf -march=mips1 -mabi=32 -mno-abicalls \
 *   -fno-pic -ffreestanding -fno-builtin -Oz -c KoreanLineBreak16char.c \
 *   -o KoreanLineBreak16char.o
 *
 * Link .text at 0x800C9800 with lld, then extract only .text.
 * Verified blob size: 336 bytes
 * SHA-256: f91ae18e51f44a2fad28e1d0620891b2b03af6172b2ac9932b39d3972718d52c
 */
