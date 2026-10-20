"""Test A of the realistic look, on a copy of the Matrice mini-town (L_M80_ProvaMatrice -> L_M80_ProvaMatrice_Look; the
original is not touched): an overcast sky (Atmosfera weather "Coperto", late morning), wet floors, the handheld camera
in Play, and the look of a real lens on top of the Mazzarino grade: barrel distortion (post-process material
M_M80_Obiettivo, instance MI_M80_Obiettivo), chromatic aberration at the edges, vignette, film grain, softer colours,
slow exposure. Then photos from the same views before (the town's summer haze at the same hour) and after, with the
editor viewport in game view (Lumen and Nanite as in game).
Env: M80_LOOK_RIFAI=1 copies the map again from the original; M80_LOOK_FOTO=0 skips the photos.
Out: Saved/Mazzarino80/Look/{prima,dopo}_<n>.png, look.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_look_realistico.py -ForceLit
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Look"
SOURCE = "/Game/Mazzarino80/Traffico/Maps/L_M80_ProvaMatrice"
MAP = SOURCE + "_Look"
LOOK = "/Game/Mazzarino80/Look"
VOLUME = "Look realistico (test A)"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
# Lens: k of the barrel distortion (0 = none); the image is scaled so that the corners stay the corners.
DISTORTION = 0.22
# "dopo": overcast; "prima": the town's own summer haze at the same hour.
# "dopo" also has wet floors (after rain) and the handheld camera in Play.
SKY = {"weather": unreal.M80Weather.OVERCAST, "hour": 10.5, "wetness": 0.7, "handheld_camera": True}
BEFORE = {"weather": unreal.M80Weather.HAZY, "hour": 10.5, "wetness": 0.0, "handheld_camera": False}


def set_sky(atmo, sky):
    for name, value in sky.items():
        atmo.set_editor_property(name, value)
    atmo.apply()


def lens_material():
    """Post-process material after tonemapping: samples the frame further out towards the edges (barrel distortion of
    a wide lens), normalised so that the corners keep their place."""
    path = LOOK + "/M_M80_Obiettivo"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    m = TOOLS.create_asset("M_M80_Obiettivo", LOOK, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property("blendable_location", unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    node = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)  # noqa: E731
    uv = node(unreal.MaterialExpressionScreenPosition, -1400, 0)
    half = node(unreal.MaterialExpressionConstant2Vector, -1400, 150)
    half.set_editor_property("r", 0.5)
    half.set_editor_property("g", 0.5)
    c = node(unreal.MaterialExpressionSubtract, -1200, 0)
    MEL.connect_material_expressions(uv, "ViewportUV", c, "A")
    MEL.connect_material_expressions(half, "", c, "B")
    r2 = node(unreal.MaterialExpressionDotProduct, -1050, 100)
    MEL.connect_material_expressions(c, "", r2, "A")
    MEL.connect_material_expressions(c, "", r2, "B")
    k = node(unreal.MaterialExpressionScalarParameter, -1050, 250)
    k.set_editor_property("parameter_name", "Distorsione")
    k.set_editor_property("default_value", DISTORTION)
    kr2 = node(unreal.MaterialExpressionMultiply, -900, 150)
    MEL.connect_material_expressions(k, "", kr2, "A")
    MEL.connect_material_expressions(r2, "", kr2, "B")
    one = node(unreal.MaterialExpressionConstant, -900, 300)
    one.set_editor_property("r", 1.0)
    grow = node(unreal.MaterialExpressionAdd, -750, 150)
    MEL.connect_material_expressions(one, "", grow, "A")
    MEL.connect_material_expressions(kr2, "", grow, "B")
    # Corners: r2 = 0.5, so dividing by 1 + k/2 keeps them in place.
    kh = node(unreal.MaterialExpressionMultiply, -900, 400)
    MEL.connect_material_expressions(k, "", kh, "A")
    half_s = node(unreal.MaterialExpressionConstant, -1050, 450)
    half_s.set_editor_property("r", 0.5)
    MEL.connect_material_expressions(half_s, "", kh, "B")
    corner = node(unreal.MaterialExpressionAdd, -750, 400)
    MEL.connect_material_expressions(one, "", corner, "A")
    MEL.connect_material_expressions(kh, "", corner, "B")
    scale = node(unreal.MaterialExpressionDivide, -600, 250)
    MEL.connect_material_expressions(grow, "", scale, "A")
    MEL.connect_material_expressions(corner, "", scale, "B")
    cs = node(unreal.MaterialExpressionMultiply, -450, 50)
    MEL.connect_material_expressions(c, "", cs, "A")
    MEL.connect_material_expressions(scale, "", cs, "B")
    src = node(unreal.MaterialExpressionAdd, -300, 50)
    MEL.connect_material_expressions(cs, "", src, "A")
    MEL.connect_material_expressions(half, "", src, "B")
    frame = node(unreal.MaterialExpressionSceneTexture, -150, 50)
    frame.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    MEL.connect_material_expressions(src, "", frame, "UVs")
    MEL.connect_material_property(frame, "Color", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


SKIPPED = []


def set_pp(settings, **values):
    """Sets and overrides each value; names this engine version does not have are noted in SKIPPED."""
    for name, value in values.items():
        try:
            settings.set_editor_property(name, value)
            settings.set_editor_property("override_" + name, True)
        except Exception:  # noqa: BLE001
            SKIPPED.append(name)


def lens_instance(base):
    """Instance of the lens material with this script's distortion (the value is tuned here, run after run)."""
    path = LOOK + "/MI_M80_Obiettivo"
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "MI_M80_Obiettivo", LOOK, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, base)
    MEL.set_material_instance_scalar_parameter_value(mi, "Distorsione", DISTORTION)
    EAL.save_loaded_asset(mi)
    return mi


def look_volume(world, material):
    """The volume of the look, spawned once; its settings are written again on every run."""
    found = [a for a in EAS.get_all_level_actors() if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == VOLUME]
    v = found[0] if found else EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    v.set_actor_label(VOLUME)
    v.set_editor_property("unbound", True)
    v.set_editor_property("priority", 10.0)
    s = v.get_editor_property("settings")
    set_pp(s,
           scene_fringe_intensity=4.0,              # chromatic aberration, at the edges
           chromatic_aberration_start_offset=0.2,
           vignette_intensity=0.7,
           film_grain_intensity=0.4,
           film_grain_texel_size=1.4,
           motion_blur_amount=0.6,
           motion_blur_max=4.0,
           bloom_intensity=0.9,
           white_temp=6300.0,                       # a little cool, as overcast daylight on video
           color_saturation=unreal.Vector4(0.86, 0.86, 0.86, 0.9),
           color_contrast=unreal.Vector4(1.08, 1.08, 1.08, 1.0),
           color_gain_highlights=unreal.Vector4(1.0, 1.0, 1.0, 1.0),
           auto_exposure_speed_up=1.2,              # the eye of a camera adapts slowly
           auto_exposure_speed_down=0.8,
           sharpen=0.4)
    s.set_editor_property("weighted_blendables",
                          unreal.WeightedBlendables(array=[unreal.WeightedBlendable(weight=1.0, object=material)]))
    v.set_editor_property("settings", s)
    return v


def views(world):
    """Eye-height views around the player start: its own direction, then turned, and one stepped back."""
    start = unreal.GameplayStatics.get_actor_of_class(world, unreal.PlayerStart)
    p, yaw = start.get_actor_location(), start.get_actor_rotation().yaw
    out = []
    for i, (turn, back) in enumerate(((0, 0), (110, 0), (-110, 0), (180, 0), (0, 900))):
        y = yaw + turn
        x0 = p.x - math.cos(math.radians(y)) * back
        y0 = p.y - math.sin(math.radians(y)) * back
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x0, y0, p.z + 3000), unreal.Vector(x0, y0, p.z - 3000),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        fields = hit.to_tuple() if hit else None
        z = fields[5].z if fields and fields[0] else p.z - 90
        out.append((unreal.Vector(x0, y0, z + 165), unreal.Rotator(roll=0.0, pitch=-3.0, yaw=y)))
    return out


def photos(tag, vs, report):
    for i, (loc, rot) in enumerate(vs):
        m80_seq.set_view(loc, rot)
        yield 240  # Nanite streaming, Lumen and the exposure settle
        since = time.time()
        m80_seq.console("HighResShot 1600x900")
        yield 30
        got = m80_seq.collect_screenshot(OUT / ("%s_%d.png" % (tag, i)), since - 1)
        report.setdefault(tag, []).append(str(got) if got else None)


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"map": MAP}
    if os.environ.get("M80_LOOK_RIFAI") == "1" and EAL.does_asset_exist(MAP):
        EAL.delete_asset(MAP)
    if not EAL.does_asset_exist(MAP):
        # Save As from the open original (duplicate_asset on a world leaves it loaded and the next map load asserts on
        # the leaked world). save_map keeps the original open: the copy is loaded right after.
        unreal.EditorLoadingAndSavingUtils.load_map(SOURCE)
        yield 30
        if not unreal.EditorLoadingAndSavingUtils.save_map(m80_seq.editor_world(), MAP):
            raise RuntimeError("copy failed: " + MAP)
        yield 5
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP + "."):
        raise RuntimeError("wrong map open: " + world.get_path_name())
    atmo = unreal.GameplayStatics.get_actor_of_class(world, unreal.M80Atmosphere)
    if not atmo:
        raise RuntimeError("no Atmosfera actor in " + MAP)
    material = lens_instance(lens_material())
    volume = look_volume(world, material)
    report["pp_skipped"] = SKIPPED
    before = BEFORE
    vs = views(world)
    report["views"] = [[v[0].x, v[0].y, v[0].z, v[1].yaw] for v in vs]
    if os.environ.get("M80_LOOK_FOTO", "1") == "1":
        unreal.SystemLibrary.execute_console_command(world, "r.TextureStreaming 0")
        unreal.EditorLevelLibrary.editor_set_game_view(True)   # no splines, icons or volume outlines in the photos
        volume.set_editor_property("enabled", False)
        set_sky(atmo, before)
        yield 30
        yield from photos("prima", vs, report)
        volume.set_editor_property("enabled", True)
        set_sky(atmo, SKY)
        yield 60
        yield from photos("dopo", vs, report)
        unreal.EditorLevelLibrary.editor_set_game_view(False)
    volume.set_editor_property("enabled", True)
    set_sky(atmo, SKY)
    if not m80_seq.editor_world().get_path_name().startswith(MAP + "."):
        raise RuntimeError("wrong map open before saving")
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    (OUT / "look.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
