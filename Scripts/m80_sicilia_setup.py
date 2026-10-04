"""Imports the typical Sicilian props (Research/Mazzarino80/Blender/M80_Sicilia.fbx) and gives them to the
house styles, with the Sicilian facade rules of each style (houses V3, steps 14.2-14.3).

- /Game/Mazzarino80/Kit/Sicilia: meshes, atlas texture, MI_M80_Sicilia_Glazed/Matte/Iron (parent M_M80_Sign),
  tiling majolica M_M80_Majolica + MI_M80_Majolica_A/B/C.
- Styles DA_M80Style_*: prop lists by category (see UM80HouseStyle "Sicilia"), MajolicaMaterial,
  WallPropYaw (computed from the imported niche so the fronts face the street) and the rules.
Report: Saved/Mazzarino80/HousesV2/sicilia_report.json.
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Research/Mazzarino80/Blender"
KIT = "/Game/Mazzarino80/Kit/Sicilia"
STYLES = "/Game/Mazzarino80/Houses/Styles/"
SIGN_MASTER = "/Game/Mazzarino80/Kit/Signs/M_M80_Sign"
REPORT = ROOT / "Saved/Mazzarino80/HousesV2/sicilia_report.json"
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary

# Category lists per style (mesh names without the SM_M80_ prefix) and Sicilian rules.
STYLE_SETUP = {
    "DA_M80Style_01_PopolarePietra": {
        "doorside_meshes": ["Quartara", "Bummulo", "Grasta_Gerani", "Pigna"], "balcony_meshes": ["Grasta_Gerani", "Grasta_Basilico", "TestaDiMoro"],
        "wall_meshes": ["Edicola"], "basket_meshes": ["Panaru"], "hanging_meshes": ["Peperoncini"], "terrace_meshes": ["Strattu", "Quartara"],
        "spout_meshes": ["Doccione"], "civic_meshes": ["Civico_1", "Civico_2", "Civico_3", "Civico_4"], "knocker_meshes": ["Batacchio"], "crest_meshes": [],
        "laundry_meshes": ["Panni_A", "Panni_B", "Panni_C"],
        "majolica": "A", "rules": {"pointed_arch_chance": 0.3, "bifora_chance": 0.08, "petto_oca_chance": 0.0, "liberty_railing_chance": 0.1,
                                   "majolica_balcony_chance": 0.15, "crest_chance": 0.0}},
    "DA_M80Style_02_PalazzoUrbano": {
        "doorside_meshes": ["TestaDiMoro", "Pigna"], "balcony_meshes": ["TestaDiMoro", "Grasta_Gerani", "Pigna"],
        "wall_meshes": ["Edicola", "Lanterna"], "basket_meshes": ["Panaru"], "hanging_meshes": [], "terrace_meshes": ["Quartara"],
        "spout_meshes": ["Doccione"], "civic_meshes": ["Civico_1", "Civico_2", "Civico_3", "Civico_4"], "knocker_meshes": ["Batacchio"], "crest_meshes": ["Stemma"],
        "laundry_meshes": ["Panni_A"],
        "majolica": "B", "rules": {"pointed_arch_chance": 0.1, "bifora_chance": 0.05, "petto_oca_chance": 0.55, "liberty_railing_chance": 0.25,
                                   "majolica_balcony_chance": 0.35, "crest_chance": 0.6}},
    "DA_M80Style_03_Intonacata5070": {
        "doorside_meshes": ["Grasta_Gerani", "Grasta_Basilico"], "balcony_meshes": ["Grasta_Gerani", "Grasta_Basilico"],
        "wall_meshes": ["Edicola"], "basket_meshes": ["Panaru"], "hanging_meshes": ["Peperoncini"], "terrace_meshes": ["Strattu"],
        "spout_meshes": [], "civic_meshes": ["Civico_1", "Civico_2", "Civico_3", "Civico_4"], "knocker_meshes": [], "crest_meshes": [],
        "laundry_meshes": ["Panni_A", "Panni_B", "Panni_C"],
        "majolica": "C", "rules": {"pointed_arch_chance": 0.0, "bifora_chance": 0.0, "petto_oca_chance": 0.0, "liberty_railing_chance": 0.15,
                                   "majolica_balcony_chance": 0.1, "crest_chance": 0.0}},
    "DA_M80Style_04_CasaPovera": {
        "doorside_meshes": ["Quartara", "Bummulo", "Grasta_Basilico"], "balcony_meshes": ["Grasta_Basilico", "Grasta_Gerani"],
        "wall_meshes": ["Edicola"], "basket_meshes": ["Panaru"], "hanging_meshes": ["Peperoncini"], "terrace_meshes": ["Strattu", "Quartara"],
        "spout_meshes": ["Doccione"], "civic_meshes": ["Civico_1", "Civico_2", "Civico_3", "Civico_4"], "knocker_meshes": ["Batacchio"], "crest_meshes": [],
        "laundry_meshes": ["Panni_A", "Panni_B", "Panni_C"],
        "majolica": "B", "rules": {"pointed_arch_chance": 0.35, "bifora_chance": 0.05, "petto_oca_chance": 0.0, "liberty_railing_chance": 0.0,
                                   "majolica_balcony_chance": 0.05, "crest_chance": 0.0}},
}


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


def instance(name, parent, params):
    path = KIT + "/" + name
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        name, KIT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in params.items():
        if isinstance(v, unreal.Texture):
            MEL.set_material_instance_texture_parameter_value(mi, k, v)
        elif isinstance(v, unreal.LinearColor):
            MEL.set_material_instance_vector_parameter_value(mi, k, v)
        else:
            MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    EAL.save_loaded_asset(mi)
    return mi


def majolica_master():
    path = KIT + "/M_M80_Majolica"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    m = TOOLS.create_asset("M_M80_Majolica", KIT, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_nanite", True)
    uv = MEL.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    tiling = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -900, 150)
    tiling.set_editor_property("parameter_name", "TilesPerMetre")
    tiling.set_editor_property("default_value", 5.0)
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -700, 50)
    MEL.connect_material_expressions(uv, "", mul, "A")
    MEL.connect_material_expressions(tiling, "", mul, "B")
    tex = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
    tex.set_editor_property("parameter_name", "Tile")
    MEL.connect_material_expressions(mul, "", tex, "UVs")
    MEL.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -300, 250)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.2)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def front_yaw(mesh):
    """Offset for UM80HouseStyle.WallPropYaw: the generator assumes the front faces -Y."""
    box = mesh.get_bounding_box()
    ext_x, ext_y = box.max.x - box.min.x, box.max.y - box.min.y
    if ext_x < ext_y:
        fx, fy = (-1.0, 0.0) if abs(box.min.x) > abs(box.max.x) else (1.0, 0.0)
    else:
        fx, fy = (0.0, -1.0) if abs(box.min.y) > abs(box.max.y) else (0.0, 1.0)
    return -90.0 - math.degrees(math.atan2(fy, fx))


def run():
    report = {}
    fbx = unreal.FbxImportUI()
    fbx.set_editor_property("import_mesh", True)
    fbx.set_editor_property("import_materials", False)
    fbx.set_editor_property("import_textures", False)
    fbx.set_editor_property("import_as_skeletal", False)
    fbx.static_mesh_import_data.set_editor_property("combine_meshes", False)
    fbx.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    import_files([SRC / "M80_Sicilia.fbx"], KIT, fbx)
    import_files([SRC / "Textures/T_M80_SiciliaAtlas.png"] + sorted((SRC / "Textures").glob("T_M80_Majolica_*.png")), KIT)
    yield 10
    atlas = unreal.load_asset(KIT + "/T_M80_SiciliaAtlas")
    atlas.set_editor_property("filter", unreal.TextureFilter.TF_BILINEAR)
    EAL.save_loaded_asset(atlas)
    sign = unreal.load_asset(SIGN_MASTER)
    mats = [instance("MI_M80_Sicilia_Glazed", sign, {"Face": atlas, "Roughness": 0.18, "Metallic": 0.0}),
            instance("MI_M80_Sicilia_Matte", sign, {"Face": atlas, "Roughness": 0.85, "Metallic": 0.0}),
            instance("MI_M80_Sicilia_Iron", sign, {"Face": atlas, "Roughness": 0.45, "Metallic": 0.7})]
    maj = majolica_master()
    majolica = {k: instance("MI_M80_Majolica_" + k, maj, {"Tile": unreal.load_asset(KIT + "/T_M80_Majolica_" + k)}) for k in "ABC"}
    meshes = {}
    for path in EAL.list_assets(KIT, recursive=False):
        asset = unreal.load_asset(path)
        if isinstance(asset, unreal.StaticMesh) and asset.get_name().startswith("SM_M80_"):
            for i in range(min(3, len(asset.get_editor_property("static_materials")))):
                asset.set_material(i, mats[i])
            EAL.save_loaded_asset(asset)
            meshes[asset.get_name()[len("SM_M80_"):]] = asset
    report["meshes"] = sorted(meshes)
    yaw = front_yaw(meshes["Edicola"]) if "Edicola" in meshes else 0.0
    report["wall_prop_yaw"] = yaw
    for style_name, setup in STYLE_SETUP.items():
        style = unreal.load_asset(STYLES + style_name)
        if not style:
            report.setdefault("missing_styles", []).append(style_name)
            continue
        for prop, names in setup.items():
            if prop.endswith("_meshes"):
                style.set_editor_property(prop, [meshes[n] for n in names if n in meshes])
        style.set_editor_property("wall_prop_yaw", yaw)
        style.set_editor_property("majolica_material", majolica[setup["majolica"]])
        rules = style.get_editor_property("rules")
        for k, v in setup["rules"].items():
            rules.set_editor_property(k, v)
        style.set_editor_property("rules", rules)
        EAL.save_loaded_asset(style, only_if_is_dirty=False)
        report.setdefault("styles", []).append(style_name)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
