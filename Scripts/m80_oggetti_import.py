"""Imports the older hand-made models made ready by Research/Mazzarino80/Blender/m80_oggetti_gioco.py
(Saved/Mazzarino80/Oggetti/<Key>/) into /Game/Mazzarino80/Buildings/<Key>: one static mesh with Nanite, collision from its
own triangles, the materials and textures Unreal builds from the FBX (textures cut to 1024 px in Blender; colour and
mask sources stored as JPEG, normals lossless). Not placed in the town: where they stand is still to decide.
Env M80_OGGETTI=Key1,Key2 (default: all). Report: Saved/Mazzarino80/Oggetti/import_report.json

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_oggetti_import.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Oggetti"
DEST = "/Game/Mazzarino80/Buildings"
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def keys():
    only = [k for k in os.environ.get("M80_OGGETTI", "").split(",") if k]
    found = sorted(p.name for p in SRC.iterdir() if (p / ("SM_M80_%s.fbx" % p.name)).exists())
    return [k for k in found if not only or k in only]


def run():
    report = {}
    for key in keys():
        dest = "%s/%s" % (DEST, key)
        ui = unreal.FbxImportUI()
        ui.set_editor_property("import_mesh", True)
        ui.set_editor_property("import_materials", True)
        ui.set_editor_property("import_textures", True)
        ui.set_editor_property("import_as_skeletal", False)
        ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        data = ui.static_mesh_import_data
        data.set_editor_property("combine_meshes", True)
        data.set_editor_property("generate_lightmap_u_vs", False)
        data.set_editor_property("auto_generate_collision", False)
        data.set_editor_property("build_nanite", True)
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(SRC / key / ("SM_M80_%s.fbx" % key)))
        t.set_editor_property("destination_path", dest)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", False)
        t.set_editor_property("options", ui)
        TOOLS.import_asset_tasks([t])
        yield 20
        rep = {"textures": 0, "materials": 0}
        for path in EAL.list_assets(dest, recursive=True):
            a = unreal.load_asset(path)
            if isinstance(a, unreal.Texture2D):
                rep["textures"] += 1
                n = a.get_name().lower()
                if "nor" not in n and "normal" not in n and "nrm" not in n:
                    unreal.M80EditorLibrary.compress_texture_source_jpeg(a, 90)
                EAL.save_loaded_asset(a, False)
            elif isinstance(a, unreal.MaterialInterface):
                rep["materials"] += 1
            elif isinstance(a, unreal.StaticMesh):
                SUB.remove_collisions(a)
                body = a.get_editor_property("body_setup")
                if body:
                    body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                b = a.get_bounding_box()
                rep["mesh"] = a.get_name()
                rep["size_m"] = [round((b.max.x - b.min.x) / 100, 1), round((b.max.y - b.min.y) / 100, 1), round((b.max.z - b.min.z) / 100, 1)]
                EAL.save_loaded_asset(a, False)
            yield 1
        report[key] = rep
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
        yield 5
    (SRC / "import_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(SRC / "import_error.txt"))
