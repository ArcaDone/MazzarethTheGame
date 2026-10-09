"""Sheet of the colour check (after m80_bartoli_colour_compare.py): every plate cut from the Unreal captures, the town
materials on the left and the Palazzo Bartoli swatches on the right of each family, with the mean base colour (sRGB)
and its lightness; the Bartoli plates also show the distance (CIE delta E) from the closest town material of their family.

python Scripts/m80_bartoli_colour_sheet.py
Out: Saved/Mazzarino80/Bartoli/ConfrontoColori/confronto_colori.jpg and misure.json
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "Saved/Mazzarino80/Bartoli/ConfrontoColori"


def to_lab(srgb):
    c = np.asarray(srgb, float)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = m @ lin / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def main():
    layout = json.loads((DIR / "layout.json").read_text(encoding="utf-8"))
    base = np.asarray(Image.open(DIR / "base.png").convert("RGB"), float) / 255
    lit = Image.open(DIR / "lit.png").convert("RGB")
    W = layout["image"]["width"]
    pitch, tile = layout["pitch_cm"], layout["tile_cm"]
    font = ImageFont.truetype("arial.ttf", 15)
    big = ImageFont.truetype("arialbd.ttf", 20)
    cell_w, cell_h, thumb = 190, 250, 150
    families = []
    for r in layout["rows"]:
        if families and families[-1][0] == r["family"]:
            families[-1][1].extend(r["cells"] and [dict(c, row=r["row"]) for c in r["cells"]])
        else:
            families.append((r["family"], [dict(c, row=r["row"]) for c in r["cells"]]))
    cols = max(len(c) for _, c in families) + 1
    sheet = Image.new("RGB", (cols * cell_w + 20, len(families) * (cell_h + 40) + 20), (28, 28, 28))
    d = ImageDraw.Draw(sheet)
    report = {}
    y = 10
    for family, cells in families:
        d.text((12, y), family, font=big, fill=(235, 235, 235))
        y += 30
        ue = [c for c in cells if c["side"] == "ue"]
        ba = [c for c in cells if c["side"] == "bartoli"]
        measured = {}
        for c in ue + ba:
            # The capture looks along +Y, so the columns come out mirrored.
            cx = W - (c["col"] * pitch + pitch / 2)
            cy = c["row"] * pitch + pitch / 2
            h = int(tile * 0.36)
            crop = base[int(cy - h):int(cy + h), int(cx - h):int(cx + h)]
            mean = crop.reshape(-1, 3).mean(0)
            measured[c["label"]] = (mean, to_lab(mean), lit.crop((int(cx - tile / 2), int(cy - tile / 2), int(cx + tile / 2), int(cy + tile / 2))))
        x = 10
        for side, group in (("ue", ue), ("gap", []), ("bartoli", ba)):
            if side == "gap":
                d.line((x + 10, y, x + 10, y + cell_h - 20), fill=(120, 120, 120), width=2)
                x += 30
                continue
            for c in group:
                mean, lab, img = measured[c["label"]]
                sheet.paste(img.resize((thumb, thumb)), (x, y))
                label = c["label"].replace("MI_M80_", "").replace("M_M80_", "").replace("_muro_hi", "").replace("_hi", "")
                d.text((x, y + thumb + 4), label[:22], font=font, fill=(230, 230, 230))
                d.text((x, y + thumb + 22), "sRGB %d %d %d  L %.0f" % (*(mean * 255).round(), lab[0]), font=font, fill=(190, 190, 190))
                rec = {"family": family, "side": side, "srgb": [round(float(v), 3) for v in mean], "lab": [round(float(v), 1) for v in lab]}
                if side == "bartoli" and ue:
                    dists = {u["label"]: float(np.linalg.norm(lab - measured[u["label"]][1])) for u in ue}
                    near = min(dists, key=dists.get)
                    dL = lab[0] - measured[near][1][0]
                    rec.update({"vicino": near, "deltaE": round(dists[near], 1), "deltaL": round(float(dL), 1)})
                    colour = (120, 220, 120) if dists[near] < 8 else (235, 200, 90) if dists[near] < 16 else (240, 110, 100)
                    d.text((x, y + thumb + 40), "dE %.0f (L %+.0f)" % (dists[near], dL), font=font, fill=colour)
                    d.text((x, y + thumb + 58), "vs " + near.replace("MI_M80_", "").replace("M_M80_", "")[:19], font=font, fill=(150, 150, 150))
                sheet.paste(Image.new("RGB", (thumb, 10), tuple(int(v * 255) for v in mean)), (x, y + thumb - 10))
                report[c["label"]] = rec
                x += cell_w
        y += cell_h + 10
    sheet.save(DIR / "confronto_colori.jpg", quality=90)
    (DIR / "misure.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


main()
