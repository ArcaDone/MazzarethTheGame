"""Builds the distance fields of every static mesh in the given folders as if two-sided, and saves them.
Meshes that are not closed (facades without interiors, like Palazzo Bartoli's) otherwise get a distance field that
is "inside" behind their walls, and Lumen (mesh SDF tracing) paints black blotches on them under the sky light;
compared on 2026-10-12: gone with r.Lumen.TraceMeshSDFs 0 or with two-sided distance fields, still there without GI.
Env M80_CARTELLE=/Game/A,/Game/B (default: Palazzo Bartoli).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_sdf_due_facce.py
"""
import json
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

EAL = unreal.EditorAssetLibrary
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
FOLDERS = [f for f in os.environ.get("M80_CARTELLE", "/Game/Mazzarino80/Buildings/Bartoli").split(",") if f]
REPORT = os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/sdf_due_facce.json")


def run():
    changed = []
    for folder in FOLDERS:
        for path in EAL.list_assets(folder, recursive=True):
            if EAL.find_asset_data(path).asset_class_path.asset_name != "StaticMesh":
                continue
            mesh = unreal.load_asset(path)
            b = SUB.get_lod_build_settings(mesh, 0)
            if b.get_editor_property("generate_distance_field_as_if_two_sided"):
                continue
            b.set_editor_property("generate_distance_field_as_if_two_sided", True)
            SUB.set_lod_build_settings(mesh, 0, b)
            EAL.save_loaded_asset(mesh, False)
            changed.append(path)
            yield 1
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump({"folders": FOLDERS, "changed": changed}, f, indent=1)
    yield 5


m80_seq.Sequencer(run(), log_file=REPORT.replace(".json", "_error.txt"))
