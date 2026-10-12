"""Animations for climbing, fists and aiming, retargeted onto the player's skeleton (UEFN mannequin):
- the user's Mixamo clips (D:/BlenderTest/animazioni: braced hang, shimmy, climb up, drop, jumps to hang, punch combo,
  rifle aiming), imported with their own skeleton into Player/Anim/Mixamo/Sorgenti, an IK rig made by Unreal's
  auto-characterisation (IK_M80_Mixamo) and a retargeter onto IK_UEFN_Mannequin (RTG_M80_Mixamo_to_UEFN, chains
  mapped automatically, root motion generated from the pelvis: the clips have no root bone);
- ALS's two-handed pistol and rifle poses and aim sweeps, through the existing RTG_M80_ALS_to_UEFN.
Results in /Game/Mazzarino80/Player/Anim with Italian names (A_M80_Appeso_*, A_M80_Pugni_Combo, A_M80_Pistola_*,
A_M80_Fucile_*). Report: Saved/Mazzarino80/Player/animazioni.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_animazioni_import.py
"""
import glob
import json
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

SRC = "D:/BlenderTest/animazioni"
ANIM = "/Game/Mazzarino80/Player/Anim"
MIX = ANIM + "/Mixamo/Sorgenti"
REPORT = os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/Player/animazioni.json")
UEFN_RIG = "/Game/Characters/UEFN_Mannequin/Rigs/IK_UEFN_Mannequin"
UEFN_MESH = "/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin"
ALS_RTG = ANIM + "/RTG_M80_ALS_to_UEFN"
ALS_MESH = "/Game/AdvancedLocomotionV4/CharacterAssets/MannequinSkeleton/Meshes/Mannequin"
ALS_DIR = "/Game/AdvancedLocomotionV4/CharacterAssets/MannequinSkeleton/AnimationExamples/Overlay/"
MIXAMO_NAMES = {"Idle To Braced Hang": "A_M80_Appeso_Presa", "Braced Hang Shimmy": "A_M80_Appeso_Laterale",
                "Braced Hang To Crouch": "A_M80_Appeso_Salita", "Braced Hang Drop": "A_M80_Appeso_Lascia",
                "Jump To Hang": "A_M80_Salto_Appeso", "Jumping To Hanging": "A_M80_Salto_Corsa_Appeso",
                "Punch Combo": "A_M80_Pugni_Combo", "Rifle Aiming Idle": "A_M80_Fucile_Mira"}
# Clips whose root motion keeps the height (the body rises onto the ledge or jumps up to it).
CLIMB = ("Braced Hang To Crouch", "Idle To Braced Hang", "Jump To Hang", "Jumping To Hanging")
ALS_NAMES = {"Pistol/ALS_Props_Pistol_2H_Aim_Sweep": "A_M80_Pistola_Mira_Sweep", "Pistol/ALS_Props_Pistol_2H_Poses": "A_M80_Pistola_Pose",
             "Pistol/ALS_Props_Pistol_1H_Poses": "A_M80_Pistola_1M_Pose",
             "M4A1/ALS_Props_M4A1_Aim_Sweep": "A_M80_Fucile_Mira_Sweep", "M4A1/ALS_Props_M4A1_Poses": "A_M80_Fucile_Pose"}
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
report = {"mixamo": {}, "als": {}, "notes": []}


def import_fbx(path, name, skeleton):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", skeleton is None)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_animations", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeleton is None else unreal.FBXImportType.FBXIT_ANIMATION)
    if skeleton:
        ui.set_editor_property("skeleton", skeleton)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path)
    t.set_editor_property("destination_path", MIX)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", ui)
    TOOLS.import_asset_tasks([t])
    return [unreal.load_asset(p) for p in t.get_editor_property("imported_object_paths")]


def asset_data(obj):
    return unreal.EditorAssetLibrary.find_asset_data(obj.get_path_name())


def retarget(assets, src_mesh, rtg, names):
    """Duplicates and retargets assets onto the UEFN mannequin, then moves each to ANIM/<name>."""
    out = {}
    made = unreal.IKRetargetBatchOperation.duplicate_and_retarget([asset_data(a) for a in assets], src_mesh, unreal.load_asset(UEFN_MESH),
                                                                  rtg, "", "", "", "_M80UEFN", False)
    for ad in made:
        obj = ad.get_asset()
        if not isinstance(obj, unreal.AnimSequence):
            continue
        src_name = obj.get_name()[:-len("_M80UEFN")]
        target = names.get(src_name)
        if not target:
            continue
        dest = "%s/%s" % (ANIM, target)
        if EAL.does_asset_exist(dest):
            EAL.delete_asset(dest)
        EAL.rename_asset(obj.get_path_name(), dest)
        anim = unreal.load_asset(dest)
        # No root motion: the movement stays in the pose and UM80ClimbComponent carries the capsule after the body.
        anim.set_editor_property("enable_root_motion", False)
        EAL.save_loaded_asset(anim, False)
        out[target] = {"length_s": round(anim.get_play_length(), 2), "frames": anim.get_editor_property("number_of_sampled_frames")}
    return out


def steps():
    # 1) Mixamo clips, the first one with its mesh and skeleton.
    files = sorted(glob.glob(SRC + "/*.fbx"))
    base = {os.path.splitext(os.path.basename(f))[0]: f for f in files}
    first = files[0]
    objs = import_fbx(first, "SK_M80_Mixamo", None)
    yield 5
    mesh = next((o for o in objs if isinstance(o, unreal.SkeletalMesh)), None) or unreal.load_asset(MIX + "/SK_M80_Mixamo")
    skeleton = mesh.get_editor_property("skeleton")
    anims = {}
    for name, f in base.items():
        tag = name.replace(" ", "_")
        got = import_fbx(f, tag, skeleton) if f != first else objs
        anim = next((o for o in got if isinstance(o, unreal.AnimSequence)), None)
        if anim:
            if anim.get_name() != tag:
                EAL.rename_asset(anim.get_path_name(), "%s/%s" % (MIX, tag))
                anim = unreal.load_asset("%s/%s" % (MIX, tag))
            anims[name] = anim
        yield 2
    report["mixamo_imported"] = sorted(anims)

    # 2) IK rig of the Mixamo skeleton, auto characterised, and the retargeter onto the UEFN mannequin.
    rig_path = ANIM + "/Mixamo/IK_M80_Mixamo"
    rig = unreal.load_asset(rig_path) if EAL.does_asset_exist(rig_path) else \
        TOOLS.create_asset("IK_M80_Mixamo", ANIM + "/Mixamo", unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    ctl = unreal.IKRigController.get_controller(rig)
    ctl.set_skeletal_mesh(mesh)
    ctl.apply_auto_generated_retarget_definition()
    report["mixamo_chains"] = [str(c.get_editor_property("chain_name")) for c in ctl.get_retarget_chains()]
    report["mixamo_root"] = str(ctl.get_retarget_root())
    EAL.save_loaded_asset(rig, False)
    rtg = mixamo_retargeter("RTG_M80_Mixamo_to_UEFN", rig, mesh, unreal.RootMotionHeightSource.SNAP_TO_GROUND)
    rtg_up = mixamo_retargeter("RTG_M80_Mixamo_to_UEFN_Quota", rig, mesh, unreal.RootMotionHeightSource.COPY_HEIGHT_FROM_SOURCE)
    yield 5

    # 3) Retarget: on the ledge (hang, shimmy, drop) the body stays at the same height; climbing up and the jumps to
    # the ledge carry their height in the root motion too.
    level = {k: v for k, v in MIXAMO_NAMES.items() if k not in CLIMB}
    report["mixamo"] = retarget([a for k, a in anims.items() if k in level], mesh, rtg, {a.get_name(): level[k] for k, a in anims.items() if k in level})
    report["mixamo"].update(retarget([a for k, a in anims.items() if k in CLIMB], mesh, rtg_up,
                                     {a.get_name(): MIXAMO_NAMES[k] for k, a in anims.items() if k in CLIMB}))
    yield 5
    als = {}
    for rel, name in ALS_NAMES.items():
        a = unreal.load_asset(ALS_DIR + rel)
        if a:
            als[a.get_name()] = (a, name)
    report["als"] = retarget([a for a, _ in als.values()], unreal.load_asset(ALS_MESH), unreal.load_asset(ALS_RTG), {k: n for k, (_, n) in als.items()})
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    yield 2


def mixamo_retargeter(name, rig, mesh, height):
    path = ANIM + "/Mixamo/" + name
    rtg = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        TOOLS.create_asset(name, ANIM + "/Mixamo", unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(rtg)
    rc.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, rig)
    rc.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, unreal.load_asset(UEFN_RIG))
    rc.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, mesh)
    rc.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, unreal.load_asset(UEFN_MESH))
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    # Mixamo's thumbs twist differently and came out sticking up (a "thumbs up" on the ledge): the mannequin keeps
    # its own relaxed thumbs.
    for side in ("Left", "Right"):
        rc.set_source_chain("None", side + "Thumb")
    # Mixamo stands in a T pose, the mannequin in an A pose: the source bones are turned onto the target's directions.
    rc.auto_align_all_bones(unreal.RetargetSourceOrTarget.SOURCE)
    # The clips have no root bone: root motion comes from the pelvis.
    rc.remove_all_ops()
    rc.add_retarget_op(unreal.RootMotionGeneratorOp)
    op = rc.get_retarget_op_at_index(0)
    op.set_editor_property("root_motion_source", unreal.RootMotionSource.GENERATE_FROM_TARGET_PELVIS)
    op.set_editor_property("root_height_source", height)
    EAL.save_loaded_asset(rtg, False)
    return rtg


m80_seq.Sequencer(steps(), log_file=REPORT.replace(".json", "_error.txt"))
