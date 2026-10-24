"""Exports the castle's meshes (/Game/Migrated/Castello, the pieces of the Blueprint CastelCompleted) to FBX exactly as
Unreal draws them, for their hand-made LODs in Blender (Research/Mazzarino80/Blender/m80_castello_lod.py). Read only.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_castello_esporta.py -TimeoutMinutes 20
Out: Saved/Mazzarino80/Castello/lod/src/<mesh>.fbx, src.json (triangles, bounds, material slots)
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Castello/lod/src"
FOLDER = "/Game/Migrated/Castello"
MESHES = ("Anfiteatro", "BaseCastello", "gateway_002", "MainCastello_001", "Muretto", "Rete", "Rocks", "Staccionata")


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {}
    for name in MESHES:
        sm = unreal.load_asset("%s/%s" % (FOLDER, name))
        task = unreal.AssetExportTask()
        task.object = sm
        task.filename = str(OUT / (name + ".fbx"))
        task.automated = True
        task.replace_identical = True
        task.prompt = False
        opts = unreal.FbxExportOption()
        opts.set_editor_property("level_of_detail", False)
        opts.set_editor_property("collision", False)
        task.options = opts
        ok = unreal.Exporter.run_asset_export_task(task)
        box = sm.get_bounding_box()
        rep[name] = {"ok": bool(ok), "tris": sm.get_num_triangles(0),
                     "min": [box.min.x, box.min.y, box.min.z], "max": [box.max.x, box.max.y, box.max.z],
                     "slots": [str(m.get_editor_property("material_slot_name")) for m in sm.get_editor_property("static_materials")]}
        yield 2
    (OUT / "src.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT.parent / "errore.txt"))
