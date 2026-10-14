"""Imports the crowd's objects made ready by Research/Mazzarino80/Blender/m80_folla_oggetti.py
(Saved/Mazzarino80/Folla/Oggetti/<Key>/) into /Game/Mazzarino80/Personaggi/Oggetti/<Key>/SM_M80_<Key>: small static
meshes without Nanite (they are carried, worn or thrown; a few hundred to a few thousand triangles), a simple
collision (a box, a sphere for the ball, none for caps and glasses), the materials and textures Unreal builds from the FBX (colour sources stored
as JPEG). The shawl is left out: it becomes clothing on the MetaHuman body, not a prop.
Env M80_OGGETTI=Key1,Key2 (default: all). Report: Saved/Mazzarino80/Folla/Oggetti/import_report.json

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_oggetti_import.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Folla/Oggetti"
DEST = "/Game/Mazzarino80/Personaggi/Oggetti"
SKIP = {"Scialle"}
WORN = {"CoppolaGrigia", "CoppolaQuadri", "CoppolaTweed", "OcchialiSole", "OcchialiVista"}
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def keys():
    only = [k for k in os.environ.get("M80_OGGETTI", "").split(",") if k]
    found = sorted(p.name for p in SRC.iterdir() if (p / ("SM_M80_%s.fbx" % p.name)).exists() and p.name not in SKIP)
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
        data.set_editor_property("auto_generate_collision", True)
        data.set_editor_property("build_nanite", False)
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(SRC / key / ("SM_M80_%s.fbx" % key)))
        t.set_editor_property("destination_path", dest)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", False)
        t.set_editor_property("options", ui)
        TOOLS.import_asset_tasks([t])
        yield 10
        rep = {"textures": 0, "materials": 0}
        for path in EAL.list_assets(dest, recursive=True):
            a = unreal.load_asset(path)
            if isinstance(a, unreal.Texture2D):
                rep["textures"] += 1
                n = a.get_name().lower()
                if "nor" not in n and "normal" not in n and "nrm" not in n:
                    unreal.M80EditorLibrary.compress_texture_source_jpeg(a, 90)
            elif isinstance(a, unreal.MaterialInterface):
                rep["materials"] += 1
            elif isinstance(a, unreal.StaticMesh):
                # Things that lie or stand on the ground get a box (the ball a sphere); worn ones none.
                SUB.remove_collisions(a)
                if key not in WORN:
                    shape = unreal.ScriptCollisionShapeType.SPHERE if key == "SuperSantos" else unreal.ScriptCollisionShapeType.BOX
                    SUB.add_simple_collisions(a, shape)
                b = a.get_bounding_box()
                rep["mesh"] = a.get_name()
                rep["size_cm"] = [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1), round(b.max.z - b.min.z, 1)]
                rep["collision_shapes"] = SUB.get_simple_collision_count(a)
            EAL.save_loaded_asset(a, False)
            yield 1
        report[key] = rep
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    (SRC / "import_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(SRC / "import_error.txt"))
