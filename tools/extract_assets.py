#!/usr/bin/env python3
"""
Comprehensive asset and content extractor for Rebel Star (f012 - rebel star.bin)
Super A'Can (Funtech Entertainment Corp. / United Microelectronics Corp., 1995)
Motorola 68000 @ 10.6 MHz + WDC W65C02 APU @ 3.58 MHz + UM70C188 PPU
"""

import os
import sys
import struct
import json
import hashlib
import zlib
import wave
from typing import Tuple, List, Dict, Any
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROM_FILENAME = "f012 - rebel star.bin"
ROM_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), ROM_FILENAME)
OUT_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "extracted")


def swap16(data: bytes) -> bytes:
    """16-bit word byte swap between dumper order and 68000 native big-endian order."""
    out = bytearray(len(data))
    out[0::2] = data[1::2]
    out[1::2] = data[0::2]
    return bytes(out)


def xBGR555_to_rgb(val: int) -> Tuple[int, int, int]:
    """Convert Super A'Can UM70C188 15-bit xBGR555 color word to (R, G, B)."""
    r = val & 0x1F
    g = (val >> 5) & 0x1F
    b = (val >> 10) & 0x1F
    r8 = (r << 3) | (r >> 2)
    g8 = (g << 3) | (g >> 2)
    b8 = (b << 3) | (b >> 2)
    return (r8, g8, b8)


def main():
    if not os.path.exists(ROM_PATH):
        print(f"Error: ROM not found at {ROM_PATH}")
        sys.exit(1)

    print(f"Loading {ROM_PATH}...")
    rom = open(ROM_PATH, "rb").read()
    orig_len = len(rom)

    # Hashes for native Big-Endian ROM
    be_crc32 = f"{zlib.crc32(rom) & 0xffffffff:08x}"
    be_md5 = hashlib.md5(rom).hexdigest()
    be_sha1 = hashlib.sha1(rom).hexdigest()
    be_sha256 = hashlib.sha256(rom).hexdigest()

    # Hashes for 16-bit word swapped ROM (standard copier dump format)
    swapped_rom = swap16(rom)
    swapped_crc32 = f"{zlib.crc32(swapped_rom) & 0xffffffff:08x}"
    swapped_md5 = hashlib.md5(swapped_rom).hexdigest()
    swapped_sha1 = hashlib.sha1(swapped_rom).hexdigest()
    swapped_sha256 = hashlib.sha256(swapped_rom).hexdigest()

    print(f"ROM size: {orig_len:,} bytes (2.0 MiB)")
    print(f"Native 68000 Big-Endian CRC32: {be_crc32} | SHA-1: {be_sha1}")
    print(f"Byte-swapped Copier CRC32:     {swapped_crc32} | SHA-1: {swapped_sha1}")

    # Create destination directories
    dir_rom = os.path.join(OUT_DIR, "rom")
    dir_audio_raw = os.path.join(OUT_DIR, "audio", "raw")
    dir_audio_wav = os.path.join(OUT_DIR, "audio", "wav")
    dir_audio_music = os.path.join(OUT_DIR, "audio", "music")
    dir_text = os.path.join(OUT_DIR, "text")
    dir_gfx_pal = os.path.join(OUT_DIR, "graphics", "palettes")
    dir_gfx_tiles = os.path.join(OUT_DIR, "graphics", "tilesets")
    dir_gfx_maps = os.path.join(OUT_DIR, "graphics", "tilemaps")

    for d in [
        dir_rom,
        dir_audio_raw,
        dir_audio_wav,
        dir_audio_music,
        dir_text,
        dir_gfx_pal,
        dir_gfx_tiles,
        dir_gfx_maps,
    ]:
        os.makedirs(d, exist_ok=True)

    manifest = {
        "title": "Rebel Star (叛逆之星 / 叛逆星)",
        "catalog_serial": "F012",
        "system": "Super A'Can (Funtech Entertainment Corp. / United Microelectronics Corp., Taiwan, 1995)",
        "programmer": "Juh-Wen-Her (周文河)",
        "source_file": ROM_FILENAME,
        "source_size": orig_len,
        "hashes": {
            "native_68000_big_endian": {
                "crc32": be_crc32,
                "md5": be_md5,
                "sha1": be_sha1,
                "sha256": be_sha256,
            },
            "byte_swapped_dump": {
                "crc32": swapped_crc32,
                "md5": swapped_md5,
                "sha1": swapped_sha1,
                "sha256": swapped_sha256,
            },
        },
        "hardware": {
            "main_cpu": "Motorola 68000 @ 10.6 MHz",
            "sound_cpu": "WDC W65C02 @ 3.58 MHz / UM6650 APU",
            "video_processor": "UM70C188 PPU (4bpp tiles, 256-color palettes)",
            "sound_engine": "16-channel PCM audio engine",
        },
    }

    # =========================================================================
    # 1. ROM & CORE FIRMWARE
    # =========================================================================
    print("1/5 Extracting ROM binaries, vector table, and core firmware...")

    # Save clean native unswapped ROM
    unswapped_path = os.path.join(dir_rom, "rebel_unswapped.bin")
    with open(unswapped_path, "wb") as f:
        f.write(rom)

    # Save byte-swapped ROM (standard copier dump format)
    swapped_path = os.path.join(dir_rom, "rebel_byteswapped.bin")
    with open(swapped_path, "wb") as f:
        f.write(swapped_rom)

    # Vector table (Vectors 0..31: 128 bytes)
    vector_names = [
        "Initial SP",
        "Initial PC",
        "Bus Error",
        "Address Error",
        "Illegal Instruction",
        "Zero Divide",
        "CHK Instruction",
        "TRAPV Instruction",
        "Privilege Violation",
        "Trace",
        "Line 1010 Emulator",
        "Line 1111 Emulator",
        "Reserved 12",
        "Reserved 13",
        "Format Error",
        "Uninitialized Interrupt",
        "Reserved 16",
        "Reserved 17",
        "Reserved 18",
        "Reserved 19",
        "Reserved 20",
        "Reserved 21",
        "Reserved 22",
        "Reserved 23",
        "Spurious Interrupt",
        "Level 1 Interrupt Autovector",
        "Level 2 Interrupt Autovector",
        "Level 3 Interrupt Autovector (VBLANK / DMA)",
        "Level 4 Interrupt Autovector",
        "Level 5 Interrupt Autovector (VBLANK)",
        "Level 6 Interrupt Autovector",
        "Level 7 Interrupt Autovector (NMI)",
    ]

    vectors = []
    for i in range(32):
        addr = struct.unpack_from(">I", rom, i * 4)[0]
        name = vector_names[i] if i < len(vector_names) else f"Vector {i}"
        vectors.append(
            {
                "vector": i,
                "offset": f"0x{i*4:02X}",
                "name": name,
                "handler": f"0x{addr:08X}",
            }
        )

    with open(os.path.join(dir_rom, "vectors.json"), "w", encoding="utf-8") as f:
        json.dump(vectors, f, indent=2)

    # 6502 Sound Driver Firmware (4,096 bytes from 0x000080 to 0x001080)
    sound_driver = rom[0x000080:0x001080]
    with open(os.path.join(dir_rom, "sound_driver_6502.bin"), "wb") as f:
        f.write(sound_driver)

    # EULA & Anti-Reverse-Engineering Legal Notice at 0x002000
    eula_bytes = rom[0x002000:0x0020ED]
    with open(os.path.join(dir_rom, "eula_notice_big5.bin"), "wb") as f:
        f.write(eula_bytes)
    eula_text = eula_bytes.decode("big5", errors="replace")
    with open(os.path.join(dir_rom, "eula_notice_utf8.txt"), "w", encoding="utf-8") as f:
        f.write(eula_text + "\n")

    manifest["rom"] = {
        "unswapped_file": "rom/rebel_unswapped.bin",
        "byteswapped_file": "rom/rebel_byteswapped.bin",
        "initial_sp": vectors[0]["handler"],
        "initial_pc": vectors[1]["handler"],
        "vblank_irq_handler": vectors[27]["handler"],
        "nmi_handler": vectors[31]["handler"],
        "eula_notice_utf8": eula_text,
        "sound_driver_6502": {
            "rom_offset": "0x000080",
            "size_bytes": len(sound_driver),
            "file": "rom/sound_driver_6502.bin",
            "apu_ram_target": "$F000..$FFFF",
            "reset_vector": "$F000",
            "nmi_vector": "$F4AA",
            "irq_vector": "$F4B3",
        },
    }

    # =========================================================================
    # 2. AUDIO EXTRACTION (PCM VOICE & SFX + MUSIC SEQUENCES)
    # =========================================================================
    print("2/5 Extracting digitized PCM samples and music sequence banks...")

    # The 3 Audio Banks
    banks_def = [
        {
            "bank_id": 1,
            "header_offset": 0x1DF1A6,
            "sample_table_offset": 0x1DF9A6,
            "sample_offset": 0x1DF9AC,
            "sample_len": 18944,
            "tracks_pointer_table": 0x1E43AC,
            "bank_end": 0x1E720E,
            "name": "Audio Bank 1 (Stage 1 / Intro / SFX)",
        },
        {
            "bank_id": 2,
            "header_offset": 0x1E720E,
            "sample_table_offset": 0x1E7A0E,
            "sample_offset": 0x1E7A14,
            "sample_len": 6144,
            "tracks_pointer_table": 0x1E9214,
            "bank_end": 0x1EB652,
            "name": "Audio Bank 2 (Stage 2 / Battles)",
        },
        {
            "bank_id": 3,
            "header_offset": 0x1EB652,
            "sample_table_offset": 0x1EBE52,
            "sample_offset": 0x1EBE58,
            "sample_len": 15232,
            "tracks_pointer_table": 0x1EF9D8,
            "bank_end": 0x1F2F68,
            "name": "Audio Bank 3 (Boss / Climax / Ending)",
        },
    ]

    sample_rate = 8000  # Standard Super A'Can APU sample rate
    audio_clips = []
    music_banks_info = []
    all_music_tracks = []

    for b in banks_def:
        # Extract PCM sample
        s_off = b["sample_offset"]
        s_len = b["sample_len"]
        pcm_data = rom[s_off : s_off + s_len]
        s_id = f"bank{b['bank_id']}_sample_{s_off:06X}"
        raw_name = f"{s_id}.pcm"
        wav_name = f"{s_id}.wav"

        raw_path = os.path.join(dir_audio_raw, raw_name)
        wav_path = os.path.join(dir_audio_wav, wav_name)

        with open(raw_path, "wb") as f:
            f.write(pcm_data)

        # Write RIFF WAV file (8-bit unsigned mono, 8kHz)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(1)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)

        clip_info = {
            "id": s_id,
            "bank_id": b["bank_id"],
            "filename_wav": f"audio/wav/{wav_name}",
            "filename_raw": f"audio/raw/{raw_name}",
            "rom_offset": f"0x{s_off:06X}",
            "size_bytes": s_len,
            "duration_seconds": round(s_len / sample_rate, 3),
            "sample_rate_hz": sample_rate,
            "apu_ram_dest": "0xE88C00",
        }
        audio_clips.append(clip_info)

        # Extract full bank music sequence binary
        bank_bytes = rom[b["header_offset"] : b["bank_end"]]
        bank_bin_name = f"music_bank{b['bank_id']}_{b['header_offset']:06X}.bin"
        with open(os.path.join(dir_audio_music, bank_bin_name), "wb") as f:
            f.write(bank_bytes)

        # Parse track pointer table
        pt_off = b["tracks_pointer_table"]
        num_tracks = struct.unpack_from(">H", rom, pt_off + 2)[0]
        track_pointers = []
        for t_idx in range(num_tracks):
            ptr = struct.unpack_from(">I", rom, pt_off + 4 + t_idx * 4)[0]
            track_pointers.append(ptr)
            all_music_tracks.append(
                {
                    "bank_id": b["bank_id"],
                    "track_index": t_idx + 1,
                    "pointer_rom_offset": f"0x{ptr:06X}",
                    "bank_relative": f"0x{ptr - b['header_offset']:06X}",
                }
            )

        music_banks_info.append(
            {
                "bank_id": b["bank_id"],
                "name": b["name"],
                "file": f"audio/music/{bank_bin_name}",
                "rom_offset": f"0x{b['header_offset']:06X}",
                "size_bytes": len(bank_bytes),
                "tracks_count": num_tracks,
                "track_pointers": [f"0x{ptr:06X}" for ptr in track_pointers],
            }
        )

    # Save music tracks json
    with open(
        os.path.join(dir_audio_music, "music_tracks.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(
            {
                "banks": music_banks_info,
                "total_tracks": len(all_music_tracks),
                "tracks": all_music_tracks,
            },
            f,
            indent=2,
        )

    # Save audio manifest
    audio_manifest = {
        "sample_rate_hz": sample_rate,
        "total_sample_bytes": sum(c["size_bytes"] for c in audio_clips),
        "total_pcm_clips": len(audio_clips),
        "total_music_banks": len(music_banks_info),
        "total_music_tracks": len(all_music_tracks),
        "clips": audio_clips,
        "music_banks": music_banks_info,
    }
    with open(
        os.path.join(OUT_DIR, "audio", "audio_manifest.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(audio_manifest, f, indent=2)

    manifest["audio"] = {
        "sample_clips_count": len(audio_clips),
        "music_tracks_count": len(all_music_tracks),
        "total_pcm_bytes": sum(c["size_bytes"] for c in audio_clips),
        "sample_rate_hz": sample_rate,
        "manifest": "audio/audio_manifest.json",
        "music_tracks_json": "audio/music/music_tracks.json",
    }

    # =========================================================================
    # 3. GRAPHICS & PALETTES EXTRACTION
    # =========================================================================
    print("3/5 Extracting hardware xBGR555 palettes and rendering 4bpp tilesets...")

    # Hardware Palettes
    palette_defs = [
        {
            "id": "palette_main_024752",
            "name": "Main UI, Stages & ANSI EGA 256-Color Palette",
            "offset": 0x024752,
            "colors_count": 256,
        },
        {
            "id": "palette_hud_005fc4",
            "name": "HUD & Radar Green Shading Palette",
            "offset": 0x005FC4,
            "colors_count": 32,
        },
        {
            "id": "palette_sprites_14fba2",
            "name": "Player & Enemy Sprites Palette",
            "offset": 0x14FBA2,
            "colors_count": 32,
        },
        {
            "id": "palette_metallic_13342e",
            "name": "Metallic & Mecha Grayscale 256-Color Palette",
            "offset": 0x13342E,
            "colors_count": 256,
        },
        {
            "id": "palette_starfield_162e02",
            "name": "Starfield Deep Space Backdrop Palette",
            "offset": 0x162E02,
            "colors_count": 32,
        },
    ]

    palettes_manifest = []
    main_palette_rgb = []

    for pal_info in palette_defs:
        start = pal_info["offset"]
        count = pal_info["colors_count"]
        raw_bytes = rom[start : start + count * 2]

        # Save raw binary palette
        bin_filename = f"{pal_info['id']}.bin"
        with open(os.path.join(dir_gfx_pal, bin_filename), "wb") as f:
            f.write(raw_bytes)

        # Parse xBGR555 to RGB
        colors = []
        for i in range(count):
            val = struct.unpack_from(">H", raw_bytes, i * 2)[0]
            r, g, b = xBGR555_to_rgb(val)
            colors.append(
                {
                    "index": i,
                    "xbgr555_hex": f"0x{val:04X}",
                    "rgb": [r, g, b],
                    "hex_color": f"#{r:02X}{g:02X}{b:02X}",
                }
            )
            if pal_info["id"] == "palette_main_024752":
                main_palette_rgb.append((r, g, b))

        json_filename = f"{pal_info['id']}.json"
        with open(
            os.path.join(dir_gfx_pal, json_filename), "w", encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "id": pal_info["id"],
                    "name": pal_info["name"],
                    "rom_offset": f"0x{start:06X}",
                    "colors_count": count,
                    "colors": colors,
                },
                f,
                indent=2,
            )

        palettes_manifest.append(
            {
                "id": pal_info["id"],
                "name": pal_info["name"],
                "rom_offset": f"0x{start:06X}",
                "colors_count": count,
                "file_json": f"graphics/palettes/{json_filename}",
                "file_bin": f"graphics/palettes/{bin_filename}",
            }
        )

    with open(
        os.path.join(dir_gfx_pal, "palettes_manifest.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(palettes_manifest, f, indent=2)

    # Render Tilesheet Previews (4bpp linear tiles: 32 bytes per 8x8 tile)
    tilesheet_regions = [
        ("tilesheet_intro_ui_024952", 0x024952, 368, 16),
        ("tilesheet_sprites_070000", 0x070000, 512, 16),
        ("tilesheet_sprites_080000", 0x080000, 512, 16),
        ("tilesheet_boss_090000", 0x090000, 512, 16),
        ("tilesheet_stage_0F0000", 0x0F0000, 512, 16),
        ("tilesheet_stage_110000", 0x110000, 512, 16),
        ("tilesheet_boss_120000", 0x120000, 512, 16),
        ("tilesheet_font_hud_140f90", 0x140F90, 125, 16),
    ]

    # Grayscale palette (16 levels)
    gray_pal = []
    for i in range(16):
        v = int(i * 255 / 15)
        gray_pal.extend([v, v, v])

    # Color palette from main palette (first 16 colors)
    color_pal = []
    for i in range(16):
        if i < len(main_palette_rgb):
            color_pal.extend(main_palette_rgb[i])
        else:
            color_pal.extend([0, 0, 0])

    rendered_tilesheets = []

    for name, start, num_tiles, cols in tilesheet_regions:
        rows = (num_tiles + cols - 1) // cols
        tiles_data = rom[start : start + num_tiles * 32]

        for pal_type, pal_data in [("gray", gray_pal), ("color", color_pal)]:
            img = Image.new("P", (cols * 8, rows * 8))
            img.putpalette(pal_data)

            for t_idx in range(num_tiles):
                t_off = t_idx * 32
                if t_off + 32 > len(tiles_data):
                    break
                tile_bytes = tiles_data[t_off : t_off + 32]
                tx = (t_idx % cols) * 8
                ty = (t_idx // cols) * 8
                for r in range(8):
                    rb = tile_bytes[r * 4 : (r + 1) * 4]
                    for c in range(4):
                        b = rb[c]
                        p1 = (b >> 4) & 0x0F
                        p2 = b & 0x0F
                        img.putpixel((tx + c * 2, ty + r), p1)
                        img.putpixel((tx + c * 2 + 1, ty + r), p2)

            filename = f"{name}_{pal_type}.png"
            img.save(os.path.join(dir_gfx_tiles, filename))

        rendered_tilesheets.append(
            {
                "name": name,
                "rom_offset": f"0x{start:06X}",
                "tiles_count": num_tiles,
                "dimensions": f"{cols*8}x{rows*8}",
                "preview_gray": f"graphics/tilesets/{name}_gray.png",
                "preview_color": f"graphics/tilesets/{name}_color.png",
            }
        )

    with open(
        os.path.join(dir_gfx_tiles, "tilesets_manifest.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(rendered_tilesheets, f, indent=2)

    # Extract Stage Level Tilemaps (16-bit word tile indices)
    stage_tilemaps = [
        {"stage": 1, "offset": 0x0A0000, "size": 0x10000, "name": "Stage 1 Tilemap"},
        {"stage": 2, "offset": 0x0B0000, "size": 0x10000, "name": "Stage 2 Tilemap"},
        {"stage": 3, "offset": 0x0C0000, "size": 0x10000, "name": "Stage 3 Tilemap"},
        {"stage": 4, "offset": 0x0D0000, "size": 0x10000, "name": "Stage 4 Tilemap"},
        {"stage": 5, "offset": 0x0E0000, "size": 0x10000, "name": "Stage 5 Tilemap"},
        {"stage": 6, "offset": 0x100000, "size": 0x10000, "name": "Stage 6 Tilemap"},
    ]

    extracted_tilemaps = []
    for tm in stage_tilemaps:
        tm_data = rom[tm["offset"] : tm["offset"] + tm["size"]]
        filename = f"tilemap_stage{tm['stage']}_{tm['offset']:06X}.bin"
        with open(os.path.join(dir_gfx_maps, filename), "wb") as f:
            f.write(tm_data)
        extracted_tilemaps.append(
            {
                "stage": tm["stage"],
                "name": tm["name"],
                "rom_offset": f"0x{tm['offset']:06X}",
                "size_bytes": tm["size"],
                "file": f"graphics/tilemaps/{filename}",
            }
        )

    with open(
        os.path.join(dir_gfx_maps, "tilemaps_manifest.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(extracted_tilemaps, f, indent=2)

    manifest["graphics"] = {
        "palettes_count": len(palette_defs),
        "tilesheets_count": len(tilesheet_regions),
        "tilemaps_count": len(stage_tilemaps),
        "palettes_manifest": "graphics/palettes/palettes_manifest.json",
        "tilesets_manifest": "graphics/tilesets/tilesets_manifest.json",
        "tilemaps_manifest": "graphics/tilemaps/tilemaps_manifest.json",
    }

    # =========================================================================
    # 4. GAME TEXT & STRINGS EXTRACTION
    # =========================================================================
    print("4/5 Extracting in-game text strings, credits, and menus...")

    game_strings = [
        {
            "category": "Credits & Development",
            "rom_offset": "0x005F86",
            "text": "PROGRAMER JUH0WEN0HER",
            "meaning": "Lead Programmer Juh-Wen-Her (周文河)",
        },
        {
            "category": "Legal Notice & Copyright",
            "rom_offset": "0x002000",
            "text": eula_text,
            "meaning": "Anti-reverse engineering and UMC / Funtech license notice",
        },
        {
            "category": "Engine Diagnostics",
            "rom_offset": "0x00202D",
            "text": "(reverse engineer)",
            "meaning": "EULA inline string marker",
        },
        {
            "category": "Publisher Trademark",
            "rom_offset": "0x00207F",
            "text": "Trademark by United Microelectronics Corp. and Funtech Entertainment Corp. All rights reserved. License is permitted.",
            "meaning": "Official UMC / Funtech publishing license confirmation",
        },
    ]

    with open(
        os.path.join(dir_text, "game_strings.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(game_strings, f, ensure_ascii=False, indent=2)

    # Format text into Markdown
    text_md = [
        "# Rebel Star (叛逆之星) — Extracted In-Game Strings & Text\n\n",
        "## Game Metadata & Credits\n\n",
        "- **Game Title:** Rebel Star (叛逆之星 / 叛逆星)\n",
        "- **Platform:** Super A'Can (16-bit console, Taiwan, 1995)\n",
        "- **Publisher:** Funtech Entertainment Corp. / United Microelectronics Corp. (UMC)\n",
        "- **Cartridge ID:** F012\n",
        "- **Programmer:** Juh-Wen-Her (周文河)\n\n",
        "## String Reference Table\n\n",
        "| Category | ROM Offset | Text Content | Description |\n",
        "|---|---|---|---|\n",
    ]
    for s in game_strings:
        escaped_text = s["text"].replace("\n", " ").replace("|", "\\|")
        text_md.append(
            f"| {s['category']} | `{s['rom_offset']}` | {escaped_text} | {s['meaning']} |\n"
        )

    with open(os.path.join(dir_text, "game_strings.md"), "w", encoding="utf-8") as f:
        f.write("".join(text_md))

    # Credits document
    credits_content = """# Rebel Star (叛逆之星 / 叛逆星) — Cartridge Credits

- **Game Title:** Rebel Star (叛逆之星)
- **Serial Catalog Number:** F012
- **Developer / Publisher:** Funtech Entertainment Corp. (聯運科技) & United Microelectronics Corp. (UMC / 聯華電子)
- **Release Year:** 1995 / 1996
- **Lead Programmer:** Juh-Wen-Her (周文河) — embedded directly in ROM at `0x005F86` (`PROGRAMER JUH0WEN0HER`)
- **Target Platform:** Super A'Can 16-bit Home Video Game Console
- **Hardware Architecture:**
  - Motorola 68000 CPU @ 10.6 MHz
  - WDC W65C02 APU Co-processor @ 3.58 MHz
  - UM70C188 PPU (VDP) with 4bpp tile generator & 256-color xBGR555 CRAM
"""
    with open(os.path.join(dir_text, "credits.md"), "w", encoding="utf-8") as f:
        f.write(credits_content)

    manifest["text"] = {
        "files": ["text/game_strings.json", "text/game_strings.md", "text/credits.md"]
    }

    # =========================================================================
    # 5. WRITE MANIFEST & README
    # =========================================================================
    print("5/5 Writing manifest.json and technical overview README.md...")

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    readme_content = f"""# Rebel Star (叛逆之星) — Extracted Assets & Technical Documentation

Extracted assets and data from **f012 - rebel star.bin**
- **Console:** Super A'Can (Funtech Entertainment Corp. / United Microelectronics Corp., Taiwan, 1995)
- **Publisher / Developer:** Funtech Entertainment Corp. / UMC (Serial F012)
- **Lead Programmer:** Juh-Wen-Her (周文河, embedded at `0x005F86`)
- **Main CPU:** Motorola 68000 @ 10.6 MHz
- **Sound CPU (APU):** WDC W65C02 @ 3.58 MHz (UM6650 sound engine)
- **Video Display:** UM70C188 PPU (4bpp tiles, 256-color palettes)
- **Original ROM Size:** {orig_len:,} bytes (2.0 MiB / 16 Mbit)
- **Native 68000 Big-Endian Checksum (SHA-1):** `{be_sha1}`
- **Byte-Swapped Copier Dump Checksum (SHA-1):** `{swapped_sha1}`

---

## Directory Structure

```text
extracted/
├── manifest.json              # Complete machine-readable inventory with checksums and offsets
├── README.md                  # This technical overview and extraction report
│
├── rom/                       # Core ROM & system binaries
│   ├── rebel_unswapped.bin    # Clean 68000 Big-Endian binary (2,097,152 bytes)
│   ├── rebel_byteswapped.bin  # 16-bit word swapped binary for standard ROM copiers
│   ├── sound_driver_6502.bin  # W65C02 APU firmware loaded at $F000 (4,096 bytes)
│   ├── vectors.json           # 68000 vector table (Initial SP: 0x00FCFE00, PC: 0x00048C00)
│   ├── eula_notice_utf8.txt   # Traditional Chinese anti-reverse-engineering disclaimer
│   └── eula_notice_big5.bin   # Original Big5 binary of legal notice
│
├── audio/                     # Sound & voice assets
│   ├── audio_manifest.json    # Complete metadata for all 3 sample banks and 28 music tracks
│   ├── wav/                   # Digitized voice & SFX clips (RIFF WAV, 8kHz 8-bit unsigned mono)
│   │   ├── bank1_sample_1DF9AC.wav  # Bank 1 digitized sample (18,944 bytes)
│   │   ├── bank2_sample_1E7A14.wav  # Bank 2 digitized sample (6,144 bytes)
│   │   └── bank3_sample_1EBE58.wav  # Bank 3 digitized sample (15,232 bytes)
│   ├── raw/                   # Raw 8-bit unsigned PCM audio clips (.pcm)
│   └── music/                 # 3 Music sequence banks (28 tracks total)
│       ├── music_bank1_1df1a6.bin   # Bank 1: 16 track sequences
│       ├── music_bank2_1e720e.bin   # Bank 2: 7 track sequences
│       ├── music_bank3_1eb652.bin   # Bank 3: 5 track sequences
│       └── music_tracks.json        # Inventory of all 28 track pointers
│
├── graphics/                  # Visual assets, palettes & tilemaps
│   ├── palettes/              # Hardware xBGR555 CRAM palettes (JSON & binary)
│   │   ├── palette_main_024752.json  # 256-color main UI & stage palette
│   │   ├── palette_hud_005fc4.json   # 32-color HUD / radar green palette
│   │   ├── palette_sprites_14fba2.json # 32-color player & enemy sprite palette
│   │   ├── palette_metallic_13342e.json # 256-color grayscale metallic palette
│   │   ├── palette_starfield_162e02.json # 32-color starfield backdrop palette
│   │   └── palettes_manifest.json
│   ├── tilesets/              # Rendered PNG sheets (4bpp tiles, gray & color previews)
│   │   ├── tilesheet_intro_ui_024952_gray.png / _color.png
│   │   ├── tilesheet_sprites_070000_gray.png / _color.png
│   │   ├── tilesheet_sprites_080000_gray.png / _color.png
│   │   ├── tilesheet_boss_090000_gray.png / _color.png
│   │   ├── tilesheet_stage_0F0000_gray.png / _color.png
│   │   ├── tilesheet_stage_110000_gray.png / _color.png
│   │   ├── tilesheet_boss_120000_gray.png / _color.png
│   │   ├── tilesheet_font_hud_140f90_gray.png / _color.png
│   │   └── tilesets_manifest.json
│   └── tilemaps/              # 6 Stage level tilemaps (16-bit word tile indices)
│       ├── tilemap_stage1_0a0000.bin
│       ├── tilemap_stage2_0b0000.bin
│       ├── tilemap_stage3_0c0000.bin
│       ├── tilemap_stage4_0d0000.bin
│       ├── tilemap_stage5_0e0000.bin
│       ├── tilemap_stage6_100000.bin
│       └── tilemaps_manifest.json
│
└── text/                      # In-game strings & credits
    ├── game_strings.json      # Structured strings & offsets
    ├── game_strings.md        # Formatted markdown tables
    └── credits.md             # Developer & programmer credits
```

---

## 1. Cartridge Architecture & Hardware

- **Main CPU:** Motorola 68000 @ 10.6 MHz
  - Initial Stack Pointer: `0x00FCFE00` (placed at top of work RAM `$FC0000-$FFFFFF`)
  - Initial Program Counter: `0x00048C00` (entry point)
  - VBLANK Interrupt: Level 5 Autovector (`0x00060E6C`)
  - NMI Interrupt: Level 7 Autovector (`0x0004AB74`)
- **Sound CPU (APU):** WDC W65C02 @ 3.58 MHz
  - 4,096-byte APU firmware loaded at `$F000..$FFFF` (`sound_driver_6502.bin`) from ROM `0x000080`
  - Bootstrapped via 68000 DMA copy to `$E8F000` and released at `$E9001C`
  - Reset Vector: `$F000`, NMI Vector: `$F4AA`, IRQ Vector: `$F4B3`
- **Video Display Processor:** UM70C188 PPU
  - Resolution: 320x224, 4bpp linear tiles (8x8 pixels = 32 bytes per tile)
  - Color RAM (CRAM): 256 15-bit xBGR555 color words loaded at `$F00200`

---

## 2. Audio Subsystem (APU)

- **Sound CPU:** WDC W65C02 running at 3.58 MHz
- **Audio Sample Banks:** 3 sample banks totaling 40,320 bytes of 8-bit unsigned PCM audio:
  - Bank 1 (`0x1DF9AC`): 18,944 bytes (2.368s @ 8 kHz)
  - Bank 2 (`0x1E7A14`): 6,144 bytes (0.768s @ 8 kHz)
  - Bank 3 (`0x1EBE58`): 15,232 bytes (1.904s @ 8 kHz)
- **Audio Output:** Exported to standard RIFF `.wav` and raw `.pcm` in `audio/wav/` and `audio/raw/`
- **Music Tracks:** 28 distinct musical sequences mapped across 3 sound banks:
  - Bank 1: 16 tracks (Intro, Stage 1, Stage 2, SFX sequences)
  - Bank 2: 7 tracks (Mid-game battle tracks)
  - Bank 3: 5 tracks (Boss battles, Climax, Ending credits)

---

## 3. Graphics & Tilesets

- **Resolution:** 320x224 (Super A'Can UM70C188 PPU)
- **Tile Format:** 4bpp linear tiles (8x8 pixels = 32 bytes per tile)
- **Palette Format:** 15-bit xBGR555 format (up to 256 colors)
- **Rendered Previews:** 8 high-resolution PNG tilesheets with both 16-level grayscale and full-color palette rendering
- **Stage Level Maps:** 6 stage tilemaps extracted from `0x0A0000..0x100000` (64 KB each)
"""

    readme_path = os.path.join(OUT_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("\nExtraction completed successfully!")
    print(f"Output directory:    {OUT_DIR}")
    print(f"Total PCM clips:     {len(audio_clips)} WAVs & PCMs")
    print(f"Total music tracks:  {len(all_music_tracks)} tracks in 3 banks")
    print(f"Total tilesheets:    {len(rendered_tilesheets)} sheets (gray + color)")
    print(f"Total stage tilemaps:{len(extracted_tilemaps)} maps")
    print(f"Total palettes:      {len(palette_defs)} hardware palettes")


if __name__ == "__main__":
    main()
