"""Crowd test map /Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla (classic level, opens in seconds): a piece of
Mazzarino (the OSM lots of the densest quarter, live procedural houses as in L_M80_ProvaAzione) with the lots of the
middle left empty as a square, paved with Palazzo Bartoli's basalt, the town's afternoon light.
In the square: card tables with chairs and Sicilian cards (old men playing), rush-seat chairs against the walls (old
women sitting by their doors), and marker points (TargetPoint, tagged) where the NPC script puts people:
  M80Folla_Tavolo  a seat at a card table      M80Folla_Sedia   a chair by a door
  M80Folla_Gruppo  standing groups (chatting)  M80Folla_Giro    waypoints of a walk around the square
  M80Folla_Gioco   where the children play
The map is this script's own output: it is made again from scratch each run.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_prova_folla_setup.py
Report: Saved/Mazzarino80/Personaggi/prova_folla.json, photos in Saved/Mazzarino80/Personaggi/ProvaFolla
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
# Same lots, styles and floor as L_M80_ProvaAzione (m80_prova_azione_setup.py starts its own run when imported).
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"
STYLE_DIR = "/Game/Mazzarino80/Houses/Styles/"
STYLES = ["DA_M80Style_01_PopolarePietra", "DA_M80Style_02_PalazzoUrbano", "DA_M80Style_03_Intonacata5070", "DA_M80Style_04_CasaPovera"]
PAVING = "/Game/Mazzarino80/Buildings/Bartoli/Materiali/MI_M80_BG_Basolato"
MAP ="/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
OUT = ROOT / "Saved/Mazzarino80/Personaggi"
REPORT = OUT / "prova_folla.json"
RADIUS = float(os.environ.get("M80_FOLLA_RAGGIO_M", "48")) * 100
SQUARE = float(os.environ.get("M80_FOLLA_PIAZZA_M", "15")) * 100
CHAIR = "/Game/Migrated/SediaVecchia"
TABLE = "/Game/Migrated/Table"
CARDS = ["/Game/Migrated/BoxCarteSiciliane", "/Game/Migrated/CarteBaked_004", "/Game/Migrated/CarteBaked_005",
         "/Game/Migrated/CarteBaked_006"]
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
V = unreal.Vector


def densest(lots):
    cells = {}
    for lot in lots:
        c = lot["center_cm"]
        cells.setdefault((math.floor(c[0] / 10000), math.floor(c[1] / 10000)), []).append(c)
    best = max(cells.values(), key=len)
    return sum(c[0] for c in best) / len(best), sum(c[1] for c in best) / len(best)


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
    if any(inside(px, py, ring) for ring in rings):
        return 0.0
    return nearest_wall(px, py, rings)[0]


def open_spots(rings, half, need, count, apart, most=800.0):
    """Free points `need` to `most` cm from the nearest wall, the most open first, `apart` cm from each other."""
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


def nearest_wall(px, py, rings):
    """Nearest point on any house wall and its distance."""
    best = (1e9, px, py)
    for ring in rings:
        for i in range(len(ring)):
            ax, ay = ring[i - 1]
            bx, by = ring[i]
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / max(dx * dx + dy * dy, 1e-6)))
            qx, qy = ax + dx * t, ay + dy * t
            d = math.hypot(px - qx, py - qy)
            if d < best[0]:
                best = (d, qx, qy)
    return best


def mesh_actor(path, loc, yaw, folder, label):
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        return None
    a = EAS.spawn_actor_from_object(mesh, loc)
    a.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    a.set_folder_path(folder)
    a.set_actor_label(label)
    return a


def bounds_of(path):
    mesh = unreal.load_asset(path)
    b = mesh.get_bounding_box()
    return b.min, b.max


def paving(size_m):
    """Palazzo Bartoli's basalt paving laid over the whole floor: its tiling master repeats every 1/Scala metres of
    UV0, and the floor cube's UV0 spans 0-1, so the scales are multiplied by the floor size."""
    mel = unreal.MaterialEditingLibrary
    parent = unreal.load_asset(PAVING)
    path = MAP.rsplit("/", 2)[0] + "/Materiali/MI_M80_ProvaFolla_Basolato"
    mi = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else \
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit("/", 1)[1], path.rsplit("/", 1)[0],
                                                                unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, parent)
    for name in ("ScalaU", "ScalaV"):
        mel.set_material_instance_scalar_parameter_value(mi, name, mel.get_material_instance_scalar_parameter_value(parent, name) * size_m)
    unreal.EditorAssetLibrary.save_loaded_asset(mi, False)
    return mi


def marker(tag, x, y, z, yaw, folder="Folla"):
    p = EAS.spawn_actor_from_class(unreal.TargetPoint, V(x, y, z))
    p.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    p.tags = [tag]
    p.set_folder_path(folder)
    return p


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    lots = [l for l in json.loads(PLAN.read_text(encoding="utf-8")) if l.get("tags", {}).get("building") not in ("roof", "grandstand")]
    cx, cy = densest(lots)
    near = [l for l in lots if math.hypot(l["center_cm"][0] - cx, l["center_cm"][1] - cy) <= RADIUS]
    # The square: every lot with a corner inside it goes, so the houses face it from all sides.
    mine = [l for l in near if all(math.hypot(p[0] - cx, p[1] - cy) > SQUARE for p in l["ring_cm"])]
    rings = [[(p[0] - cx, p[1] - cy) for p in l["ring_cm"]] for l in mine]
    half = RADIUS + 2500

    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
        yield 5
    LES.new_level(MAP)
    yield 10
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected %s to be open, got %s" % (MAP, world.get_path_name()))
    world.get_world_settings().set_editor_property("default_game_mode", unreal.M80GameMode.static_class())

    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cube"), V(0, 0, -5))
    floor.set_actor_scale3d(V(half * 2 / 100, half * 2 / 100, 0.1))
    floor.set_actor_label("Pavimento")
    floor.tags = ["M80Ground"]
    floor.static_mesh_component.set_material(0, paving(half * 2 / 100))
    atmo = EAS.spawn_actor_from_class(unreal.M80Atmosphere, V(0, 0, 0))
    atmo.set_actor_label("Atmosfera")
    atmo.set_editor_property("hour", 15.0)   # afternoon, sun still high enough to light the square
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
        params.set_editor_property("style", styles[rng.choices(STYLES, [0.45, 0.2, 0.25, 0.1])[0]])
        params.set_editor_property("alternative_styles", [s for s in styles.values() if s])
        params.set_editor_property("floors", max(1, min(4, round((lot.get("height_m", 7) - 1.0) / 3.2))))
        params.set_editor_property("seed", int(lot["id"]) % 100000)
        params.set_editor_property("decay", rng.uniform(0.2, 0.7))
        roll = rng.random()
        params.set_editor_property("roof_type", unreal.M80RoofType.GABLE if roll < 0.55 else unreal.M80RoofType.TERRACE if roll < 0.85 else unreal.M80RoofType.SHED)
        if lot.get("front_edge") is not None:
            params.set_editor_property("front_edge", int(lot["front_edge"]))
        actor.set_editor_property("house", params)
        houses.append(actor)
    yield 5
    for _ in range(2):
        for i, actor in enumerate(houses):
            actor.rebuild()
            if i % 10 == 9:
                yield 1
    for actor in houses:
        actor.set_editor_property("live_rebuild", True)

    placed = {"tables": [], "chairs": [], "markers": {}}

    def count(tag):
        placed["markers"][tag] = placed["markers"].get(tag, 0) + 1

    # Card tables in the open middle: a table, four chairs around it, a deck and a few cards on top.
    tmin, tmax = bounds_of(TABLE)
    cmin, cmax = bounds_of(CHAIR)
    top = tmax.z
    reach = max(tmax.x - tmin.x, tmax.y - tmin.y) * 0.5 + (cmax.x - cmin.x) * 0.35
    middle = [s for s in open_spots(rings, SQUARE, 600, 20, 450, most=1e9) if math.hypot(*s) < SQUARE * 0.8]
    for n, (x, y) in enumerate(middle[:3]):
        yaw = rng.uniform(0, 90)
        mesh_actor(TABLE, V(x, y, 0), yaw, "Tavoli", "Tavolo_carte_%d" % n)
        for k in range(4):
            a = math.radians(yaw + 90 * k)
            sx, sy = x + math.cos(a) * reach, y + math.sin(a) * reach
            face = math.degrees(math.atan2(y - sy, x - sx))
            # The chair mesh faces +X: turn it to the table. Seat markers sit on it, facing the table.
            mesh_actor(CHAIR, V(sx, sy, 0), face, "Tavoli", "Sedia_tavolo_%d_%d" % (n, k))
            marker("M80Folla_Tavolo", sx, sy, 0, face)
            count("M80Folla_Tavolo")
        for j, card in enumerate(CARDS):
            mesh_actor(card, V(x + rng.uniform(-25, 25), y + rng.uniform(-25, 25), top + 0.5 + j * 0.2), rng.uniform(0, 360),
                       "Tavoli", "Carte_%d_%d" % (n, j))
        placed["tables"].append([x, y])
    yield 5

    # Rush-seat chairs by the walls, looking at the square: an old woman sits on each.
    by_wall = []
    for i in range(-int(SQUARE / 100) - 4, int(SQUARE / 100) + 5):
        for j in range(-int(SQUARE / 100) - 4, int(SQUARE / 100) + 5):
            x, y = i * 100.0, j * 100.0
            d, qx, qy = nearest_wall(x, y, rings)
            if 70 <= d <= 110 and clearance(x, y, rings) > 0 and math.hypot(x, y) < SQUARE + 600:
                by_wall.append((x, y, qx, qy))
    rng.shuffle(by_wall)
    chairs = []
    for x, y, qx, qy in by_wall:
        if len(chairs) >= 6:
            break
        if all(math.hypot(x - a, y - b) > 500 for a, b in chairs + [tuple(t) for t in placed["tables"]]):
            face = math.degrees(math.atan2(y - qy, x - qx))
            mesh_actor(CHAIR, V(x, y, 0), face, "Sedie", "Sedia_porta_%d" % len(chairs))
            marker("M80Folla_Sedia", x, y, 0, face)
            count("M80Folla_Sedia")
            chairs.append((x, y))
    placed["chairs"] = chairs

    # Standing groups, a walk around the square, the children's corner.
    free = [s for s in open_spots(rings, SQUARE + 800, 250, 60, 300) if all(math.hypot(s[0] - a, s[1] - b) > 350
                                                                             for a, b in chairs + [tuple(t) for t in placed["tables"]])]
    for x, y in free[:5]:
        for k in range(3):
            a = math.radians(120 * k + rng.uniform(-20, 20))
            px, py = x + math.cos(a) * 70, y + math.sin(a) * 70
            marker("M80Folla_Gruppo", px, py, 0, math.degrees(math.atan2(y - py, x - px)))
            count("M80Folla_Gruppo")
    ring_r = SQUARE * 0.95
    for k in range(10):
        a = 2 * math.pi * k / 10
        x, y = math.cos(a) * ring_r, math.sin(a) * ring_r
        if clearance(x, y, rings) > 150:
            marker("M80Folla_Giro", x, y, 0, math.degrees(a) + 90)
            count("M80Folla_Giro")
    if len(free) > 5:
        gx, gy = free[5]
        for k in range(6):
            marker("M80Folla_Gioco", gx + rng.uniform(-250, 250), gy + rng.uniform(-250, 250), 0, rng.uniform(0, 360))
            count("M80Folla_Gioco")
        placed["gioco"] = [gx, gy]

    sx, sy = free[-1] if free else (0.0, -SQUARE)
    start = EAS.spawn_actor_from_class(unreal.PlayerStart, V(sx, sy, 100))
    start.set_actor_rotation(unreal.Rotator(0, 0, math.degrees(math.atan2(-sy, -sx))), False)
    placed["start"] = [sx, sy]
    cam = EAS.spawn_actor_from_class(unreal.CameraActor, V(sx, sy, 400))
    cam.set_actor_label("CameraTest")
    yield 5
    LES.save_current_level()

    shots = OUT / "ProvaFolla"
    for name, eye, target, fov in (("alto", V(-SQUARE * 1.6, -SQUARE * 1.6, SQUARE * 1.5), V(0, 0, 0), 70),
                                   ("piazza", V(sx, sy, 170), V(0, 0, 120), 80)):
        rot = unreal.MathLibrary.find_look_at_rotation(eye, target)
        m80_seq.set_view(eye, rot)
        yield 150
        cap = m80_seq.ViewCapture(1600, 900, fov)
        cap.capture(eye, rot, shots / ("%s.png" % name))
        cap.destroy()
        yield 3
    REPORT.write_text(json.dumps({"map": MAP, "centre_town_cm": [cx, cy], "lots": len(mine), "houses": len(houses),
                                  "placed": placed}, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(REPORT.with_suffix(".error.txt")))
