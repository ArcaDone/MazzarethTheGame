"""Sidewalks made by the house ("Marciapiedi" on AM80House) and their far view (HLOD), in a level made in memory (/Temp,
never saved): an octagonal house with all sides ticked (one ring), the same with sides 0, 1 and 3 (two open lines),
a rectangular house switched on and off. For each case: sidewalks made, their points' distance from the facade, closed
or not, curb side; then what UM80DynamicMeshHLODBuilder makes of them (triangles, materials).
Out: Saved/Mazzarino80/Marciapiedi/Auto/report.json + dall_alto.png, ottagono.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_marciapiedi_auto_test.py -ForceLit -TimeoutMinutes 15
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
OUT = ROOT / "Saved/Mazzarino80/Marciapiedi/Auto"
STYLE = "/Game/Mazzarino80/Houses/Styles/DA_M80Style_01_PopolarePietra"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OCT = [(600 * math.cos(math.radians(22.5 + 45 * i)), 600 * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
RECT = [(2000, -500), (3200, -500), (3200, 500), (2000, 500)]


def house(label, pts, seed):
    a = EAS.spawn_actor_from_class(unreal.M80House, unreal.Vector(pts[0][0], pts[0][1], 0))
    a.set_actor_label(label)
    a.set_footprint_world([unreal.Vector(x, y, 0) for x, y in pts])
    p = a.get_editor_property("house")
    p.set_editor_property("style", unreal.load_asset(STYLE))
    p.set_editor_property("floors", 2)
    p.set_editor_property("seed", seed)
    a.set_editor_property("house", p)
    a.rebuild()
    return a


def seg_dist(q, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(q[0] - ax - t * dx, q[1] - ay - t * dy)


def describe(h, footprint):
    out = []
    for soft in h.get_editor_property("marciapiedi_creati"):
        s = soft.get() if hasattr(soft, "get") else soft
        if s is None:
            out.append("perso")
            continue
        path = s.get_editor_property("path")
        pts = [path.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD) for i in range(path.get_number_of_spline_points())]
        n = len(footprint)
        dists = [round(min(seg_dist((q.x, q.y), footprint[i], footprint[(i + 1) % n]) for i in range(n)), 1) for q in pts]
        out.append({"nome": s.get_actor_label(), "punti": len(pts), "chiuso": s.get_editor_property("closed_loop"),
                    "cordolo": str(s.get_editor_property("curb_side")), "distanze_dal_muro": dists,
                    "agganciati": s.get_editor_property("snapped_points"),
                    "hlod": unreal.M80EditorLibrary.test_dynamic_mesh_hlod([s])})
    return out


def set_on(h, sides=None):
    h.set_editor_property("marciapiedi", True)
    if sides is not None:
        h.set_editor_property("lati_marciapiede", sides)
    h.rifai_marciapiedi()


def build():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level("/Temp/L_M80_ProvaMarciapiediAuto", False)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -50, 60))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    ground = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cube"), unreal.Vector(1200, 0, -50))
    ground.set_actor_scale3d(unreal.Vector(80, 50, 1))
    mat = unreal.load_asset("/Game/Mazzarino80/Kit/Stairs/MI_M80_Cemento")
    if mat:
        ground.static_mesh_component.set_material(0, mat)

    rep = {}
    octa = house("Casa_Ottagono", OCT, 7)
    rep["ottagono_lati_iniziali"] = list(octa.get_editor_property("lati_marciapiede"))
    set_on(octa)
    rep["ottagono_tutti"] = {"lati": list(octa.get_editor_property("lati_marciapiede")), "marciapiedi": describe(octa, OCT)}
    set_on(octa, [True, True, False, True, False, False, False, False])
    rep["ottagono_0_1_3"] = describe(octa, OCT)

    rect = house("Casa_Rettangolo", RECT, 8)
    set_on(rect)
    rep["rettangolo_acceso"] = describe(rect, RECT)
    rect.set_editor_property("marciapiedi", False)
    rect.rifai_marciapiedi()
    rep["rettangolo_spento"] = {"creati": len(rect.get_editor_property("marciapiedi_creati")),
                                "nel_livello": len([a for a in EAS.get_all_level_actors() if isinstance(a, unreal.M80Sidewalk)])}
    set_on(rect, [True, False, True, False])
    rep["rettangolo_lati_0_2"] = describe(rect, RECT)
    return rep


VIEWS = {
    "dall_alto": ((1200, -200, 4200), (1200, 0, 0)),
    "ottagono": ((-1300, -1500, 500), (0, 0, 50)),
}


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = build()
    (OUT / "report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 300
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    for name, (eye, target) in VIEWS.items():
        r = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        cap.capture(unreal.Vector(*eye), r, OUT / ("%s.png" % name))
        yield 2
    cap.destroy()


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
