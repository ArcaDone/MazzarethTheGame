"""Atmosphere of the town map (L_M80_Paese): one "Atmosfera (Mazzarino)" actor (sun at the real solar position,
moon, hazy sky, volumetric clouds, fog, warm filmic grade) replaces the plain Unreal sky actors, and an
"Orizzonte (colline ed Etna)" actor fills the land around the map out to the horizon.
Then photos at several hours: Saved/Mazzarino80/Foto/atmo_<hour>_<view>.png, and cinematic 21:9 shots
(dawn over the roofs, a morning alley, scirocco at noon, Etna with a long lens, sunset against the light
and on the facades, blue hour, night on the Corso): Saved/Mazzarino80/Foto/cine_*.png.
Env: M80_ATMO_MAP, M80_ATMO_SKIP_SETUP=1 (only photos), M80_ATMO_HOURS="7,10,13.5,18.5,20.3,22.5",
     M80_ATMO_SAVE=0 (try without saving the map).
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402
from m80_town_views import corso_shot, ground, town_centre  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_ATMO_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
SKY = "/Game/Mazzarino80/Sky"
OUT = ROOT / "Saved/Mazzarino80/Foto"
REPORT = ROOT / "Saved/Mazzarino80/atmosphere_report.json"
CINEMATIC = os.environ.get("M80_ATMO_CINEMATIC", "1") == "1"
HOURS = [float(h) for h in os.environ.get("M80_ATMO_HOURS", "7,10,13.5,18.5,20.3,22.5").split(",")]
SKIP_SETUP = os.environ.get("M80_ATMO_SKIP_SETUP") == "1"
SAVE = os.environ.get("M80_ATMO_SAVE", "1") == "1"
PHOTOS = os.environ.get("M80_ATMO_PHOTOS", "1") == "1"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
OLD_SKY = (unreal.DirectionalLight, unreal.SkyAtmosphere, unreal.SkyLight, unreal.ExponentialHeightFog, unreal.VolumetricCloud)


def horizon_material():
    path = SKY + "/M_M80_Horizon"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    m = TOOLS.create_asset("M_M80_Horizon", SKY, unreal.Material, unreal.MaterialFactoryNew())
    vc = MEL.create_material_expression(m, unreal.MaterialExpressionVertexColor, -400, 0)
    MEL.connect_material_property(vc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.92)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    spec = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 300)
    spec.set_editor_property("r", 0.25)
    MEL.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def material_values():
    """Parameter collection written by the atmosphere: Finestre (rooms behind windows), Notte (0 day, 1 night)."""
    path = SKY + "/MPC_M80_Atmosfera"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    mpc = TOOLS.create_asset("MPC_M80_Atmosfera", SKY, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    params = []
    for name, value in (("Finestre", 1.0), ("Notte", 0.0)):
        p = unreal.CollectionScalarParameter()
        p.set_editor_property("parameter_name", name)
        p.set_editor_property("default_value", value)
        params.append(p)
    mpc.set_editor_property("scalar_parameters", params)
    EAL.save_loaded_asset(mpc)
    return mpc


def cloud_material(report):
    path = SKY + "/MI_M80_Clouds"
    parent = unreal.load_asset("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud")
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "MI_M80_Clouds", SKY, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    report["cloud_scalar_params"] = [str(n) for n in MEL.get_scalar_parameter_names(parent)]
    report["cloud_vector_params"] = [str(n) for n in MEL.get_vector_parameter_names(parent)]
    EAL.save_loaded_asset(mi)
    return mi


def look(cap, eye, target, name):
    d = target - eye
    rot = unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))
    cap.capture(eye, rot, OUT / ("atmo_" + name + ".png"))


def cinematic(world, atmo, c, gz, etna_yaw, street):
    """Shots chosen like frames of a film: (name, hour, weather, eye, target, field of view)."""
    east = unreal.Vector(math.cos(math.radians(-8.5)), math.sin(math.radians(-8.5)), 0)
    etna = unreal.Vector(math.cos(etna_yaw), math.sin(etna_yaw), 0)
    W = unreal.M80Weather
    shots = [
        ("cine_1_alba_tetti", 6.6, W.HAZY, c - east * 2500 + unreal.Vector(0, 0, gz - c.z + 1600), c + east * 30000 + unreal.Vector(0, 0, gz - c.z + 300), 55),
        ("cine_3_scirocco_mezzogiorno", 13.5, W.SCIROCCO, c + unreal.Vector(-45000, 40000, gz - c.z + 18000), c + unreal.Vector(0, 0, gz - c.z), 50),
        ("cine_4_etna_teleobiettivo", 18.9, W.HAZY, c + unreal.Vector(0, 0, gz - c.z + 3500), c + etna * 4500000 + unreal.Vector(0, 0, 60000), 9),
        ("cine_5_tramonto_controluce", 19.45, W.HAZY, c + east * 9000 + unreal.Vector(0, 0, gz - c.z + 2600), c - east * 20000 + unreal.Vector(0, 0, gz - c.z - 500), 45),
        ("cine_6_tramonto_facciate", 19.2, W.HAZY, c - east * 7000 + unreal.Vector(0, 6000, gz - c.z + 2200), c + unreal.Vector(0, 0, gz - c.z + 300), 50),
        ("cine_7_ora_blu", 20.55, W.CLEAR, c + unreal.Vector(-30000, -25000, gz - c.z + 9000), c + unreal.Vector(0, 0, gz - c.z), 45),
    ]
    if street:
        eye, target = street
        shots.insert(1, ("cine_2_mattina_corso", 9.3, W.CLEAR, eye, target, 60))
        shots.append(("cine_8_notte_corso", 22.6, W.CLEAR, eye, target, 60))
    cap = m80_seq.ViewCapture(2560, 1080, 60)
    yield 200
    for name, hour, weather, eye, target, fov in shots:
        atmo.set_editor_property("weather", weather)
        atmo.set_hour(hour)
        cap.comp.set_editor_property("fov_angle", fov)
        yield 150
        look(cap, eye, target, "_riscaldamento")
        yield 30
        d = target - eye
        rot = unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))
        cap.capture(eye, rot, OUT / (name + ".png"))
        yield 5
    cap.destroy()
    atmo.set_editor_property("weather", W.HAZY)


def run():
    report = {"map": MAP}
    OUT.mkdir(parents=True, exist_ok=True)
    mpc = clouds = None
    if not SKIP_SETUP:
        horizon_material()
        clouds = cloud_material(report)
        mpc = material_values()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    report["post_process_volumes"] = [a.get_actor_label() for a in actors if isinstance(a, unreal.PostProcessVolume)]
    atmo = next((a for a in actors if isinstance(a, unreal.M80Atmosphere)), None)
    horizon = next((a for a in actors if isinstance(a, unreal.M80Horizon)), None)
    if not SKIP_SETUP:
        removed = []
        for a in actors:
            if isinstance(a, OLD_SKY) or "Sky_Sphere" in a.get_class().get_name():
                removed.append(a.get_actor_label())
                a.destroy_actor()
        report["removed"] = removed
        centre = town_centre()
        if not atmo:
            atmo = eas.spawn_actor_from_class(unreal.M80Atmosphere, centre)
            atmo.set_actor_label("Atmosfera")
            atmo.set_folder_path("Atmosfera")
        if not horizon:
            horizon = eas.spawn_actor_from_class(unreal.M80Horizon, unreal.Vector(0, 0, 0))
            horizon.set_actor_label("Orizzonte")
            horizon.set_folder_path("Atmosfera")
        if clouds:
            atmo.set_editor_property("cloud_material", clouds)
        if mpc:
            atmo.set_editor_property("material_values", mpc)
        horizon.rebuild()
        report["horizon"] = horizon.get_editor_property("build_info")
        atmo.apply()
        if SAVE:
            unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 30
    if not PHOTOS:
        REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
        return

    # Views: over the town from the south, towards Etna from the edge of town, a street, the Corso.
    c = town_centre()
    gz = ground(world, c.x, c.y) or c.z
    etna_yaw = math.radians(horizon.get_editor_property("etna_yaw"))   # north-east of the town
    views = {
        "paese": (c + unreal.Vector(-60000, 70000, 30000), c),
        "etna": (unreal.Vector(c.x, c.y, gz + 2500), unreal.Vector(c.x + math.cos(etna_yaw) * 100000, c.y + math.sin(etna_yaw) * 100000, gz + 2000)),
    }
    sx, sy = c.x + 1200, c.y + 300
    sz = ground(world, sx, sy)
    if sz is not None:
        views["strada"] = (unreal.Vector(sx, sy, sz + 170), unreal.Vector(sx + 3000, sy + 800, sz + 400))
    cap = m80_seq.ViewCapture(1920, 1080, 70)
    yield 300
    for h in HOURS:
        atmo.set_hour(h)
        yield 120   # sky light capture, Lumen and auto exposure settle
        for name, (eye, target) in views.items():
            look(cap, eye, target, "%05.2f_%s" % (h, name))
            yield 20
            look(cap, eye, target, "%05.2f_%s" % (h, name))
            yield 3
        report.setdefault("sun_elevation", {})[str(h)] = round(atmo.get_sun_elevation(), 1)
    cap.destroy()
    if CINEMATIC:
        yield from cinematic(world, atmo, c, gz, etna_yaw, corso_shot(world, c))
    atmo.apply()
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
