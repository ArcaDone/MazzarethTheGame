"""Levels of detail for the drivable cars (Unreal skeletal mesh reduction, UVs and seams kept).

The Ape mesh is very dense (1.7 M vertices): far away it is drawn with a fraction of them. A Blender
decimation was tried and dropped (at 10 % the textures tear, at 35 % the file is still 240 MB).
Report: Saved/Mazzarino80/Vehicles/lods_report.json.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Vehicles/lods_report.json"
MESHES = ["/Game/Drive/fiat126/fiat126", "/Game/Drive/ApeCar/ApeDrivable"]


def run():
    sk = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    report = {}
    if unreal.EditorAssetLibrary.does_asset_exist("/Game/Drive/ApeCar/SK_M80_Ape"):
        unreal.EditorAssetLibrary.delete_asset("/Game/Drive/ApeCar/SK_M80_Ape")
    for path in MESHES:
        mesh = unreal.load_asset(path)
        ok = sk.regenerate_lod(mesh, 3, True, False)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        report[path] = {"ok": ok, "verts": [sk.get_num_verts(mesh, i) for i in range(3)]}
        yield 5
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
