"""Builds the test map for the new procedural houses (AM80House).

1. Creates or updates the four style assets (Style 01-04 boards).
2. Duplicates the 18-house sample map without the old generator's houses.
3. Spawns one AM80House per lot of Buildings_Test18.json and rebuilds them twice
   (the second pass sees the neighbours, so shared walls are detected).
4. Saves the map and captures the same views used for the baseline.

Env: M80_V2_CAPTURE=0 skips screenshots, M80_V2_REBUILD_MAP=1 recreates the map.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SOURCE_MAP = "/Game/Levels/Mazzarino80_CaseStoriche_Campione"
MAP = "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2"
STYLE_DIR = "/Game/Mazzarino80/Houses/Styles"
CATALOG = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18.json"
OUT_DIR = ROOT / "Saved/Mazzarino80/HousesV2"
REPORT = OUT_DIR / "setup_report.json"
CAPTURE = os.environ.get("M80_V2_CAPTURE", "1") != "0"
REBUILD_MAP = os.environ.get("M80_V2_REBUILD_MAP", "0") == "1"
OLD_CLASSES = ("MazzarinoProceduralBuilding", "MazzarinoHistoricBuilding", "MazzarinoBuilding", "BP_ProceduralBuilding")

MAT = "/Game/Mazzarino80/Historic/Materials/"
PLACEHOLDER_MATERIALS = {
    "ashlar_material": MAT + "M80_Pietra_esposta",
    "rubble_material": MAT + "M80_Muratura_locale_0",
    "plaster_material": MAT + "M80_Calce_consumata_0",
    "plaster_worn_material": MAT + "M80_Calce_consumata_3",
    "trim_material": MAT + "M80_Pietra_modesta",
    "roof_material": MAT + "M80_Coppi_vecchi",
    "terrace_material": MAT + "M80_Terrazza_calce",
    "wood_material": MAT + "M80_Legno_persiane_0",
    "glass_material": MAT + "M80_Vetro_ombra",
    "iron_material": MAT + "M80_Ferro_ossidato",
    "raw_wall_material": MAT + "M80_Muratura_locale_1",
}
PROPS = ["/Game/Mazzarino80/ReuseKit/Modules/SM_M80_PROP__PottedPlant_Small_01"]

# Rules per style, from the reference boards.
STYLES = {
    "DA_M80Style_01_PopolarePietra": dict(
        finish="ASHLAR", corner="QUOINS", bay=300, balcony=0.35, shutters=0.9, open_=0.6, roller=0.0, arch=0.5,
        garage=0.05, ornate=False, small_top=False, string=True, plinth=70, cornice_h=30, cornice_p=24, pitch=21, overhang=30),
    "DA_M80Style_02_PalazzoUrbano": dict(
        finish="ASHLAR", corner="PILASTER", bay=330, balcony=0.7, shutters=0.95, open_=0.55, roller=0.0, arch=0.85,
        garage=0.0, ornate=True, small_top=True, string=True, plinth=85, cornice_h=42, cornice_p=34, pitch=20, overhang=38),
    "DA_M80Style_03_Intonacata5070": dict(
        finish="PLASTER_WORN", corner="NONE", bay=310, balcony=0.5, shutters=0.7, open_=0.4, roller=0.45, arch=0.1,
        garage=0.35, ornate=False, small_top=False, string=False, plinth=55, cornice_h=22, cornice_p=16, pitch=18, overhang=26),
    "DA_M80Style_04_CasaPovera": dict(
        finish="RUBBLE", corner="QUOINS", bay=290, balcony=0.25, shutters=0.85, open_=0.5, roller=0.0, arch=0.3,
        garage=0.0, ornate=False, small_top=False, string=False, plinth=45, cornice_h=20, cornice_p=14, pitch=23, overhang=24),
}
FAMILY_STYLE = {
    "PALAZZETTO": "DA_M80Style_02_PalazzoUrbano",
    "EXTENDED": "DA_M80Style_03_Intonacata5070",
    "CORNER": "DA_M80Style_01_PopolarePietra",
    "COURTYARD": "DA_M80Style_01_PopolarePietra",
    "NARROW": "DA_M80Style_03_Intonacata5070",
    "POPULAR": "DA_M80Style_04_CasaPovera",
}
WALL_TINTS = [unreal.LinearColor(1, 1, 1, 1), unreal.LinearColor(1.0, 0.93, 0.82, 1), unreal.LinearColor(0.95, 0.85, 0.7, 1),
              unreal.LinearColor(1.0, 0.8, 0.68, 1), unreal.LinearColor(0.9, 0.9, 0.86, 1)]
WOOD_TINTS = [unreal.LinearColor(0.16, 0.30, 0.20, 1), unreal.LinearColor(0.25, 0.18, 0.12, 1), unreal.LinearColor(0.20, 0.32, 0.30, 1),
              unreal.LinearColor(0.35, 0.33, 0.30, 1)]


def load(path):
    asset = unreal.load_asset(path)
    if not asset:
        unreal.log_warning("M80 missing asset " + path)
    return asset


def make_style(name, spec):
    path = STYLE_DIR + "/" + name
    style = unreal.load_asset(path)
    if not style:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.M80HouseStyle)
        style = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, STYLE_DIR, unreal.M80HouseStyle, factory)
    rules = style.get_editor_property("rules")
    values = {
        "bay_width": spec["bay"], "balcony_chance": spec["balcony"], "shutter_chance": spec["shutters"],
        "shutter_open_chance": spec["open_"], "roller_shutter_chance": spec["roller"], "arched_door_chance": spec["arch"],
        "garage_chance": spec["garage"], "ornate_corbels": spec["ornate"], "small_top_windows": spec["small_top"],
        "string_course": spec["string"], "plinth_height": spec["plinth"], "cornice_height": spec["cornice_h"],
        "cornice_projection": spec["cornice_p"], "roof_pitch": spec["pitch"], "eave_overhang": spec["overhang"],
        "corner_style": getattr(unreal.M80CornerStyle, spec["corner"]),
    }
    for key, value in values.items():
        rules.set_editor_property(key, value)
    style.set_editor_property("rules", rules)
    style.set_editor_property("default_finish", getattr(unreal.M80WallFinish, spec["finish"]))
    style.set_editor_property("wall_tints", WALL_TINTS)
    style.set_editor_property("wood_tints", WOOD_TINTS)
    for prop, mat_path in PLACEHOLDER_MATERIALS.items():
        # Keep materials already assigned (e.g. the master material instances).
        if not style.get_editor_property(prop):
            style.set_editor_property(prop, load(mat_path))
    style.set_editor_property("prop_meshes", [m for m in (load(p) for p in PROPS) if m])
    unreal.EditorAssetLibrary.save_loaded_asset(style)
    return style


def prepare_map():
    """Opens the test map, creating it as a "save as" copy of the sample on first use.

    Duplicating a map asset in the background leaves its world referenced and the next
    map load fails with a world leak, so the copy is made from the open editor world.
    """
    if REBUILD_MAP or not unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
        world = m80_seq.editor_world()
        if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
            raise RuntimeError("Could not save " + MAP)
    # save_map writes a copy but keeps the source open: always reopen the test map,
    # so later edits and saves can never touch the original sample.
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    opened = m80_seq.editor_world().get_path_name()
    if not opened.startswith(MAP):
        raise RuntimeError("Expected {} to be open, got {}".format(MAP, opened))


def remove_old_houses(world):
    removed = 0
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        name = actor.get_class().get_name()
        if any(token in name for token in OLD_CLASSES):
            actor.destroy_actor()
            removed += 1
    return removed


def spawn_houses(world, styles):
    lots = json.loads(CATALOG.read_text(encoding="utf-8"))["buildings"]
    existing = {a.get_editor_property("lot_id"): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House)}
    houses = []
    for lot in lots:
        actor = existing.get(lot["building_id"])
        if not actor:
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.M80House, unreal.Vector(*lot["position_world_cm"]))
        actor.set_actor_label("Casa_" + lot["building_id"])
        actor.set_editor_property("lot_id", lot["building_id"])
        actor.set_editor_property("live_rebuild", False)
        actor.set_footprint_world([unreal.Vector(*p) for p in lot["footprint_world_cm"]])
        params = actor.get_editor_property("house")
        params.set_editor_property("style", styles[FAMILY_STYLE.get(lot["family"], "DA_M80Style_01_PopolarePietra")])
        params.set_editor_property("floors", int(lot["primary_floors"]))
        params.set_editor_property("seed", int(lot["variation_seed"]))
        params.set_editor_property("decay", float(lot.get("decay", 0.35)))
        params.set_editor_property("roof_type", unreal.M80RoofType.TERRACE if lot["roof_type"] == "Terrace" else unreal.M80RoofType.GABLE)
        if lot.get("facade_type") == "ExposedStone":
            params.set_editor_property("use_style_finish", False)
            params.set_editor_property("finish", unreal.M80WallFinish.ASHLAR)
        actor.set_editor_property("house", params)
        houses.append(actor)
    for _ in range(2):
        for actor in houses:
            actor.rebuild()
    for actor in houses:
        actor.set_editor_property("live_rebuild", True)
    return houses


def look_at(eye, target):
    d = [t - e for t, e in zip(target, eye)]
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return unreal.Vector(*eye), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def views(houses):
    """Overview plus one street view per house, in front of its resolved main facade."""
    lots = json.loads(CATALOG.read_text(encoding="utf-8"))["buildings"]
    out = []
    pts = [p for b in lots for p in b["footprint_world_cm"]]
    cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    cz = sum(p[2] for p in pts) / len(pts)
    out.append(("Overview", *look_at((cx - 9000, cy, cz + 7000), (cx, cy, cz))))
    out.append(("Overview_Low", *look_at((cx - 5200, cy - 3000, cz + 1800), (cx, cy, cz + 300))))
    for h in houses:
        fp = h.get_footprint_world2d() if hasattr(h, "get_footprint_world2d") else h.get_footprint_world_2d()
        poly = [(q.x, q.y) for q in fp]
        i = h.get_editor_property("resolved_front_edge") % len(poly)
        a, c = poly[i], poly[(i + 1) % len(poly)]
        mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
        n = math.hypot(c[0] - a[0], c[1] - a[1]) or 1.0
        # CCW footprint: the outward normal of edge (dx, dy) is (dy, -dx).
        ox, oy = (c[1] - a[1]) / n, -(c[0] - a[0]) / n
        z = h.get_actor_location().z
        dist = min(1100, max(650, n * 0.6))
        out.append(("Street_" + h.get_editor_property("lot_id"), *look_at((mx + ox * dist, my + oy * dist, z + 170), (mx, my, z + 420))))
    return out


LIGHT_CLASSES = ("DirectionalLight", "SkyLight", "SkyAtmosphere", "ExponentialHeightFog", "VolumetricCloud", "HDRIBackdrop", "PostProcessVolume")


def lighting_report(world):
    found = {}
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        name = actor.get_class().get_name()
        for cls in LIGHT_CLASSES:
            if cls in name:
                found[cls] = found.get(cls, 0) + 1
    return found


def ensure_lighting(world, found):
    """The test map must be readable: add sun, sky and fog when the copy has none."""
    added = []
    if not found.get("DirectionalLight"):
        sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(78000, 11800, 30000), unreal.Rotator(roll=0, pitch=-42, yaw=135))
        sun.get_editor_property("light_component").set_editor_property("atmosphere_sun_light", True)
        sun.get_editor_property("light_component").set_editor_property("intensity", 9.0)
        added.append("DirectionalLight")
    if not found.get("SkyAtmosphere"):
        unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(78000, 11800, 0))
        added.append("SkyAtmosphere")
    if not found.get("SkyLight") and not found.get("HDRIBackdrop"):
        sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(78000, 11800, 20000))
        sky.get_editor_property("light_component").set_editor_property("real_time_capture", True)
        added.append("SkyLight")
    if not found.get("ExponentialHeightFog"):
        unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(78000, 11800, 16000))
        added.append("ExponentialHeightFog")
    return added


def run():
    report = {}
    styles = {name: make_style(name, spec) for name, spec in STYLES.items()}
    prepare_map()
    yield 30
    world = m80_seq.editor_world()
    report["removed_old_actors"] = remove_old_houses(world)
    report["lighting_found"] = lighting_report(world)
    report["lighting_added"] = ensure_lighting(world, report["lighting_found"])
    t0 = time.time()
    houses = spawn_houses(world, styles)
    report["build_seconds_two_passes"] = round(time.time() - t0, 2)
    report["houses"] = {h.get_editor_property("lot_id"): h.get_editor_property("build_info") for h in houses}
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    yield 60
    if CAPTURE:
        # Let shaders and texture streaming settle, then render each view twice (the first
        # pass warms streaming for that viewpoint). The capture actor is never saved.
        capture = m80_seq.ViewCapture()
        yield 300
        for name, loc, rot in views(houses):
            target = OUT_DIR / "Views" / (name + ".png")
            m80_seq.set_view(loc, rot)
            capture.capture(loc, rot, target)
            yield 30
            capture.capture(loc, rot, target)
            yield 5
        capture.destroy()
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


m80_seq.Sequencer(run(), quit_when_done=os.environ.get("M80_V2_QUIT", "1") == "1", log_file=str(OUT_DIR / "setup_error.txt"))
