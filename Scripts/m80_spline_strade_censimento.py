"""Survey of the town's road splines (MazzarinoRoadSpline in L_M80_Paese_WP): how many have a paving mesh, how many
have pieces, which meshes. Nothing is saved.
Out: Saved/Mazzarino80/Risalva/spline_strade_censimento.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_spline_strade_censimento.py
"""
import collections
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Risalva"


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs("MazzarinoRoadSpline")
    m80_seq.load(descs)
    yield 60
    roads = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
             if a.get_class().get_name() == "MazzarinoRoadSpline"]
    counts = collections.Counter()
    meshes = collections.Counter()
    examples = []
    for a in roads:
        m = a.get_editor_property("road_mesh")
        n = len([x for x in a.get_components_by_class(unreal.SplineMeshComponent) if x.component_has_tag("M80RoadGenerated")])
        counts["con_mesh" if m else "senza_mesh"] += 1
        counts["con_pezzi" if n else "senza_pezzi"] += 1
        counts["pezzi_totali"] += n
        meshes[m.get_name() if m else "-"] += 1
        if m and len(examples) < 5:
            examples.append([a.get_actor_label(), n])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "spline_strade_censimento.json").write_text(json.dumps({"descs": len(descs), "loaded": len(roads), "counts": counts,
                                                                   "meshes": meshes, "examples": examples}, indent=1),
                                                       encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "spline_strade_censimento_errore.txt"))
