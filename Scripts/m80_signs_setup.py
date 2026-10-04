"""Imports the Blender road signs and street plaques and places them in a houses map (houses V3, step 11).

Sources: Research/Mazzarino80/Blender (M80_Signs.fbx from m80_signs_blender.py, textures from
m80_signs_textures.py) and Research/Mazzarino80/streets_world.json (m80_streets_world.py).
- /Game/Mazzarino80/Kit/Signs: meshes, M_M80_Sign + instances, sign and plaque textures.
- Placement: a marble plaque with the real street name on the front corner of every house near a
  named street (one per street every ~25 m), and pole signs at some house corners (one-way streets
  get "senso unico"/"senso vietato", the others "divieto di sosta", "stop", "precedenza").
  Placed actors are tagged M80Sign and replaced on every run.
Env: M80_SIGNS_MAP (default the 18-house test map), M80_SIGNS_SKIP_IMPORT=1.
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
SRC = ROOT / "Research/Mazzarino80/Blender"
KIT = "/Game/Mazzarino80/Kit/Signs"
MAP = os.environ.get("M80_SIGNS_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2")
REPORT = ROOT / "Saved/Mazzarino80/HousesV2/signs_report.json"
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
SIGNS = ["Stop", "Yield", "NoParking", "NoEntry", "NoTransit", "OneWay"]


def import_files(files, dest, options=None):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(f))
        t.set_editor_property("destination_path", dest)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", True)
        if options:
            t.set_editor_property("options", options)
        tasks.append(t)
    TOOLS.import_asset_tasks(tasks)


def master():
    path = KIT + "/M_M80_Sign"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    m = TOOLS.create_asset("M_M80_Sign", KIT, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_nanite", True)
    tex = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0)
    tex.set_editor_property("parameter_name", "Face")
    tex.set_editor_property("texture", unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture"))
    tint = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -600, 250)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 50)
    MEL.connect_material_expressions(tex, "RGB", mul, "A")
    MEL.connect_material_expressions(tint, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for name, value, prop, y in (("Roughness", 0.6, unreal.MaterialProperty.MP_ROUGHNESS, 350), ("Metallic", 0.0, unreal.MaterialProperty.MP_METALLIC, 450)):
        s = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -300, y)
        s.set_editor_property("parameter_name", name)
        s.set_editor_property("default_value", value)
        MEL.connect_material_property(s, "", prop)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def instance(name, parent, texture=None, scalars=None, tint=None):
    path = KIT + "/Materials/" + name
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        name, KIT + "/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    if texture:
        MEL.set_material_instance_texture_parameter_value(mi, "Face", texture)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    if tint:
        MEL.set_material_instance_vector_parameter_value(mi, "Tint", tint)
    EAL.save_loaded_asset(mi)
    return mi


def import_all(report):
    fbx = unreal.FbxImportUI()
    fbx.set_editor_property("import_mesh", True)
    fbx.set_editor_property("import_materials", False)
    fbx.set_editor_property("import_textures", False)
    fbx.set_editor_property("import_as_skeletal", False)
    fbx.static_mesh_import_data.set_editor_property("combine_meshes", False)
    fbx.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    import_files([SRC / "M80_Signs.fbx"], KIT, fbx)
    import_files(sorted((SRC / "Textures").glob("T_M80_Sign_*.png")), KIT + "/Textures")
    import_files(sorted((SRC / "Textures/Plaques").glob("*.jpg")), KIT + "/Plaques")
    for path in EAL.list_assets(KIT + "/Plaques", recursive=False) + EAL.list_assets(KIT + "/Textures", recursive=False):
        tex = unreal.load_asset(path)
        if isinstance(tex, unreal.Texture2D):
            tex.set_editor_property("max_texture_size", 256)
            EAL.save_loaded_asset(tex)
    m = master()
    metal = instance("MI_M80_SignMetal", m, scalars={"Roughness": 0.45, "Metallic": 0.85}, tint=unreal.LinearColor(0.42, 0.42, 0.40, 1))
    stone = instance("MI_M80_PlaqueStone", m, scalars={"Roughness": 0.55}, tint=unreal.LinearColor(0.78, 0.75, 0.68, 1))
    for s in SIGNS:
        mesh = unreal.load_asset(KIT + "/SM_M80_Sign_" + s)
        if not mesh:
            report.setdefault("missing", []).append(s)
            continue
        face = instance("MI_M80_SignFace_" + s, m, unreal.load_asset(KIT + "/Textures/T_M80_Sign_" + s), {"Roughness": 0.5})
        mesh.set_material(0, face)
        mesh.set_material(1, metal)
        EAL.save_loaded_asset(mesh)
    plaque = unreal.load_asset(KIT + "/SM_M80_StreetPlaque")
    plaque.set_material(1, stone)
    EAL.save_loaded_asset(plaque)


def front_axis(mesh):
    """Unit vector the printed face looks at, in mesh space (the plate is the thinnest, farthest part)."""
    box = mesh.get_bounding_box()
    ext = (box.max.x - box.min.x, box.max.y - box.min.y)
    if ext[0] < ext[1]:
        return (-1.0, 0.0) if abs(box.min.x) > abs(box.max.x) else (1.0, 0.0)
    return (0.0, -1.0) if abs(box.min.y) > abs(box.max.y) else (0.0, 1.0)


def yaw_facing(mesh, nx, ny):
    fx, fy = front_axis(mesh)
    return math.degrees(math.atan2(ny, nx) - math.atan2(fy, fx))


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def ground_z(world, x, y, guess, ignore):
    result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, guess + 3000), unreal.Vector(x, y, guess - 3000),
                                                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
    hit = result[1] if isinstance(result, tuple) else result
    f = hit.to_tuple() if hit else None
    return f[5].z if f and f[0] else guess


def run():
    report = {}
    if os.environ.get("M80_SIGNS_SKIP_IMPORT") != "1":
        import_all(report)
        yield 30
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actors.get_all_level_actors():
        if a.actor_has_tag("M80Sign"):
            a.destroy_actor()
    streets = json.loads((ROOT / "Research/Mazzarino80/streets_world.json").read_text(encoding="utf-8"))["streets"]
    plaques = json.loads((SRC / "Textures/Plaques/plaques.json").read_text(encoding="utf-8"))
    m = master()
    plaque_mesh = unreal.load_asset(KIT + "/SM_M80_StreetPlaque")
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    ignore = houses + []
    rnd = random.Random(7)
    placed_plaques, placed_signs = [], []

    def spawn(mesh, loc, yaw, label, material=None):
        a = actors.spawn_actor_from_object(mesh, loc, unreal.Rotator(0, 0, yaw))
        a.set_actor_label(label)
        a.tags = [unreal.Name("M80Sign")]
        a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
        if material:
            a.static_mesh_component.set_material(0, material)
        a.set_folder_path("Segnaletica")
        return a

    for house in houses:
        if house.is_excluded():
            continue
        poly = [(q.x, q.y) for q in house.get_footprint_world2d()]
        i = house.get_editor_property("resolved_front_edge") % len(poly)
        a, b = poly[i], poly[(i + 1) % len(poly)]
        length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        nx, ny = uy, -ux  # outward for a counter-clockwise footprint
        mid = ((a[0] + b[0]) / 2 + nx * 300, (a[1] + b[1]) / 2 + ny * 300)
        best = None
        for s in streets:
            pts = s["points_cm"]
            d = min(seg_dist(mid, pts[k], pts[k + 1]) for k in range(len(pts) - 1))
            if d < 1500 and (best is None or d < best[0]):
                best = (d, s)
        if not best:
            continue
        street = best[1]
        gz = ground_z(world, a[0] + nx * 100, a[1] + ny * 100, house.get_actor_location().z, ignore)
        # Marble plaque near the corner, under the first-floor windows.
        corner = (a[0] + ux * 45, a[1] + uy * 45)
        name = street["name"]
        if name in plaques and all(n != name or math.hypot(p[0] - corner[0], p[1] - corner[1]) > 2500 for n, p in placed_plaques):
            tex = unreal.load_asset(KIT + "/Plaques/" + plaques[name])
            mi = instance("MI_M80_Plaque_" + plaques[name][len("T_M80_Plaque_"):], m, tex, {"Roughness": 0.45})
            spawn(plaque_mesh, unreal.Vector(corner[0] + nx * 0.5, corner[1] + ny * 0.5, gz + 290), yaw_facing(plaque_mesh, nx, ny),
                  "Targa_" + plaques[name][len("T_M80_Plaque_"):], mi)
            placed_plaques.append((name, corner))
        # Pole sign at the far corner of some houses, facing the traffic along the street.
        if rnd.random() < 0.45:
            kind = rnd.choice(["OneWay", "NoEntry"]) if street.get("oneway") else rnd.choice(["NoParking", "NoParking", "Stop", "Yield", "NoTransit"])
            pos = (b[0] - ux * 35 + nx * 45, b[1] - uy * 35 + ny * 45)
            if all(math.hypot(p[0] - pos[0], p[1] - pos[1]) > 1500 for p in placed_signs):
                mesh = unreal.load_asset(KIT + "/SM_M80_Sign_" + kind)
                sgz = ground_z(world, pos[0], pos[1], gz, ignore)
                spawn(mesh, unreal.Vector(pos[0], pos[1], sgz - 5), yaw_facing(mesh, ux, uy) + rnd.uniform(-6, 6), "Cartello_" + kind)
                placed_signs.append(pos)
    report["plaques"] = len(placed_plaques)
    report["signs"] = len(placed_signs)
    report["streets"] = sorted({n for n, _ in placed_plaques})
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    yield 10


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
