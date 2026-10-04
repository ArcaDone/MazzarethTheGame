"""Player character in an 80s shiny acetate tracksuit and sunglasses (GTA-like game, step 17).

- Imports Research/.../Player/T_M80_Tuta_*_D.png (painted by Research/Mazzarino80/Blender/m80_tracksuit.py)
  and makes MI_M80_Tuta_Giacca / MI_M80_Tuta_Pantaloni (MetaHuman fabric material: shinier, no fuzz).
- /Game/Mazzarino80/Player/BP_M80_Giocatore: copy of the sample's MetaHuman (Kellan) character with the
  tracksuit on the hoodie and the trousers. AM80GameMode spawns it.
Report: Saved/Mazzarino80/Player/setup_report.json.
"""
import json
import os
import shutil
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Player"
TEX_SRC = ROOT / "Research/Mazzarino80/Player"
PLAYER = "/Game/Mazzarino80/Player"
BP_SRC = "/Game/Blueprints/RetargetedCharacters/CBP_SandboxCharacter_Metahuman_Kellan"
BP = PLAYER + "/BP_M80_Giocatore"
OUT = SRC / "setup_report.json"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
PARTS = {"Giacca": ("T_Torso", "hoodie"), "Pantaloni": ("T_Legs", "cargopants")}


def import_tex(path, name):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(path))
    t.set_editor_property("destination_path", PLAYER)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    TOOLS.import_asset_tasks([t])
    tex = unreal.load_asset(PLAYER + "/" + name)
    tex.set_editor_property("virtual_texture_streaming", False)
    unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
    EAL.save_loaded_asset(tex)
    return tex


def simple_material(name, color, rough, metal=0.0, spec=0.5):
    path = PLAYER + "/" + name
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, PLAYER, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    for prop, val, y in ((unreal.MaterialProperty.MP_BASE_COLOR, color, 0), (unreal.MaterialProperty.MP_ROUGHNESS, rough, 200),
                         (unreal.MaterialProperty.MP_METALLIC, metal, 300), (unreal.MaterialProperty.MP_SPECULAR, spec, 400)):
        if isinstance(val, tuple):
            e = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, y)
            e.set_editor_property("constant", unreal.LinearColor(*val, 1))
        else:
            e = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, y)
            e.set_editor_property("r", val)
        MEL.connect_material_property(e, "", prop)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def acetate_master():
    """Shiny acetate: base colour and normal textures, low roughness, a little metallic sheen."""
    path = PLAYER + "/M_M80_Acetato"
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset("M_M80_Acetato", PLAYER, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("used_with_skeletal_mesh", True)

    def node(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e
    bc = node(unreal.MaterialExpressionTextureSampleParameter2D, -600, 0, parameter_name="BaseColor")
    nm = node(unreal.MaterialExpressionTextureSampleParameter2D, -600, 300, parameter_name="Normal",
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, texture=unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"))
    rough = node(unreal.MaterialExpressionScalarParameter, -300, 500, parameter_name="Roughness", default_value=0.2)
    metal = node(unreal.MaterialExpressionScalarParameter, -300, 600, parameter_name="Metallic", default_value=0.3)
    spec = node(unreal.MaterialExpressionScalarParameter, -300, 700, parameter_name="Specular", default_value=0.8)
    MEL.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def sunglasses():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.static_mesh_import_data.set_editor_property("combine_meshes", True)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(SRC / "M80_Occhiali.fbx"))
    t.set_editor_property("destination_path", PLAYER)
    t.set_editor_property("destination_name", "SM_M80_Occhiali")
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", ui)
    TOOLS.import_asset_tasks([t])
    mesh = unreal.load_asset(PLAYER + "/SM_M80_Occhiali")
    mesh.set_material(0, simple_material("M_M80_Occhiali_Montatura", (0.01, 0.01, 0.012), 0.18, 0.0, 0.6))
    if len(mesh.static_materials) > 1:
        mesh.set_material(1, simple_material("M_M80_Occhiali_Lenti", (0.004, 0.005, 0.006), 0.04, 0.0, 1.0))
    EAL.save_loaded_asset(mesh)
    b = mesh.get_bounding_box()
    return [round(v, 1) for v in (b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z)]


def run():
    report = {}
    report["occhiali_box"] = sunglasses()
    yield 2
    TEX_SRC.mkdir(parents=True, exist_ok=True)
    mis = {}
    parent = acetate_master()
    for part, (kellan, _) in PARTS.items():
        png = TEX_SRC / ("T_M80_Tuta_%s_D.png" % part)
        shutil.copy2(SRC / png.name, png)
        tex = import_tex(png, "T_M80_Tuta_%s_D" % part)
        name = "MI_M80_Tuta_" + part
        path = PLAYER + "/" + name
        mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
            name, PLAYER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, parent)
        MEL.set_material_instance_texture_parameter_value(mi, "BaseColor", tex)
        MEL.set_material_instance_texture_parameter_value(mi, "Normal", unreal.load_asset("/Game/MetaHumans/Kellan/Body/Textures/%s_Normal" % kellan))
        MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", 0.18)
        EAL.save_loaded_asset(mi)
        mis[part] = mi
    yield 5
    if not EAL.does_asset_exist(BP):
        EAL.duplicate_asset(BP_SRC, BP)
    bp = unreal.load_asset(BP)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    changed = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        obj = lib.get_object(lib.get_data(h))
        if not isinstance(obj, unreal.SkeletalMeshComponent):
            continue
        mesh = obj.get_skinned_asset()
        mname = mesh.get_name() if mesh else ""
        for part, (_, key) in PARTS.items():
            if key in mname:
                n = len(mesh.materials) if mesh else 1
                obj.set_editor_property("override_materials", [mis[part]] * max(1, n))
                changed.append([obj.get_name(), mname, part])
    report["components"] = changed
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
