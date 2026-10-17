"""What is around the Matrice in L_M80_Paese_WP: actors by class within 100/150/200 m of the square, the roads there
(kind, width), the landscape tiles. For cutting out the traffic test map (m80_prova_matrice.py).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_matrice_zona_sonda.py -TimeoutMinutes 30
Report: Saved/Mazzarino80/ProvaMatrice/zona.json
"""
import collections
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/ProvaMatrice"
MATRICE = "M80_Recuperato_Matrice"
V = unreal.Vector


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    mat = [d for d in descs if str(d.get_editor_property("label")) == MATRICE]
    m80_seq.load(mat)
    yield 30
    world = m80_seq.editor_world()
    old = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == MATRICE)
    t = old.get_actor_transform()
    square = t.transform_location(V(50.0, 4000.0, 0.0))
    rep = {"matrice": [t.translation.x, t.translation.y, t.translation.z], "yaw": t.rotation.rotator().yaw, "square": [square.x, square.y, square.z]}
    for r in (10000, 15000, 20000):
        near = m80_seq.near(descs, square.x, square.y, r)
        rep["classes_%d" % (r // 100)] = dict(collections.Counter(str(d.get_editor_property("native_class").get_name()) for d in near).most_common())
    near = m80_seq.near(descs, square.x, square.y, 20000)
    labels = [(str(d.get_editor_property("label")), str(d.get_editor_property("native_class").get_name()),
               round(math.hypot(m80_seq.desc_center(d).x - square.x, m80_seq.desc_center(d).y - square.y) / 100)) for d in near
              if not m80_seq.desc_class_is(d, "M80House", "MazzarinoRoadSpline", "WorldPartitionHLOD", "LandscapeStreamingProxy", "M80StreetLight")]
    rep["others"] = sorted(labels, key=lambda x: x[2])[:300]
    roads = [d for d in near if m80_seq.desc_class_is(d, "MazzarinoRoadSpline", "M80Road")]
    m80_seq.load(roads)
    yield 30
    rr = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        cls = a.get_class().get_name()
        if cls == "MazzarinoRoadSpline":
            sp = a.get_editor_property("spline")
            c = sp.get_location_at_distance_along_spline(sp.get_spline_length() / 2, unreal.SplineCoordinateSpace.WORLD)
            rr.append([a.get_actor_label(), a.get_editor_property("road_name"), a.get_editor_property("osm_highway"), round(a.get_editor_property("width_meters"), 1),
                       round(sp.get_spline_length() / 100), round(math.hypot(c.x - square.x, c.y - square.y) / 100)])
        elif cls == "M80Road":
            rr.append([a.get_actor_label(), "", "M80Road", round(a.get_editor_property("width_cm") / 100, 1), 0, 0])
    rep["roads"] = sorted(rr, key=lambda x: x[5])
    rep["road_kinds"] = dict(collections.Counter(r[2] for r in rr))
    (OUT / "zona.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "zona.errore.txt"))
