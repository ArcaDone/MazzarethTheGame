"""Textures and materials of the procedural bougainvillea (AM80Bougainvillea, plugin MazzarinoHouses) in
/Game/Mazzarino80/Vegetazione/Bouganvillea, from the textures in D:/Mazzarino80_Sorgenti/Vegetazione/Bouganvillea:
- M_M80_BGV_Card: masked, two-sided foliage card; colour x Tinta, a little lighter or darker per card (vertex colour
  B), light through it (subsurface), cut by the texture's alpha, swaying in the wind by vertex colour G.
- M_M80_BGV_Legno: bark colour, OpenGL normal and roughness on the branches' UVs (20 cm per unit), same wind.
- Instances the actor loads by name: MI_M80_BGV_Foglie, MI_M80_BGV_Brattee_<Magenta|Viola|Arancione|Rosso>,
  MI_M80_BGV_Fiorellini, MI_M80_BGV_Corteccia.
Card textures keep their alpha (PNG sources); bark colour and roughness are stored as JPEG.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bouganvillea_materiali.py
"""
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

SRC = "D:/Mazzarino80_Sorgenti/Vegetazione/Bouganvillea"
DEST = "/Game/Mazzarino80/Vegetazione/Bouganvillea"
TEX = DEST + "/Textures"
WIND = "/Engine/Functions/Engine_MaterialFunctions01/WorldPositionOffset/SimpleGrassWind"
BRACTS = {"Magenta": "T_Bouganvillea_Bracts_BaseColor", "Viola": "T_Bouganvillea_Bracts_Violet_BaseColor",
          "Arancione": "T_Bouganvillea_Bracts_Orange_BaseColor", "Rosso": "T_Bouganvillea_Bracts_Red_BaseColor"}
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MP = unreal.MaterialProperty
ST = unreal.MaterialSamplerType


def texture(name, kind):
    """kind: C (colour with alpha), D (colour, JPEG), N (OpenGL normal), M (mask)."""
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", "%s/%s.png" % (SRC, name))
    t.set_editor_property("destination_path", TEX)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    TOOLS.import_asset_tasks([t])
    tex = unreal.load_asset("%s/%s" % (TEX, name))
    if kind == "N":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("flip_green_channel", True)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif kind == "M":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    if kind in ("D", "M"):
        unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
    EAL.save_loaded_asset(tex, False)
    return tex


def new_material(name):
    path = "%s/%s" % (DEST, name)
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    return TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())


def builder(m):
    def expr(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e
    return expr


def wind(m, expr, vc):
    """WorldPositionOffset from the engine's SimpleGrassWind, weighted by vertex colour G."""
    fn = unreal.load_asset(WIND)
    if not fn:
        return
    call = expr(unreal.MaterialExpressionMaterialFunctionCall, -400, 700)
    call.set_editor_property("material_function", fn)
    MEL.update_material_function(fn)
    strength = expr(unreal.MaterialExpressionScalarParameter, -700, 650, parameter_name="Vento", default_value=0.25)
    speed = expr(unreal.MaterialExpressionScalarParameter, -700, 750, parameter_name="VelocitaVento", default_value=0.5)
    MEL.connect_material_expressions(strength, "", call, "WindIntensity")
    MEL.connect_material_expressions(vc, "G", call, "WindWeight")
    MEL.connect_material_expressions(speed, "", call, "WindSpeed")
    zero = expr(unreal.MaterialExpressionConstant3Vector, -700, 850)
    MEL.connect_material_expressions(zero, "", call, "AdditionalWPO")
    unreal.M80EditorLibrary.connect_world_position_offset(call, "")


def card_master(default_tex):
    m = new_material("M_M80_BGV_Card")
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    m.set_editor_property("opacity_mask_clip_value", 0.4)
    expr = builder(m)
    tex = expr(unreal.MaterialExpressionTextureSampleParameter2D, -900, 0, parameter_name="Tex",
               sampler_type=ST.SAMPLERTYPE_COLOR, texture=default_tex)
    vc = expr(unreal.MaterialExpressionVertexColor, -900, 350)
    dark = expr(unreal.MaterialExpressionScalarParameter, -900, 450, parameter_name="VariazioneScura", default_value=0.8)
    light = expr(unreal.MaterialExpressionScalarParameter, -900, 520, parameter_name="VariazioneChiara", default_value=1.12)
    var = expr(unreal.MaterialExpressionLinearInterpolate, -650, 400)
    MEL.connect_material_expressions(dark, "", var, "A")
    MEL.connect_material_expressions(light, "", var, "B")
    MEL.connect_material_expressions(vc, "B", var, "Alpha")
    tint = expr(unreal.MaterialExpressionVectorParameter, -650, -200, parameter_name="Tinta", default_value=unreal.LinearColor(1, 1, 1, 1))
    a = expr(unreal.MaterialExpressionMultiply, -450, -50)
    MEL.connect_material_expressions(tex, "RGB", a, "A")
    MEL.connect_material_expressions(tint, "", a, "B")
    colour = expr(unreal.MaterialExpressionMultiply, -300, 50)
    MEL.connect_material_expressions(a, "", colour, "A")
    MEL.connect_material_expressions(var, "", colour, "B")
    MEL.connect_material_property(colour, "", MP.MP_BASE_COLOR)
    through = expr(unreal.MaterialExpressionScalarParameter, -450, 200, parameter_name="Trasluce", default_value=0.6)
    sss = expr(unreal.MaterialExpressionMultiply, -200, 200)
    MEL.connect_material_expressions(colour, "", sss, "A")
    MEL.connect_material_expressions(through, "", sss, "B")
    MEL.connect_material_property(sss, "", MP.MP_SUBSURFACE_COLOR)
    rough = expr(unreal.MaterialExpressionScalarParameter, -300, 300, parameter_name="Ruvidita", default_value=0.6)
    MEL.connect_material_property(rough, "", MP.MP_ROUGHNESS)
    MEL.connect_material_property(tex, "A", MP.MP_OPACITY_MASK)
    wind(m, expr, vc)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def wood_master(col, nor, rough):
    m = new_material("M_M80_BGV_Legno")
    expr = builder(m)
    c = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, -100, parameter_name="Colore", sampler_type=ST.SAMPLERTYPE_COLOR, texture=col)
    n = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, 200, parameter_name="Normali", sampler_type=ST.SAMPLERTYPE_NORMAL, texture=nor)
    r = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, 500, parameter_name="Ruvidita", sampler_type=ST.SAMPLERTYPE_MASKS, texture=rough)
    tint = expr(unreal.MaterialExpressionVectorParameter, -700, -300, parameter_name="Tinta", default_value=unreal.LinearColor(1, 1, 1, 1))
    a = expr(unreal.MaterialExpressionMultiply, -350, -150)
    MEL.connect_material_expressions(c, "RGB", a, "A")
    MEL.connect_material_expressions(tint, "", a, "B")
    MEL.connect_material_property(a, "", MP.MP_BASE_COLOR)
    MEL.connect_material_property(n, "RGB", MP.MP_NORMAL)
    MEL.connect_material_property(r, "R", MP.MP_ROUGHNESS)
    wind(m, expr, expr(unreal.MaterialExpressionVertexColor, -900, 700))
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def instance(name, parent, textures, colours=None):
    path = "%s/%s" % (DEST, name)
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        TOOLS.create_asset(name, DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for p, t in textures.items():
        MEL.set_material_instance_texture_parameter_value(mi, p, t)
    for p, c in (colours or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, p, c)
    EAL.save_loaded_asset(mi, False)
    return mi


def run():
    leaves = texture("T_Bouganvillea_Leaves_BaseColor", "C")
    yield 2
    bracts = {k: texture(v, "C") for k, v in BRACTS.items()}
    yield 2
    flowers = texture("T_BGV_FlowerCenters_RGBA", "C")
    bark = (texture("T_Bouganvillea_Bark_BaseColor", "D"), texture("T_Bouganvillea_Bark_NormalGL", "N"),
            texture("T_Bouganvillea_Bark_Roughness", "M"))
    yield 5
    card = card_master(leaves)
    wood = wood_master(*bark)
    yield 5
    instance("MI_M80_BGV_Foglie", card, {"Tex": leaves})
    for k, t in bracts.items():
        instance("MI_M80_BGV_Brattee_" + k, card, {"Tex": t})
    instance("MI_M80_BGV_Fiorellini", card, {"Tex": flowers})
    # The bark photo is very dark brown: lifted towards the grey-brown of old bougainvillea trunks.
    instance("MI_M80_BGV_Corteccia", wood, {}, {"Tinta": unreal.LinearColor(1.7, 1.55, 1.4, 1)})
    yield 5


m80_seq.Sequencer(run(), log_file=os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/bouganvillea_materiali_error.txt"))
