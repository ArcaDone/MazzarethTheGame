"""Build one matte PBR parent and a small set of reusable surface instances."""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export/textures/texture_manifest.json"
IMPORTED = ROOT / "Pipeline/Unreal/reuse_import_result.json"
OUT = ROOT / "Pipeline/Unreal/reuse_master_material_result.json"
BASE = "/Game/Mazzarino80/ReuseKit/Materials"
ASSETS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.MaterialEditingLibrary


def import_texture(row):
    name = Path(row["file"]).stem
    package = f"{BASE}/Textures/{name}"
    asset = unreal.EditorAssetLibrary.load_asset(package)
    if asset:
        return asset
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", row["file"])
    task.set_editor_property("destination_path", f"{BASE}/Textures")
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("replace_existing", False)
    ASSETS.import_asset_tasks([task])
    asset = unreal.EditorAssetLibrary.load_asset(package)
    if not isinstance(asset, unreal.Texture):
        raise RuntimeError("Texture import failed: " + package)
    return asset


textures = {row["role"]: import_texture(row)
            for row in json.loads(SOURCE.read_text(encoding="utf-8"))}
master_path = f"{BASE}/M_M80_WeatheredSurface"
master = unreal.EditorAssetLibrary.load_asset(master_path)
if master is None:
    master = ASSETS.create_asset("M_M80_WeatheredSurface", BASE,
                                unreal.Material, unreal.MaterialFactoryNew())
if not isinstance(master, unreal.Material):
    raise RuntimeError("Unable to create PBR parent")

# The graph is deliberately small: texture × tint × low-frequency variation,
# matte roughness, modest specular, and zero metal on masonry. No noisy normals.
LIB.delete_all_material_expressions(master)


def node(cls, x, y):
    return LIB.create_material_expression(master, cls, x, y)


def scalar(name, value, x, y):
    expression = node(unreal.MaterialExpressionScalarParameter, x, y)
    expression.set_editor_property("parameter_name", name)
    expression.set_editor_property("default_value", value)
    return expression


def connect(source, target, input_name, output_name=""):
    LIB.connect_material_expressions(source, output_name, target, input_name)


base = node(unreal.MaterialExpressionTextureSampleParameter2D, -900, -150)
base.set_editor_property("parameter_name", "BaseTexture")
base.set_editor_property("texture", textures["StoneWall"])
tint = node(unreal.MaterialExpressionVectorParameter, -900, 90)
tint.set_editor_property("parameter_name", "Tint")
tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
color = node(unreal.MaterialExpressionMultiply, -620, -100)
connect(base, color, "A", "RGB")
connect(tint, color, "B")

macro_texture = unreal.EditorAssetLibrary.load_asset(
    "/Game/Mazzarino80/Historic/Materials/T_M80_FacadeMacroNoise")
if not isinstance(macro_texture, unreal.Texture):
    raise RuntimeError("Missing existing macro-noise texture")
uv = node(unreal.MaterialExpressionTextureCoordinate, -950, 470)
macro_tiling = scalar("MacroTiling", .12, -950, 650)
macro_uv = node(unreal.MaterialExpressionMultiply, -730, 490)
connect(uv, macro_uv, "A")
connect(macro_tiling, macro_uv, "B")
macro = node(unreal.MaterialExpressionTextureSampleParameter2D, -500, 460)
macro.set_editor_property("parameter_name", "MacroTexture")
macro.set_editor_property("texture", macro_texture)
connect(macro_uv, macro, "Coordinates")
neutral = node(unreal.MaterialExpressionConstant3Vector, -500, 700)
neutral.set_editor_property("constant", unreal.LinearColor(1, 1, 1, 1))
macro_strength = scalar("MacroStrength", .12, -300, 750)
macro_mix = node(unreal.MaterialExpressionLinearInterpolate, -230, 390)
connect(neutral, macro_mix, "A")
connect(macro, macro_mix, "B", "RGB")
connect(macro_strength, macro_mix, "Alpha")
albedo = node(unreal.MaterialExpressionMultiply, 60, 0)
connect(color, albedo, "A")
connect(macro_mix, albedo, "B")
LIB.connect_material_property(albedo, "", unreal.MaterialProperty.MP_BASE_COLOR)
LIB.connect_material_property(scalar("Roughness", .90, 80, 190), "",
                              unreal.MaterialProperty.MP_ROUGHNESS)
LIB.connect_material_property(scalar("Metallic", 0, 80, 300), "",
                              unreal.MaterialProperty.MP_METALLIC)
LIB.connect_material_property(scalar("Specular", .18, 80, 420), "",
                              unreal.MaterialProperty.MP_SPECULAR)
LIB.recompile_material(master)
if not unreal.EditorAssetLibrary.save_loaded_asset(master, only_if_is_dirty=False):
    raise RuntimeError("Unable to save PBR parent")

SETTINGS = {
    "StoneWall": (.93, 0, .18, .12),
    "StoneFormal": (.90, 0, .18, .09),
    "PlasterWarm": (.94, 0, .16, .10),
    "OldWood": (.87, 0, .21, .09),
    "Iron": (.82, .30, .23, .08),
    "Terracotta": (.91, 0, .18, .10),
    "StoneTrim": (.92, 0, .18, .08),
    "Glass": (.43, 0, .20, .02),
}
instances = {}
for role, (roughness, metallic, specular, macro_amount) in SETTINGS.items():
    name = "MI_M80_" + role
    instance = unreal.EditorAssetLibrary.load_asset(f"{BASE}/{name}")
    if not instance:
        instance = ASSETS.create_asset(name, BASE, unreal.MaterialInstanceConstant,
                                       unreal.MaterialInstanceConstantFactoryNew())
    instance.set_editor_property("parent", master)
    LIB.set_material_instance_texture_parameter_value(instance, "BaseTexture", textures[role])
    LIB.set_material_instance_scalar_parameter_value(instance, "Roughness", roughness)
    LIB.set_material_instance_scalar_parameter_value(instance, "Metallic", metallic)
    LIB.set_material_instance_scalar_parameter_value(instance, "Specular", specular)
    LIB.set_material_instance_scalar_parameter_value(instance, "MacroStrength", macro_amount)
    if not unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False):
        raise RuntimeError("Unable to save material instance: " + name)
    instances[role] = instance

group_to_role = {"stone": "StoneWall", "formal": "StoneFormal",
                 "plaster": "PlasterWarm", "wood": "OldWood",
                 "iron": "Iron", "tile": "Terracotta", "glass": "Glass"}
staging = json.loads(IMPORTED.read_text(encoding="utf-8"))
assigned = []
for section in ("modules", "pilots", "pilot_stages"):
    for row in staging[section]:
        mesh = unreal.EditorAssetLibrary.load_asset(row["asset"])
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError("Missing imported StaticMesh: " + row["asset"])
        for index, group in enumerate(row["material_groups"]):
            role = group_to_role.get(group)
            if role:
                mesh.set_material(index, instances[role])
        unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
        assigned.append(row["asset"])

result = {"master": master_path, "textures": {k: v.get_path_name() for k, v in textures.items()},
          "instances": {k: v.get_path_name() for k, v in instances.items()},
          "meshes_assigned": len(assigned), "mesh_paths": assigned}
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_SHARED_MASTER", len(instances), "instances", len(assigned), "meshes")
