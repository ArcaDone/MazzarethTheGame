"""Why the castle (Blueprint CastelCompleted in the town) turns black from far away: pictures of it from 50 m to 1 km,
first as it is (Nanite), then with Nanite switched off on its meshes in memory (nothing is saved). The castle and the
town around it are loaded, so these are the real meshes, not the HLODs.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_castello_distanze.py -ForceLit -TimeoutMinutes 40
Out: Saved/Mazzarino80/Castello/<nanite|classico>_<m>.png
"""
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Castello"
DISTANCES_M = (50, 150, 400, 1000)
HEADING = 200.0          # the cameras look at the castle from this side (degrees, world yaw)


def views(centre):
    out = []
    for d in DISTANCES_M:
        a = math.radians(HEADING)
        eye = unreal.Vector(centre.x + math.cos(a) * d * 100, centre.y + math.sin(a) * d * 100, centre.z + 1500 + d * 15)
        out.append((d, eye, unreal.MathLibrary.find_look_at_rotation(eye, centre)))
    return out


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    castle = next(d for d in descs if str(d.get_editor_property("label")) == "CastelCompleted")
    c = m80_seq.desc_center(castle)
    m80_seq.load(m80_seq.near(descs, c.x, c.y, 60000))
    yield 200
    actor = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                 if a.get_actor_label() == "CastelCompleted")
    origin, extent = actor.get_actor_bounds(False)
    centre = unreal.Vector(origin.x, origin.y, origin.z)
    OUT.mkdir(parents=True, exist_ok=True)
    cap = m80_seq.ViewCapture(1600, 900, 50.0)
    meshes = {cm.get_editor_property("static_mesh") for cm in actor.get_components_by_class(unreal.StaticMeshComponent)}
    meshes.discard(None)
    for mode in ("nanite", "classico"):
        if mode == "classico":
            for sm in meshes:
                ns = sm.get_editor_property("nanite_settings")
                ns.set_editor_property("enabled", False)
                sm.set_editor_property("nanite_settings", ns)
            yield 300
        for d, eye, rot in views(centre):
            m80_seq.set_view(eye, rot)
            yield 120
            cap.capture(eye, rot, OUT / ("%s_%04dm.png" % (mode, d)))
            yield 2
    cap.destroy()
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
