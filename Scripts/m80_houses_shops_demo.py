"""Puts shops and a bar on the main facade of a few houses of the test map (houses V3, step 6).

In the editor the same is done by hand: select a house, "Uso piano terra di ogni lato", one entry per
edge index (see "Lati rilevati"). Env: M80_SHOPS_MAP, M80_SHOPS ("lot:use,lot:use", use = shop|bar).
M80_SHOPS=auto: houses facing the main streets (MAIN_STREETS, from streets_world.json) get shops
(55%) or a bar (12%) on their main facade.
"""
import json
import math
import os
import random
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

MAP = os.environ.get("M80_SHOPS_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2")
SHOPS = os.environ.get("M80_SHOPS", "1249069204:shop,1249069200:bar,1249069275:shop,1249069271:shop")
USES = {"shop": unreal.M80GroundUse.SHOP, "bar": unreal.M80GroundUse.BAR}
MAIN_STREETS = {"Corso Vittorio Emanuele Secondo", "Via Roma", "Piazza Giuseppe Artale", "Via Principe di Butera", "Via Concezione"}


def auto_uses(houses):
    """Lot id -> use for houses whose main facade is within 9 m of a main street."""
    root = Path(unreal.Paths.project_dir())
    streets = [s for s in json.loads((root / "Research/Mazzarino80/streets_world.json").read_text(encoding="utf-8"))["streets"]
               if s["name"] in MAIN_STREETS]
    rnd = random.Random(11)
    out = {}
    for house in houses:
        poly = [(q.x, q.y) for q in house.get_footprint_world2d()]
        i = house.get_editor_property("resolved_front_edge") % len(poly)
        a, b = poly[i], poly[(i + 1) % len(poly)]
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        for s in streets:
            pts = s["points_cm"]
            for k in range(len(pts) - 1):
                p, q = pts[k], pts[k + 1]
                vx, vy = q[0] - p[0], q[1] - p[1]
                t = max(0.0, min(1.0, ((m[0] - p[0]) * vx + (m[1] - p[1]) * vy) / (vx * vx + vy * vy or 1)))
                if math.hypot(m[0] - p[0] - t * vx, m[1] - p[1] - t * vy) < 900:
                    roll = rnd.random()
                    if roll < 0.55:
                        out[house.get_editor_property("lot_id")] = "shop"
                    elif roll < 0.67:
                        out[house.get_editor_property("lot_id")] = "bar"
                    break
            else:
                continue
            break
    return out


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    wanted = auto_uses(houses) if SHOPS == "auto" else dict(item.split(":") for item in SHOPS.split(","))
    for house in houses:
        use = wanted.get(house.get_editor_property("lot_id"))
        if not use or house.is_excluded():
            continue
        params = house.get_editor_property("house")
        edges = len(house.get_editor_property("resolved_edge_kinds"))
        uses = [unreal.M80GroundUse.HOME] * edges
        uses[house.get_editor_property("resolved_front_edge") % edges] = USES[use]
        params.set_editor_property("edge_ground_use", uses)
        house.set_editor_property("house", params)
        house.rebuild()
        unreal.log("M80 shops: {} -> {} ({})".format(house.get_editor_property("lot_id"), use, house.get_editor_property("build_info")))
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10


m80_seq.Sequencer(run())
