"""Draws the faces of the Italian road signs and the marble street name plaques (houses V3, step 11).

Aged 1980s look: faded colours, dirt, scratches and rust spots. Plain Python + Pillow.
Writes Textures/T_M80_Sign_<Name>.png (256 px) and Textures/Plaques/T_M80_Plaque_<n>.jpg + plaques.json.
"""
import json
import math
import random
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "Textures"
RESEARCH = HERE.parent
RED, BLUE, WHITE = (176, 32, 34), (24, 66, 140), (236, 232, 222)
S = 512  # drawn at 512, saved at 256


def font(names, size):
    for n in names:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/" + n, size)
        except OSError:
            pass
    return ImageFont.load_default()


def age(img, seed, amount=1.0):
    """Fading, dirt and rust spots."""
    rnd = random.Random(seed)
    img = Image.blend(img, Image.new("RGB", img.size, (200, 190, 170)), 0.12 * amount)
    dirt = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(dirt)
    for _ in range(int(220 * amount)):
        x, y, r = rnd.uniform(0, img.width), rnd.uniform(0, img.height), rnd.uniform(1, 9)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.randint(20, 90))
    for _ in range(int(25 * amount)):
        x, y = rnd.uniform(0, img.width), rnd.uniform(0, img.height)
        d.line((x, y, x + rnd.uniform(-40, 40), y + rnd.uniform(-6, 6)), fill=rnd.randint(40, 110), width=1)
    # Streaks from the top edge, like rain washing dust down.
    for _ in range(int(14 * amount)):
        x = rnd.uniform(0, img.width)
        d.line((x, 0, x + rnd.uniform(-4, 4), rnd.uniform(img.height * 0.2, img.height)), fill=rnd.randint(15, 45), width=rnd.randint(2, 6))
    dirt = dirt.filter(ImageFilter.GaussianBlur(1.5))
    img = Image.composite(Image.new("RGB", img.size, (70, 58, 44)), img, dirt)
    rust = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(rust)
    for _ in range(int(8 * amount)):
        x, y, r = rnd.uniform(0, img.width), rnd.uniform(0, img.height), rnd.uniform(4, 18)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.randint(90, 200))
    rust = rust.filter(ImageFilter.GaussianBlur(4))
    return Image.composite(Image.new("RGB", img.size, (120, 62, 30)), img, rust)


def sign(name, draw_fn, seed):
    img = Image.new("RGB", (S, S), (150, 150, 150))
    draw_fn(ImageDraw.Draw(img))
    age(img, seed).resize((256, 256), Image.LANCZOS).save(OUT / "T_M80_Sign_{}.png".format(name))


def regular(n, r, rot=0.0, c=S / 2):
    return [(c + r * math.cos(rot + 2 * math.pi * k / n), c + r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def stop(d):
    d.polygon(regular(8, 255, math.pi / 8), fill=WHITE)
    d.polygon(regular(8, 236, math.pi / 8), fill=RED)
    f = font(["arialbd.ttf", "Arial.ttf"], 150)
    d.text((S / 2, S / 2), "STOP", fill=WHITE, font=f, anchor="mm")


def yield_sign(d):
    tri = [(0, 40), (S, 40), (S / 2, S - 20)]
    d.polygon(tri, fill=RED)
    inner = [(70, 78), (S - 70, 78), (S / 2, S - 110)]
    d.polygon(inner, fill=WHITE)


def no_parking(d):
    d.ellipse((2, 2, S - 2, S - 2), fill=RED)
    d.ellipse((52, 52, S - 52, S - 52), fill=BLUE)
    d.line((110, 110, S - 110, S - 110), fill=RED, width=56)


def no_entry(d):
    d.ellipse((2, 2, S - 2, S - 2), fill=RED)
    d.rectangle((90, S / 2 - 45, S - 90, S / 2 + 45), fill=WHITE)


def no_transit(d):
    d.ellipse((2, 2, S - 2, S - 2), fill=RED)
    d.ellipse((62, 62, S - 62, S - 62), fill=WHITE)


def one_way(d):
    d.rectangle((0, 0, S, S), fill=WHITE)
    d.rectangle((14, 14, S - 14, S - 14), fill=BLUE)
    # Horizontal arrow (the plate is 2:1, texture squashed vertically on the mesh).
    d.rectangle((70, S / 2 - 55, S - 190, S / 2 + 55), fill=WHITE)
    d.polygon([(S - 200, S / 2 - 150), (S - 60, S / 2), (S - 200, S / 2 + 150)], fill=WHITE)


def plaque(text, seed):
    """Marble street plaque: black serif capitals in a black frame."""
    rnd = random.Random(seed)
    w, h = 1024, 256
    img = Image.new("RGB", (w, h), (226, 220, 206))
    d = ImageDraw.Draw(img)
    for _ in range(40):  # marble veins
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        pts = [(x, y)]
        for _ in range(6):
            x += rnd.uniform(20, 90)
            y += rnd.uniform(-25, 25)
            pts.append((x, y))
        d.line(pts, fill=(196, 190, 178), width=rnd.randint(1, 3))
    d.rectangle((14, 14, w - 14, h - 14), outline=(30, 28, 26), width=8)
    words = text.upper().replace(" SECONDO", " II").replace(" PRIMO", " I")
    size = 120
    f = font(["timesbd.ttf", "georgiab.ttf"], size)
    while d.textlength(words, font=f) > w - 90 and size > 80:
        size -= 6
        f = font(["timesbd.ttf", "georgiab.ttf"], size)
    if d.textlength(words, font=f) > w - 90:
        # Two lines, split at the space nearest the middle.
        parts = words.split(" ")
        best = min(range(1, len(parts)), key=lambda k: abs(len(" ".join(parts[:k])) - len(" ".join(parts[k:]))))
        lines = [" ".join(parts[:best]), " ".join(parts[best:])]
        size = 90
        f = font(["timesbd.ttf", "georgiab.ttf"], size)
        while max(d.textlength(l, font=f) for l in lines) > w - 90 and size > 30:
            size -= 4
            f = font(["timesbd.ttf", "georgiab.ttf"], size)
        d.text((w / 2, h / 2 - size * 0.52), lines[0], fill=(28, 26, 24), font=f, anchor="mm")
        d.text((w / 2, h / 2 + size * 0.58), lines[1], fill=(28, 26, 24), font=f, anchor="mm")
    else:
        d.text((w / 2, h / 2 + 4), words, fill=(28, 26, 24), font=f, anchor="mm")
    return age(img, seed, 0.7).resize((512, 128), Image.LANCZOS)


def slug(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in t).strip("_")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "Plaques").mkdir(exist_ok=True)
    for i, (name, fn) in enumerate([("Stop", stop), ("Yield", yield_sign), ("NoParking", no_parking), ("NoEntry", no_entry),
                                    ("NoTransit", no_transit), ("OneWay", one_way)]):
        sign(name, fn, 100 + i)
    streets = json.loads((RESEARCH / "streets_world.json").read_text(encoding="utf-8"))["streets"]
    names = sorted({s["name"] for s in streets if s["highway"] not in ("trunk", "primary", "secondary") or s["name"].startswith(("Via", "Corso", "Viale", "Piazza", "Vicolo"))})
    table = {}
    for i, n in enumerate(names):
        key = slug(n)
        plaque(n, 1000 + i).save(OUT / "Plaques" / "T_M80_Plaque_{}.jpg".format(key), quality=82)
        table[n] = "T_M80_Plaque_" + key
    (OUT / "Plaques" / "plaques.json").write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(names), "plaques")


if __name__ == "__main__":
    main()
