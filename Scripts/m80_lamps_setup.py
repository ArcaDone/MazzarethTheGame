"""Imports the cast-iron street lamps (Research/Mazzarino80/Blender/M80_Lamps.fbx, m80_lamps_blender.py).

- /Game/Mazzarino80/Kit/Lamps: SM_M80_Lampione_Muro and SM_M80_Lampione_Palo (Nanite), their baked
  2K textures (colour, normal, ORM), master M_M80_Lamp + one instance per lamp, and the frosted glass
  M_M80_LampGlass whose glow follows the "Lampioni" value of MPC_M80_Atmosfera (set by the Atmosfera:
  0 by day, 1 at night).
Report: Saved/Mazzarino80/lamps_report.json.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Research/Mazzarino80/Blender"
KIT = "/Game/Mazzarino80/Kit/Lamps"
MPC_PATH = "/Game/Mazzarino80/Sky/MPC_M80_Atmosfera"
REPORT = ROOT / "Saved/Mazzarino80/lamps_report.json"
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
LAMPS = ("Lampione_Muro", "Lampione_Palo")


def import_files(files, options=None):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(f))
        t.set_editor_property("destination_path", KIT)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("automated", True)
        t.set_editor_property("save", False)
        if options:
            t.set_editor_property("options", options)
        tasks.append(t)
    TOOLS.import_asset_tasks(tasks)


def fresh_material(name):
    path = KIT + "/" + name
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    m = TOOLS.create_asset(name, KIT, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_nanite", True)
    return m


def lamp_master():
    m = fresh_material("M_M80_Lamp")
    col = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, -200)
    col.set_editor_property("parameter_name", "Colore")
    nrm = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 100)
    nrm.set_editor_property("parameter_name", "Normali")
    nrm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, 400)
    orm.set_editor_property("parameter_name", "ORM")
    orm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    MEL.connect_material_property(col, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "B", unreal.MaterialProperty.MP_METALLIC)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def glass_material(mpc):
    m = fresh_material("M_M80_LampGlass")
    base = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -500, -200)
    base.set_editor_property("constant", unreal.LinearColor(0.78, 0.76, 0.7, 1))
    MEL.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -500, 0)
    rough.set_editor_property("r", 0.35)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    light = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -700, 200)
    light.set_editor_property("parameter_name", "Colore luce")
    light.set_editor_property("default_value", unreal.LinearColor(1.0, 0.6, 0.28, 1))
    power = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -700, 350)
    power.set_editor_property("parameter_name", "Intensita")
    power.set_editor_property("default_value", 40.0)
    on = MEL.create_material_expression(m, unreal.MaterialExpressionCollectionParameter, -700, 450)
    on.set_editor_property("collection", mpc)
    on.set_editor_property("parameter_name", "Lampioni")
    mul1 = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -450, 250)
    MEL.connect_material_expressions(light, "", mul1, "A")
    MEL.connect_material_expressions(power, "", mul1, "B")
    mul2 = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -250, 300)
    MEL.connect_material_expressions(mul1, "", mul2, "A")
    MEL.connect_material_expressions(on, "", mul2, "B")
    MEL.connect_material_property(mul2, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def ensure_mpc_param(mpc, name):
    params = list(mpc.get_editor_property("scalar_parameters"))
    if any(str(p.get_editor_property("parameter_name")) == name for p in params):
        return False
    p = unreal.CollectionScalarParameter()
    p.set_editor_property("parameter_name", name)
    p.set_editor_property("default_value", 0.0)
    params.append(p)
    mpc.set_editor_property("scalar_parameters", params)
    EAL.save_loaded_asset(mpc)
    return True


def run():
    report = {}
    fbx = unreal.FbxImportUI()
    fbx.set_editor_property("import_mesh", True)
    fbx.set_editor_property("import_materials", False)
    fbx.set_editor_property("import_textures", False)
    fbx.set_editor_property("import_as_skeletal", False)
    fbx.static_mesh_import_data.set_editor_property("combine_meshes", False)
    fbx.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    import_files([SRC / "M80_Lamps.fbx"], fbx)
    tex_dir = SRC / "Textures/Lamps"
    import_files(sorted(tex_dir.glob("T_M80_Lampione_*")))
    yield 10
    for lamp in LAMPS:
        n = unreal.load_asset(f"{KIT}/T_M80_{lamp}_N")
        n.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        n.set_editor_property("srgb", False)
        orm = unreal.load_asset(f"{KIT}/T_M80_{lamp}_ORM")
        orm.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        orm.set_editor_property("srgb", False)
        for t in (n, orm):
            EAL.save_loaded_asset(t)
    mpc = unreal.load_asset(MPC_PATH)
    report["mpc_param_added"] = ensure_mpc_param(mpc, "Lampioni")
    master = lamp_master()
    glass = glass_material(mpc)
    yield 5
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for lamp in LAMPS:
        mi_path = f"{KIT}/MI_M80_{lamp}"
        mi = unreal.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else \
            TOOLS.create_asset(f"MI_M80_{lamp}", KIT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, master)
        for param, key in (("Colore", "D"), ("Normali", "N"), ("ORM", "ORM")):
            MEL.set_material_instance_texture_parameter_value(mi, param, unreal.load_asset(f"{KIT}/T_M80_{lamp}_{key}"))
        EAL.save_loaded_asset(mi)
        mesh = unreal.load_asset(f"{KIT}/SM_M80_{lamp}")
        slots = mesh.get_editor_property("static_materials")
        names = [str(s.get_editor_property("material_slot_name")) for s in slots]
        for i, name in enumerate(names):
            mesh.set_material(i, glass if "glass" in name.lower() else mi)
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", True)
        sub.set_nanite_settings(mesh, settings, apply_changes=True)
        EAL.save_loaded_asset(mesh)
        box = mesh.get_bounding_box()
        report[lamp] = {"slots": names, "bounds_min": [round(box.min.x), round(box.min.y), round(box.min.z)],
                        "bounds_max": [round(box.max.x), round(box.max.y), round(box.max.z)]}
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
