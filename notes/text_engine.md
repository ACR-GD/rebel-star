# Rebel Star (Super A'Can) - Text Rendering Engine Architecture

This document details the reverse engineering of the text rendering systems in **Rebel Star** (*叛逆之星*, Funtech / UMC, 1995, Serial `F012`) for the Super A'Can 16-bit console.

---

## 1. Architectural Overview

Unlike typical Super Nintendo or Sega Genesis games which often store dialogue as encoded byte strings (e.g. ASCII, Shift-JIS, or Big-5) and render them on a tilemap, *Rebel Star* utilizes **two specialized text rendering engines** directly tailored to the Super A'Can hardware (Motorola 68000 CPU + UMC UM70C188 PPU):

1. **Prologue 3D Perspective Crawl Engine**:
   - Uses the UM70C188 PPU **ROZ (Rotation/Scaling/Affine - Mode 7 style)** hardware plane to perform a real-time 3D Star Wars-like perspective text scroll.
2. **In-Game Stage Cutscene & Dialogue Engine**:
   - Uses a dynamic CPU blitter to expand 1bpp font tiles into 8-bit palette indexed pixel buffers in WRAM, transferred to VRAM and displayed as an animated window overlay during gameplay.

---

## 2. Text System 1: Prologue 3D Crawl Engine

### 2.1 Hardware Configuration
- **Hardware Layer**: ROZ (Affine / Mode 7) Layer (`PPU Register $F00180 = 0x0402`).
- **Layer Dimensions**: 32x32 tiles (256x256 pixel virtual plane), 4 bits-per-pixel (16 colors per tile).
- **Transformation Registers**: Affine matrix registers `A, B, C, D`, center point `(X0, Y0)`, and scroll offsets `(HScroll, VScroll)` manipulated per frame at interrupt handler `0x061020` to project the plane backward at an acute perspective tilt.

### 2.2 Memory Mapping & Font Storage
- **Font Table Address**: ROM `0x05763C` – `0x05DAEC` (3,222 8x8 1bpp glyphs, 25,776 bytes).
- **Glyph Format**:
  - 1 bit per pixel: `8 bytes per 8x8 tile`.
  - Bit value `1` = character stroke (white/yellow text).
  - Bit value `0` = transparent background.
- **Character Composition**:
  - Each Traditional Chinese character is **16x16 pixels**, constructed from **four 8x8 tiles** (2x2 grid):
    - Top-left tile
    - Top-right tile
    - Bottom-left tile
    - Bottom-right tile

### 2.3 Script Storage & Tile Mapping
- **Script Table Address**: ROM `0x05DAEC` – `0x060E6C` (103 lines of text).
- **Line Structure**: Each line is stored as 64 16-bit big-endian words (`128 bytes` per line):
  - **Words 0–31**: The top 8x8 halves (top-left & top-right tiles) of up to 16 Chinese characters.
  - **Words 32–63**: The bottom 8x8 halves (bottom-left & bottom-right tiles) of up to 16 Chinese characters.
- **Blitter Routine (`ROM 0x06115C`–`0x0611FC`)**:
  - The 68000 CPU reads the 1bpp font bits for each tile in the script line.
  - Expands 1bpp bits into 4bpp nibbles (`0x10`, `0x01`, `0x11`, `0x00`) into a staging buffer in WRAM (`$FC156E`).
  - DMAs the expanded 4bpp tile graphics to VRAM (`$F40000`–`$F47800`) via DMA controller register `$4AAC0`.
  - Sequential tile numbers from `0x1000` upward are loaded into the ROZ tilemap, creating continuous scrolling text lines.

---

## 3. Text System 2: In-Game Stage Dialogue Engine

### 3.1 Architecture
The dialogue system triggers during stage cutscenes, radio transmissions, and boss encounters.

- **Font Table Address**: ROM `0x12506C`. Tiles `0x00–0x35` are UI/ASCII glyphs, the Chinese dialogue and names use tiles up to `0x1081`; **after that the area holds the dialogue frame and map graphics** (see the README's ROM notes). The English build moves the dialogue font to `$200000`.
- **Dialogue Script Storage**: ROM `0x00561C` – `0x01A294` (404 distinct dialogue blocks grouped across all stages).

### 3.2 Script Block Structure
Each dialogue box entry in ROM is **196 bytes** (`0xC4` bytes):
1. **Header (4 bytes)**:
   - `0x0010` (Width: 16 tiles = 128 pixels).
   - `0x0006` (Height: 6 tile rows = 48 pixels; 3 lines of 16x16 characters).
2. **Tile Stream (192 bytes / 96 16-bit words)**:
   - 6 sequential tile rows of 16 words each.
   - Row 0: Top halves of 8 characters in Line 1.
   - Row 1: Bottom halves of 8 characters in Line 1.
   - Row 2: Top halves of 8 characters in Line 2.
   - Row 3: Bottom halves of 8 characters in Line 2.
   - Row 4: Top halves of 8 characters in Line 3.
   - Row 5: Bottom halves of 8 characters in Line 3.
   - Each dialogue frame holds up to **24 Chinese characters** (3 lines × 8 characters).

### 3.3 Blitter & Event Execution Loop (`ROM 0x04E60E`–`0x04E856`)
```m68k
0x04E60E: move.w #$94, d1        ; Target VRAM tile index
0x04E618: lea.l $fc156e.l, a4    ; WRAM tile staging buffer
0x04E69E: moveq #$0, d4
0x04E6A0: move.w (a1)+, d4       ; Read 16-bit tile index from dialogue block
0x04E6A2: lsl.l #$3, d4          ; Multiply by 8 bytes per tile
0x04E6A8: move.b (a2, d4.l), d6  ; Read 1bpp font byte from 0x12506C
...
0x04E6B4: move.b #$e1, (a4)+     ; Bit = 1 -> Foreground color index 0xE1
0x04E6BC: move.b #$e0, (a4)+     ; Bit = 0 -> Background transparent color 0xE0
```
- **Player Input & Pacing**:
  - The CPU loops at `0x04E81A`, checking `$FC0270` (controller 1 inputs) for button press (Start / Button A, bit 15).
  - During pause, it animates a blinking prompt cursor by cycling palette index registers at `$F00280`.
  - Once dismissed, it triggers the next stage event or resumes gameplay.
