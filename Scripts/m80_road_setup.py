"""Roads kit: the full material of the secondary lava paving (T_Basalto_* in
/Game/Mazzarino80/Kit/Stairs/Textures/LavicaSecondaria, from D:/BlenderTest/Pavimento_Basalto_PBR) and test roads
of the "Strada (Mazzarino)" actor added to /Game/Mazzarino80/Kit/Stairs/L_M80_ProvaScalinate (the stairs already
there are left alone; the roads, folder "Strade", and their test terrain are remade each run).
Renders go to Saved/Mazzarino80/Roads/Render.

Master M_M80_LavicaCompleta (parameters in the instance MI_M80_Lavica_secondaria):
  Lunghezza / Larghezza ripetizione (m)  size of one repeat of the pattern along U and V (UV0 in metres)
  Parallasse (switch), Rilievo           parallax occlusion from the height map (stones stand out of the joints)
  Intensita normale, Intensita AO, Ruvidita, Tinta, Luminosita
  Variazione macro                       large-scale light/dark patches that hide the repetition
  Bagnato (0-1)                          wet: the joints first, then the stones (darker, glossy)

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_road_setup.py -ForceLit
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
KIT = "/Game/Mazzarino80/Kit/Stairs"
TEX = KIT + "/Textures/LavicaSecondaria/T_Basalto_"
MAP = KIT + "/L_M80_ProvaScalinate"
RENDER = ROOT / "Saved/Mazzarino80/Roads/Render"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
CUBE = "/Engine/BasicShapes/Cube"
POM = "/Engine/Functions/Engine_MaterialFunctions01/Texturing/ParallaxOcclusionMapping"
FOLDER = "Strade"


def fix_textures():
    """The set came in with default settings: data maps must be linear, the normal is the DirectX one."""
    TC = unreal.TextureCompressionSettings
    for name, comp, srgb in (("BaseColor", TC.TC_DEFAULT, True), ("Normal_DX", TC.TC_NORMALMAP, False),
                             ("ORM", TC.TC_MASKS, False), ("Height", TC.TC_MASKS, False), ("AO", TC.TC_MASKS, False),
                             ("Roughness", TC.TC_MASKS, False), ("Metallic", TC.TC_MASKS, False),
                             ("Height16", TC.TC_MASKS, False)):
        t = unreal.load_asset(TEX + name)
        t.set_editor_property("compression_settings", comp)
        t.set_editor_property("srgb", srgb)
        t.set_editor_property("flip_green_channel", False)
        unreal.EditorAssetLibrary.save_loaded_asset(t, False)


def new_material(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)
        return m
    return TOOLS.create_asset(path.rsplit("/", 1)[1], path.rsplit("/", 1)[0], unreal.Material, unreal.MaterialFactoryNew())


def node(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def scalar(m, x, y, name, value, group="Lavica"):
    return node(m, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value, group=group)


def op(m, cls, x, y, a, b, a_out="", b_out=""):
    """Binary node fed by a and b (expressions or constants)."""
    e = node(m, cls, x, y)
    for pin, src, out in (("A", a, a_out), ("B", b, b_out)):
        if isinstance(src, (int, float)):
            e.set_editor_property("const_" + pin.lower(), float(src))
        else:
            MEL.connect_material_expressions(src, out, e, pin)
    return e


def lerp(m, x, y, a, b, alpha, alpha_out=""):
    e = node(m, unreal.MaterialExpressionLinearInterpolate, x, y)
    for pin, src in (("A", a), ("B", b)):
        if isinstance(src, (int, float)):
            e.set_editor_property("const_" + pin.lower(), float(src))
        else:
            MEL.connect_material_expressions(src, "", e, pin)
    MEL.connect_material_expressions(alpha, alpha_out, e, "Alpha")
    return e


def lava_master():
    m = new_material(KIT + "/M_M80_LavicaCompleta")
    st = unreal.MaterialSamplerType
    # UV0 is in metres on the road slab and the stairs: one repeat every Lunghezza x Larghezza metres.
    tc = node(m, unreal.MaterialExpressionTextureCoordinate, -2200, 0)
    rep = node(m, unreal.MaterialExpressionAppendVector, -2200, 150)
    MEL.connect_material_expressions(scalar(m, -2450, 120, "Lunghezza ripetizione (m)", 2.0, "Ripetizione"), "", rep, "A")
    MEL.connect_material_expressions(scalar(m, -2450, 220, "Larghezza ripetizione (m)", 2.0, "Ripetizione"), "", rep, "B")
    uv0 = op(m, unreal.MaterialExpressionDivide, -2000, 50, tc, rep)

    height = node(m, unreal.MaterialExpressionTextureObjectParameter, -2000, 300, parameter_name="Height",
                  texture=unreal.load_asset(TEX + "Height"), sampler_type=st.SAMPLERTYPE_MASKS)
    pom = node(m, unreal.MaterialExpressionMaterialFunctionCall, -1700, 250)
    pom.set_editor_property("material_function", unreal.load_asset(POM))
    MEL.connect_material_expressions(height, "", pom, "Heightmap Texture")
    MEL.connect_material_expressions(scalar(m, -2000, 450, "Rilievo", 0.012, "Rilievo"), "", pom, "Height Ratio")
    MEL.connect_material_expressions(node(m, unreal.MaterialExpressionConstant, -2000, 550, r=8.0), "", pom, "Min Steps")
    MEL.connect_material_expressions(node(m, unreal.MaterialExpressionConstant, -2000, 620, r=24.0), "", pom, "Max Steps")
    MEL.connect_material_expressions(uv0, "", pom, "UVs")
    MEL.connect_material_expressions(node(m, unreal.MaterialExpressionConstant4Vector, -2000, 700,
                                          constant=unreal.LinearColor(1, 0, 0, 0)), "", pom, "Heightmap Channel")
    sw = node(m, unreal.MaterialExpressionStaticSwitchParameter, -1350, 50, parameter_name="Parallasse", default_value=True, group="Rilievo")
    MEL.connect_material_expressions(pom, "Parallax UVs", sw, "True")
    MEL.connect_material_expressions(uv0, "", sw, "False")
    uv = sw

    samp = {}
    for i, (k, tex, s) in enumerate((("D", "BaseColor", st.SAMPLERTYPE_COLOR), ("N", "Normal_DX", st.SAMPLERTYPE_NORMAL),
                                     ("ORM", "ORM", st.SAMPLERTYPE_MASKS))):
        e = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1050, -400 + i * 300, parameter_name=k,
                 texture=unreal.load_asset(TEX + tex), sampler_type=s, group="Texture")
        MEL.connect_material_expressions(uv, "", e, "UVs")
        samp[k] = e
    h = node(m, unreal.MaterialExpressionTextureSample, -1050, 550, sampler_type=st.SAMPLERTYPE_MASKS)
    MEL.connect_material_expressions(height, "", h, "Tex")
    MEL.connect_material_expressions(uv, "", h, "UVs")

    # Large patches: the albedo itself sampled ~9 times bigger, as a light/dark mask.
    big = op(m, unreal.MaterialExpressionMultiply, -1350, 900, uv0, 0.11)
    macro = node(m, unreal.MaterialExpressionTextureSample, -1050, 900, texture=unreal.load_asset(TEX + "BaseColor"), sampler_type=st.SAMPLERTYPE_COLOR)
    MEL.connect_material_expressions(big, "", macro, "UVs")
    var = scalar(m, -1050, 1150, "Variazione macro", 0.35, "Colore")
    centred = op(m, unreal.MaterialExpressionSubtract, -800, 900, macro, 0.25, "G")
    macro_k = op(m, unreal.MaterialExpressionAdd, -450, 950, op(m, unreal.MaterialExpressionMultiply, -600, 950, centred, var), 1.0)

    # Wet: rises from the joints (low height) to the stones.
    wet_in = op(m, unreal.MaterialExpressionSubtract, -700, 600,
                op(m, unreal.MaterialExpressionMultiply, -800, 700, scalar(m, -1050, 750, "Bagnato", 0.0, "Bagnato"), 1.3), h, "", "R")
    wet = node(m, unreal.MaterialExpressionSaturate, -400, 600)
    MEL.connect_material_expressions(op(m, unreal.MaterialExpressionMultiply, -550, 600, wet_in, 5.0), "", wet, "")

    tint = node(m, unreal.MaterialExpressionVectorParameter, -800, -600, parameter_name="Tinta", default_value=unreal.LinearColor(1, 1, 1, 1), group="Colore")
    col = op(m, unreal.MaterialExpressionMultiply, -600, -400, samp["D"], tint, "RGB")
    col = op(m, unreal.MaterialExpressionMultiply, -450, -400, col, scalar(m, -800, -450, "Luminosita", 1.0, "Colore"))
    col = op(m, unreal.MaterialExpressionMultiply, -300, -400, col, macro_k)
    col = op(m, unreal.MaterialExpressionMultiply, -100, -400, col, lerp(m, -250, -250, 1.0, 0.45, wet))
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)

    flat = node(m, unreal.MaterialExpressionConstant3Vector, -800, -150, constant=unreal.LinearColor(0, 0, 1, 1))
    nrm = node(m, unreal.MaterialExpressionLinearInterpolate, -450, -100)
    MEL.connect_material_expressions(flat, "", nrm, "A")
    MEL.connect_material_expressions(samp["N"], "RGB", nrm, "B")
    MEL.connect_material_expressions(scalar(m, -800, -50, "Intensita normale", 1.0, "Rilievo"), "", nrm, "Alpha")
    MEL.connect_material_property(nrm, "", unreal.MaterialProperty.MP_NORMAL)

    rough = node(m, unreal.MaterialExpressionSaturate, -300, 150)
    MEL.connect_material_expressions(op(m, unreal.MaterialExpressionMultiply, -450, 150, samp["ORM"], scalar(m, -800, 200, "Ruvidita", 1.0, "Colore"), "G"), "", rough, "")
    MEL.connect_material_property(lerp(m, -100, 150, rough, 0.08, wet), "", unreal.MaterialProperty.MP_ROUGHNESS)
    ao = node(m, unreal.MaterialExpressionLinearInterpolate, -300, 300)
    ao.set_editor_property("const_a", 1.0)
    MEL.connect_material_expressions(samp["ORM"], "R", ao, "B")
    MEL.connect_material_expressions(scalar(m, -800, 350, "Intensita AO", 1.0, "Colore"), "", ao, "Alpha")
    MEL.connect_material_property(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)

    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m, False)
    return m


def lava_instance(master):
    """MI_M80_Lavica_secondaria (made by hand on the stairs master) moved onto the full master."""
    path = KIT + "/MI_M80_Lavica_secondaria"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = TOOLS.create_asset("MI_M80_Lavica_secondaria", KIT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, master)
    MEL.clear_all_material_instance_parameters(mi)
    # The hand-made instance repeated every 1.4 m.
    MEL.set_material_instance_scalar_parameter_value(mi, "Lunghezza ripetizione (m)", 1.4)
    MEL.set_material_instance_scalar_parameter_value(mi, "Larghezza ripetizione (m)", 1.4)
    unreal.EditorAssetLibrary.save_loaded_asset(mi, False)


def box(label, loc, size, rot=(0, 0, 0), mat=None, mesh=CUBE):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.set_actor_label(label)
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset(mesh))
    a.set_actor_scale3d(unreal.Vector(size[0] / 100, size[1] / 100, size[2] / 100))
    if mat:
        c.set_material(0, mat)
    a.set_folder_path(FOLDER + "/Terreno")
    return a


def road(label, points, **props):
    a = EAS.spawn_actor_from_class(unreal.M80Road, unreal.Vector(*points[0]))
    a.set_actor_label(label)
    a.set_folder_path(FOLDER)
    path = a.get_component_by_class(unreal.SplineComponent)
    path.set_spline_points([unreal.Vector(*p) for p in points], unreal.SplineCoordinateSpace.WORLD, True)
    for k, v in props.items():
        a.set_editor_property(k, v)
    a.rebuild()
    unreal.log("ROAD %s: %d pezzi" % (label, a.get_editor_property("piece_count")))
    return a


def build_roads():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    for a in EAS.get_all_level_actors():
        if str(a.get_folder_path()).startswith(FOLDER):
            a.destroy_actor()
    ground = unreal.load_asset("/Game/Mazzarino80/Vehicles/M_M80_ProvaGuida_Suolo") or unreal.load_asset(KIT + "/MI_M80_Cemento")
    # South of the stairs: a bank sloping sideways (6 degrees), a hump and a ramp up to a 2.5 m edge.
    box("Pendio_laterale", (500, -3600, 0), (5200, 1800, 200), rot=(6, 0, 0), mat=ground)
    box("Rampa", (300, -5300, -20), (3400, 1600, 200), rot=(0, 7, 0), mat=ground)
    # A 50 cm hump: two gentle ramps meeting at a crest (boxes: their collision matches what is seen).
    box("Dosso_a", (-2100, -5300, -50), (1200, 1600, 200), rot=(0, 5, 0), mat=ground)
    box("Dosso_b", (-1000, -5300, -50), (1200, 1600, 200), rot=(0, -5, 0), mat=ground)
    S = unreal.M80RoadSurface
    # 1. The main lava road across the side slope, with a bend: it tilts with the bank.
    road("1_Lavica_principale", [(-2100, -3700, 0), (400, -3450, 0), (2900, -3800, 0)], surface=S.MAIN_LAVA, width_cm=600)
    # 2. The cambered lava road on flat ground, turning.
    road("2_Lavica_bombata", [(-2300, -2500, 0), (0, -2500, 0), (1800, -2700, 0), (2800, -3100, 0)], surface=S.CURVED_LAVA, width_cm=500)
    # 3. The secondary lava slab over a hump and up the ramp: draped on the terrain.
    road("3_Lastra_lavica_secondaria", [(-2800, -5300, 0), (-500, -5300, 0), (1700, -5150, 0)], surface=S.SLAB, width_cm=450)


VIEWS = {
    "panoramica_strade": ((-3600, -7600, 1900), (300, -4000, 0)),
    "1_lavica_principale": ((-2600, -2700, 420), (600, -3600, 60)),
    "1_pendio_laterale": ((700, -1900, 260), (700, -3600, 80)),
    "2_lavica_bombata": ((-2700, -1700, 330), (1000, -2700, 0)),
    "3_lastra_secondaria": ((-3600, -4300, 450), (300, -5250, 120)),
    "3_lastra_rampa": ((2600, -4400, 600), (500, -5200, 250)),
    "dettaglio_lastra": ((-1400, -5000, 140), (-800, -5300, 40)),
    "dettaglio_lavica": ((-700, -3150, 160), (-200, -3500, 80)),
}


def views():
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    for name, (eye, target) in VIEWS.items():
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        cap.capture(unreal.Vector(*eye), rot, RENDER / ("%s.png" % name))
        yield 2
    cap.destroy()


def steps():
    fix_textures()
    yield 5
    lava_instance(lava_master())
    yield 5
    build_roads()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 600
    for _ in views():
        yield 2
    yield 200
    for _ in views():
        yield 2


m80_seq.Sequencer(steps(), log_file=str(ROOT / "Saved/Mazzarino80/Roads/setup_error.txt"))
