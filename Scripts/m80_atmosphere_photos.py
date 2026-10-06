"""Cinematic 21:9 shots of the town taken from the editor viewport (Lumen GI, real eye adaptation, like a
screenshot in the editor), at chosen hours and weathers set on the "Atmosfera (Mazzarino)" actor.
The map is not saved. Output: Saved/Mazzarino80/Foto/cine_*.png. Env M80_CINE_ONLY=name1,name2.
"""
import glob
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402
import m80_town_views as setup  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Houses/Maps/L_M80_Paese"
OUT = ROOT / "Saved/Mazzarino80/Foto"
SHOTS_DIR = ROOT / "Saved/Screenshots"
ONLY = [n for n in os.environ.get("M80_CINE_ONLY", "").split(",") if n]
REPORT = ROOT / "Saved/Mazzarino80/cine_report.json"


def shots(world, atmo, horizon):
    c = setup.town_centre()
    gz = setup.ground(world, c.x, c.y) or c.z
    up = unreal.Vector(0, 0, gz - c.z)
    east = unreal.Vector(math.cos(math.radians(-8.5)), math.sin(math.radians(-8.5)), 0)
    ey = math.radians(horizon.get_editor_property("etna_yaw"))
    etna = unreal.Vector(math.cos(ey), math.sin(ey), 0)
    W = unreal.M80Weather
    out = [
        ("cine_1_alba_tetti", 6.6, W.HAZY, c - east * 2500 + up + unreal.Vector(0, 0, 1600), c + east * 30000 + up + unreal.Vector(0, 0, 300), 55),
        ("cine_3_scirocco_mezzogiorno", 13.5, W.SCIROCCO, c + up + unreal.Vector(-45000, 40000, 18000), c + up, 50),
        ("cine_4_etna_teleobiettivo", 19.3, W.CLEAR, c + up + unreal.Vector(0, 0, 3500), c + etna * 4500000 + unreal.Vector(0, 0, 60000), 9),
        ("cine_5_tramonto_controluce", 19.45, W.HAZY, c + east * 9000 + up + unreal.Vector(0, 0, 2600), c - east * 20000 + up + unreal.Vector(0, 0, -500), 45),
        ("cine_6_tramonto_facciate", 19.2, W.HAZY, c - east * 7000 + up + unreal.Vector(0, 6000, 2200), c + up + unreal.Vector(0, 0, 300), 50),
        ("cine_7_ora_blu", 20.55, W.CLEAR, c + up + unreal.Vector(-30000, -25000, 9000), c + up, 45),
        ("cine_9_paese_pomeriggio", 17.0, W.HAZY, c + up + unreal.Vector(-60000, 70000, 30000), c + up, 50),
    ]
    street = setup.corso_shot(world, c)
    if street:
        eye, target = street
        out.insert(1, ("cine_2_mattina_corso", 9.3, W.CLEAR, eye, target, 60))
        out.append(("cine_8_notte_corso", 22.6, W.CLEAR, eye, target, 60))
    return [s for s in out if not ONLY or s[0] in ONLY]


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 120
    world = m80_seq.editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    atmo = next(a for a in actors if isinstance(a, unreal.M80Atmosphere))
    horizon = next(a for a in actors if isinstance(a, unreal.M80Horizon))
    cam = eas.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, 0))
    cc = cam.get_editor_property("camera_component")
    cc.set_editor_property("constrain_aspect_ratio", False)
    report = {}
    yield 300   # Nanite, distance fields and Lumen settle
    for name, hour, weather, eye, target, fov in shots(world, atmo, horizon):
        atmo.set_editor_property("weather", weather)
        atmo.set_hour(hour)
        d = target - eye
        rot = unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))
        cam.set_actor_location_and_rotation(eye, rot, False, False)
        cc.set_editor_property("field_of_view", fov)
        # Pilot the viewport through the camera so Lumen and the exposure adapt to the shot.
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).pilot_level_actor(cam)
        yield 240
        start = time.time()
        unreal.AutomationLibrary.take_high_res_screenshot(2560, 1080, name + ".png", cam, False, False,
                                                          unreal.ComparisonTolerance.LOW, "", 0.0, True)
        yield 60
        found = sorted(glob.glob(str(SHOTS_DIR / "**" / (name + "*.png")), recursive=True), key=os.path.getmtime)
        if found and os.path.getmtime(found[-1]) >= start - 1:
            shutil.copyfile(found[-1], OUT / (name + ".png"))
            report[name] = "ok"
        else:
            report[name] = "missing"
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).eject_pilot_level_actor()
    cam.destroy_actor()
    atmo.set_editor_property("weather", unreal.M80Weather.HAZY)
    atmo.apply()
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
