"""Create a candidate material family for the *existing* approved PCG surfaces.

Does not load, save, or edit Mazzarino80_CaseStoriche_Campione. The original
materials and approved PCG assets remain untouched until visual sign-off.
"""
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
BASE = "/Game/Mazzarino80/PCG/SurfaceMaster"
OLD = "/Game/Mazzarino80/Historic/Materials/"
OUT = ROOT / "Pipeline/Unreal/approved_pcg_surface_master_result.json"
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary

stone = "/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_"
stucco = "/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Stucco_Facade_wfnjdgl/T_Stucco_Facade_wfnjdgl_2K_"
damaged = "/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Damaged_Brick_Wall_Plaster_vcvodh0/T_Damaged_Brick_Wall_Plaster_vcvodh0_4K_"
roof = "/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Red_Roof_Tiles_tfqnfggs/T_Red_Roof_Tiles_tfqnfggs_4K_"
wood = "/Game/Megascans/Surfaces/Flaked_Paint_Wooden_Panel_tlsmbafdy/T_Flaked_Paint_Wooden_Panel_tlsmbafdy_4K_"
texture_groups = {name: (unreal.load_asset(prefix + "D"), unreal.load_asset(prefix + "N"))
                  for name, prefix in {"stone": stone, "stucco": stucco,
                                       "damaged": damaged, "roof": roof,
                                       "wood": wood}.items()}
for name, pair in texture_groups.items():
    if not all(pair):
        raise RuntimeError("Missing source maps for " + name)
color_virtual = {bool(pair[0].get_editor_property("virtual_texture_streaming"))
                 for pair in texture_groups.values()}
normal_virtual = {bool(pair[1].get_editor_property("virtual_texture_streaming"))
                  for pair in texture_groups.values()}
macro_texture = unreal.load_asset(OLD + "T_M80_FacadeMacroNoise")
if not macro_texture:
    raise RuntimeError("Missing existing facade macro texture")

def build_parent(asset_name, default_group, virtual):
    parent = unreal.EditorAssetLibrary.load_asset(BASE + "/" + asset_name)
    if parent is None:
        parent = tools.create_asset(asset_name, BASE, unreal.Material,
                                    unreal.MaterialFactoryNew())
    if not isinstance(parent, unreal.Material):
        raise RuntimeError("Unable to create surface parent")
    lib.delete_all_material_expressions(parent)
    parent.set_editor_property("used_with_instanced_static_meshes", True)
    
    def node(cls, x, y):
        return lib.create_material_expression(parent, cls, x, y)
    
    def scalar(name, value, x, y):
        n = node(unreal.MaterialExpressionScalarParameter, x, y)
        n.set_editor_property("parameter_name", name)
        n.set_editor_property("default_value", value)
        return n
    
    def vector(name, value, x, y):
        n = node(unreal.MaterialExpressionVectorParameter, x, y)
        n.set_editor_property("parameter_name", name)
        n.set_editor_property("default_value", unreal.LinearColor(*value, 1))
        return n
    
    def connect(a, b, pin, output=""):
        if not lib.connect_material_expressions(a, output, b, pin):
            raise RuntimeError("Material graph connection failed: " + pin)
    
    # A shared graph, with a tint/texture blend that can represent both old lime
    # plaster and the solid-colour 3D coppi. Normal detail is intentionally mild.
    diffuse = node(unreal.MaterialExpressionTextureSampleParameter2D, -1200, -400)
    diffuse.set_editor_property("parameter_name", "SurfaceColor")
    diffuse.set_editor_property("texture", texture_groups[default_group][0])
    diffuse.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if virtual else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    white = node(unreal.MaterialExpressionConstant3Vector, -1190, -150)
    white.set_editor_property("constant", unreal.LinearColor(1, 1, 1, 1))
    texture_mix = node(unreal.MaterialExpressionLinearInterpolate, -940, -300)
    connect(white, texture_mix, "A")
    connect(diffuse, texture_mix, "B", "RGB")
    connect(scalar("TextureWeight", 1.0, -1180, 80), texture_mix, "Alpha")
    tinted = node(unreal.MaterialExpressionMultiply, -710, -300)
    connect(texture_mix, tinted, "A")
    connect(vector("Tint", (0.55, 0.47, 0.36), -960, -10), tinted, "B")
    
    instance_random = node(unreal.MaterialExpressionPerInstanceRandom, -940, 210)
    centered_random = node(unreal.MaterialExpressionSubtract, -720, 210)
    centered_random.set_editor_property("const_b", .5)
    connect(instance_random, centered_random, "A")
    random_strength = node(unreal.MaterialExpressionMultiply, -500, 210)
    connect(centered_random, random_strength, "A")
    connect(scalar("TileVariation", 0, -730, 420), random_strength, "B")
    random_factor = node(unreal.MaterialExpressionAdd, -280, 210)
    random_factor.set_editor_property("const_b", 1.0)
    connect(random_strength, random_factor, "A")
    varied = node(unreal.MaterialExpressionMultiply, -80, -250)
    connect(tinted, varied, "A")
    connect(random_factor, varied, "B")
    
    position = node(unreal.MaterialExpressionWorldPosition, -1200, 600)
    xy = node(unreal.MaterialExpressionComponentMask, -980, 550)
    xy.set_editor_property("r", True)
    xy.set_editor_property("g", True)
    xy.set_editor_property("b", False)
    connect(position, xy, "")
    xz = node(unreal.MaterialExpressionComponentMask, -980, 790)
    xz.set_editor_property("r", True)
    xz.set_editor_property("g", False)
    xz.set_editor_property("b", True)
    connect(position, xz, "")
    macro_values = []
    for src, y, tiling_name, default in ((xy, 560, "MacroXYScale", .00065),
                                        (xz, 900, "MacroXZScale", .00085)):
        uv = node(unreal.MaterialExpressionMultiply, -710, y)
        connect(src, uv, "A")
        connect(scalar(tiling_name, default, -930, y + 140), uv, "B")
        sample = node(unreal.MaterialExpressionTextureSample, -470, y)
        sample.set_editor_property("texture", macro_texture)
        sample.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        connect(uv, sample, "UVs")
        macro_values.append(sample)
    average = node(unreal.MaterialExpressionAdd, -220, 600)
    connect(macro_values[0], average, "A", "R")
    connect(macro_values[1], average, "B", "R")
    half = node(unreal.MaterialExpressionMultiply, -10, 600)
    half.set_editor_property("const_b", .5)
    connect(average, half, "A")
    center = node(unreal.MaterialExpressionSubtract, 190, 600)
    center.set_editor_property("const_b", .5)
    connect(half, center, "A")
    amount = node(unreal.MaterialExpressionMultiply, 390, 600)
    connect(center, amount, "A")
    connect(scalar("MacroStrength", .10, 160, 800), amount, "B")
    factor = node(unreal.MaterialExpressionAdd, 590, 600)
    factor.set_editor_property("const_b", 1.)
    connect(amount, factor, "A")
    color = node(unreal.MaterialExpressionMultiply, 780, -120)
    connect(varied, color, "A")
    connect(factor, color, "B")
    lib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    
    normal = node(unreal.MaterialExpressionTextureSampleParameter2D, -1200, 1150)
    normal.set_editor_property("parameter_name", "SurfaceNormal")
    normal.set_editor_property("texture", texture_groups[default_group][1])
    normal.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if virtual else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    flat = node(unreal.MaterialExpressionConstant3Vector, -1160, 1370)
    flat.set_editor_property("constant", unreal.LinearColor(0, 0, 1, 1))
    normal_mix = node(unreal.MaterialExpressionLinearInterpolate, -900, 1190)
    connect(flat, normal_mix, "A")
    connect(normal, normal_mix, "B", "RGB")
    connect(scalar("NormalStrength", .08, -1150, 1540), normal_mix, "Alpha")
    lib.connect_material_property(normal_mix, "", unreal.MaterialProperty.MP_NORMAL)
    lib.connect_material_property(scalar("Roughness", .94, -300, 1190), "",
                                  unreal.MaterialProperty.MP_ROUGHNESS)
    lib.connect_material_property(scalar("Specular", .16, -300, 1360), "",
                                  unreal.MaterialProperty.MP_SPECULAR)
    lib.connect_material_property(scalar("Metallic", 0, -300, 1510), "",
                                  unreal.MaterialProperty.MP_METALLIC)
    lib.recompile_material(parent)
    if not unreal.EditorAssetLibrary.save_loaded_asset(parent, only_if_is_dirty=False):
        raise RuntimeError("Cannot save surface master")
    return parent

parent = build_parent('M_M80_PCG_Surface', 'stone', False)
vt_parent = build_parent('M_M80_PCG_Surface_VT', 'stucco', True)

# Palette mirrors the approved architecture and keeps roof/wood/stone distinct.
presets = {
    "Stone_0": ("stone", (.52, .39, .25), 1, .11, .96, .14, 0, .10, 0),
    "Stone_1": ("stone", (.42, .35, .26), 1, .11, .96, .14, 0, .10, 0),
    "StoneTrim": ("stone", (.49, .44, .34), 0, .13, .95, .14, 0, .06, 0),
    "Plaster_0": ("damaged", (.54, .49, .40), .30, .08, .95, .14, 0, .10, 0),
    "Plaster_1": ("stucco", (.65, .59, .48), .30, .07, .96, .14, 0, .09, 0),
    "Plaster_2": ("damaged", (.42, .41, .35), .30, .08, .96, .14, 0, .08, 0),
    "Plaster_3": ("damaged", (.60, .46, .33), .30, .07, .96, .14, 0, .10, 0),
    "Plaster_4": ("damaged", (.69, .66, .56), .30, .07, .97, .14, 0, .08, 0),
    "Plaster_5": ("stucco", (.51, .43, .36), .30, .07, .96, .14, 0, .10, 0),
    "RoofSurface": ("roof", (.60, .49, .36), 1, .10, .94, .16, 0, .07, 0),
    "Tile3D": ("stucco", (.16, .072, .031), 0, .025, .94, .16, 0, .06, .75),
    "Terrace": ("stucco", (.42, .39, .32), .25, .10, .95, .14, 0, .06, 0),
    "GutterStone": ("stone", (.47, .42, .33), 0, .09, .96, .14, 0, .05, 0),
    "Wood_0": ("wood", (.14, .21, .17), .60, .12, .88, .16, 0, .05, 0),
    "Wood_1": ("wood", (.30, .24, .17), .60, .12, .88, .16, 0, .05, 0),
    "Wood_2": ("wood", (.29, .30, .26), .60, .12, .88, .16, 0, .05, 0),
    "Iron": ("stone", (.065, .055, .042), 0, 0, .83, .20, .45, 0, 0),
    "Glass": ("stone", (.028, .04, .034), 0, 0, .48, .20, 0, 0, 0),
    "Paving": ("stone", (.49, .43, .33), 1, .10, .95, .16, 0, .07, 0),
    "BrickRed": ("roof", (.48, .29, .19), 1, .10, .94, .16, 0, .08, 0),
    "BrickYellow": ("stone", (.55, .45, .31), 1, .10, .94, .16, 0, .08, 0),
}
instances = {}
for name, (group, tint, weight, relief, roughness, specular, metallic, macro, variation) in presets.items():
    path = BASE + "/MI_M80_PCG_" + name
    mi = unreal.EditorAssetLibrary.load_asset(path)
    if mi is None:
        mi = tools.create_asset(path.rsplit("/", 1)[-1], BASE,
                                unreal.MaterialInstanceConstant,
                                unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", vt_parent if group == "stucco" else parent)
    lib.set_material_instance_texture_parameter_value(mi, "SurfaceColor", texture_groups[group][0])
    lib.set_material_instance_texture_parameter_value(mi, "SurfaceNormal", texture_groups[group][1])
    lib.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(*tint, 1))
    for param, value in (("TextureWeight", weight), ("NormalStrength", relief),
                         ("Roughness", roughness), ("Specular", specular),
                         ("Metallic", metallic), ("MacroStrength", macro),
                         ("TileVariation", variation)):
        lib.set_material_instance_scalar_parameter_value(mi, param, value)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mi, only_if_is_dirty=False):
        raise RuntimeError("Cannot save " + path)
    instances[name] = path + "." + path.rsplit("/", 1)[-1]

report = {"masters": [parent.get_path_name(), vt_parent.get_path_name()],
          "instances": instances,
          "source_textures_are_virtual": {"color": True in color_virtual,
                                           "normal": True in normal_virtual},
          "approved_level_edited": False}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_PCG_SURFACE_MASTER", len(instances), "instances")
