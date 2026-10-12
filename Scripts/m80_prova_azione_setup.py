"""Small action test map /Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione (classic level, opens in seconds): a real piece of
Mazzarino, the OSM lots of the densest quarter within M80_PROVA_RAGGIO_M (default 45 m) brought onto a flat floor
around the origin as live procedural houses (same styles, floors and roofs as the town), the town's atmosphere, the
player start in the most open spot, weapons on the ground, a Fiat 126, the town game mode. For fighting, weapons
and climbing on houses, balconies and roofs.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_prova_azione_setup.py
Report: Saved/Mazzarino80/Player/prova_azione.json
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

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione"
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"
REPORT = ROOT / "Saved/Mazzarino80/Player/prova_azione.json"
RADIUS = float(os.environ.get("M80_PROVA_RAGGIO_M", "45")) * 100
STYLE_DIR = "/Game/Mazzarino80/Houses/Styles/"
STYLES = ["DA_M80Style_01_PopolarePietra", "DA_M80Style_02_PalazzoUrbano", "DA_M80Style_03_Intonacata5070", "DA_M80Style_04_CasaPovera"]
FLOOR_MATERIAL = "/Game/Mazzarino80/Kit/Stairs/MI_M80_Lavica_secondaria"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
V = unreal.Vector
W = unreal.M80Weapon


def densest(lots):
    cells = {}
    for lot in lots:
        c = lot["center_cm"]
        cells.setdefault((math.floor(c[0] / 10000), math.floor(c[1] / 10000)), []).append(c)
    best = max(cells.values(), key=len)
    return sum(c[0] for c in best) / len(best), sum(c[1] for c in best) / len(best)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / max(dx * dx + dy * dy, 1e-6)))
    return math.hypot(px - ax - dx * t, py - ay - dy * t)


def inside(px, py, ring):
    c = False
    for i in range(len(ring)):
        ax, ay = ring[i]
        bx, by = ring[i - 1]
        if (ay > py) != (by > py) and px < (bx - ax) * (py - ay) / (by - ay) + ax:
            c = not c
    return c


def clearance(px, py, rings):
    """Distance to the nearest house wall (0 inside a house)."""
    best = 1e9
    for ring in rings:
        if inside(px, py, ring):
            return 0.0
        for i in range(len(ring)):
            best = min(best, seg_dist(px, py, ring[i - 1][0], ring[i - 1][1], ring[i][0], ring[i][1]))
    return best


def open_spots(rings, half, need, count, apart, most=800.0):
    """Free points in the streets of the quarter: `need` to `most` cm from the nearest wall (not the open field
    around it), the most open first, `apart` cm from each other."""
    cand = []
    for i in range(-int(half / 150), int(half / 150) + 1):
        for j in range(-int(half / 150), int(half / 150) + 1):
            x, y = i * 150.0, j * 150.0
            c = clearance(x, y, rings)
            if need <= c <= most:
                cand.append((c, x, y))
    cand.sort(reverse=True)
    out = []
    for c, x, y in cand:
        if all(math.hypot(x - a, y - b) >= apart for a, b in out):
            out.append((x, y))
        if len(out) >= count:
            break
    return out


def steps():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lots = [l for l in json.loads(PLAN.read_text(encoding="utf-8")) if l.get("tags", {}).get("building") not in ("roof", "grandstand")]
    cx, cy = densest(lots)
    mine = [l for l in lots if math.hypot(l["center_cm"][0] - cx, l["center_cm"][1] - cy) <= RADIUS]
    rings = [[(p[0] - cx, p[1] - cy) for p in l["ring_cm"]] for l in mine]
    half = RADIUS + 2500

    # The map is this script's own output: it is made again from scratch each run.
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
        yield 5
    LES.new_level(MAP)
    yield 10
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected %s to be open, got %s" % (MAP, world.get_path_name()))
    world.get_world_settings().set_editor_property("default_game_mode", unreal.M80GameMode.static_class())

    # Flat floor (a thin box, so traces and the houses' ground contact find it), the town's sky.
    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cube"), V(0, 0, -5))
    floor.set_actor_scale3d(V(half * 2 / 100, half * 2 / 100, 0.1))
    floor.set_actor_label("Pavimento")
    floor.tags = ["M80Ground"]
    mat = unreal.load_asset(FLOOR_MATERIAL)
    if mat:
        floor.static_mesh_component.set_material(0, mat)
    atmo = EAS.spawn_actor_from_class(unreal.M80Atmosphere, V(0, 0, 0))
    atmo.set_actor_label("Atmosfera")
    atmo.set_editor_property("hour", 10.5)   # a late summer morning: light from high up into the alleys
    yield 5

    styles = {s: unreal.load_asset(STYLE_DIR + s) for s in STYLES}
    rng = random.Random(80)
    houses = []
    for lot in mine:
        actor = EAS.spawn_actor_from_class(unreal.M80House, V(0, 0, 0))
        actor.set_actor_label("Casa_" + lot["id"])
        actor.set_folder_path("Case")
        actor.set_editor_property("lot_id", lot["id"])
        actor.set_editor_property("live_rebuild", False)
        actor.set_footprint_world([V(p[0] - cx, p[1] - cy, 0) for p in lot["ring_cm"]])
        params = actor.get_editor_property("house")
        d = lot.get("distance_corso_m", 200)
        weights = [0.4, 0.4, 0.2, 0.0] if d < 60 else [0.5, 0.05, 0.3, 0.15] if d < 250 else [0.25, 0.0, 0.3, 0.45]
        params.set_editor_property("style", styles[rng.choices(STYLES, weights)[0]])
        params.set_editor_property("alternative_styles", [s for s in styles.values() if s])
        params.set_editor_property("floors", max(1, min(5, round((lot.get("height_m", 7) - 1.0) / 3.2))))
        params.set_editor_property("seed", int(lot["id"]) % 100000)
        params.set_editor_property("decay", rng.uniform(0.15, 0.7))
        roll = rng.random()
        params.set_editor_property("roof_type", unreal.M80RoofType.GABLE if roll < 0.55 else unreal.M80RoofType.TERRACE if roll < 0.85 else unreal.M80RoofType.SHED)
        if lot.get("front_edge") is not None:
            params.set_editor_property("front_edge", int(lot["front_edge"]))
        actor.set_editor_property("house", params)
        houses.append(actor)
    yield 5
    # Two passes: the second sees every neighbour, so shared walls are found.
    for _ in range(2):
        for i, actor in enumerate(houses):
            actor.rebuild()
            if i % 10 == 9:
                yield 1
    for actor in houses:
        actor.set_editor_property("live_rebuild", True)

    # Player start in the most open spot, weapons and a car in the next ones.
    spots = open_spots(rings, RADIUS * 0.7, 250, 10, 900)
    sx, sy = spots[0]
    start = EAS.spawn_actor_from_class(unreal.PlayerStart, V(sx, sy, 100))
    toward = spots[1] if len(spots) > 1 else (0.0, 0.0)
    start.set_actor_rotation(unreal.Rotator(0, math.degrees(math.atan2(toward[1] - sy, toward[0] - sx)), 0), False)
    placed = {"start": [sx, sy], "pickups": [], "car": None}
    weapons = [W.BERETTA, W.REVOLVER, W.LUPARA, W.MAZZA, W.COLTELLO]
    for (x, y), w in zip(spots[1:1 + len(weapons)], weapons):
        p = EAS.spawn_actor_from_class(unreal.M80WeaponPickup, V(x, y, 55))
        p.set_weapon(w, -1)
        p.set_folder_path("Armi")
        placed["pickups"].append([str(w), x, y])
    car_spots = open_spots(rings, RADIUS * 0.8, 300, 12, 900)
    if len(car_spots) > 6:
        x, y = car_spots[6]
        car = EAS.spawn_actor_from_class(unreal.M80CarFiat126, V(x, y, 80))
        placed["car"] = [x, y]
    # Climbing blocks of known heights next to the start (tests and practice): 1 m, 2.2 m, 2.9 m (2 m deep, to stand on).
    blocks = []
    free = open_spots(rings, RADIUS * 0.9, 450, 6, 600)
    for (x, y), (h, depth, name) in zip(free[1:], ((100, 150, "Muretto_1m"), (220, 150, "Muro_2_2m"), (290, 200, "Blocco_2_9m"))):
        b = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cube"), V(x, y, h / 2.0))
        b.set_actor_scale3d(V(depth / 100.0, 3.0, h / 100.0))
        b.set_actor_label("Prova_" + name)
        b.set_folder_path("Prove arrampicata")
        b.tags = ["M80ProvaArrampicata"]
        blocks.append([name, x, y, h])
    placed["blocks"] = blocks
    # A camera the automatic tests move around (Python cannot spawn actors in Play In Editor).
    cam = EAS.spawn_actor_from_class(unreal.CameraActor, V(sx, sy, 400))
    cam.set_actor_label("CameraTest")
    yield 5
    LES.save_current_level()
    # Check photos: from above and from the start.
    out = ROOT / "Saved/Mazzarino80/Player/ProvaAzione"
    for name, eye, target, fov in (("alto", V(-RADIUS, -RADIUS, RADIUS * 1.1), V(0, 0, 0), 70),
                                   ("partenza", V(sx, sy, 170), V(toward[0], toward[1], 300), 80)):
        rot = unreal.MathLibrary.find_look_at_rotation(eye, target)
        m80_seq.set_view(eye, rot)
        yield 150
        cap = m80_seq.ViewCapture(1600, 900, fov)
        cap.capture(eye, rot, out / ("%s.png" % name))
        cap.destroy()
        yield 3
    REPORT.write_text(json.dumps({"map": MAP, "centre_town_cm": [cx, cy], "lots": len(mine), "houses": len(houses),
                                  "units": sum(a.get_editor_property("unit_count") for a in houses), "placed": placed}, indent=1),
                      encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(REPORT.with_suffix(".error.txt")))
