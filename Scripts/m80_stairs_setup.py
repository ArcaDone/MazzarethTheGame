"""Stairs kit: imports the textures of m80_stairs_textures.py, makes the materials used by the
"Scalinata (Mazzarino)" actor (/Game/Mazzarino80/Kit/Stairs) and builds the test level
/Game/Mazzarino80/Kit/Stairs/L_M80_ProvaScalinate (rebuilt from scratch each run) with examples:
a straight stair onto a terrace, a stepped path (cordonata) on a slope, a stair turning down from the
terrace, a slab stair onto a platform, low walls and fences on their own. Renders go to
Saved/Mazzarino80/Stairs/Render.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_stairs_setup.py -ForceLit
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
KIT = "/Game/Mazzarino80/Kit/Stairs"
MAP = KIT + "/L_M80_ProvaScalinate"
SRC = ROOT / "Saved/Mazzarino80/Stairs/Textures"
RENDER = ROOT / "Saved/Mazzarino80/Stairs/Render"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
CUBE = "/Engine/BasicShapes/Cube"
# Texture sets: metres per repeat (the meshes have one UV unit per metre).
SETS = {"PietraLavica": 1.0, "Basolato": 1.2, "MuroConci": 2.0, "Cemento": 2.0, "Legno": 1.0}
COLOURS = {"Ferro": ((0.035, 0.033, 0.03), 0.55, 0.6), "Canne": ((0.20, 0.15, 0.075), 0.7, 0.0)}


def import_textures():
    tasks = []
    for name in SETS:
        for m in ("D", "N", "ORM"):
            t = unreal.AssetImportTask()
            t.filename = str(SRC / ("T_M80_%s_%s.png" % (name, m)))
            t.destination_path = KIT + "/Textures"
            t.replace_existing = True
            t.automated = True
            t.save = False
            tasks.append(t)
    TOOLS.import_asset_tasks(tasks)
    for name in SETS:
        n = unreal.load_asset("%s/Textures/T_M80_%s_N" % (KIT, name))
        n.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        n.set_editor_property("srgb", False)
        n.set_editor_property("flip_green_channel", True)          # made OpenGL-style
        o = unreal.load_asset("%s/Textures/T_M80_%s_ORM" % (KIT, name))
        o.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        o.set_editor_property("srgb", False)
        for t in (n, o, unreal.load_asset("%s/Textures/T_M80_%s_D" % (KIT, name))):
            unreal.EditorAssetLibrary.save_loaded_asset(t)


def new_material(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    return TOOLS.create_asset(path.rsplit("/", 1)[1], path.rsplit("/", 1)[0], unreal.Material, unreal.MaterialFactoryNew())


def node(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def stone_master():
    """Textured master: UV0 (metres) / TileM -> D (tinted), N, ORM (AO, roughness)."""
    m = new_material(KIT + "/M_M80_KitPietra")
    tc = node(m, unreal.MaterialExpressionTextureCoordinate, -1100, 0)
    tile = node(m, unreal.MaterialExpressionScalarParameter, -1100, 150, parameter_name="TileM", default_value=1.0)
    uv = node(m, unreal.MaterialExpressionDivide, -900, 0)
    MEL.connect_material_expressions(tc, "", uv, "A")
    MEL.connect_material_expressions(tile, "", uv, "B")
    st = unreal.MaterialSamplerType
    samp = {}
    for i, (k, s) in enumerate((("D", st.SAMPLERTYPE_COLOR), ("N", st.SAMPLERTYPE_NORMAL), ("ORM", st.SAMPLERTYPE_MASKS))):
        tex = unreal.load_asset("%s/Textures/T_M80_PietraLavica_%s" % (KIT, k))
        e = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -600, -300 + i * 300, parameter_name=k, texture=tex, sampler_type=s)
        MEL.connect_material_expressions(uv, "", e, "UVs")
        samp[k] = e
    tint = node(m, unreal.MaterialExpressionVectorParameter, -600, 600, parameter_name="Tinta", default_value=unreal.LinearColor(1, 1, 1, 1))
    col = node(m, unreal.MaterialExpressionMultiply, -250, -300)
    MEL.connect_material_expressions(samp["D"], "RGB", col, "A")
    MEL.connect_material_expressions(tint, "", col, "B")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(samp["N"], "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(samp["ORM"], "G", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(samp["ORM"], "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def colour_master():
    m = new_material(KIT + "/M_M80_KitColore")
    c = node(m, unreal.MaterialExpressionVectorParameter, -500, 0, parameter_name="Colore", default_value=unreal.LinearColor(0.5, 0.5, 0.5, 1))
    r = node(m, unreal.MaterialExpressionScalarParameter, -500, 200, parameter_name="Ruvidita", default_value=0.6)
    mt = node(m, unreal.MaterialExpressionScalarParameter, -500, 300, parameter_name="Metallo", default_value=0.0)
    MEL.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(mt, "", unreal.MaterialProperty.MP_METALLIC)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def instance(name, parent):
    path = "%s/MI_M80_%s" % (KIT, name)
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    mi = TOOLS.create_asset("MI_M80_" + name, KIT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    return mi


def materials():
    stone, colour = stone_master(), colour_master()
    for name, tile in SETS.items():
        mi = instance(name, stone)
        for k in ("D", "N", "ORM"):
            MEL.set_material_instance_texture_parameter_value(mi, k, unreal.load_asset("%s/Textures/T_M80_%s_%s" % (KIT, name, k)))
        MEL.set_material_instance_scalar_parameter_value(mi, "TileM", tile)
        unreal.EditorAssetLibrary.save_loaded_asset(mi)
    for name, (rgb, rough, metal) in COLOURS.items():
        mi = instance(name, colour)
        MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(*rgb, 1))
        MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", rough)
        MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", metal)
        unreal.EditorAssetLibrary.save_loaded_asset(mi)


def box(label, loc, size, rot=(0, 0, 0), mat=None):
    """Static block: loc is its centre, size in cm (the engine cube is 100 cm); rot is (roll, pitch, yaw)."""
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.set_actor_label(label)
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset(CUBE))
    a.set_actor_scale3d(unreal.Vector(size[0] / 100, size[1] / 100, size[2] / 100))
    if mat:
        c.set_material(0, mat)
    a.set_folder_path("Terreno")
    return a


def stairs(label, points, **props):
    a = EAS.spawn_actor_from_class(unreal.M80Stairs, unreal.Vector(*points[0]))
    a.set_actor_label(label)
    a.set_folder_path("Scalinate")
    path = a.get_component_by_class(unreal.SplineComponent)
    path.set_spline_points([unreal.Vector(*p) for p in points], unreal.SplineCoordinateSpace.WORLD, True)
    for k, v in props.items():
        a.set_editor_property(k, v)
    a.rebuild()
    unreal.log("STAIRS %s: %d gradini, %d pianerottoli, alzata %.1f, pedata %.1f" % (
        label, a.get_editor_property("step_count"), a.get_editor_property("landing_count"),
        a.get_editor_property("real_riser_cm"), a.get_editor_property("real_tread_cm")))
    return a


def build_level():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -38, 130))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(2.0)          # readable shadows
    EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    ground = unreal.load_asset("/Game/Mazzarino80/Vehicles/M_M80_ProvaGuida_Suolo") or unreal.load_asset(KIT + "/MI_M80_Cemento")
    wall = unreal.load_asset(KIT + "/MI_M80_Cemento")
    box("Suolo", (500, 0, -50), (12000, 12000, 100), mat=ground)
    box("Terrazza", (750, -1200, 150), (1500, 1600, 300), mat=wall)
    box("Piattaforma", (3300, -1200, 100), (600, 600, 200), mat=wall)
    # A 10 % slope 25 m long, then a plateau 2.5 m up.
    box("Salita", (255, 600, 125 - 50 * 0.995), (2512, 800, 100), rot=(0, 5.71, 0), mat=ground)
    box("Salita_ripiano", (2000, 600, 125), (1000, 800, 250), mat=ground)

    K, S, F, T, W = unreal.M80StairsKind, unreal.M80StairsSide, unreal.M80FenceKind, unreal.M80TreadFinish, unreal.M80StairsWallFinish
    # 1. Straight stair onto the terrace, retaining walls flush with the steps and wrought-iron railings.
    stairs("1_Scalinata_terrazza", [(-560, -1200, 0), (30, -1200, 300)], kind=K.STEPS, width_cm=300, riser_cm=16,
           wall_sides=S.BOTH, wall_height_cm=0, fence_kind=F.WROUGHT_IRON, fence_sides=S.BOTH)
    # 2. Cordonata up the slope: long setts treads with lava edges, tubular railing on the right.
    stairs("2_Cordonata", [(-1150, 600, 0), (1550, 600, 250)], kind=K.STEPPED_PATH, width_cm=400, riser_cm=12, tread_cm=180,
           fence_kind=F.IRON_TUBE, fence_sides=S.RIGHT)
    # 3. Down from the terrace, turning south: solid to the ground, stone parapet outside, wooden fence inside.
    stairs("3_Scalinata_curva", [(1300, -700, 300), (1750, -700, 300), (2050, -400, 300), (2100, 150, 0)], kind=K.STEPS,
           width_cm=220, riser_cm=17, wall_sides=S.LEFT, wall_height_cm=90, fence_kind=F.WOOD, fence_sides=S.RIGHT)
    # 4. Slab stair (not filled) onto the platform, lava treads, railings both sides.
    stairs("4_Scala_soletta", [(2350, -1200, 0), (3030, -1200, 200)], kind=K.STEPS, width_cm=160, riser_cm=17,
           fill_to_ground=False, tread_finish=T.LAVA, fence_kind=F.WROUGHT_IRON, fence_sides=S.BOTH)
    # 5. Walls and fences alone: a concrete wall with a tubular rail, a reed fence, a stone wall.
    stairs("5_Muretto_tubolare", [(-1500, 1800, 0), (0, 1900, 0), (1500, 1800, 0)], kind=K.FENCE_ONLY, wall_sides=S.LEFT,
           wall_height_cm=70, wall_finish=W.CONCRETE, fence_kind=F.IRON_TUBE, fence_sides=S.LEFT)
    stairs("5_Staccionata_canne", [(-1500, 2500, 0), (1500, 2700, 0)], kind=K.FENCE_ONLY, fence_kind=F.CANE, fence_sides=S.LEFT,
           fence_height_cm=160)
    stairs("5_Muretto_conci", [(-1500, 3200, 0), (1500, 3200, 0)], kind=K.FENCE_ONLY, wall_sides=S.LEFT, wall_height_cm=110,
           wall_finish=W.STONE)


VIEWS = {
    "1_scalinata_terrazza": ((-1400, -2300, 450), (-150, -1200, 120)),
    "1_scalinata_dettaglio": ((-750, -1000, 220), (-250, -1200, 100)),
    "2_cordonata": ((-1700, 1300, 350), (300, 600, 100)),
    "2_cordonata_dall_alto": ((1900, 900, 520), (200, 600, 100)),
    "3_scalinata_curva": ((2900, 700, 650), (1800, -350, 150)),
    "4_scala_soletta": ((2300, -300, 350), (2750, -1200, 80)),
    "5_muretti_staccionate": ((-2300, 1100, 380), (0, 2600, 60)),
    "panoramica": ((-2600, -3600, 2200), (900, 200, 0)),
}


def views():
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    for name, (eye, target) in VIEWS.items():
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        cap.capture(unreal.Vector(*eye), rot, RENDER / ("%s.png" % name))
        yield 2
    cap.destroy()


def steps():
    import_textures()
    yield 5
    materials()
    yield 5
    build_level()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    # Shaders of the new materials and the sky capture.
    yield 900
    for _ in views():
        yield 2
    yield 300
    for _ in views():                    # second pass, after everything has streamed in
        yield 2


m80_seq.Sequencer(steps(), log_file=str(ROOT / "Saved/Mazzarino80/Stairs/setup_error.txt"))
