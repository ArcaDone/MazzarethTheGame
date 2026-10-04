"""Builds the test-drive level /Game/Mazzarino80/Vehicles/L_M80_ProvaGuida (rebuilt from scratch each run).

Game mode "Prova guida (Mazzarino)": Play possesses the first car, Tab switches car; HUD with speed,
gear and rpm. Areas (signs on the ground): 400 m straight, ramps at 10/20/30 %, a 12 % street climb
like the town, slalom, a 25 m circle, a narrow alley (4 m) with a right-angle bend, speed bumps and a
patch of uneven paving. Cars: Fiat 126 and Ape (drivable), the old car as a parked prop.
"""
import math
import os
import random
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida"
GROUND_MAT = "/Game/Mazzarino80/Vehicles/M_M80_ProvaGuida_Suolo"
OUT = ROOT / "Saved/Mazzarino80/Vehicles/drive_level.txt"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
CUBE = "/Engine/BasicShapes/Cube"
CYL = "/Engine/BasicShapes/Cylinder"
CONE = "/Engine/BasicShapes/Cone"


def ground_material():
    if unreal.EditorAssetLibrary.does_asset_exist(GROUND_MAT):
        return unreal.load_asset(GROUND_MAT)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(GROUND_MAT.rsplit("/", 1)[1], GROUND_MAT.rsplit("/", 1)[0],
                                                                 unreal.Material, unreal.MaterialFactoryNew())
    wp = MEL.create_material_expression(m, unreal.MaterialExpressionWorldPosition, -900, 0)
    xy = MEL.create_material_expression(m, unreal.MaterialExpressionComponentMask, -750, 0)
    xy.set_editor_property("r", True)
    xy.set_editor_property("g", True)
    MEL.connect_material_expressions(wp, "", xy, "")
    div = MEL.create_material_expression(m, unreal.MaterialExpressionDivide, -600, 0)
    div.set_editor_property("const_b", 240.0)
    MEL.connect_material_expressions(xy, "", div, "A")
    for i, (name, prop) in enumerate((("D", unreal.MaterialProperty.MP_BASE_COLOR), ("N", unreal.MaterialProperty.MP_NORMAL))):
        t = unreal.load_asset("/Game/Mazzarino80/Terrain/Textures/T_M80_Pavers_" + name)
        e = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, -350, i * 300)
        e.set_editor_property("texture", t)
        e.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if name == "N" else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
        MEL.connect_material_expressions(div, "", e, "UVs")
        MEL.connect_material_property(e, "RGB", prop)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -350, 600)
    r.set_editor_property("r", 0.8)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def box(label, loc, size, rot=(0, 0, 0), mesh=CUBE, mat=None, folder="Pista"):
    """Static block; size in cm (the engine cube is 100 cm)."""
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator(*rot))
    a.static_mesh_component.set_static_mesh(unreal.load_asset(mesh))
    a.set_actor_scale3d(unreal.Vector(size[0] / 100, size[1] / 100, size[2] / 100))
    if mat:
        a.static_mesh_component.set_material(0, mat)
    a.set_actor_label(label)
    a.set_folder_path(folder)
    return a


def sign(text, loc, yaw=0):
    a = EAS.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(*loc), unreal.Rotator(0, 90, yaw))
    c = a.text_render
    c.set_text(text)
    c.set_world_size(140)
    c.set_text_render_color(unreal.Color(255, 220, 120, 255))
    c.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    a.set_folder_path("Cartelli")
    return a


def ramp(label, x, y, grade, length=2000, width=700, plateau=1200):
    """Up ramp, flat top, down ramp (all along +X)."""
    ang = math.degrees(math.atan(grade))
    h = length * grade
    run_len = length / math.cos(math.radians(ang))
    box(label + "_su", (x + length / 2, y, h / 2 - 10), (run_len, width, 20), (0, ang, 0))
    box(label + "_piano", (x + length + plateau / 2, y, h - 10), (plateau, width, 20))
    box(label + "_giu", (x + length + plateau + length / 2, y, h / 2 - 10), (run_len, width, 20), (0, -ang, 0))
    box(label + "_base", (x + length + plateau / 2, y, h / 2 - 20), (plateau, width, h - 20))
    sign(label, (x - 300, y, 5), 0)


def run():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)  # new_level does not replace an existing map
    unreal.EditorLevelLibrary.new_level(MAP)
    yield 10
    if not m80_seq.editor_world().get_path_name().startswith(MAP):
        raise RuntimeError("Expected " + MAP)
    mat = ground_material()
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -35, 40))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    fog = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    fog.get_component_by_class(unreal.ExponentialHeightFogComponent).set_fog_density(0.004)
    # Ground: 2 km along the straight.
    box("Suolo", (60000, 0, -50), (200000, 80000, 100), mat=mat)  # 2 km x 800 m
    # Straight with distance marks every 100 m.
    sign("RETTILINEO 400 m", (1500, 0, 5), 0)
    for k in range(1, 5):
        box("Riga_%dm" % (k * 100), (k * 10000, 0, 1), (30, 900, 2), mat=None, folder="Pista/Righe")
        sign("%d m" % (k * 100), (k * 10000 - 300, 600, 5), 0)
    # Ramps.
    ramp("RAMPA 10%", 1500, 3000, 0.10)
    ramp("RAMPA 20%", 1500, 4200, 0.20)
    ramp("RAMPA 30%", 1500, 5400, 0.30, length=1500)
    # Town-like climb: 80 m at 12 % between walls, then a flat top.
    gx, gy = 10000, 3600
    ang = math.degrees(math.atan(0.12))
    box("Salita_12", (gx + 4000, gy, 480 / 2 - 10), (8000 / math.cos(math.radians(ang)), 600, 20), (0, ang, 0))
    box("Salita_12_base", (gx + 4000, gy, 230), (8000, 600, 460))
    box("Salita_12_cima", (gx + 9000, gy, 470), (2000, 600, 20))
    box("Salita_12_base_cima", (gx + 9000, gy, 230), (2000, 600, 460))
    box("Salita_muro_a", (gx + 4500, gy - 400, 400), (10000, 40, 800))
    box("Salita_muro_b", (gx + 4500, gy + 400, 400), (10000, 40, 800))
    sign("SALITA 12% (come in paese)", (gx - 300, gy, 5), 0)
    # Slalom: cones every 14 m.
    sign("SLALOM", (1500, -3000, 5), 0)
    for k in range(10):
        box("Cono_%d" % k, (3000 + k * 1400, -3000 + (150 if k % 2 else -150), 40), (60, 60, 80), mesh=CONE, folder="Pista/Coni")
    # 25 m circle.
    cx, cy = -6000, 0
    sign("CERCHIO r 25 m", (cx, cy, 5), 0)
    for k in range(24):
        a = 2 * math.pi * k / 24
        box("Cerchio_%d" % k, (cx + math.cos(a) * 2500, cy + math.sin(a) * 2500, 40), (60, 60, 80), mesh=CONE, folder="Pista/Coni")
    # Narrow alley 4 m with a right-angle bend.
    ax, ay = 3000, -7000
    sign("VICOLO 4 m", (ax - 400, ay, 5), 0)
    box("Vicolo_a1", (ax + 2500, ay - 220, 350), (5000, 40, 700))
    box("Vicolo_b1", (ax + 2300, ay + 220, 350), (4600, 40, 700))
    box("Vicolo_a2", (ax + 5220, ay + 2300, 350), (40, 5000, 700))
    box("Vicolo_b2", (ax + 4780, ay + 2500, 350), (40, 4600, 700))
    # Speed bumps and uneven paving.
    bx, by = 12000, -3000
    sign("DOSSI E BASOLATO", (bx - 400, by, 5), 0)
    for k in range(5):
        box("Dosso_%d" % k, (bx + k * 1500, by, -2), (60, 700, 60), (90, 0, 0), mesh=CYL, folder="Pista/Dossi")
    rnd = random.Random(5)
    for i in range(18):
        for j in range(6):
            box("Basolo", (bx + 8000 + i * 110, by - 300 + j * 110, rnd.uniform(-2, 3)), (105, 105, 10), (rnd.uniform(-2, 2), rnd.uniform(-2, 2), 0),
                mat=mat, folder="Pista/Basolato")
    # Cars on the start line, facing +X.
    fiat = EAS.spawn_actor_from_class(unreal.M80CarFiat126, unreal.Vector(0, -350, 60), unreal.Rotator(0, 0, 0))
    fiat.set_actor_label("A_Fiat126")
    ape = EAS.spawn_actor_from_class(unreal.M80CarApe, unreal.Vector(0, 350, 70), unreal.Rotator(0, 0, 0))
    ape.set_actor_label("B_Ape")
    # The cars imported from Blender (Scripts/m80_import_blender_assets.py), further along the line.
    for label, cls, y in (("C_Panda", "M80CarPanda", -1050), ("D_Fiat127", "M80CarFiat127", 1050), ("E_FiatUno", "M80CarFiatUno", -1750),
                          ("F_Golf", "M80CarGolf", 1750), ("G_Vespa", "M80CarVespa", 2450)):
        c = getattr(unreal, cls, None)
        if c:
            EAS.spawn_actor_from_class(c, unreal.Vector(0, y, 70), unreal.Rotator(0, 0, 0)).set_actor_label(label)
    old = EAS.spawn_actor_from_class(unreal.EditorAssetLibrary.load_blueprint_class("/Game/Drive/AutoFake/OldCar"), unreal.Vector(-800, -900, 0),
                                     unreal.Rotator(0, 0, 30))
    old.set_actor_label("Auto_ferma_OldCar")
    ws = m80_seq.editor_world().get_world_settings()
    ws.set_editor_property("default_game_mode", unreal.M80DriveTestGameMode)
    yield 10
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("ok " + MAP, encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
