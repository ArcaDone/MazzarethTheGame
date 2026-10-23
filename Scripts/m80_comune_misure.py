"""Where the old Comune Blueprint (M80_Recuperato_ComuneCompleto) puts its main pieces in the town: per component of
MainComune, ComuneScale, ChurchTownHall, StatuaComume, Fontana and MarciapiedeComune_01 its world transform, the mesh's
own bounding box and the 8 corners of that box in the world. Used to place the new Comune + church on the old one.
Read only. Out: Saved/Mazzarino80/Comune/misure.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_comune_misure.py -TimeoutMinutes 20
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Comune"
PIECES = ("MainComune", "ComuneScale", "ChurchTownHall", "StatuaComume", "Fontana", "MarciapiedeComune_01")


def vec(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = [d for d in m80_seq.actor_descs() if str(d.get_editor_property("label")) == "M80_Recuperato_ComuneCompleto"]
    m80_seq.load(descs)
    yield 60
    actor = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                 if a.get_actor_label() == "M80_Recuperato_ComuneCompleto")
    rep = {"attore": {"loc": vec(actor.get_actor_location()), "rot": [actor.get_actor_rotation().roll, actor.get_actor_rotation().pitch,
                                                                    actor.get_actor_rotation().yaw],
                      "scala": vec(actor.get_actor_scale3d())}, "pezzi": []}
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        sm = c.get_editor_property("static_mesh")
        if not sm or sm.get_name() not in PIECES:
            continue
        box = sm.get_bounding_box()
        t = c.get_world_transform()
        corners = []
        for x in (box.min.x, box.max.x):
            for y in (box.min.y, box.max.y):
                for z in (box.min.z, box.max.z):
                    corners.append(vec(unreal.MathLibrary.transform_location(t, unreal.Vector(x, y, z))))
        rel = c.get_relative_transform() if hasattr(c, "get_relative_transform") else None
        rep["pezzi"].append({"mesh": sm.get_name(), "componente": c.get_name(), "loc": vec(t.translation),
                             "rot": [round(t.rotation.rotator().roll, 3), round(t.rotation.rotator().pitch, 3), round(t.rotation.rotator().yaw, 3)],
                             "scala": vec(t.scale3d), "box_min": vec(box.min), "box_max": vec(box.max), "angoli": corners,
                             "rel_loc": vec(c.get_editor_property("relative_location")),
                             "rel_rot": [c.get_editor_property("relative_rotation").roll, c.get_editor_property("relative_rotation").pitch,
                                         c.get_editor_property("relative_rotation").yaw],
                             "rel_scala": vec(c.get_editor_property("relative_scale3d"))})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "misure.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
