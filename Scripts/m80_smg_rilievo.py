"""Survey of the lot of Santa Maria di Gesù and the old hospital in L_M80_Paese_WP (read only), for the Blender model
(Research/Mazzarino80/Blender/m80_santa_maria_gesu.py):
- the ground on a 1 m grid over the block: the first hit of the landscape or a road, everything else ignored (a trace
  stops at the first blocking hit, and the editor's HLOD actors and the houses would be hit first);
- every actor whose bounds touch the block: label, class, mesh, bounds.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_smg_rilievo.py -TimeoutMinutes 30
Out: Saved/Mazzarino80/SantaMariaGesu/rilievo.json
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/SantaMariaGesu"
# the block in world cm: church (OSM way 372575840), old hospital (372575833), convent ruins and courts around
X0, X1, Y0, Y1 = -500.0, 9000.0, 29500.0, 38500.0
STEP = 100.0
TOP, BOTTOM = 30000.0, 5000.0
BUILDING_CLASSES = ("M80House", "StaticMeshActor", "Blueprint")


def is_ground(actor):
    if actor is None:
        return False
    name = actor.get_class().get_name()
    if "Landscape" in name or "RoadSpline" in name:
        return True
    label = actor.get_actor_label()
    return any(w in label for w in ("Terreno", "Strada", "Road", "Marciapiede", "Sidewalk", "Piazza", "Asfalto"))


def trace(world, x, y, ignore):
    hits = unreal.SystemLibrary.line_trace_multi(world, unreal.Vector(x, y, TOP), unreal.Vector(x, y, BOTTOM),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    hits = hits[1] if isinstance(hits, tuple) and len(hits) == 2 and isinstance(hits[1], (list, tuple)) else hits
    first = ground = None
    for h in hits or []:
        t = h.to_tuple()
        a = t[9]
        if first is None:
            first = (round(t[5].z, 1), a.get_actor_label() if a else "")
        if ground is None and is_ground(a):
            ground = (round(t[5].z, 1), a.get_actor_label())
    return first, ground


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = []
    for d in m80_seq.actor_descs():
        b = d.get_editor_property("bounds")
        if b.max.x >= X0 and b.min.x <= X1 and b.max.y >= Y0 and b.min.y <= Y1:
            descs.append(d)
    m80_seq.load(descs)
    yield 120
    world = m80_seq.editor_world()
    rep = {"box_cm": [X0, X1, Y0, Y1], "step_cm": STEP, "actors": [], "grid": []}
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        o, e = a.get_actor_bounds(False)
        if o.x + e.x < X0 or o.x - e.x > X1 or o.y + e.y < Y0 or o.y - e.y > Y1 or e.x > 50000:
            continue
        mesh = ""
        smc = a.get_component_by_class(unreal.StaticMeshComponent)
        if smc and smc.get_editor_property("static_mesh"):
            mesh = smc.get_editor_property("static_mesh").get_path_name()
        rep["actors"].append({"label": a.get_actor_label(), "class": a.get_class().get_name(), "mesh": mesh,
                              "loc": [round(v, 1) for v in (a.get_actor_location().x, a.get_actor_location().y,
                                                           a.get_actor_location().z)],
                              "yaw": round(a.get_actor_rotation().yaw, 2),
                              "min": [round(o.x - e.x), round(o.y - e.y), round(o.z - e.z)],
                              "max": [round(o.x + e.x), round(o.y + e.y), round(o.z + e.z)],
                              "hidden": a.is_hidden_ed(), "hlod": str(a.get_editor_property("hlod_layer"))})
    yield 2
    ignore = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if not is_ground(a)]
    nx, ny = int((X1 - X0) / STEP) + 1, int((Y1 - Y0) / STEP) + 1
    for j in range(ny):
        row = []
        for i in range(nx):
            first, ground = trace(world, X0 + i * STEP, Y0 + j * STEP, ignore)
            row.append([first, ground])
        rep["grid"].append(row)
        if j % 10 == 9:
            yield 1
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rilievo.json").write_text(json.dumps(rep), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "rilievo_errore.txt"))
