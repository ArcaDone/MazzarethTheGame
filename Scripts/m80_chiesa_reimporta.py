"""Reimports a church's two meshes (SM_M80_<Key>, SM_M80_<Key>_Dettagli in /Game/Mazzarino80/Buildings/Chiese/<Key>) from
a new FBX of the same model, e.g. after Research/Mazzarino80/Blender/m80_normali_fuori.py turned its faces outward,
keeping everything else: the materials on every slot (put back if the import changed them), Nanite on the main mesh,
the details' three LODs, collision from their own triangles. Only the meshes change: no material is touched.
Env M80_CHIESA=<Key>, M80_FBX_DIR=<folder with SM_M80_<Key>.fbx and SM_M80_<Key>_Dettagli.fbx, one mesh each>
(default Saved/Mazzarino80/Chiese/<Key>); nothing is saved
unless M80_SALVA=1. Report: Saved/Mazzarino80/Chiese/<Key>/reimporta.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_chiesa_reimporta.py -TimeoutMinutes 30
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
KEY = os.environ.get("M80_CHIESA", "")
FBX_DIR = Path(os.environ.get("M80_FBX_DIR") or ROOT / ("Saved/Mazzarino80/Chiese/%s" % KEY))
DEST = "/Game/Mazzarino80/Buildings/Chiese/" + KEY
SAVE = os.environ.get("M80_SALVA") == "1"
OUT = ROOT / ("Saved/Mazzarino80/Chiese/%s" % KEY)
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def import_fbx(file, dest, name):
    """As Scripts/m80_chiese_import.py imports a church (no materials), one file into the asset `name`."""
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    data = ui.static_mesh_import_data
    data.set_editor_property("combine_meshes", False)
    data.set_editor_property("generate_lightmap_u_vs", False)
    data.set_editor_property("auto_generate_collision", False)
    data.set_editor_property("build_nanite", True)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    t.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])


def settings(mesh, nanite):
    """As Scripts/m80_chiese_import.py sets a church mesh up (without saving it)."""
    st = mesh.get_editor_property("nanite_settings")
    st.set_editor_property("enabled", nanite)
    SUB.set_nanite_settings(mesh, st, apply_changes=True)
    if not nanite:
        opts = unreal.StaticMeshReductionOptions()
        opts.set_editor_property("auto_compute_lod_screen_size", True)
        opts.set_editor_property("reduction_settings", [unreal.StaticMeshReductionSettings(p, 0.0) for p in (1.0, 0.5, 0.25)])
        SUB.set_lods(mesh, opts)
    SUB.remove_collisions(mesh)
    body = mesh.get_editor_property("body_setup")
    if body:
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)


def state(mesh):
    return {"materiali": {str(m.get_editor_property("material_slot_name")): m.get_editor_property("material_interface")
                          for m in mesh.get_editor_property("static_materials")},
            "nanite": bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")),
            "lod": mesh.get_num_lods(), "triangoli": mesh.get_num_triangles(0)}


def steps():
    names = ["SM_M80_%s" % KEY, "SM_M80_%s_Dettagli" % KEY]
    before = {n: state(unreal.load_asset("%s/%s" % (DEST, n))) for n in names}
    for n in names:
        import_fbx(FBX_DIR / (n + ".fbx"), DEST, n)
        yield 10
    rep = {"fbx": str(FBX_DIR), "salvato": SAVE, "mesh": {},
           "asset": sorted(str(a) for a in unreal.EditorAssetLibrary.list_assets(DEST, recursive=False))}
    for n in names:
        mesh = unreal.load_asset("%s/%s" % (DEST, n))
        put_back = []
        for i, m in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(m.get_editor_property("material_slot_name"))
            old = before[n]["materiali"].get(slot)
            if old and m.get_editor_property("material_interface") != old:
                mesh.set_material(i, old)
                put_back.append(slot)
        settings(mesh, before[n]["nanite"])
        after = state(mesh)
        rep["mesh"][n] = {"prima": {k: v for k, v in before[n].items() if k != "materiali"},
                          "dopo": {k: v for k, v in after.items() if k != "materiali"},
                          "slot_rimessi": put_back,
                          "slot_mancanti": sorted(set(before[n]["materiali"]) - set(after["materiali"])),
                          "slot_nuovi": sorted(set(after["materiali"]) - set(before[n]["materiali"]))}
        yield 2
    if SAVE:
        for n in names:
            unreal.EditorAssetLibrary.save_asset("%s/%s" % (DEST, n), only_if_is_dirty=False)
    (OUT / "reimporta.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "reimporta_errore.txt"))
