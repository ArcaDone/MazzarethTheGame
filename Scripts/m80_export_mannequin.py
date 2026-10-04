"""Exports the UEFN mannequin (the skeleton that drives the player animations) to FBX for Blender.
Output: Saved/Mazzarino80/Player/SKM_UEFN_Mannequin.fbx
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Player"


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    mesh = unreal.load_asset("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin")
    task = unreal.AssetExportTask()
    task.object = mesh
    task.filename = str(OUT / "SKM_UEFN_Mannequin.fbx")
    task.automated = True
    task.replace_identical = True
    task.prompt = False
    opts = unreal.FbxExportOption()
    opts.set_editor_property("level_of_detail", False)
    task.options = opts
    ok = unreal.Exporter.run_asset_export_task(task)
    (OUT / "export.txt").write_text("ok %s skeleton %s" % (ok, mesh.skeleton.get_path_name()), encoding="utf-8")
    yield 1


m80_seq.Sequencer(run(), log_file=str(OUT / "export_error.txt"))
