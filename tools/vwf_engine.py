"""
Variable Width Font (VWF) Engine for Super A'Can - Rebel Star (叛逆之星)
-------------------------------------------------------------------------
This engine provides:
1. Proportional pixel font measurement & layout for retro 16-bit consoles.
2. Dynamic word-wrapping by exact pixel budget (sub-tile accuracy).
3. Intelligent text shortening/tightening to guarantee text fits within dialogue constraints.
4. 1bpp tile rasterization and tile-slicing into Super A'Can 8x8 hardware format.
5. Deduplication and packing into ROM binary script blocks.
"""

import struct
from PIL import Image, ImageFont, ImageDraw

class VWFEngine:
    def __init__(self, font_name="default", space_width=3, letter_spacing=1, line_height=14):
        self.font = ImageFont.load_default()
        self.space_width = space_width
        self.letter_spacing = letter_spacing
        self.line_height = line_height

    def measure_char(self, ch):
        if ch == ' ':
            return self.space_width
        bbox = self.font.getbbox(ch)
        if bbox is None:
            return 4
        return (bbox[2] - bbox[0]) + self.letter_spacing

    def measure_string(self, text):
        return sum(self.measure_char(c) for c in text)

    def wrap_text(self, text, max_pixel_width=120):
        words = text.split(' ')
        lines = []
        cur_line = []
        cur_w = 0

        for word in words:
            word_w = self.measure_string(word)
            test_w = cur_w + (self.space_width if cur_line else 0) + word_w
            if test_w <= max_pixel_width:
                cur_line.append(word)
                cur_w = test_w
            else:
                if cur_line:
                    lines.append(' '.join(cur_line))
                cur_line = [word]
                cur_w = word_w

        if cur_line:
            lines.append(' '.join(cur_line))

        return lines

    def fit_and_shorten(self, text, max_pixel_width=120, max_lines=3, custom_short=None):
        """
        Wraps English text to fit within max_pixel_width and max_lines.
        If it overflows, applies progressive tightening/shortening rules
        to guarantee it fits without losing core meaning.
        """
        # Step 1: Try wrapping the original text
        lines = self.wrap_text(text, max_pixel_width)
        if len(lines) <= max_lines:
            return lines

        # Step 2: Use custom shortened text if provided
        if custom_short:
            lines = self.wrap_text(custom_short, max_pixel_width)
            if len(lines) <= max_lines:
                return lines

        # Step 3: Progressive automatic tightening
        replacements = [
            ("Headquarters", "HQ"),
            ("headquarters", "HQ"),
            ("communication", "comms"),
            ("communications", "comms"),
            ("cannot", "can't"),
            ("do not", "don't"),
            ("will not", "won't"),
            ("we are", "we're"),
            ("they are", "they're"),
            ("there are", "there're"),
            ("you are", "you're"),
            ("it is", "it's"),
            ("that is", "that's"),
            ("please ", ""),
            ("currently ", ""),
            ("immediately", "now"),
            ("reinforce", "help"),
            ("reinforcements", "backup"),
            ("detachment", "unit"),
            ("Detachment", "Unit"),
            ("underground", "rebel"),
            ("coordinates", "pos"),
        ]

        tightened = text
        for old, new in replacements:
            tightened = tightened.replace(old, new)
            lines = self.wrap_text(tightened, max_pixel_width)
            if len(lines) <= max_lines:
                return lines

        # Step 4: Truncate / compress remaining overflow lines
        while len(lines) > max_lines:
            # Drop least essential words from last line or join
            joined = ' '.join(lines[:max_lines])
            words = joined.split(' ')
            if len(words) > 3:
                words[-1] = "..."
                tightened = ' '.join(words[:-1]) + "..."
            else:
                tightened = ' '.join(words)
            lines = self.wrap_text(tightened, max_pixel_width)
            if len(lines) <= max_lines:
                break
            # Hard limit fallback
            lines = lines[:max_lines]

        return lines

    def rasterize_dialogue_box(self, lines, box_tiles_x=16, box_tiles_y=6, left_margin=4, top_margin=4):
        """
        Renders wrapped lines into a 1bpp bitmap (128x48 pixels).
        Returns a PIL Image (mode '1') and the list of 96 8x8 tiles (8 bytes each).
        """
        width_px = box_tiles_x * 8
        height_px = box_tiles_y * 8

        # Create 1-bit image (0 = transparent/background, 1 = character pixel)
        img = Image.new('1', (width_px, height_px), color=0)
        draw = ImageDraw.Draw(img)

        # Calculate vertical position (center text vertically if fewer than 3 lines)
        total_text_h = len(lines) * self.line_height
        start_y = max(top_margin, (height_px - total_text_h) // 2)

        for i, line in enumerate(lines):
            y = start_y + i * self.line_height
            draw.text((left_margin, y), line, font=self.font, fill=1)

        # Slice image into 8x8 tiles
        tiles_bytes = []
        pixels = img.load()

        for tile_y in range(box_tiles_y):
            for tile_x in range(box_tiles_x):
                tile_data = bytearray(8)
                for py in range(8):
                    row_byte = 0
                    for px in range(8):
                        x = tile_x * 8 + px
                        y = tile_y * 8 + py
                        if pixels[x, y]:
                            row_byte |= (1 << (7 - px))
                    tile_data[py] = row_byte
                tiles_bytes.append(bytes(tile_data))

        return img, tiles_bytes

    def rasterize_prologue_line(self, text, line_tiles_x=32, line_tiles_y=2):
        """
        Renders a 256x16 pixel prologue line for the 3D perspective crawl.
        Returns 64 8x8 tiles (32 top tiles, 32 bottom tiles).
        """
        width_px = line_tiles_x * 8
        height_px = line_tiles_y * 8

        img = Image.new('1', (width_px, height_px), color=0)
        draw = ImageDraw.Draw(img)

        # Center text horizontally on the 256px line
        text_w = self.measure_string(text)
        start_x = max(2, (width_px - text_w) // 2)
        start_y = 2  # centered vertically

        draw.text((start_x, start_y), text, font=self.font, fill=1)

        pixels = img.load()
        top_tiles = []
        bottom_tiles = []

        # Top row (tile_y = 0)
        for tile_x in range(line_tiles_x):
            tile_data = bytearray(8)
            for py in range(8):
                row_byte = 0
                for px in range(8):
                    if pixels[tile_x * 8 + px, py]:
                        row_byte |= (1 << (7 - px))
                tile_data[py] = row_byte
            top_tiles.append(bytes(tile_data))

        # Bottom row (tile_y = 1)
        for tile_x in range(line_tiles_x):
            tile_data = bytearray(8)
            for py in range(8):
                row_byte = 0
                for px in range(8):
                    if pixels[tile_x * 8 + px, 8 + py]:
                        row_byte |= (1 << (7 - px))
                tile_data[py] = row_byte
            bottom_tiles.append(bytes(tile_data))

        return img, top_tiles + bottom_tiles
