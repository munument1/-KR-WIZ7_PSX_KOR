/*
 * Wizardry VII PSX - direct-native Korean item-name draw wrappers.
 *
 * SCENARIJ.DBS item names are already encoded in the Korean native DBCS used
 * by FONT.MMT. The stock Japanese/full-width wrappers first translate their
 * input through the game's Shift-JIS conversion table, which corrupts those
 * already-native bytes. These wrappers preserve the two original cursor/font
 * families but bypass Shift-JIS conversion and call the low-level renderers
 * directly.
 *
 * Production link address: 0x800C4070 (PSX.EXE file offset 0xB4870).
 * Build used for the embedded blob in korean/tools/patch_korean_psx_exe.py:
 *
 * clang --target=mipsel-none-elf -Os -mips1 -mabi=32 -msoft-float \
 *   -fno-pic -mno-abicalls -G0 -ffreestanding -fno-builtin \
 *   -fno-stack-protector -fomit-frame-pointer
 */

typedef int s32;
typedef void (*draw_a_fn)(int, int, int, int, const char *);
typedef void (*draw_b_fn)(int, int, int, int, const char *);
typedef int (*strlen_fn)(const char *);
typedef void (*setpos_fn)(int, int);

#define AX (*(volatile s32 *)0x800d1498u)
#define AY (*(volatile s32 *)0x800d14c8u)
#define BX (*(volatile s32 *)0x800d04d8u)
#define BY (*(volatile s32 *)0x800d04dcu)
#define COLOR (*(volatile s32 *)0x800e3734u)

#define DRAW_A ((draw_a_fn)0x80076f50u)
#define DRAW_B ((draw_b_fn)0x80074f0cu)
#define STRLEN ((strlen_fn)0x80083c24u)
#define SET_A ((setpos_fn)0x8006cd84u)
#define SET_B ((setpos_fn)0x8006ccb4u)

__attribute__((section(".text.native"), noinline))
void draw_native_a(const char *s, int unused) {
    int x = AX;
    int y = AY;
    (void)unused;
    DRAW_A(-1, x / 12, y / 12, COLOR, s);
    /* Native Korean is two bytes per full-width glyph: 2 * 6 = 12 pixels. */
    AX = x + STRLEN(s) * 6;
}

__attribute__((section(".text.native"), noinline))
void draw_native_a_at(const char *s, int x, int y) {
    SET_A(x, y);
    draw_native_a(s, 0);
}

__attribute__((section(".text.native"), noinline))
void draw_native_b(const char *s, int unused) {
    int x = BX;
    int y = BY;
    (void)unused;
    DRAW_B(1, (x - 42) / 12, (y - 96) / 12, COLOR, s);
    BX = x + STRLEN(s) * 6;
}

__attribute__((section(".text.native"), noinline))
void draw_native_b_at(const char *s, int x, int y) {
    SET_B(x, y);
    draw_native_b(s, 0);
}
