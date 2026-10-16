"""Play In Editor check of the town's generated roads and cars: after Play and some streaming, for the roads named
in M80_STRADE (default 3_Lastra_lavica_secondaria2) the number of pieces and where the first and last ones are
(they must match the editor: not rebuilt underground), and for every car whether it exists in the game world.
Out: Saved/Mazzarino80/Risalva/pie_check.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_pie_strade_check.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Risalva"
ROADS = [k for k in os.environ.get("M80_STRADE", "3_Lastra_lavica_secondaria2").split(",") if k]


def xyz(v):
    return [round(v.x), round(v.y), round(v.z)]


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 1500
    world = unreal.EditorLevelLibrary.get_game_world()
    report = {"play": bool(world), "roads": {}, "cars": []}
    if world:
        for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            lab = a.get_actor_label()
            if lab in ROADS:
                comps = a.get_components_by_class(unreal.SplineMeshComponent)
                centres = [xyz(unreal.SystemLibrary.get_component_bounds(c)[0]) for c in comps]
                report["roads"][lab] = {"pieces": len(comps), "first": centres[:2], "last": centres[-2:]}
            if a.get_class().get_name().startswith("M80Car"):
                report["cars"].append({"label": lab, "location": xyz(a.get_actor_location())})
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pie_check.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 60


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore_pie.txt"))
