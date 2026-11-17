# Rebel Star (叛星, Super A'Can) — English Translation

## Patch

| Patch | Apply to | Result |
|---|---|---|
| `rebel_star_en.ips` | `f012 - rebel star.bin` (2,097,152 bytes, CRC32 `a3469172`, SHA-1 `3a1b093d7aee6d5b1f260723499d4c283a2a0169`, the MAME `rebelst` dump) | `rebel_star_en.bin` (3,145,728 bytes) |

The patched ROM is **3 MB**: the English dialogue font lives in the third megabyte (data-ROM window
`$200000`, same layout as Sango Fighter).

- **Repo emulator:** open `rebel_star_en.bin`.
- **MAME:** the `rebelst` software-list entry is 2 MB, so MAME cuts the file and the dialogue boxes
  come out empty. Load it as a loose cartridge instead; loose carts must be byte-swapped:
  `dd if=rebel_star_en.bin of=rebel_star_en_mame.bin conv=swab` then
  `mame supracan -cart rebel_star_en_mame.bin`.

## Status

Translated: prologue crawl, all 402 dialogue boxes, the 34 pilot / rank names shown in the unit
panel. Unit and weapon names (VAG-23, DN-2X, ...) and the title menu were already English. The
叛星 logo is left as is (REBEL is printed under it).

Tested in the repo emulator and MAME 0.28x: intro, prologue, title, the first stage's dialogue,
unit panel. Not yet seen: later stages, the ending, game over, load screen.

## Build

Put your own `f012 - rebel star.bin` in this folder, then:

```
python3 tools/build_rom.py      # -> rebel_star_en.bin + rebel_star_en.ips
```

Needs Python 3 with Pillow, and the Arial Narrow / Arial Black fonts from macOS
(`/System/Library/Fonts/Supplemental/`).

- `notes/translations.json`: English text per dialogue box index.
- `notes/boxes.json`: ROM address of each box (index 0 is not a real box).
- Names: `NAMES` in `tools/build_rom.py`; prologue: `PARAGRAPHS` in the same file.
- `notes/text_engine.md`: prologue crawl and dialogue engine notes.
- `tools/extract_assets.py`: dumps palettes, tiles, audio and the dialogue box images to `extracted/`.

## ROM notes

- Dialogue box = `w,h` (16,6) + 96 tile indices into a 1bpp 8×8 font; the blitter at `$04E5F4`
  reads the font base from `lea $12506C,a2` at `$04E5FE`. The build repoints it to `$200000`.
- The font at `$12506C` is **not** one contiguous font: tiles `0x00–0x35` are UI/ASCII, the Chinese
  dialogue used tiles up to `0x1081`, and the area after that holds the dialogue frame and map
  graphics. Writing past tile `0x1081` corrupts them.
- Names: 34 blocks of 12×2 tiles at `$3820`, stride `$34`. Their English tiles reuse slots
  `0x500–0x1081` that only the Chinese dialogue used.
- Only free space in the 2 MB ROM: `$1F2F6A–$1FFFFF` (53 KB), too small for the 62 KB dialogue font.
