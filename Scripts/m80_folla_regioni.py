"""Probe: the face regions (Creator blend/move handles) of a MetaHuman preset, with their positions, so the crowd
script can name them (nose, eyes, jaw ...): X sideways, Y forward, Z up. Out: Saved/Mazzarino80/Personaggi/Folla/regioni.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_regioni.py
"""
import json
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Personaggi/Folla"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
OUT.mkdir(parents=True, exist_ok=True)
report = {}
for name in ("Bruce", "Lorenzo", "Jelena"):
    p = unreal.load_asset("/MetaHumanCharacter/Optional/Presets/" + name)
    SUB.try_add_object_to_edit(p)
    report[name] = [[round(v.x, 2), round(v.y, 2), round(v.z, 2)] for v in unreal.M80EditorLibrary.get_meta_human_face_regions(p)]
    SUB.remove_object_to_edit(p)
(OUT / "regioni.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
unreal.SystemLibrary.quit_editor()
