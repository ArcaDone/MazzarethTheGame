"""Paints the texture atlas of the typical Sicilian props (houses V3, step 14.1). Plain Python + Pillow.

T_M80_SiciliaAtlas.png, 1024 x 1024, cells of 256 px (column, row from the top):
  row 0: majolica A, majolica B, majolica C, votive icon
  row 1: Moor's head face (two cells wide, wraps around the vase), pine-cone glaze, civic numbers 1-4 (2x2)
  rows 2-3: colour swatches, 128 px each, SWATCHES order (8 per line, 4 lines)
The cell rectangles are written to sicilia_atlas.json for the Blender script.
"""
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "Textures"
SIZE = 1024
SWATCHES = [
    ("terracotta", (178, 92, 58)), ("terracotta_dark", (140, 70, 45)), ("soil", (70, 50, 36)), ("leaf", (52, 96, 40)),
    ("geranium", (196, 28, 40)), ("lemon", (232, 196, 40)), ("wicker", (176, 140, 84)), ("rope", (160, 136, 96)),
    ("stone", (196, 176, 140)), ("stone_dark", (150, 132, 104)), ("iron", (40, 38, 36)), ("wood", (110, 74, 44)),
    ("paste", (150, 28, 20)), ("pepper", (190, 30, 22)), ("glass_amber", (230, 170, 80)), ("whitewash", (232, 226, 210)),
    ("gold", (200, 160, 60)), ("black", (24, 22, 20)), ("glaze_blue", (30, 70, 150)), ("glaze_green", (40, 120, 70)),
    ("glaze_yellow", (226, 180, 40)), ("glaze_white", (236, 232, 220)), ("brass", (170, 130, 60)), ("red_glass", (170, 20, 20)),
]
BLUE, YELLOW, GREEN, WHITE, OCHRE, MANGANESE = (28, 64, 140), (232, 184, 40), (38, 118, 72), (238, 234, 222), (196, 120, 40), (70, 40, 50)


def font(size, bold=True):
    for n in (["arialbd.ttf", "timesbd.ttf"] if bold else ["arial.ttf"]):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + n, size)
        except OSError:
            pass
    return ImageFont.load_default()


def crackle(img, seed, amount=60):
    """Glaze crazing and chips, the look of old majolica."""
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img)
    w, h = img.size
    for _ in range(amount):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        pts = [(x, y)]
        for _ in range(4):
            x += rnd.uniform(-25, 25)
            y += rnd.uniform(-25, 25)
            pts.append((x, y))
        d.line(pts, fill=(150, 140, 120), width=1)
    for _ in range(amount // 10):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(2, 6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(170, 120, 80))
    return img


def tile_a(s):
    """Star and cross pattern (Arab-Norman legacy), blue, yellow and green."""
    img = Image.new("RGB", (s, s), WHITE)
    d = ImageDraw.Draw(img)
    q = s // 2
    for ox in (0, q):
        for oy in (0, q):
            c = (ox + q / 2, oy + q / 2)
            star = [(c[0] + (q * 0.48 if k % 2 == 0 else q * 0.22) * math.cos(k * math.pi / 4), c[1] + (q * 0.48 if k % 2 == 0 else q * 0.22) * math.sin(k * math.pi / 4)) for k in range(8)]
            d.polygon(star, fill=BLUE)
            d.ellipse((c[0] - q * 0.12, c[1] - q * 0.12, c[0] + q * 0.12, c[1] + q * 0.12), fill=YELLOW)
            d.rectangle((ox, oy, ox + q, oy + q), outline=GREEN, width=4)
    return crackle(img, 1)


def tile_b(s):
    """Baroque flower in a lozenge, the classic Caltagirone riggiola."""
    img = Image.new("RGB", (s, s), WHITE)
    d = ImageDraw.Draw(img)
    c = s / 2
    d.polygon([(c, 6), (s - 6, c), (c, s - 6), (6, c)], fill=YELLOW)
    d.polygon([(c, 30), (s - 30, c), (c, s - 30), (30, c)], fill=WHITE)
    for k in range(8):
        a = k * math.pi / 4
        x, y = c + math.cos(a) * s * 0.18, c + math.sin(a) * s * 0.18
        d.ellipse((x - s * 0.08, y - s * 0.08, x + s * 0.08, y + s * 0.08), fill=BLUE if k % 2 else GREEN)
    d.ellipse((c - s * 0.07, c - s * 0.07, c + s * 0.07, c + s * 0.07), fill=OCHRE)
    for x, y in ((0, 0), (s, 0), (0, s), (s, s)):
        d.pieslice((x - s * 0.22, y - s * 0.22, x + s * 0.22, y + s * 0.22), 0, 360, fill=BLUE)
    return crackle(img, 2)


def tile_c(s):
    """Geometric strip with arches, for the bands under the balconies."""
    img = Image.new("RGB", (s, s), WHITE)
    d = ImageDraw.Draw(img)
    for i in range(4):
        x0 = i * s / 4
        d.rectangle((x0, 0, x0 + s / 4, s), outline=MANGANESE, width=3)
        d.pieslice((x0 + 6, s * 0.2, x0 + s / 4 - 6, s * 0.7), 180, 360, fill=GREEN)
        d.rectangle((x0 + 6, s * 0.45, x0 + s / 4 - 6, s * 0.8), fill=GREEN)
        d.ellipse((x0 + s / 8 - 12, s * 0.5 - 12, x0 + s / 8 + 12, s * 0.5 + 12), fill=YELLOW)
    d.rectangle((0, 0, s, s * 0.12), fill=BLUE)
    d.rectangle((0, s * 0.88, s, s), fill=BLUE)
    return crackle(img, 3)


def icon(s):
    """Votive majolica: a Madonna in a blue mantle with a gold halo, on a sky-blue ground, simple and naive."""
    img = Image.new("RGB", (s, s), (150, 190, 220))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, s - 1, s - 1), outline=YELLOW, width=10)
    d.rectangle((14, 14, s - 15, s - 15), outline=BLUE, width=4)
    cx = s / 2
    d.ellipse((cx - 46, 34, cx + 46, 126), fill=(230, 190, 60))  # halo
    d.polygon([(cx, 70), (cx + 70, s - 30), (cx - 70, s - 30)], fill=BLUE)  # mantle
    d.polygon([(cx, 110), (cx + 28, s - 30), (cx - 28, s - 30)], fill=(200, 60, 70))  # dress
    d.ellipse((cx - 24, 56, cx + 24, 104), fill=(236, 200, 170))  # face
    d.polygon([(cx - 30, 60), (cx, 44), (cx + 30, 60), (cx + 26, 110), (cx - 26, 110)], outline=BLUE, fill=None, width=0)
    for k in range(12):
        a = k * math.pi / 6
        d.ellipse((cx + math.cos(a) * 52 - 4, 80 + math.sin(a) * 52 - 4, cx + math.cos(a) * 52 + 4, 80 + math.sin(a) * 52 + 4), fill=WHITE)
    return crackle(img, 4, 40)


def moor_face(w, h):
    """Face of the testa di moro, painted on a strip that wraps around the vase (front at the centre)."""
    img = Image.new("RGB", (w, h), (88, 54, 40))
    d = ImageDraw.Draw(img)
    cx = w / 2
    # Crown band at the top: lemons and leaves on a white glaze.
    d.rectangle((0, 0, w, h * 0.24), fill=WHITE)
    for i in range(10):
        x = (i + 0.5) * w / 10
        d.polygon([(x - 40, h * 0.23), (x - 10, h * 0.04), (x + 4, h * 0.23)], fill=GREEN)
        d.polygon([(x + 40, h * 0.23), (x + 10, h * 0.04), (x - 4, h * 0.23)], fill=GREEN)
        d.ellipse((x - 26, h * 0.06, x + 26, h * 0.19), fill=YELLOW)
    d.rectangle((0, h * 0.24, w, h * 0.29), fill=(200, 160, 60))
    # Eyes, brows, nose, lips, moustache and beard (the front covers about a third of the turn).
    for sx in (-1, 1):
        ex = cx + sx * 78
        d.ellipse((ex - 34, h * 0.42 - 18, ex + 34, h * 0.42 + 18), fill=WHITE)
        d.ellipse((ex - 15, h * 0.42 - 15, ex + 15, h * 0.42 + 15), fill=(30, 20, 18))
        d.arc((ex - 44, h * 0.42 - 50, ex + 44, h * 0.42 + 6), 200, 340, fill=(20, 14, 12), width=10)
        d.ellipse((cx + sx * 230 - 16, h * 0.56, cx + sx * 230 + 16, h * 0.56 + 36), outline=(220, 180, 60), width=8)
    d.polygon([(cx, h * 0.44), (cx + 28, h * 0.62), (cx - 28, h * 0.62)], fill=(110, 68, 50))
    d.ellipse((cx - 50, h * 0.69, cx + 50, h * 0.80), fill=(170, 40, 40))
    d.arc((cx - 80, h * 0.58, cx + 80, h * 0.76), 200, 340, fill=(20, 14, 12), width=16)
    d.pieslice((cx - 100, h * 0.66, cx + 100, h * 1.06), 0, 180, fill=(30, 20, 16))
    return crackle(img, 5, 50)


def pine(s):
    """Scales of the Caltagirone pine cone, green glaze with yellow edges."""
    img = Image.new("RGB", (s, s), (40, 110, 60))
    d = ImageDraw.Draw(img)
    rows, cols = 8, 6
    for r in range(rows):
        for c in range(cols):
            x = (c + 0.5 * (r % 2)) * s / cols
            y = r * s / rows
            d.pieslice((x - s / cols * 0.6, y - s / rows * 0.4, x + s / cols * 0.6, y + s / rows * 1.2), 0, 180, fill=(52, 140, 78), outline=YELLOW, width=4)
    return crackle(img, 6, 30)


def numbers(s):
    img = Image.new("RGB", (s, s), WHITE)
    d = ImageDraw.Draw(img)
    f = font(80)
    for i, n in enumerate(("7", "12", "23", "41")):
        x0, y0 = (i % 2) * s / 2, (i // 2) * s / 2
        d.rectangle((x0 + 6, y0 + 6, x0 + s / 2 - 6, y0 + s / 2 - 6), outline=BLUE, width=6)
        d.text((x0 + s / 4, y0 + s / 4), n, fill=BLUE, font=f, anchor="mm")
    return crackle(img, 7, 30)


def swatch(colour, seed):
    rnd = random.Random(seed)
    img = Image.new("RGB", (128, 128), colour)
    d = ImageDraw.Draw(img)
    for _ in range(300):
        x, y = rnd.uniform(0, 128), rnd.uniform(0, 128)
        k = rnd.uniform(0.82, 1.15)
        d.point((x, y), fill=tuple(max(0, min(255, int(v * k))) for v in colour))
    return img.filter(ImageFilter.GaussianBlur(0.8))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("RGB", (SIZE, SIZE), (128, 128, 128))
    cells = {}

    def put(name, img, col, row, wcells=1, hcells=1):
        atlas.paste(img.resize((256 * wcells, 256 * hcells)), (col * 256, row * 256))
        cells[name] = [col * 256 / SIZE, row * 256 / SIZE, (col + wcells) * 256 / SIZE, (row + hcells) * 256 / SIZE]

    put("majolica_a", tile_a(512), 0, 0)
    put("majolica_b", tile_b(512), 1, 0)
    put("majolica_c", tile_c(512), 2, 0)
    put("icon", icon(512), 3, 0)
    put("moor_face", moor_face(1024, 512), 0, 1, 2, 1)
    put("pine", pine(512), 2, 1)
    put("numbers", numbers(512), 3, 1)
    for i, (name, colour) in enumerate(SWATCHES):
        col, line = i % 8, i // 8
        x, y = col * 128, 512 + line * 128
        atlas.paste(swatch(colour, 100 + i), (x, y))
        cells["sw_" + name] = [x / SIZE, y / SIZE, (x + 128) / SIZE, (y + 128) / SIZE]
    atlas.save(OUT / "T_M80_SiciliaAtlas.png")
    # Tiling majolica textures for the balcony undersides (one tile each).
    for name, fn, seed in (("A", tile_a, 1), ("B", tile_b, 2), ("C", tile_c, 3)):
        fn(512).save(OUT / "T_M80_Majolica_{}.png".format(name))
    (HERE / "sicilia_atlas.json").write_text(json.dumps(cells, indent=1), encoding="utf-8")
    print("atlas", len(cells), "cells")


if __name__ == "__main__":
    main()
