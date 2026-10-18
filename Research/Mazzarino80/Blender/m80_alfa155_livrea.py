"""Carabinieri livery of the Alfa Romeo 155, after a photo of a real one (night blue, white roof), drawn at 1 px = 1 mm
in the car's own coordinates (metres: front towards -Y, left side +X, up +Z, the wheels' bottom at Z -0.18), for
m80_alfa155_carabinieri.py to project on the body:
  Livrea_SX.png  left side (seen from +X: the front on the left), Y -2.35..2.15 -> u, Z 1.35..-0.20 -> v
  Livrea_DX.png  right side (seen from -X: the front on the right)
  Livrea_Retro.png  the tail (seen from behind), X 0.9..-0.9
  Targa_Ant.png, Targa_Post.png  the plates (CC, the Carabinieri's own)
On each side: a thin red line along the waist, rising towards the tail with the body's wedge, ending in a small
lightning zigzag on the rear wing with 112 over it; CARABINIERI in spaced white capitals under the line from the front
door to the rear door, the red flame shield before it. Transparent everywhere else (the paint and the white roof are
made by the material). The positions were measured on the photo (the car 4.44 m long: about 232 px a metre).

python Research/Mazzarino80/Blender/m80_alfa155_livrea.py <out_dir>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

PX = 1000                       # px per metre
Y0, Y1, Z0, Z1 = -2.35, 2.15, -0.20, 1.35
XR = 0.9
RED = (190, 18, 30, 255)
WHITE = (245, 245, 242, 255)
BOLD = "C:/Windows/Fonts/arialbd.ttf"
CONDENSED = ("C:/Windows/Fonts/bahnschrift.ttf", b"Bold Condensed")

REGULAR = "C:/Windows/Fonts/arial.ttf"
LINE_W = 0.025
# The waist line: (y, z) of its middle, front to back, then the zigzag on the rear wing.
LINE = [(-2.12, 0.392), (-1.0, 0.462), (0.10, 0.532), (1.62, 0.622), (1.70, 0.626), (1.60, 0.690), (2.04, 0.712)]
TEXT = ("CARABINIERI", -0.70, 0.94, 0.335, 0.135)   # from y, to y (letters spread between), baseline z, cap height
EMBLEM = (-0.87, 0.32, 0.13)                         # y of its centre, bottom z, height
NUMBER = ("112", 1.86, 0.735, 0.105)                 # centre y, baseline z, cap height


def load(font, size):
    if isinstance(font, tuple):
        f = ImageFont.truetype(font[0], size)
        f.set_variation_by_name(font[1])
        return f
    return ImageFont.truetype(font, size)


def font_for_cap(font, cap_m):
    """A font size whose capitals are cap_m tall."""
    size = 100
    l, t, r, b = load(font, size).getbbox("H")
    return load(font, max(4, int(round(size * cap_m * PX / (b - t)))))


def text_at(d, s, font, cap_m, x, base_y, fill, anchor="c"):
    """anchor: c = x is the centre, l = x is the left end, r = the right end."""
    f = font_for_cap(font, cap_m)
    l, t, r, b = f.getbbox(s)
    lh, th, rh, bh = f.getbbox("H")
    w = r - l
    left = {"c": x - w / 2, "l": x, "r": x - w}[anchor]
    d.text((left - l, base_y - bh), s, font=f, fill=fill)
    return w


def emblem(d, x0, x1, zb, zt, pz):
    """The Carabinieri flame on a red shield: a grenade (circle) with its flame, white."""
    top, bot = pz(zt), pz(zb)
    left, right = min(x0, x1), max(x0, x1)
    w = right - left
    shield = [(left, top), (right, top), (right, top + (bot - top) * 0.62), ((left + right) / 2, bot), (left, top + (bot - top) * 0.62)]
    d.polygon(shield, fill=WHITE)
    k = 0.12 * w
    inner = [(left + k, top + k), (right - k, top + k), (right - k, top + (bot - top) * 0.6), ((left + right) / 2, bot - k * 1.4),
             (left + k, top + (bot - top) * 0.6)]
    d.polygon(inner, fill=RED)
    cx, cy, r = (left + right) / 2, top + (bot - top) * 0.58, w * 0.16
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)
    flame = [(cx - r * 0.8, cy - r * 0.6), (cx - r * 1.2, cy - r * 2.6), (cx - r * 0.3, cy - r * 1.5), (cx, cy - r * 3.1),
             (cx + r * 0.3, cy - r * 1.5), (cx + r * 1.2, cy - r * 2.6), (cx + r * 0.8, cy - r * 0.6)]
    d.polygon(flame, fill=WHITE)


def side(front_on_left):
    w, h = int((Y1 - Y0) * PX), int((Z1 - Z0) * PX)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    py = (lambda y: (y - Y0) * PX) if front_on_left else (lambda y: (Y1 - y) * PX)
    pz = lambda z: (Z1 - z) * PX
    d.line([(py(y), pz(z)) for y, z in LINE], fill=RED, width=int(LINE_W * PX), joint="curve")
    yc, zb, eh = EMBLEM
    emblem(d, py(yc - eh * 0.45), py(yc + eh * 0.45), zb, zb + eh, pz)
    # Spaced capitals: each letter at its place between the two ends, read left to right from either side.
    s, ya, yb, base, cap = TEXT
    f = font_for_cap(REGULAR, cap)
    xa, xb = sorted((py(ya), py(yb)))
    widths = [f.getbbox(c)[2] - f.getbbox(c)[0] for c in s]
    gap = (xb - xa - sum(widths)) / (len(s) - 1)
    x = xa
    for c, w in zip(s, widths):
        text_at(d, c, REGULAR, cap, x, pz(base), WHITE, "l")
        x += w + gap
    s, yc, base, cap = NUMBER
    text_at(d, s, BOLD, cap, py(yc), pz(base), WHITE)
    return im


def rear():
    w, h = int(2 * XR * PX), int((Z1 - Z0) * PX)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    px = lambda x: (XR - x) * PX          # seen from behind the car's +X is on the viewer's left
    pz = lambda z: (Z1 - z) * PX
    text_at(d, "CARABINIERI", CONDENSED, 0.045, px(-0.30), pz(0.56), WHITE)
    return im


def plate(w_mm, h_mm, lines):
    """An Italian plate of the time: white, black letters, the CC of the Carabinieri in red."""
    im = Image.new("RGBA", (w_mm * 4, h_mm * 4), (238, 238, 232, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((6, 6, im.width - 7, im.height - 7), outline=(20, 20, 20, 255), width=6)
    n = len(lines)
    for i, parts in enumerate(lines):
        cap = h_mm * 4 / n * 0.62 / PX
        base = im.height * (i + 1) / n - im.height / n * 0.19
        f = font_for_cap(CONDENSED, cap)
        widths = [f.getbbox(t)[2] - f.getbbox(t)[0] for t, _ in parts]
        gap = cap * PX * 0.35
        x = (im.width - sum(widths) - gap * (len(parts) - 1)) / 2
        for (t, col), w in zip(parts, widths):
            text_at(d, t, CONDENSED, cap, x, base, col, "l")
            x += w + gap
    return im


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    side(True).save(os.path.join(out, "Livrea_SX.png"))
    side(False).save(os.path.join(out, "Livrea_DX.png"))
    rear().save(os.path.join(out, "Livrea_Retro.png"))
    black, red = (15, 15, 15, 255), RED
    plate(520, 110, [[("CC", red), ("VS", black), ("155", black)]]).save(os.path.join(out, "Targa_Ant.png"))
    plate(340, 200, [[("CC", red), ("VS", black)], [("155", black)]]).save(os.path.join(out, "Targa_Post.png"))
    print("livrea ok", out)
