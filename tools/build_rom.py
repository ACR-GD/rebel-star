#!/usr/bin/env python3
"""
Full English translation build for Rebel Star (Super A'Can, F012).
- Prologue 3D crawl: Arial Black 15 (extra-bold, fills 16px band).
- Dialogue: Arial Narrow 12, 3-line layout (matches original box).
"""
import json, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
from vwf_engine import VWFEngine
from create_ips import create_ips_patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM_IN = os.path.join(ROOT, "f012 - rebel star.bin")
ROM_OUT = os.path.join(ROOT, "rebel_star_en.bin")
IPS_OUT = os.path.join(ROOT, "rebel_star_en.ips")
DLG_FONT = 0x12506C          # original font: shared by dialogue, names and ASCII UI strings
NEW_DLG_FONT = 0x200000      # English dialogue font, in the third megabyte (3 MB ROM)
DLG_FONT_LEA = 0x04E5FE      # lea $12506C,a2 in the dialogue box blitter
ROM_SIZE = 0x300000
NAME_TABLE, NAME_COUNT, NAME_STRIDE = 0x3820, 34, 0x34   # 12x2-tile pilot/rank name blocks
BLANK = 0x0040               # empty tile in the original font
PRO_FONT = 0x05763C
PRO_SCRIPT = 0x05DAEC
NUM_PRO_LINES = 103

ARIAL_NARROW = "/System/Library/Fonts/Supplemental/Arial Narrow.ttf"
ARIAL_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

PARAGRAPHS = [
    "In another corner of the vast cosmos, there existed humanoid lifeforms who, as history progressed, developed an advanced yet overcrowded civilization. In the Second Galaxy, within the \"Flo\" star system, lies the very origin of this saga.",
    "Large-scale interstellar migrations sparked a new struggle for economic dominance and political power. Once unified rule was established, a military empire spearheaded by the \"Titan\" warlords launched a series of aggressive campaigns to expand its galactic territory.",
    "In the year 571 of the New Titan Calendar, the fleet of the Titan Empire's Pro Dynasty arrived at the \"Dahl\" star system. Fleet Commander Boris Mitchell issued orders to invade and occupy the second planet—Dana (DANA)—and establish a colonial regime.",
    "The former prime minister of the Dana Republic was appointed Governor-General of Planet Dana to handle nominal self-governance. The Dana Republican Guard was forcibly disbanded, and planetary defense was seized by imperial forces whose primary mandate was crushing all dissenting factions across the colony.",
    "Under this harsh reign of tyranny, underground resistance movements flourished. Anti-oppression rebel organizations arose across the planet, erupting into fierce armed conflict against the Imperial army.",
    "During a raid, underground operatives successfully captured a cache of military equipment, using it to form the 21st Rebel Detachment. The commander who led this daring operation to victory was none other than the son of Dana's Governor-General—Jim Vandaneer."
]


# Name blocks in table order (34 x 12x2 tiles = 96x16 px).
NAMES = [
    "Brin Sinkin", "Larry Carter", "James Peng", "Tom Thompson", "Scott Vincent",
    "Mike Julian", "Tucker Vandaneer", "Marianne Ivan", "George Buchanan", "Ruska Hoover",
    "Jim Vandaneer", "Amy Prodo", "Brandon Van", "Marg Wolf", "Angela Jones",
    "Abel Dimock", "Carson Moore", "Yu Hanji", "Tony Prussia", "Adrian Hank",
    "Joy Bilin", "Julie Kevin", "Richard Galto", "Colin Doff", "Anita Cliff",
    "Fanny Camo", "Jessie Doyle", "Chris Ann", "Wilma Linda", "Mickey Anderson",
    "Meda Kepson", "Imperial Soldier", "Imperial NCO", "Imperial Officer",
]


class Font(VWFEngine):
    def __init__(self, path, size, ls=0):
        super().__init__()
        self.font = ImageFont.truetype(path, size)
        self.letter_spacing = ls
        self.line_height = size + 2

    def rasterize_box(self, lines, box_w=16, box_h=6, left=0):
        W, H = box_w * 8, box_h * 8
        img = Image.new("1", (W, H), 0)
        d = ImageDraw.Draw(img)
        lh = self.line_height
        total = len(lines) * lh
        y0 = max(0, (H - total) // 2)
        for i, ln in enumerate(lines):
            d.text((left, y0 + i * lh), ln, font=self.font, fill=1)
        px = img.load()
        tiles = []
        for ty in range(box_h):
            for tx in range(box_w):
                td = bytearray(8)
                for py in range(8):
                    rb = 0
                    for pxx in range(8):
                        if px[tx * 8 + pxx, ty * 8 + py]:
                            rb |= (1 << (7 - pxx))
                    td[py] = rb
                tiles.append(bytes(td))
        return tiles


def rasterize_pro(font, text):
    W, H = 256, 16
    img = Image.new("1", (W, H), 0)
    d = ImageDraw.Draw(img)
    tw = font.measure_string(text)
    x0 = max(2, (W - tw) // 2)
    d.text((x0, 1), text, font=font.font, fill=1)
    px = img.load()
    top, bot = [], []
    for tx in range(32):
        for half, out in ((0, top), (1, bot)):
            td = bytearray(8)
            for py in range(8):
                rb = 0
                for pxx in range(8):
                    if px[tx * 8 + pxx, half * 8 + py]:
                        rb |= (1 << (7 - pxx))
                td[py] = rb
            out.append(bytes(td))
    return img, top, bot


def main():
    rom = bytearray(open(ROM_IN, "rb").read())
    vwf = Font(ARIAL_NARROW, 12)
    vwf_pro = Font(ARIAL_BLACK, 15)

    # ---- 1. PROLOGUE ----
    crawl = []
    for p in PARAGRAPHS:
        crawl.extend(vwf_pro.wrap_text(p, max_pixel_width=250))
        crawl.append("")
    print(f"Prologue: {len(crawl)} lines / {NUM_PRO_LINES} slots")
    pro_tile_map = {b"\x00" * 8: 24}
    next_tile = 100
    for li in range(NUM_PRO_LINES):
        off = PRO_SCRIPT + li * 128
        text = crawl[li] if li < len(crawl) else ""
        if not text.strip():
            for pos in range(64):
                struct.pack_into(">H", rom, off + pos * 2, 24)
            continue
        _, top, bot = rasterize_pro(vwf_pro, text)
        for pos, tb in enumerate(top + bot):
            if tb == b"\x00" * 8:
                tid = 24
            else:
                if tb not in pro_tile_map:
                    pro_tile_map[tb] = next_tile
                    o = PRO_FONT + next_tile * 8
                    rom[o:o + 8] = tb
                    next_tile += 1
                tid = pro_tile_map[tb]
            struct.pack_into(">H", rom, off + pos * 2, tid)
    print(f"Prologue patched: {len(pro_tile_map)} tiles")

    # ---- 2. DIALOGUE ----
    trans = json.load(open(os.path.join(ROOT, "notes/translations.json")))
    script = {o["addr"]: o for o in json.load(open(os.path.join(ROOT, "notes/boxes.json")))}
    # Tiles >= 0x500 of the original font that only the Chinese dialogue used; the
    # English dialogue no longer reads them, so the English names go there.
    # Entry 0 is not a real box. (The original font is NOT one block: past tile 0x1081 it holds frame/map graphics.)
    name_slots = sorted({struct.unpack_from(">H", rom, o["addr"] + 4 + 2 * i)[0]
                         for o in script.values() if o["idx"] != 0 for i in range(96)} & set(range(0x500, 0x1082)))

    rom.extend(b"\x00" * (ROM_SIZE - len(rom)))
    assert rom[DLG_FONT_LEA:DLG_FONT_LEA + 6] == bytes.fromhex("45f9") + DLG_FONT.to_bytes(4, "big")
    struct.pack_into(">I", rom, DLG_FONT_LEA + 2, NEW_DLG_FONT)

    tile_map = {b"\x00" * 8: 0}
    next_dlg = 1
    patched = 0
    overflow = []
    for k, text in sorted(trans.items(), key=lambda kv: int(kv[0])):
        idx = int(k)
        addr = [o["addr"] for o in script.values() if o["idx"] == idx]
        if not addr:
            continue
        addr = addr[0]
        lines = vwf.wrap_text(text, 128)
        if len(lines) > 3:
            lines = lines[:3]
            overflow.append(idx)
        tiles = vwf.rasterize_box(lines)
        struct.pack_into(">HH", rom, addr, 16, 6)
        for pos, tb in enumerate(tiles):
            if tb not in tile_map:
                tile_map[tb] = next_dlg
                o = NEW_DLG_FONT + next_dlg * 8
                rom[o:o + 8] = tb
                next_dlg += 1
            struct.pack_into(">H", rom, addr + 4 + pos * 2, tile_map[tb])
        patched += 1
    print(f"Dialogue: {patched} blocks, {next_dlg} tiles at 0x{NEW_DLG_FONT:06X}..0x{NEW_DLG_FONT + next_dlg * 8:06X}")
    if overflow:
        print("OVERFLOW (forced 3 lines):", overflow)
    assert NEW_DLG_FONT + next_dlg * 8 <= ROM_SIZE

    # ---- 3. NAMES ----
    assert len(NAMES) == NAME_COUNT
    name_map = {b"\x00" * 8: BLANK}
    free = iter(name_slots)
    for i, name in enumerate(NAMES):
        addr = NAME_TABLE + i * NAME_STRIDE
        assert struct.unpack_from(">HH", rom, addr) == (12, 2), hex(addr)
        assert vwf.measure_string(name) <= 96, name
        for pos, tb in enumerate(vwf.rasterize_box([name], box_w=12, box_h=2)):
            if tb not in name_map:
                name_map[tb] = next(free)
                o = DLG_FONT + name_map[tb] * 8
                rom[o:o + 8] = tb
            struct.pack_into(">H", rom, addr + 4 + pos * 2, name_map[tb])
    print(f"Names: {NAME_COUNT} blocks, {len(name_map) - 1} tiles of {len(name_slots)} free slots")

    open(ROM_OUT, "wb").write(rom)
    print(f"Wrote {ROM_OUT}")
    create_ips_patch(ROM_IN, ROM_OUT, IPS_OUT)


if __name__ == "__main__":
    main()
