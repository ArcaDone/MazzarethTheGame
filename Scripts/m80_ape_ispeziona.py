"""The drivable Ape's skeletal mesh (/Game/Drive/ApeCar/ApeDrivable), read only: bones, LODs, vertices, material
slots and the FBX it was imported from, before replacing it with the user's lighter model.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_ape_ispeziona.py -TimeoutMinutes 20
Out: Saved/Mazzarino80/Vehicles/ape_ispeziona.json
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
MESH = "/Game/Drive/ApeCar/ApeDrivable"


def steps():
    mesh = unreal.load_asset(MESH)
    sk = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    rep = {"verts": [sk.get_num_verts(mesh, i) for i in range(sk.get_lod_count(mesh))]}
    skel = mesh.get_editor_property("skeleton")
    rep["skeleton"] = skel.get_path_name() if skel else None
    try:
        rep["bones"] = [str(b) for b in unreal.SkeletalMeshEditorSubsystem.get_bone_names(mesh)] \
            if hasattr(unreal.SkeletalMeshEditorSubsystem, "get_bone_names") else None
    except Exception as e:  # noqa: BLE001
        rep["bones"] = "errore %s" % e
    if not rep.get("bones"):
        comp = unreal.SkeletalMeshComponent()
        comp.set_skinned_asset_and_update(mesh) if hasattr(comp, "set_skinned_asset_and_update") else comp.set_skeletal_mesh(mesh)
        n = comp.get_num_bones()
        rep["bones"] = [[str(comp.get_bone_name(i)), str(comp.get_parent_bone(comp.get_bone_name(i)))] for i in range(n)]
    rep["materials"] = [{"slot": str(m.get_editor_property("material_slot_name")),
                         "mat": m.get_editor_property("material_interface").get_path_name() if m.get_editor_property("material_interface") else None}
                        for m in mesh.get_editor_property("materials")]
    data = mesh.get_editor_property("asset_import_data")
    try:
        rep["source"] = [str(f) for f in data.extract_filenames()]
    except Exception as e:  # noqa: BLE001
        rep["source"] = "errore %s" % e
    b = mesh.get_bounds()
    rep["bounds_cm"] = {"origin": [b.origin.x, b.origin.y, b.origin.z], "extent": [b.box_extent.x, b.box_extent.y, b.box_extent.z]}
    # reference pose of every bone, component space (cm): Research/Mazzarino80/Blender/m80_ape_leggera.py puts the
    # light model's object origins there
    pose = unreal.AnimPoseExtensions.get_reference_pose(skel)
    rep["ossa_cm"] = {}
    for bn in unreal.AnimPoseExtensions.get_bone_names(pose):
        t = unreal.AnimPoseExtensions.get_ref_bone_pose(pose, bn, unreal.AnimPoseSpaces.WORLD)
        rep["ossa_cm"][str(bn)] = [t.translation.x, t.translation.y, t.translation.z]
    phys = mesh.get_editor_property("physics_asset")
    rep["physics_asset"] = phys.get_path_name() if phys else None
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ape_ispeziona.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "ape_ispeziona_errore.txt"))
