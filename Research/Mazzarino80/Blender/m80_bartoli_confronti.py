"""Side-by-side sheets: reference photo (left) and the high-poly model from the same viewpoint (right).

python m80_bartoli_confronti.py  ->  Saved/Mazzarino80/Bartoli/confronto_<view>.jpg and a contact sheet
of the interiors and aerial views (riepilogo_interni.jpg, riepilogo_aerei.jpg).
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PREV = os.path.join(HERE, "Previews", "Bartoli")
OUT = os.path.join(ROOT, "Saved", "Mazzarino80", "Bartoli")
PHOTOS = "D:/BlenderTest/Palazzo Bartoli/Screenshot 2026-10-07 %s.png"
CHAT = os.environ.get("M80_CHAT_IMAGES", "")
PAIRS = {
    "frontale_bartoli": PHOTOS % "095747",
    "corso_222": PHOTOS % "095257",
    "corso_271": PHOTOS % "095309",
    "angolo_farmacia": os.path.join(CHAT, "57.webp"),
    "corso_ovest_b": os.path.join(CHAT, "58.webp"),
    "salita_teatro": os.path.join(CHAT, "59.webp"),
    "cortile_scalone": PHOTOS % "095650",
    "cortile_da_loggia": PHOTOS % "095639",
}
SHEETS = {
    "riepilogo_interni": ["salone", "pranzo", "biblioteca", "anticamera_dal_ballatoio", "cinema_platea", "cinema_galleria", "cinema_foyer", "giardino_loggia"],
    "riepilogo_aerei": ["aereo_sudest", "aereo_nordovest", "via_butera", "cortile_scalone"],
}


def font(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:
        return ImageFont.load_default()


def label(img, text, xy):
    ImageDraw.Draw(img).text(xy, text, fill="white", font=font(28), stroke_width=3, stroke_fill="black")


def main():
    os.makedirs(OUT, exist_ok=True)
    for view, photo in PAIRS.items():
        model = os.path.join(PREV, "alta_%s.png" % view)
        if not (os.path.exists(photo) and os.path.exists(model)):
            print("skip", view)
            continue
        a, b = Image.open(photo).convert("RGB"), Image.open(model).convert("RGB")
        h = 760
        a = a.resize((int(a.width * h / a.height), h))
        b = b.resize((int(b.width * h / b.height), h))
        sheet = Image.new("RGB", (a.width + b.width + 10, h), "white")
        sheet.paste(a, (0, 0))
        sheet.paste(b, (a.width + 10, 0))
        label(sheet, "FOTO", (15, 15))
        label(sheet, "MODELLO (alta definizione)", (a.width + 25, 15))
        sheet.save(os.path.join(OUT, "confronto_%s.jpg" % view), quality=88)
    for name, views in SHEETS.items():
        tiles = [(v, os.path.join(PREV, "alta_%s.png" % v)) for v in views if os.path.exists(os.path.join(PREV, "alta_%s.png" % v))]
        w, h = 800, 450
        cols = 2
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w, rows * h), "white")
        for k, (v, path) in enumerate(tiles):
            im = Image.open(path).convert("RGB").resize((w, h))
            label(im, v.replace("_", " "), (12, 10))
            sheet.paste(im, ((k % cols) * w, (k // cols) * h))
        sheet.save(os.path.join(OUT, name + ".jpg"), quality=88)
    print("ok")


if __name__ == "__main__":
    main()
