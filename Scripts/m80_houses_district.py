"""Builds a whole district of procedural houses from the OSM footprint plan.

Creates /Game/Mazzarino80/Houses/Maps/L_M80_District_V2 as a copy of the town overview
map, removes the old placeholder building volumes and spawns one AM80House per OSM lot
within a radius. Hand-made landmark structures already in the map are kept: lots whose
centre falls inside one of them are skipped.

Env: M80_DISTRICT_RADIUS_M (default 160; "all" takes every OSM lot), M80_DISTRICT_CENTER "x,y" in cm
     (default: centre of the 18 sample lots), M80_DISTRICT_REBUILD_MAP=1 recreates the map,
     M80_DISTRICT_KEEP_EXISTING=1 (default) leaves the houses already in the map as they are (hand edits
     kept): only new lots are spawned, and existing houses next to them are rebuilt with their own
     settings so shared walls are found. M80_DISTRICT_SKIP_TAGS: OSM building tags that are not houses
     (default "roof,grandstand": canopies and stands).
     M80_DISTRICT_BATCH=N spawns at most N new lots per run (nearest to the centre first) and
     M80_DISTRICT_BAKE=1 bakes them to Nanite before saving: thousands of unbaked houses do not fit in
     8 GB of video memory, so a whole town is added by running the script until "remaining" is 0.
"""
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SOURCE_MAP = "/Game/Levels/Mazzarino80_Panoramica"
MAP = os.environ.get("M80_DISTRICT_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_District_V2")
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"
SAMPLE = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18.json"
OUT = ROOT / "Saved/Mazzarino80/HousesV2/district_report.json"
STYLE_DIR = "/Game/Mazzarino80/Houses/Styles/"
_radius = os.environ.get("M80_DISTRICT_RADIUS_M", "160")
RADIUS = float("inf") if _radius == "all" else float(_radius) * 100
KEEP_EXISTING = os.environ.get("M80_DISTRICT_KEEP_EXISTING", "1") == "1"
SKIP_TAGS = {t for t in os.environ.get("M80_DISTRICT_SKIP_TAGS", "roof,grandstand").split(",") if t}
BATCH = int(os.environ.get("M80_DISTRICT_BATCH", "0"))
BAKE = os.environ.get("M80_DISTRICT_BAKE", "0") == "1"
BAKE_FOLDER = "/Game/Mazzarino80/Houses/Baked/" + MAP.rsplit("/", 1)[-1]
NEIGHBOUR_CM = 4000   # existing houses this close to a new lot are rebuilt (shared walls)
REBUILD_MAP = os.environ.get("M80_DISTRICT_REBUILD_MAP", "0") == "1"
OLD_CLASSES = ("MazzarinoProceduralBuilding", "MazzarinoHistoricBuilding", "MazzarinoBuilding", "BP_ProceduralBuilding")
OLD_MESHES = ("M80_Edifici_WorldYReflected",)

STYLES = ["DA_M80Style_01_PopolarePietra", "DA_M80Style_02_PalazzoUrbano", "DA_M80Style_03_Intonacata5070", "DA_M80Style_04_CasaPovera"]


def default_center():
    pts = [p for b in json.loads(SAMPLE.read_text(encoding="utf-8"))["buildings"] for p in b["footprint_world_cm"]]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def pick_style(lot, rng):
    """Grand houses along the Corso, poorer houses towards the edges of town."""
    d = lot.get("distance_corso_m", 200)
    weights = [0.4, 0.4, 0.2, 0.0] if d < 60 else [0.5, 0.05, 0.3, 0.15] if d < 250 else [0.25, 0.0, 0.3, 0.45]
    return rng.choices(STYLES, weights)[0]


def landmark_boxes(world):
    """XY boxes of hand-made structures: big static geometry that is not terrain, road or house."""
    boxes = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        name = actor.get_class().get_name()
        if isinstance(actor, unreal.M80House) or "RoadSpline" in name or "Landscape" in name:
            continue
        if not isinstance(actor, unreal.StaticMeshActor) and "_C" not in name:
            continue
        origin, extent = actor.get_actor_bounds(False)
        if 300 < max(extent.x, extent.y) < 15000 and extent.z > 250:
            # Shrink a little: OSM outlines rarely match the modelled walls exactly.
            boxes.append((origin.x - extent.x * 0.9, origin.y - extent.y * 0.9, origin.x + extent.x * 0.9, origin.y + extent.y * 0.9, actor.get_actor_label()))
    return boxes


def prepare_map():
    if REBUILD_MAP or not unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
        if not unreal.EditorLoadingAndSavingUtils.save_map(m80_seq.editor_world(), MAP):
            raise RuntimeError("Could not save " + MAP)
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    opened = m80_seq.editor_world().get_path_name()
    if not opened.startswith(MAP):
        raise RuntimeError("Expected {} to be open, got {}".format(MAP, opened))


def remove_old(world):
    removed = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        name = actor.get_class().get_name()
        mesh_names = []
        if isinstance(actor, unreal.StaticMeshActor):
            mesh = actor.static_mesh_component.get_editor_property("static_mesh")
            mesh_names.append(mesh.get_name() if mesh else "")
        if any(t in name for t in OLD_CLASSES) or any(m in OLD_MESHES for m in mesh_names):
            removed.append(actor.get_actor_label())
            actor.destroy_actor()
    return removed


def run():
    report = {"radius_m": "all" if RADIUS == float("inf") else RADIUS / 100, "keep_existing": KEEP_EXISTING}
    prepare_map()
    yield 60
    world = m80_seq.editor_world()
    report["removed"] = remove_old(world)
    boxes = landmark_boxes(world)
    report["landmarks"] = [b[4] for b in boxes]

    cx, cy = default_center()
    if os.environ.get("M80_DISTRICT_CENTER"):
        cx, cy = (float(v) for v in os.environ["M80_DISTRICT_CENTER"].split(","))
    report["center"] = [cx, cy]
    styles = {name: unreal.load_asset(STYLE_DIR + name) for name in STYLES}
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    existing = {a.get_editor_property("lot_id"): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House)}

    houses, skipped, kept, not_houses = [], [], [], []
    remaining = 0
    plan.sort(key=lambda l: math.hypot(l["center_cm"][0] - cx, l["center_cm"][1] - cy))
    t0 = time.time()
    for lot in plan:
        x, y, z = lot["center_cm"]
        if math.hypot(x - cx, y - cy) > RADIUS:
            continue
        if KEEP_EXISTING and lot["id"] in existing:
            kept.append(existing[lot["id"]])
            continue
        tags = lot.get("tags") or {}
        if isinstance(tags, dict) and tags.get("building") in SKIP_TAGS:
            not_houses.append(lot["id"])
            continue
        if any(b[0] < x < b[2] and b[1] < y < b[3] for b in boxes):
            skipped.append(lot["id"])
            continue
        if unreal.M80ExclusionZone.is_point_excluded(world, unreal.Vector(x, y, z)) and lot["id"] not in existing:
            skipped.append(lot["id"])  # area reserved for hand-made buildings
            continue
        if BATCH and len(houses) >= BATCH and lot["id"] not in existing:
            remaining += 1
            continue
        rng = random.Random(int(lot["id"]))
        actor = existing.get(lot["id"]) or unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
            unreal.M80House, unreal.Vector(x, y, z))
        actor.set_actor_label("Casa_" + lot["id"])
        actor.set_folder_path("Case")
        actor.set_editor_property("lot_id", lot["id"])
        actor.set_editor_property("live_rebuild", False)
        actor.set_footprint_world([unreal.Vector(p[0], p[1], z) for p in lot["ring_cm"]])
        params = actor.get_editor_property("house")
        params.set_editor_property("style", styles[pick_style(lot, rng)])
        params.set_editor_property("alternative_styles", [s for s in styles.values() if s])
        params.set_editor_property("floors", max(1, min(5, round((lot.get("height_m", 7) - 1.0) / 3.2))))
        params.set_editor_property("seed", int(lot["id"]) % 100000)
        params.set_editor_property("decay", rng.uniform(0.15, 0.7))
        roll = rng.random()
        params.set_editor_property("roof_type", unreal.M80RoofType.GABLE if roll < 0.55 else unreal.M80RoofType.TERRACE if roll < 0.85 else unreal.M80RoofType.SHED)
        params.set_editor_property("front_edge", int(lot.get("front_edge", -1)) if lot.get("front_edge") is not None else -1)
        actor.set_editor_property("house", params)
        houses.append(actor)
    report["spawn_seconds"] = round(time.time() - t0, 1)
    report["kept_existing"] = len(kept)
    report["remaining"] = remaining
    report["skipped_not_houses"] = len(not_houses)
    yield 5

    # Existing houses next to the new ones: rebuilt as they are, to see their new neighbours.
    new_xy = [(a.get_actor_location().x, a.get_actor_location().y) for a in houses]
    border = []
    if KEEP_EXISTING and new_xy:
        cell = NEIGHBOUR_CM
        grid = {}
        for x, y in new_xy:
            grid.setdefault((int(x // cell), int(y // cell)), []).append((x, y))
        for a in kept:
            loc = a.get_actor_location()
            gx, gy = int(loc.x // cell), int(loc.y // cell)
            near = any(math.hypot(loc.x - x, loc.y - y) < cell
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1) for x, y in grid.get((gx + dx, gy + dy), []))
            if near:
                border.append(a)
    report["existing_rebuilt_as_neighbours"] = len(border)
    for actor in border:
        actor.set_editor_property("live_rebuild", False)

    # Two passes: the second one sees every neighbour, so shared walls are found.
    t0 = time.time()
    for _ in range(2):
        for i, actor in enumerate(houses + border):
            actor.rebuild()
            if i % 40 == 39:
                yield 1
    report["build_seconds_two_passes"] = round(time.time() - t0, 1)
    for actor in houses + border:
        actor.set_editor_property("live_rebuild", True)
    if BAKE:
        t0 = time.time()
        baked = 0
        for i, actor in enumerate(houses + border):
            if unreal.M80EditorLibrary.bake_house(actor, BAKE_FOLDER, True):
                baked += 1
            if i % 10 == 9:
                unreal.SystemLibrary.collect_garbage()
                yield 1
        unreal.EditorAssetLibrary.save_directory(BAKE_FOLDER, only_if_is_dirty=True, recursive=True)
        report["baked"] = baked
        report["bake_seconds"] = round(time.time() - t0, 1)
    report["houses"] = len(houses)
    report["skipped_inside_landmarks"] = skipped
    report["units"] = sum(a.get_editor_property("unit_count") for a in houses)
    report["triangles"] = sum(a.get_editor_property("shell").get_dynamic_mesh().get_triangle_count() for a in houses)
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
