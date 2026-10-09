"""Test level for the sidewalk magnet ("Attacca alle facciate"): /Game/Mazzarino80/Kit/Sidewalk/L_M80_ProvaMarciapiedi.

Two houses in a row (shared wall) and a third one turned by 20 degrees; sidewalks drawn roughly: one 1 m
inside the row, one 2 m off the turned house (within reach), one 6 m away (out of reach, stays where it is),
one turning round the back corner of the row (drawn with its curb on the house side: it moves to the street).
Then the turned house moves 1.5 m away from its sidewalk, which must follow it.
Report and renders: Saved/Mazzarino80/Sidewalks/Magnet/.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_sidewalk_magnet_test.py -ForceLit
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
MAP = "/Game/Mazzarino80/Kit/Sidewalk/L_M80_ProvaMarciapiedi"
STYLE = "/Game/Mazzarino80/Houses/Styles/DA_M80Style_01_PopolarePietra"
OUT = ROOT / "Saved/Mazzarino80/Sidewalks/Magnet"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TURN = math.radians(20)


def rot(x, y, a=TURN, cx=4000.0, cy=0.0):
    dx, dy = x - cx, y - cy
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


def house(label, pts, seed):
    a = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.M80House, unreal.Vector(pts[0][0], pts[0][1], 0))
    a.set_actor_label(label)
    a.set_footprint_world([unreal.Vector(x, y, 0) for x, y in pts])
    p = a.get_editor_property("house")
    p.set_editor_property("style", unreal.load_asset(STYLE))
    p.set_editor_property("floors", 2)
    p.set_editor_property("seed", seed)
    a.set_editor_property("house", p)
    a.rebuild()
    return a


def sidewalk(label, pts, snap=True):
    s = EAS.spawn_actor_from_class(unreal.M80Sidewalk, unreal.Vector(pts[0][0], pts[0][1], 0))
    s.set_actor_label(label)
    path = s.get_editor_property("path")
    path.set_spline_points([unreal.Vector(x, y, 0) for x, y in pts], unreal.SplineCoordinateSpace.WORLD, True)
    for i in range(len(pts)):
        path.set_spline_point_type(i, unreal.SplinePointType.LINEAR, False)
    path.update_spline()
    s.set_editor_property("snap_to_houses", snap)
    s.rebuild()
    return s


def points(s):
    path = s.get_editor_property("path")
    return [[round(v, 1) for v in (q.x, q.y)] for q in
            (path.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD) for i in range(path.get_number_of_spline_points()))]


def build_level():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -50, 60))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    ground = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cube"), unreal.Vector(2500, 0, -50))
    ground.set_actor_scale3d(unreal.Vector(120, 80, 1))
    mat = unreal.load_asset("/Game/Mazzarino80/Kit/Stairs/MI_M80_Cemento")
    if mat:
        ground.static_mesh_component.set_material(0, mat)
    # Row of two houses, fronts on y = 0 facing -Y; a third one turned by 20 degrees.
    house("Casa_A", [(0, 0), (1000, 0), (1000, 900), (0, 900)], 3)
    house("Casa_B", [(1000, 0), (2200, 0), (2200, 900), (1000, 900)], 4)
    turned = house("Casa_Ruotata", [rot(x, y) for x, y in ((3300, 0), (4700, 0), (4700, 1000), (3300, 1000))], 5)
    rep = {}
    # Drawn 1 m inside the row (curb on the right = street side walking towards +X).
    a = sidewalk("Marciapiede_dentro_le_case", [(-300, 100), (1100, 100), (2500, 100)])
    # 2 m off the turned house: within reach (3 m).
    b = sidewalk("Marciapiede_vicino", [rot(x, y) for x, y in ((3100, -275), (4900, -275))])
    # 6 m away: stays.
    c = sidewalk("Marciapiede_lontano", [(-300, -700), (2500, -700)])
    # Round the back corner of the row: the corner point goes to the corner of the house, half a width out.
    d = sidewalk("Marciapiede_angolo", [(1500, 1000), (2320, 1000), (2320, 300)])
    for s in (a, b, c, d):
        rep[s.get_actor_label()] = {"agganciati": s.get_editor_property("snapped_points"), "stato": s.get_editor_property("snap_status"),
                                    "punti": points(s)}
    # The turned house moves 1.5 m away from its sidewalk (north, perpendicular to its front).
    d = unreal.Vector(-150 * math.sin(TURN), 150 * math.cos(TURN), 0)
    turned.set_actor_location(turned.get_actor_location() + d, False, False)
    turned.rebuild()
    # In the editor dragging the house re-attaches it by itself (construction script); here: rebuild.
    b.rebuild()
    rep["dopo lo spostamento"] = {"agganciati": b.get_editor_property("snapped_points"), "punti": points(b)}
    return rep


VIEWS = {
    "dall_alto": ((2300, -2600, 3200), (2300, 0, 0)),
    "fila": ((-600, -1400, 260), (1200, 0, 60)),
    "ruotata": ((2600, -2400, 500), (4000, -300, 50)),
    "angolo": ((2900, 1700, 260), (2275, 900, 20)),
    "fila_cordolo": ((500, -650, 160), (1100, -60, 10)),
}


def views():
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    for name, (eye, target) in VIEWS.items():
        r = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        cap.capture(unreal.Vector(*eye), r, OUT / ("%s.png" % name))
        yield 2
    cap.destroy()


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = build_level()
    (OUT / "report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    world = m80_seq.editor_world()
    assert world.get_path_name().startswith(MAP), world.get_path_name()
    yield 400
    for _ in views():
        yield 2
    yield 200
    for _ in views():
        yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
