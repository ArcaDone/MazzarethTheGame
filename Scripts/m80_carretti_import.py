"""Imports the four soapbox carts prepared by Research/Mazzarino80/Blender/m80_carretti_gioco.py
(Saved/Mazzarino80/Import/out/Carretti) and the rider's pose on each.

- /Game/Mazzarino80/Vehicles/Carretti/Carretto<Key>/SK_M80_Carretto<Key>: skeletal mesh (Root, Steer, wheels, Sella,
  Mano_L/R, Piede_L/R), a box on Root for physics, 3 LODs; materials as instances of the vehicles' masters
  (M_M80_Veicolo), textures in /Game/Mazzarino80/Vehicles/Carretti/Textures.
- /Game/Mazzarino80/Player/Anim/A_M80_Carretto_<Key>: the rider's pose on the UEFN mannequin skeleton.
The drivable classes are AM80CarrettoCuscinetti / Triangolo / Cassetta / Persiana (MazzarinoVehicles).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_carretti_import.py
Report: Saved/Mazzarino80/Import/carretti_report.json
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Import/out/Carretti"
OUT = ROOT / "Saved/Mazzarino80/Import/carretti_report.json"
KEYS = ["Cuscinetti", "Triangolo", "Cassetta", "Persiana"]
FOLDER = "/Game/Mazzarino80/Vehicles/Carretti"
TEXTURES = FOLDER + "/Textures"
ANIM = "/Game/Mazzarino80/Player/Anim"
SKELETON = "/Game/Characters/UEFN_Mannequin/Meshes/SK_UEFN_Mannequin"
MASTER = "/Game/Mazzarino80/Vehicles/Materials/M_M80_Veicolo"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


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


def texture(file):
    """Named by content: the same wood used by two carts is imported once."""
    digest = hashlib.md5(Path(file).read_bytes()).hexdigest()[:8]
    base = re.sub(r"^T_[^_]+_", "", os.path.splitext(os.path.basename(file))[0])[:40]
    name = "T_M80_%s_%s" % (base, digest)
    if EAL.does_asset_exist(TEXTURES + "/" + name):
        return unreal.load_asset(TEXTURES + "/" + name)
    tex = task(file, TEXTURES, name, None)
    if tex:
        tex.set_editor_property("virtual_texture_streaming", False)
        EAL.save_loaded_asset(tex)
    return tex


def instances(key, info, folder):
    master = unreal.load_asset(MASTER)
    out = {}
    for blender_name, d in info["materials"].items():
        name = "MI_M80_Carretto%s_%s" % (key, d["slot"])
        path = folder + "/Materials/" + name
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
            name, folder + "/Materials", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, master)
        c = d.get("color") or [0.5, 0.5, 0.5]
        MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(c[0], c[1], c[2], 1))
        MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", max(0.05, min(0.95, d.get("roughness", 0.8))))
        MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", max(0.0, min(1.0, d.get("metallic", 0.0))))
        if d.get("base_tex"):
            tex = texture(SRC / "Textures" / d["base_tex"])
            if tex:
                MEL.set_material_instance_texture_parameter_value(mi, "TexColore", tex)
        EAL.save_loaded_asset(mi)
        out[norm(blender_name)] = mi
        out[norm(d["slot"])] = mi
    return out


def cart(key):
    info = json.loads((SRC / ("Carretto%s.json" % key)).read_text(encoding="utf-8"))
    folder = "%s/Carretto%s" % (FOLDER, key)
    mis = instances(key, info, folder)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("create_physics_asset", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
    mesh = task(SRC / ("Carretto%s.fbx" % key), folder, "SK_M80_Carretto" + key, ui)
    if not mesh:
        return {"error": "import failed"}
    r = {}
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
    r["missing_materials"] = missing
    # One box for the body (the parts on Root), clear of the road by most of a wheel radius.
    b = info["body_box_cm"]
    wr = min(w["radius_cm"] for w in info["wheels"].values())
    lo, hi = unreal.Vector(b[0], -b[4], max(b[2], 0.8 * wr)), unreal.Vector(b[3], -b[1], b[5])
    r["physics"] = unreal.M80EditorLibrary.make_vehicle_physics_asset(mesh, "Root", lo, hi, b[5], 0.55)
    sk = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    r["lods"] = sk.regenerate_lod(mesh, 3, True, False)
    EAL.save_loaded_asset(mesh)
    pa = unreal.load_asset(folder + "/SK_M80_Carretto%s_PhysicsAsset" % key)
    if pa:
        EAL.save_loaded_asset(pa)
    # The rider's pose, on the player's skeleton.
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
    anim = task(SRC / ("A_M80_Carretto_%s.fbx" % key), ANIM, "A_M80_Carretto_" + key, ui)
    r["pose"] = anim.get_path_name() if anim else None
    if anim:
        r["pose_frames"] = unreal.AnimationLibrary.get_num_frames(anim)
    return r


def run():
    report = {}
    yield 5
    for key in KEYS:
        report[key] = cart(key)
        yield 5
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
