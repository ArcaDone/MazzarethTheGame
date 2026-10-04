"""GTA-style map of the town for the HUD radar and the full map (plain Python + Pillow).

Sources: Research/Mazzarino80/building_footprint_plan.json (3216 OSM footprints, world cm) and
streets_world.json (streets, world cm). Output: Research/Mazzarino80/Map/T_M80_Mappa.png (4096 px,
image column = world X, row = world Y, i.e. the top view of the level) and map_bounds.json with the
world square it covers (AM80HUD uses the same numbers).
Usage: python Tools/Map/m80_make_map.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Research/Mazzarino80"
OUT = SRC / "Map"
SIZE = 4096
PAD_CM = 15000
LAND = (43, 49, 56)
BLOCK = (78, 86, 96)
BLOCK_EDGE = (98, 107, 118)
ROAD = {"primary": (226, 222, 196, 10.0), "secondary": (220, 220, 210, 9.0), "tertiary": (205, 208, 212, 8.0),
        "residential": (165, 172, 180, 6.0), "unclassified": (165, 172, 180, 6.0), "service": (130, 137, 146, 4.0),
        "pedestrian": (120, 128, 138, 4.0), "footway": (98, 106, 116, 2.0), "steps": (98, 106, 116, 2.0), "track": (110, 104, 92, 3.0)}


def main():
    buildings = json.loads((SRC / "building_footprint_plan.json").read_text(encoding="utf-8"))
    streets = json.loads((SRC / "streets_world.json").read_text(encoding="utf-8"))["streets"]
    xs = [p[0] for b in buildings for p in b["ring_cm"]]
    ys = [p[1] for b in buildings for p in b["ring_cm"]]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + PAD_CM
    x0, y0, span = cx - half, cy - half, 2 * half
    px_per_cm = SIZE / span

    def P(p):
        return ((p[0] - x0) * px_per_cm, (p[1] - y0) * px_per_cm)

    img = Image.new("RGB", (SIZE, SIZE), LAND)
    d = ImageDraw.Draw(img)
    order = ["track", "footway", "steps", "service", "pedestrian", "unclassified", "residential", "tertiary", "secondary", "primary"]
    for kind in order:
        col = ROAD[kind]
        w = max(1, int(round(col[3] * 100 * px_per_cm)))
        for s in streets:
            if s.get("highway") != kind or len(s["points_cm"]) < 2:
                continue
            pts = [P(p) for p in s["points_cm"]]
            d.line(pts, fill=col[:3], width=w, joint="curve")
            r = w / 2
            for q in (pts[0], pts[-1]):
                d.ellipse((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill=col[:3])
    for b in buildings:
        ring = [P(p) for p in b["ring_cm"]]
        if len(ring) >= 3:
            d.polygon(ring, fill=BLOCK, outline=BLOCK_EDGE)
    img = img.filter(ImageFilter.SMOOTH)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / "T_M80_Mappa.png")
    bounds = {"min_x_cm": x0, "min_y_cm": y0, "span_cm": span, "size_px": SIZE}
    (OUT / "map_bounds.json").write_text(json.dumps(bounds, indent=1), encoding="utf-8")
    img.resize((1024, 1024)).save(OUT / "preview.png")
    print(json.dumps(bounds))


if __name__ == "__main__":
    main()
