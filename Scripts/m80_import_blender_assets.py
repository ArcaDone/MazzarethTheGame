"""Imports the assets prepared by Research/Mazzarino80/Blender/m80_prepare_vehicle.py
(Saved/Mazzarino80/Import/out/<Key>.fbx + <Key>.json + Textures/) into Unreal.

- Cars (Panda, Fiat127, FiatUno, Golf) and the Vespa: skeletal mesh /Game/Mazzarino80/Vehicles/<Key>/SK_M80_<Key>
  (skeleton Root + Wheel_FL/FR/RL/RR), physics asset of two boxes (UM80EditorLibrary), 3 LODs.
- Vespa: drivable too, skeletal mesh /Game/Mazzarino80/Vehicles/Vespa/SK_M80_Vespa (Root + Wheel_F/Wheel_R).
- Poste: static meshes /Game/Mazzarino80/Buildings/Poste/SM_M80_Poste and SM_M80_Poste_Antenna (Nanite).
- Town buildings: /Game/Mazzarino80/Buildings/<Key>/SM_M80_<Key> (+ pieces) for Comune, ChiesaComune (stand-ins
  for the Comune), Matrice (+ _Interno), Castello, Madonna (every part a mesh of its own); collision = the mesh
  itself, so they can be walked on and entered. Their textures are shared in /Game/Mazzarino80/Buildings/Textures
  (the same Poly Haven stone or marble used by several buildings is imported once).
- Street furniture: /Game/Mazzarino80/Kit/Arredo/SM_M80_Cassonetto and SM_M80_Tombino (box collision).
- Materials: one instance per Blender material on three masters in /Game/Mazzarino80/Vehicles/Materials:
  M_M80_Vernice (car paint, clear coat), M_M80_Veicolo (generic: colour x texture, normal map, emission),
  M_M80_Vetro (glass, translucent). Textures at most 2K, colour ones stored as JPEG.
Env M80_IMPORT_ONLY=Key1,Key2 limits the import; M80_PHYSICS_ONLY=1 only rebuilds the cars' physics assets. Report: Saved/Mazzarino80/Import/import_report.json.
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
SRC = ROOT / "Saved/Mazzarino80/Import/out"
OUT = ROOT / "Saved/Mazzarino80/Import/import_report.json"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MASTERS = "/Game/Mazzarino80/Vehicles/Materials"
CARS = ["Panda", "Fiat127", "FiatUno", "Golf", "Vespa"]   # drivable (the Vespa too: two wheels)
DEST = {k: "/Game/Mazzarino80/Vehicles/" + k for k in CARS}
DEST["Poste"] = "/Game/Mazzarino80/Buildings/Poste"
BUILDINGS = ["Comune", "ChiesaComune", "Matrice", "Castello", "Madonna"]
PROPS = ["Cassonetto", "Tombino"]
for k in BUILDINGS:
    DEST[k] = "/Game/Mazzarino80/Buildings/" + k
for k in PROPS:
    DEST[k] = "/Game/Mazzarino80/Kit/Arredo"
BUILDING_TEXTURES = "/Game/Mazzarino80/Buildings/Textures"
ONLY = [k for k in os.environ.get("M80_IMPORT_ONLY", "").split(",") if k]
PHYSICS_ONLY = os.environ.get("M80_PHYSICS_ONLY", "") == "1"


def norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


# ---------------------------------------------------------------------------------------------
# Master materials

def new_material(name):
    path = MASTERS + "/" + name
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, MASTERS, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("used_with_skeletal_mesh", True)
    m.set_editor_property("used_with_nanite", True)
    return m


def node(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def scalar(m, name, value, x, y):
    return node(m, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value)


def vector(m, name, value, x, y):
    return node(m, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name, default_value=unreal.LinearColor(*value))


def masters():
    # Once made they are kept: the car classes load the meshes at start-up, so the masters are rooted
    # and clearing their nodes would crash the editor. M80_REBUILD_MASTERS=1 rebuilds them anyway.
    names = {"generic": "M_M80_Veicolo", "paint": "M_M80_Vernice", "glass": "M_M80_Vetro"}
    if not os.environ.get("M80_REBUILD_MASTERS") and all(EAL.does_asset_exist(MASTERS + "/" + n) for n in names.values()):
        return {k: unreal.load_asset(MASTERS + "/" + n) for k, n in names.items()}
    white = unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture")
    flat = unreal.load_asset("/Engine/EngineMaterials/DefaultNormal")
    # Generic: colour x texture, metallic, roughness, normal map, emission.
    m = new_material("M_M80_Veicolo")
    col = vector(m, "Colore", (0.5, 0.5, 0.5, 1), -900, 0)
    tex = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 200, parameter_name="TexColore", texture=white)
    mul = node(m, unreal.MaterialExpressionMultiply, -500, 100)
    MEL.connect_material_expressions(col, "", mul, "A")
    MEL.connect_material_expressions(tex, "RGB", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    nm = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 500, parameter_name="TexNormale", texture=flat,
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(scalar(m, "Metallo", 0.0, -500, 300), "", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(scalar(m, "Ruvidita", 0.5, -500, 400), "", unreal.MaterialProperty.MP_ROUGHNESS)
    em = vector(m, "Emissivo", (0, 0, 0, 1), -900, 800)
    emul = node(m, unreal.MaterialExpressionMultiply, -500, 800)
    MEL.connect_material_expressions(em, "", emul, "A")
    MEL.connect_material_expressions(tex, "RGB", emul, "B")
    MEL.connect_material_property(emul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    # Car paint: clear coat over the colour.
    p = new_material("M_M80_Vernice")
    p.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    MEL.connect_material_property(vector(p, "Colore", (0.5, 0.05, 0.05, 1), -600, 0), "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(scalar(p, "Metallo", 0.2, -600, 200), "", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(scalar(p, "Ruvidita", 0.35, -600, 300), "", unreal.MaterialProperty.MP_ROUGHNESS)
    # Clear coat amount and roughness keep their defaults (1.0 and 0.1): Python cannot reach those pins.
    MEL.recompile_material(p)
    EAL.save_loaded_asset(p)
    # Glass: translucent, shiny, both sides.
    g = new_material("M_M80_Vetro")
    g.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    g.set_editor_property("two_sided", True)
    g.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    MEL.connect_material_property(vector(g, "Colore", (0.05, 0.06, 0.06, 1), -600, 0), "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(scalar(g, "Opacita", 0.3, -600, 200), "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(scalar(g, "Ruvidita", 0.03, -600, 300), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(scalar(g, "Metallo", 0.0, -600, 400), "", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(scalar(g, "Specular", 1.0, -600, 500), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(g)
    EAL.save_loaded_asset(g)
    return {"generic": m, "paint": p, "glass": g}


# ---------------------------------------------------------------------------------------------
# Textures and material instances

def import_texture(file, folder, normal, name=None):
    name = name or os.path.splitext(os.path.basename(file))[0]
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", folder)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    TOOLS.import_asset_tasks([t])
    tex = unreal.load_asset(folder + "/" + name)
    if not tex:
        return None
    tex.set_editor_property("virtual_texture_streaming", False)
    if normal:
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    else:
        unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
    EAL.save_loaded_asset(tex)
    return tex


# Textures of all the vehicles in one folder, named by content: the same light or leather texture used by
# several cars is imported once.
SHARED_TEXTURES = MASTERS + "/Textures"


def shared_texture(file, normal, folder):
    digest = hashlib.md5(Path(file).read_bytes()).hexdigest()[:8]
    base = re.sub(r"^T_[^_]+_", "", os.path.splitext(os.path.basename(file))[0])[:48]
    name = "T_M80_%s_%s" % (base, digest)
    path = folder + "/" + name
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    return import_texture(file, folder, normal, name)


def make_instances(key, info, mats):
    folder = DEST[key] + "/Materials"
    texfolder = SHARED_TEXTURES if key in CARS else (BUILDING_TEXTURES if key in BUILDINGS else DEST[key] + "/Textures")
    out = {}
    cache = {}
    for blender_name, d in info["materials"].items():
        kind = d.get("type", "generic")
        parent = mats["paint"] if kind == "paint" else (mats["glass"] if kind == "glass" else mats["generic"])
        name = "MI_M80_%s_%s" % (key, d["slot"])[:60]
        path = folder + "/" + name
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
            name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        c = d.get("color") or [0.5, 0.5, 0.5]
        MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(c[0], c[1], c[2], 1))
        MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", max(0.03, min(0.95, d.get("roughness", 0.5))))
        if kind == "glass":
            MEL.set_material_instance_scalar_parameter_value(mi, "Opacita", max(0.15, min(0.6, d.get("opacity", 1.0) if d.get("opacity", 1.0) < 1 else 0.3)))
        else:
            metal = d.get("metallic", 0.0)
            if kind == "metal":
                metal = max(metal, 0.9)
            MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", max(0.0, min(1.0, metal)))
        if kind != "paint" and kind != "glass":
            for slot, param, normal in (("base_tex", "TexColore", False), ("normal_tex", "TexNormale", True)):
                f = d.get(slot)
                if not f:
                    continue
                if f not in cache:
                    cache[f] = shared_texture(SRC / "Textures" / f, normal, texfolder)
                if cache[f]:
                    MEL.set_material_instance_texture_parameter_value(mi, param, cache[f])
            e = d.get("emissive") or [0, 0, 0]
            if kind == "light" and max(e) < 0.01:
                e = [x * 0.15 for x in c]   # lenses: a faint glow
            MEL.set_material_instance_vector_parameter_value(mi, "Emissivo", unreal.LinearColor(e[0], e[1], e[2], 1))
        EAL.save_loaded_asset(mi)
        out[norm(blender_name)] = mi
        out[norm(d["slot"])] = mi
        # FBX cuts names at ':' ("gloss blue:20:56:176.005" arrives as "176_005").
        out.setdefault(norm(blender_name.split(":")[-1]), mi)
    return out


# ---------------------------------------------------------------------------------------------
# Meshes

def import_fbx(file, folder, name, skeletal):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", skeletal)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("create_physics_asset", False)
    if skeletal:
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        ui.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
    else:
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        ui.static_mesh_import_data.set_editor_property("combine_meshes", True)
        ui.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
        ui.static_mesh_import_data.set_editor_property("build_nanite", True)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", folder)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", ui)
    TOOLS.import_asset_tasks([t])
    return unreal.load_asset(folder + "/" + name)


def assign(mesh, mis, skeletal):
    missing = []
    if skeletal:
        mats = list(mesh.get_editor_property("materials"))
        for i, sm in enumerate(mats):
            slot = str(sm.get_editor_property("material_slot_name"))
            mi = mis.get(norm(slot))
            if mi:
                sm.set_editor_property("material_interface", mi)
                mats[i] = sm
            else:
                missing.append(slot)
        mesh.set_editor_property("materials", mats)
    else:
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(sm.get_editor_property("material_slot_name"))
            mi = mis.get(norm(slot))
            if mi:
                mesh.set_material(i, mi)
            else:
                missing.append(slot)
    return missing


def physics(key, mesh, info):
    """Body of two boxes (lower body and cabin) on the Root bone, saved with the mesh."""
    b = info["body_box_cm"]
    # The box stays clear of the road: its bottom not lower than half a wheel radius.
    wr = min(w["radius_cm"] for w in info["wheels"].values())
    lo, hi = unreal.Vector(b[0], -b[4], max(b[2], 0.5 * wr)), unreal.Vector(b[3], -b[1], b[5])
    ok = unreal.M80EditorLibrary.make_vehicle_physics_asset(mesh, "Root", lo, hi, b[2] + 0.55 * (b[5] - b[2]), 0.55)
    EAL.save_loaded_asset(mesh)
    pa = unreal.load_asset(DEST[key] + "/SK_M80_" + key + "_PhysicsAsset")
    if pa:
        EAL.save_loaded_asset(pa)
    return ok


def collision(key, mesh):
    """Buildings collide with their own triangles (walk on the steps, go inside); furniture with a box."""
    if key in BUILDINGS:
        body = mesh.get_editor_property("body_setup")
        if body:
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    elif key in PROPS:
        sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        sub.remove_collisions(mesh)
        sub.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)


def run():
    report = {}
    mats = None if PHYSICS_ONLY else masters()
    yield 5
    sk = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    for key in CARS + ["Poste"] + BUILDINGS + PROPS:
        if ONLY and key not in ONLY:
            continue
        jf = SRC / (key + ".json")
        if not jf.exists():
            report[key] = "not prepared"
            continue
        info = json.loads(jf.read_text(encoding="utf-8"))
        r = {}
        if PHYSICS_ONLY:
            mesh = unreal.load_asset("%s/SK_M80_%s" % (DEST[key], key)) if key in CARS else None
            if mesh:
                r["physics"] = physics(key, mesh, info)
                report[key] = r
            continue
        mis = make_instances(key, info, mats)
        yield 2
        if key in CARS:
            mesh = import_fbx(SRC / (key + ".fbx"), DEST[key], "SK_M80_" + key, True)
            if not mesh:
                report[key] = "import failed"
                continue
            r["missing_materials"] = assign(mesh, mis, True)
            r["physics"] = physics(key, mesh, info)
            r["lods"] = sk.regenerate_lod(mesh, 3, True, False)
            r["bones"] = [str(mesh.get_editor_property("skeleton").get_name())]
            EAL.save_loaded_asset(mesh)
            r["verts"] = [sk.get_num_verts(mesh, i) for i in range(sk.get_lod_count(mesh))]
        else:
            names = [key] + [key + "_" + p for p in info.get("pieces", {})]
            for n in names:
                mesh = import_fbx(SRC / (n + ".fbx"), DEST[key], "SM_M80_" + n, False)
                if not mesh:
                    r[n] = "import failed"
                    continue
                r[n] = {"missing_materials": assign(mesh, mis, False)}
                collision(key, mesh)
                EAL.save_loaded_asset(mesh)
                yield 1
            if info.get("pieces"):
                r["pieces_offset_cm"] = {k: v["offset_cm"] for k, v in info["pieces"].items()}
        report[key] = r
        yield 5
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
