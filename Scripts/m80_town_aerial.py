"""Aerial photos of the whole town (L_M80_Paese): one view from straight above and oblique views from
the four sides, plus closer views of the outskirts. Read only: the map is not saved.
Output: Saved/Mazzarino80/Foto/aerea_*.png. Env M80_AERIAL_MAP overrides the map.
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_AERIAL_MAP", m80_seq.TOWN_MAP)
OUT = ROOT / "Saved/Mazzarino80/Foto"
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"


def look(cap, eye, target, name):
    d = target - eye
    rot = unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))
    cap.capture(eye, rot, OUT / ("aerea_" + name + ".png"))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    m80_seq.load(m80_seq.actor_descs())  # World Partition: the whole town, these views need it
    yield 120
    lots = json.loads(PLAN.read_text(encoding="utf-8"))
    xs = sorted(l["center_cm"][0] for l in lots)
    ys = sorted(l["center_cm"][1] for l in lots)
    zs = sorted(l["center_cm"][2] for l in lots)
    # Centre and size of the built-up area (ignoring the 2 % farthest lots on each side).
    k = len(xs) // 50
    x0, x1, y0, y1 = xs[k], xs[-k - 1], ys[k], ys[-k - 1]
    c = unreal.Vector((x0 + x1) / 2, (y0 + y1) / 2, zs[len(zs) // 2])
    span = max(x1 - x0, y1 - y0)
    cap = m80_seq.ViewCapture(2560, 1440, 60)
    yield 400  # Nanite, distance fields and Lumen settle
    look(cap, c + unreal.Vector(-1, 0, span * 1.05), c, "alto")
    yield 30
    look(cap, c + unreal.Vector(-1, 0, span * 1.05), c, "alto")
    yield 5
    for name, (dx, dy) in {"sud": (0, -1), "nord": (0, 1), "est": (1, 0), "ovest": (-1, 0)}.items():
        eye = c + unreal.Vector(dx * span * 0.75, dy * span * 0.75, span * 0.45)
        look(cap, eye, c, name)
        yield 30
        look(cap, eye, c, name)
        yield 5
    # Closer views of the four corners of the town (the new outskirts).
    for name, (fx, fy) in {"periferia_ne": (0.8, 0.8), "periferia_no": (0.2, 0.8), "periferia_se": (0.8, 0.2), "periferia_so": (0.2, 0.2)}.items():
        t = unreal.Vector(x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, c.z)
        eye = t + unreal.Vector((t.x - c.x) * 0.5, (t.y - c.y) * 0.5, 0) + unreal.Vector(0, 0, 9000)
        look(cap, eye, t, name)
        yield 30
        look(cap, eye, t, name)
        yield 5
    cap.destroy()
    yield 5


m80_seq.Sequencer(run(), log_file=str(OUT / "aerea_error.txt"))
