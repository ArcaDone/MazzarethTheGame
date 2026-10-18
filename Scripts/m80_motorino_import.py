"""Imports the Piaggio Si prepared by Research/Mazzarino80/Blender/m80_motorino_gioco.py (Saved/Mazzarino80/Import/out/Motorino)
and its rider's clips, and puts it in the test maps.

- /Game/Mazzarino80/Vehicles/PiaggioSi/SK_M80_PiaggioSi: skeletal mesh (Root, Steer along the raked fork, Wheel_F/R, Sella,
  Mano_L/R, Piede_L/R), a box on Root for physics, one LOD (about 25 thousand triangles); materials as instances of
  M_M80_VeicoloPBR (colour, normal map, metal in R and roughness in G of one more map), textures in .../PiaggioSi/Textures.
- /Game/Mazzarino80/Player/Anim/A_M80_Motorino_Guida (riding), _Sale (getting on), _Scende (getting off) on the UEFN
  mannequin skeleton. The drivable class is AM80CarPiaggioSi (MazzarinoVehicles).
- L_M80_ProvaGuida: the Piaggio where the Vespa stood (C_PiaggioSi); L_M80_ProvaAzione: one beside the Fiat 500, facing the
  longest free straight (for Scripts/m80_motorino_test.py).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_motorino_import.py
Env M80_SOLO_MAPPE=1: only the placing in the maps. Report: Saved/Mazzarino80/Import/motorino_report.json
"""
import json
import math
import os
import re
import struct
import sys
import zlib
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Import/out/Motorino"
OUT = ROOT / "Saved/Mazzarino80/Import/motorino_report.json"
KEY = "PiaggioSi"
FOLDER = "/Game/Mazzarino80/Vehicles/" + KEY
ANIM = "/Game/Mazzarino80/Player/Anim"
SKELETON = "/Game/Characters/UEFN_Mannequin/Meshes/SK_UEFN_Mannequin"
MASTER = "/Game/Mazzarino80/Vehicles/Materials/M_M80_VeicoloPBR"
CLIPS = ["A_M80_Motorino_Guida", "A_M80_Motorino_Sale", "A_M80_Motorino_Scende", "A_M80_Motorino_Raccoglie"]
MAP_GUIDA = "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida"
MAP_AZIONE = "/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
V = unreal.Vector
report = {}


def norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def task(file, folder, name, options):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", folder)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    if options:
        t.set_editor_property("options", options)
    TOOLS.import_asset_tasks([t])
    return unreal.load_asset(folder + "/" + name)


def node(m, cls, x, y, **props):
    n = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def white_mask():
    """A 4x4 white map stored as masks (linear): the default of the metal/roughness slot, so the scalars pass through. A
    colour texture there would not compile (the slot samples masks)."""
    path = "/Game/Mazzarino80/Vehicles/Materials/Textures/T_M80_BiancoMaschera"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    png = ROOT / "Saved/Mazzarino80/Import/out/T_M80_BiancoMaschera.png"
    raw = bytes([0] + [255] * 16) * 4   # 4 rows: filter byte, 4 white RGBA pixels
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png.write_bytes(bytes([137, 80, 78, 71, 13, 10, 26, 10]) + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    tex = task(png, path.rsplit("/", 1)[0], path.rsplit("/", 1)[1], None)
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    EAL.save_loaded_asset(tex)
    return tex


def master():
    """Colour x texture, normal map, metal (R) and roughness (G) of a masks map times their scalars. Made once."""
    if EAL.does_asset_exist(MASTER):
        return unreal.load_asset(MASTER)
    m = TOOLS.create_asset(MASTER.rsplit("/", 1)[1], MASTER.rsplit("/", 1)[0], unreal.Material, unreal.MaterialFactoryNew())
    white = unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture")
    flat = unreal.load_asset("/Engine/EngineMaterials/DefaultNormal")
    col = node(m, unreal.MaterialExpressionVectorParameter, -900, 0, parameter_name="Colore", default_value=unreal.LinearColor(1, 1, 1, 1))
    tex = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 200, parameter_name="TexColore", texture=white)
    mul = node(m, unreal.MaterialExpressionMultiply, -500, 100)
    MEL.connect_material_expressions(col, "", mul, "A")
    MEL.connect_material_expressions(tex, "RGB", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    nm = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 500, parameter_name="TexNormale", texture=flat,
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    mr = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 800, parameter_name="TexMetalloRuvidita", texture=white_mask(),
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    met = node(m, unreal.MaterialExpressionScalarParameter, -900, 1050, parameter_name="Metallo", default_value=1.0)
    rough = node(m, unreal.MaterialExpressionScalarParameter, -900, 1150, parameter_name="Ruvidita", default_value=1.0)
    mm = node(m, unreal.MaterialExpressionMultiply, -500, 800)
    MEL.connect_material_expressions(mr, "R", mm, "A")
    MEL.connect_material_expressions(met, "", mm, "B")
    MEL.connect_material_property(mm, "", unreal.MaterialProperty.MP_METALLIC)
    rm = node(m, unreal.MaterialExpressionMultiply, -500, 1000)
    MEL.connect_material_expressions(mr, "G", rm, "A")
    MEL.connect_material_expressions(rough, "", rm, "B")
    MEL.connect_material_property(rm, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def texture(file, kind):
    name = "T_M80_" + os.path.splitext(os.path.basename(file))[0][2:]
    tex = task(file, FOLDER + "/Textures", name, None)
    if not tex:
        return None
    tex.set_editor_property("virtual_texture_streaming", False)
    if kind == "normal":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif kind == "masks":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    else:
        unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
    EAL.save_loaded_asset(tex)
    return tex


def instances(info):
    parent = master()
    out = {}
    for blender_name, d in info["materials"].items():
        name = "MI_M80_%s_%s" % (KEY, d["slot"])
        path = FOLDER + "/Materials/" + name
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
            name, FOLDER + "/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        c = d.get("color") or [1, 1, 1]
        MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(c[0], c[1], c[2], 1))
        MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", float(d.get("metallic", 1.0)))
        MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", float(d.get("roughness", 1.0)))
        for slot, param, kind in (("base_tex", "TexColore", "colour"), ("normal_tex", "TexNormale", "normal"),
                                  ("metal_rough_tex", "TexMetalloRuvidita", "masks")):
            if d.get(slot):
                tex = texture(SRC / "Textures" / d[slot], kind)
                if tex:
                    MEL.set_material_instance_texture_parameter_value(mi, param, tex)
        EAL.save_loaded_asset(mi)
        out[norm(blender_name)] = mi
        out[norm(d["slot"])] = mi
    return out


def moped(info):
    mis = instances(info)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("create_physics_asset", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
    mesh = task(SRC / (KEY + ".fbx"), FOLDER, "SK_M80_" + KEY, ui)
    if not mesh:
        report["error"] = "import failed"
        return
    mats = list(mesh.get_editor_property("materials"))
    missing = []
    for i, sm in enumerate(mats):
        mi = mis.get(norm(str(sm.get_editor_property("material_slot_name"))))
        if mi:
            sm.set_editor_property("material_interface", mi)
            mats[i] = sm
        else:
            missing.append(str(sm.get_editor_property("material_slot_name")))
    mesh.set_editor_property("materials", mats)
    report["missing_materials"] = missing
    # One box for the frame (seat, tank, engine), clear of the road by most of a wheel radius.
    b = info["body_box_cm"]
    wr = min(w["radius_cm"] for w in info["wheels"].values())
    wf, wb = info["wheels"]["F"], info["wheels"]["R"]
    front = max(b[3], wf["centre_cm"][0] + wf["radius_cm"] - 3.0)
    # Behind, only to just past the rear axle and well off the road: the tail (rack, mudguard) under the box struck the road
    # in a wheelie and the knock threw the front over.
    back = wb["centre_cm"][0] - 10.0
    # Narrow (the frame, not the pedals): down on its side it rests on a pedal and the tyres, leaning about 56 degrees, not
    # on the box's edge at 39.
    lo, hi = V(back, -10.0, max(b[2], 0.8 * wr)), V(front, 10.0, b[5])
    report["physics"] = unreal.M80EditorLibrary.make_vehicle_physics_asset(mesh, "Root", lo, hi, b[5], 0.55)
    sk = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    n = sk.get_lod_count(mesh)
    if n > 1:
        sk.remove_lo_ds(mesh, list(range(1, n)))
    report["lods"] = sk.get_lod_count(mesh)
    report["verts"] = sk.get_num_verts(mesh, 0)
    EAL.save_loaded_asset(mesh)
    pa = unreal.load_asset(FOLDER + "/SK_M80_%s_PhysicsAsset" % KEY)
    if pa:
        EAL.save_loaded_asset(pa)


def clips():
    out = {}
    for name in CLIPS:
        ui = unreal.FbxImportUI()
        ui.set_editor_property("import_mesh", False)
        ui.set_editor_property("import_animations", True)
        ui.set_editor_property("import_as_skeletal", True)
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
        ui.set_editor_property("import_materials", False)
        ui.set_editor_property("import_textures", False)
        ui.set_editor_property("skeleton", unreal.load_asset(SKELETON))
        ui.anim_sequence_import_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        ui.anim_sequence_import_data.set_editor_property("remove_redundant_keys", False)
        anim = task(SRC / (name + ".fbx"), ANIM, name, ui)
        out[name] = round(anim.get_play_length(), 2) if anim else None
    report["clips_s"] = out


def ground(world, x, y, z):
    hit = unreal.SystemLibrary.line_trace_single(world, V(x, y, z + 300), V(x, y, z - 600), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                  False, [], unreal.DrawDebugTrace.NONE, True)
    return hit.to_tuple()[4].z if hit and hit.to_tuple()[0] else None


def free_run(world, start, yaw, ignore):
    """Free metres ahead of start (a 70 cm ball 90 cm up: clear of the ground, catching kerbs and walls) towards yaw, up to 60 m."""
    d = V(math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0)
    a = start + V(0, 0, 90)
    hit = unreal.SystemLibrary.sphere_trace_single(world, a, a + d * 6000, 35, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore,
                                                   unreal.DrawDebugTrace.NONE, True)
    t = hit.to_tuple() if hit else None
    return (t[3] / 100.0) if t and t[0] else 60.0


def place(path, label, where):
    unreal.EditorLoadingAndSavingUtils.load_map(path)
    yield 30
    world = m80_seq.editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)):
        if a.get_actor_label() in (label, "C_Vespa"):
            eas.destroy_actor(a)
    loc, yaw = where(world)
    if loc is None:
        report[label + "_" + path] = "no place"
        return
    a = eas.spawn_actor_from_class(unreal.M80CarPiaggioSi, loc, unreal.Rotator(0, 0, yaw))
    a.set_actor_label(label)
    yield 5
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    report[label + " " + path] = {"loc": [round(c) for c in (loc.x, loc.y, loc.z)], "yaw": round(yaw, 1)}
    yield 5


def where_guida(world):
    return V(0, 1050, 70), 0.0   # the start line, where the Vespa was (Scripts/m80_drive_test_level.py)


def where_azione(world):
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80CarFiat500))
    if not cars:
        return None, 0.0
    car = cars[0]
    best = None
    for side in (-350, 350):
        p = car.get_actor_location() + car.get_actor_right_vector() * side
        z = ground(world, p.x, p.y, p.z)
        if z is None:
            continue
        for k in range(16):
            yaw = k * 22.5
            run = free_run(world, V(p.x, p.y, z), yaw, [car])
            if best is None or run > best[0]:
                best = (run, V(p.x, p.y, z + 40), yaw)
    report["azione_free_run_m"] = round(best[0], 1) if best else None
    return (best[1], best[2]) if best else (None, 0.0)


def run():
    info = json.loads((SRC / (KEY + ".json")).read_text(encoding="utf-8"))
    yield 5
    if not os.environ.get("M80_SOLO_MAPPE"):
        moped(info)
        yield 5
        clips()
        yield 5
    for s in place(MAP_GUIDA, "C_PiaggioSi", where_guida):
        yield s
    for s in place(MAP_AZIONE, "C_PiaggioSi", where_azione):
        yield s
    OUT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
