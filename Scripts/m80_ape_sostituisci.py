"""Replaces the drivable Ape's heavy skeletal mesh (/Game/Drive/ApeCar/ApeDrivable, 1.7 M vertices) with the user's
lighter model, exported by Research/Mazzarino80/Blender/m80_ape_leggera.py (Saved/Mazzarino80/Vehicles/ApeLeggera.fbx).
1. The FBX goes first into /Game/Drive/ApeCar/Prova/SK_ApeLeggera with a skeleton of its own; its bones are compared
   with the old mesh's, by name, in component space (the Chaos wheels hang from Circle, Circle_001, Circle_002).
2. With M80_SOSTITUISCI=1 and every bone within TOL_CM: the FBX is imported over ApeDrivable on its own skeleton, the
   old materials go back on the slots of the same name, the physics asset stays, three LODs are rebuilt, and the
   test asset is deleted. Otherwise nothing of the old Ape is touched.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_ape_sostituisci.py -TimeoutMinutes 40
Out: Saved/Mazzarino80/Vehicles/ape_sostituisci.json
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Vehicles"
FBX = OUT / "ApeLeggera.fbx"
OLD = "/Game/Drive/ApeCar/ApeDrivable"
TEST_DIR = "/Game/Drive/ApeCar/Prova"
TEST = TEST_DIR + "/SK_ApeLeggera"
REPLACE = os.environ.get("M80_SOSTITUISCI") == "1"
TOL_CM = 2.0
EAL = unreal.EditorAssetLibrary
SK = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def import_fbx(dest_dir, name, skeleton):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False)
    ui.set_editor_property("create_physics_asset", False)
    if skeleton:
        ui.set_editor_property("skeleton", skeleton)
    data = ui.skeletal_mesh_import_data
    data.set_editor_property("import_morph_targets", False)
    data.set_editor_property("convert_scene", True)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(FBX))
    t.set_editor_property("destination_path", dest_dir)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    t.set_editor_property("options", ui)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return [str(p) for p in t.get_editor_property("imported_object_paths")]


def bones(mesh):
    pose = unreal.AnimPoseExtensions.get_reference_pose(mesh.get_editor_property("skeleton"))
    out = {}
    for b in unreal.AnimPoseExtensions.get_bone_names(pose):
        t = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)
        out[str(b)] = [t.translation.x, t.translation.y, t.translation.z]
    return out


def slot_key(name):
    """The old import kept spaces in slot names ("Black Metal Paint"), the new one has underscores."""
    return str(name).replace(" ", "_").replace(".", "_").replace("-", "_").lower()


def state(mesh):
    return {"verts": [SK.get_num_verts(mesh, i) for i in range(SK.get_lod_count(mesh))],
            "slots": {slot_key(m.get_editor_property("material_slot_name")): m.get_editor_property("material_interface")
                      for m in mesh.get_editor_property("materials")}}


def steps():
    old = unreal.load_asset(OLD)
    rep = {"sostituito": False, "fbx": str(FBX)}
    old_bones = bones(old)
    before = state(old)
    rep["vecchia_verts"] = before["verts"]
    rep["import_prova"] = import_fbx(TEST_DIR, "SK_ApeLeggera", None)
    yield 30
    test = unreal.load_asset(TEST)
    new_bones = bones(test)
    rep["prova_verts"] = state(test)["verts"]
    diff = {}
    for name, p in old_bones.items():
        q = new_bones.get(name)
        diff[name] = None if q is None else round(sum((a - b) ** 2 for a, b in zip(p, q)) ** 0.5, 2)
    rep["ossa_scarto_cm"] = diff
    rep["ossa_nuove"] = sorted(set(new_bones) - set(old_bones))
    ok = all(v is not None and v <= TOL_CM for v in diff.values()) and not rep["ossa_nuove"]
    rep["ossa_ok"] = ok
    rep["slot_prova"] = sorted(state(test)["slots"])
    if REPLACE and ok:
        skel = old.get_editor_property("skeleton")
        phys = old.get_editor_property("physics_asset")
        rep["import"] = import_fbx("/Game/Drive/ApeCar", "ApeDrivable", skel)
        yield 60
        mesh = unreal.load_asset(OLD)
        mats = mesh.get_editor_property("materials")
        missing = []
        for i, m in enumerate(mats):
            slot = str(m.get_editor_property("material_slot_name"))
            mat = before["slots"].get(slot_key(slot))
            if mat:
                m.set_editor_property("material_interface", mat)
                mats[i] = m
            else:
                missing.append(slot)
        mesh.set_editor_property("materials", mats)
        mesh.set_editor_property("physics_asset", phys)
        rep["slot_senza_materiale"] = missing
        SK.regenerate_lod(mesh, 3, True, False)
        yield 30
        rep["nuova_verts"] = state(mesh)["verts"]
        EAL.save_loaded_asset(mesh)
        rep["sostituito"] = True
    yield 5
    EAL.delete_directory(TEST_DIR)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ape_sostituisci.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "ape_sostituisci_errore.txt"))
