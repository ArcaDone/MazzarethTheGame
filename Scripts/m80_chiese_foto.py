"""Photos of the churches placed by m80_chiese_place.py in the town, under a temporary daylight (nothing saved): the
facade from above the houses in front, three quarters at roof height, and from the air. The editor viewport goes to each view first so Nanite streams it in.
Env M80_CHIESE=Key1,Key2 (default: every placed church).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_chiese_foto.py -ForceLit
Out: Saved/Mazzarino80/Chiese/Foto/<Key>_<view>.png
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
SRC = ROOT / "Saved/Mazzarino80/Chiese"
OUT = SRC / "Foto"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def daylight():
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 30000))
    sun.set_actor_rotation(unreal.Rotator(pitch=-42.0, yaw=-110.0, roll=0.0), False)
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("atmosphere_sun_light", True)
    c.set_intensity(7.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 20000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight) and a != sun:
            a.get_component_by_class(unreal.DirectionalLightComponent).set_visibility(False)


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    report = json.loads((SRC / "place_report.json").read_text(encoding="utf-8"))
    only = [k for k in os.environ.get("M80_CHIESE", "").split(",") if k]
    ks = [k for k in report if k != "saved_packages" and (not only or k in only)]
    ms = {k: json.loads((SRC / k / ("%s.json" % k)).read_text(encoding="utf-8")) for k in ks}
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    near = []
    for m in ms.values():
        near += m80_seq.near(descs, *m["osm_centroid_world_cm"], 9000)
    m80_seq.load(near + m80_seq.actor_descs("LandscapeStreamingProxy"))
    yield 300
    m80_seq.console("r.TextureStreaming 0")
    daylight()
    yield 120
    for k in ks:
        m = ms[k]
        loc = report[k]["location"]
        yaw = math.radians(-m["rotation_deg"])
        cx, cy = m["osm_centroid_world_cm"]
        z = loc[2]
        fd = math.radians(-m.get("facade_dir_deg", 0.0)) + yaw
        fx, fy = math.cos(fd), math.sin(fd)          # facade direction in Unreal
        L = max(m["extent_m"]) * 100
        views = {
            # Over the houses in front (the town is dense: from the street the next house hides the church).
            "fronte": ((cx + fx * (0.5 * L + 1800), cy + fy * (0.5 * L + 1800), z + 900), (cx + fx * 0.3 * L, cy + fy * 0.3 * L, z + 600), 75),
            "tre_quarti": ((cx + fx * (0.5 * L + 1400) + fy * (0.5 * L + 1400), cy + fy * (0.5 * L + 1400) - fx * (0.5 * L + 1400), z + 0.4 * L + 1000), (cx, cy, z + 500), 70),
            "aereo": ((cx + fx * L * 0.9 - fy * L * 0.7, cy + fy * L * 0.9 + fx * L * 0.7, z + 0.9 * L + 1500), (cx, cy, z + 300), 60),
        }
        for name, (e, t, fov) in views.items():
            e, t = unreal.Vector(*e), unreal.Vector(*t)
            rot = unreal.MathLibrary.find_look_at_rotation(e, t)
            m80_seq.set_view(e, rot)
            yield 240
            cap = m80_seq.ViewCapture(1600, 900, fov)
            cap.capture(e, rot, OUT / ("%s_%s.png" % (k, name)))
            cap.destroy()
            yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
