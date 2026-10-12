"""Test of the procedural bougainvillea (AM80Bougainvillea) away from the houses in the town map, nothing saved: a 1.5 m
cube with a climbing magenta plant spilling over its edges, a sphere with a violet one, a free orange bush, a wall with
a red plant running along its top; photographed under a temporary daylight.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bouganvillea_prova.py -ForceLit
Out: Saved/Mazzarino80/Bouganvillea/<test>_<view>.png, prova.json (branches, leaves, flowers, triangles)
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
OUT = ROOT / "Saved/Mazzarino80/Bouganvillea"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
SPOT = unreal.Vector(-300000, -300000, 60000)
V = unreal.Vector
C = unreal.M80BougainvilleaColour
# name: (prop mesh, prop offset, prop scale, plant offset, spline points (local), colour, climbing)
TESTS = {
    "Cubo": ("/Engine/BasicShapes/Cube", V(0, 0, 75), V(1.5, 1.5, 1.5), V(-90, -30, 0),
             [V(0, 0, 0), V(10, 5, 70), V(12, 15, 140), V(40, 30, 160), V(100, 40, 160)], C.MAGENTA, True),
    "Sfera": ("/Engine/BasicShapes/Sphere", V(900, 0, 100), V(2, 2, 2), V(900, -120, 0),
              [V(0, 0, 0), V(0, 15, 90), V(0, 60, 170), V(0, 120, 205)], C.VIOLA, True),
    "Cespuglio": (None, None, None, V(1800, 0, 0), [V(0, 0, 0), V(5, 0, 80), V(15, 5, 170)], C.ARANCIONE, False),
    "Muro": ("/Engine/BasicShapes/Cube", V(0, 1200, 150), V(0.25, 6, 3), V(-25, 900, 0),
             [V(0, 0, 0), V(-2, 10, 150), V(0, 30, 285), V(20, 120, 312), V(20, 400, 312), V(20, 560, 312)], C.ROSSO, True),
}


def daylight():
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, SPOT + V(0, 0, 5000))
    sun.set_actor_rotation(unreal.Rotator(pitch=-40.0, yaw=-130.0, roll=0.0), False)
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("atmosphere_sun_light", True)
    c.set_intensity(7.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, SPOT + V(0, 0, 3000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), SPOT - V(0, 0, 1))
    floor.set_actor_scale3d(V(100, 100, 1))
    return [sun, sky, floor]


def shoot(name, eye, target, fov=55):
    rot = unreal.MathLibrary.find_look_at_rotation(eye, target)
    m80_seq.set_view(eye, rot)
    yield 120
    cap = m80_seq.ViewCapture(1600, 1000, fov)
    cap.capture(eye, rot, OUT / ("%s.png" % name))
    cap.destroy()
    yield 3


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    m80_seq.console("r.TextureStreaming 0")
    spawned = daylight()
    yield 30
    report = {}
    plants = {}
    for name, (mesh, off, scale, at, pts, colour, climbing) in TESTS.items():
        if mesh:
            prop = EAS.spawn_actor_from_object(unreal.load_asset(mesh), SPOT + off)
            prop.set_actor_scale3d(scale)
            prop.get_component_by_class(unreal.StaticMeshComponent).set_material(
                0, unreal.load_asset("/Game/Mazzarino80/Buildings/Bartoli/Materiali/MI_M80_BG_Muro_D_Piazza") or
                unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
            spawned.append(prop)
        yield 2
        plant = EAS.spawn_actor_from_class(unreal.M80Bougainvillea, SPOT + at)
        plant.get_editor_property("stem").set_spline_points(pts, unreal.SplineCoordinateSpace.LOCAL, True)
        plant.set_editor_property("colour", colour)
        plant.set_editor_property("climbing", climbing)
        plant.rebuild()
        report[name] = plant.get_editor_property("build_info")
        plants[name] = plant
        spawned.append(plant)
        yield 5
    (OUT / "prova.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 600   # shaders of the new material instances
    for name, plant in plants.items():
        o, e = plant.get_actor_bounds(False)
        R = max(e.x, e.y, e.z) * 2.2 + 150
        for view, ang, h in (("fronte", 200, 0.25), ("lato", 270, 0.35), ("alto", 150, 0.9)):
            a = math.radians(ang)
            eye = o + V(math.cos(a) * R, math.sin(a) * R, R * h)
            yield from shoot("%s_%s" % (name, view), eye, o)
        # Close up on the flowers.
        yield from shoot(name + "_vicino", o + V(-e.x - 60, -60, e.z * 0.6), o + V(0, 0, e.z * 0.6), 40)
    for a in spawned:
        a.destroy_actor()


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
