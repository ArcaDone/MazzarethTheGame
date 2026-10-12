"""Imports the Madonna's railing prepared by Research/Mazzarino80/Blender/m80_muretto_madonna.py
(Saved/Mazzarino80/Import/out/MurettoMadonna) for the walls of the "Scalinata (Mazzarino)" actor (fence kind
"Ringhiera della Madonna"): /Game/Mazzarino80/Kit/Stairs/SM_M80_MurettoMadonna_Pilastrino (the stone post, box
collision) and SM_M80_MurettoMadonna_Ringhiera (one bay of iron rails, colliding with its own triangles), with the
Madonna's own material instances, without Nanite (thin rails) and with 3 LODs.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_muretto_madonna_import.py
Report: Saved/Mazzarino80/Import/muretto_madonna_report.json
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Import/out/MurettoMadonna"
OUT = ROOT / "Saved/Mazzarino80/Import/muretto_madonna_report.json"
KIT = "/Game/Mazzarino80/Kit/Stairs"
MATS = "/Game/Mazzarino80/Buildings/Madonna/Materials/"
PIECES = {"Pilastrino": "MI_M80_Madonna_MainMaterial", "Ringhiera": "MI_M80_Madonna_Metal_001"}
EAL = unreal.EditorAssetLibrary
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def import_mesh(file, name):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.static_mesh_import_data.set_editor_property("combine_meshes", True)
    ui.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    ui.static_mesh_import_data.set_editor_property("build_nanite", False)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", KIT)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return unreal.load_asset(KIT + "/" + name)


def run():
    yield 5
    report = {"blender": json.loads((SRC / "MurettoMadonna.json").read_text(encoding="utf-8"))}
    for piece, mi in PIECES.items():
        name = "SM_M80_MurettoMadonna_" + piece
        mesh = import_mesh(SRC / ("MurettoMadonna_%s.fbx" % piece), name)
        if not mesh:
            report[piece] = "import failed"
            continue
        mat = unreal.load_asset(MATS + mi)
        slots = list(mesh.get_editor_property("static_materials"))
        for i, s in enumerate(slots):
            s.set_editor_property("material_interface", mat)
            slots[i] = s
        mesh.set_editor_property("static_materials", slots)
        if piece == "Pilastrino":
            SUB.remove_collisions(mesh)
            SUB.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        else:
            mesh.get_editor_property("body_setup").set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        opts = unreal.StaticMeshReductionOptions()
        opts.set_editor_property("auto_compute_lod_screen_size", True)
        opts.set_editor_property("reduction_settings", [unreal.StaticMeshReductionSettings(p, 0.0) for p in (1.0, 0.5, 0.25)])
        SUB.set_lods(mesh, opts)
        EAL.save_loaded_asset(mesh)
        bb = mesh.get_bounding_box()
        report[piece] = {"path": mesh.get_path_name(), "material": mat.get_path_name() if mat else None,
                         "box_cm": [round(v, 1) for v in (bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z)],
                         "lods": SUB.get_lod_count(mesh)}
        yield 2
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
