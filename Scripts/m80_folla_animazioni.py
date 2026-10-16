"""The crowd's Mixamo clips (D:/animations: old man's walk and idle, sad walk, walking with a shopping bag, zombie walks for
the dragging legs of the old, talking, arguing, telling a secret, yelling, tripping) retargeted onto the UEFN mannequin
that AM80Pedone animates.
Their skeleton is not the climbing clips' one (SK_M80_Mixamo, Scripts/m80_animazioni_import.py: legs 44 cm a bone,
these 32 cm): through that one the hips read as crouched and the feet as lifted (squatting old, badly placed feet).
So they come with their own skeleton, from Research/Mazzarino80/Blender/m80_mixamo_folla.py (SK_M80_MixamoFolla + the
clips re-exported from the same armature), get their own IK rig (Unreal's auto-characterisation) and the retargeter
RTG_M80_Folla_Mixamo_to_UEFN (a copy of the climbing one, its source rig swapped: root motion from the pelvis, the
clips have no root bone). Mixamo's old man walks with his hips at 87% of his leg, the zombies lower (a squat on our people): those
clips go through copies with the pelvis raised (RTG_M80_Folla_Mixamo_to_UEFN_Vecchio, ALZA_VECCHIO), the back stays bent.
Sources in /Game/Mazzarino80/Personaggi/Animazioni/Mixamo/Folla, results /Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_*.
Report: Saved/Mazzarino80/Folla/animazioni.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_animazioni.py
"""
import json
import os
import sys
import traceback

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

SRC = os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/Folla/Animazioni")
DEST = "/Game/Mazzarino80/Personaggi/Animazioni"
MIX = DEST + "/Mixamo/Folla"
PLAYER_RTG = "/Game/Mazzarino80/Player/Anim/Mixamo/RTG_M80_Mixamo_to_UEFN"
UEFN_MESH = "/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin"
SCALA_VERTICALE = float(os.environ.get("M80_SCALA_VERTICALE", "1.0"))
# Pelvis raised per clip: hips while walking / rest hips (0.962): old man 0.884, his idle 0.892, zombies 0.872 / 0.785.
ALZA_VECCHIO = {"Mixamo_VecchioCammina": 1.11, "Mixamo_VecchioFermo": 1.07, "Mixamo_Trascina": 1.07, "Mixamo_Trascina2": 1.09}
REPORT = os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/Folla/animazioni.json")
# Blender's file names (m80_mixamo_folla.py) -> ours.
NAMES = {"OldManIdle": "VecchioFermo", "OldManWalk": "VecchioCammina", "SadWalk": "CamminaTriste",
         "StandingArguing": "Litigare", "Talking": "Parlare", "Talking1": "Parlare2", "TellingASecret": "Segreto",
         "Tripping": "Inciampo", "WalkingWithShoppingBag": "CamminaSpesa", "Walkingzombie2": "Trascina2",
         "Yelling": "Urlare", "ZombieWalk": "Trascina"}
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
report = {"clips": {}, "missing": [], "notes": []}


def import_fbx(path, name, skeleton):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", skeleton is None)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("import_animations", skeleton is not None)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("create_physics_asset", False)
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


def attempt(label, fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001 - noted, the rest goes on
        report["notes"].append(label + ": " + traceback.format_exc().splitlines()[-1])
        return None


def retarget(anims, mesh, rtg):
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", [EAL.find_asset_data(a.get_path_name()) for a in anims])
    inputs.set_editor_property("source_mesh", mesh)
    inputs.set_editor_property("target_mesh", unreal.load_asset(UEFN_MESH))
    inputs.set_editor_property("ik_retarget_asset", rtg)
    inputs.set_editor_property("search", "Mixamo_")
    inputs.set_editor_property("replace", "A_M80_Folla_")
    inputs.set_editor_property("target_path", DEST)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", True)
    out = []
    for ad in unreal.IKRetargetBatchOperation.run_batch_retarget(inputs):
        anim = ad.get_asset()
        if isinstance(anim, unreal.AnimSequence):
            # AM80Pedone reads the travel from the root track and keeps the root in place itself.
            anim.set_editor_property("enable_root_motion", False)
            EAL.save_loaded_asset(anim, False)
            out.append(anim)
    return out


def steps():
    # 1) The skeleton with its dummy mesh, then the clips onto it.
    got = import_fbx(os.path.join(SRC, "SK_M80_MixamoFolla.fbx"), "SK_M80_MixamoFolla", None)
    mesh = next((o for o in got if isinstance(o, unreal.SkeletalMesh)), None) or unreal.load_asset(MIX + "/SK_M80_MixamoFolla")
    skeleton = mesh.get_editor_property("skeleton")
    report["mesh"] = mesh.get_path_name()
    yield 5
    sources = {}
    for blender, ours in NAMES.items():
        path = os.path.join(SRC, "A_M80_%s.fbx" % blender)
        if not os.path.exists(path):
            report["missing"].append(blender)
            continue
        tag = "Mixamo_" + ours
        anim = next((o for o in import_fbx(path, tag, skeleton) if isinstance(o, unreal.AnimSequence)), None)
        if anim and anim.get_name() != tag:
            EAL.rename_asset(anim.get_path_name(), "%s/%s" % (MIX, tag))
            anim = unreal.load_asset("%s/%s" % (MIX, tag))
        if anim:
            sources[tag] = anim
        else:
            report["missing"].append(blender)
        yield 2

    # 2) Its IK rig, characterised automatically.
    rig_path = MIX + "/IK_M80_MixamoFolla"
    rig = unreal.load_asset(rig_path) if EAL.does_asset_exist(rig_path) else \
        TOOLS.create_asset("IK_M80_MixamoFolla", MIX, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    ctl = unreal.IKRigController.get_controller(rig)
    ctl.set_skeletal_mesh(mesh)
    ctl.apply_auto_generated_retarget_definition()
    report["chains"] = [str(c.get_editor_property("chain_name")) for c in ctl.get_retarget_chains()]
    EAL.save_loaded_asset(rig, False)

    # 3) The retargeter: the climbing one's ops (pelvis, FK chains, IK, root motion from the pelvis) on this source.
    rtg_path = DEST + "/Mixamo/RTG_M80_Folla_Mixamo_to_UEFN"
    if not EAL.does_asset_exist(rtg_path):
        EAL.duplicate_asset(PLAYER_RTG, rtg_path)
    rtg = unreal.load_asset(rtg_path)
    rc = unreal.IKRetargeterController.get_controller(rtg)
    src = unreal.RetargetSourceOrTarget.SOURCE
    rc.set_ik_rig(src, rig)
    attempt("assign_ik_rig_to_all_ops", lambda: rc.assign_ik_rig_to_all_ops(src, rig))
    rc.set_preview_mesh(src, mesh)
    attempt("auto_map_chains", lambda: rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True))
    # Mixamo's thumbs twist differently (they stuck up on the climbing clips): the mannequin keeps its own.
    for side in ("Left", "Right"):
        attempt("thumb " + side, lambda side=side: rc.set_source_chain("None", side + "Thumb"))
    # Mixamo stands in a T pose, the mannequin in an A pose: the source bones are turned onto the target's directions.
    attempt("auto_align_all_bones", lambda: rc.auto_align_all_bones(src))
    pelvis = rc.get_op_controller(rc.get_index_of_op_by_name("Pelvis Motion"))
    settings = pelvis.get_settings()
    settings.set_editor_property("scale_vertical", SCALA_VERTICALE)
    pelvis.set_settings(settings)
    report["scale_vertical"] = pelvis.get_settings().get_editor_property("scale_vertical")
    report["ops"] = [str(rc.get_op_name(i)) for i in range(rc.get_num_retarget_ops())]
    EAL.save_loaded_asset(rtg, False)
    yield 5

    # 4) Retarget onto the mannequin: the old man's clips one by one with their pelvis raised, the others together.
    report["scale_vertical_old"] = {}
    groups = [([a for t, a in sources.items() if t not in ALZA_VECCHIO], rtg)]
    for tag, scale in ALZA_VECCHIO.items():
        if tag not in sources:
            continue
        path = "%s_Vecchio%d" % (rtg_path, round(scale * 100))
        if not EAL.does_asset_exist(path):
            EAL.duplicate_asset(rtg_path, path)
        old = unreal.load_asset(path)
        oc = unreal.IKRetargeterController.get_controller(old)
        op = oc.get_op_controller(oc.get_index_of_op_by_name("Pelvis Motion"))
        st = op.get_settings()
        st.set_editor_property("scale_vertical", scale)
        op.set_settings(st)
        EAL.save_loaded_asset(old, False)
        report["scale_vertical_old"][tag] = op.get_settings().get_editor_property("scale_vertical")
        groups.append(([sources[tag]], old))
    for anims, retargeter in groups:
        for anim in retarget(anims, mesh, retargeter):
            report["clips"][anim.get_name()] = {"length_s": round(anim.get_play_length(), 2),
                                                "frames": anim.get_editor_property("number_of_sampled_frames")}
        yield 2
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    yield 2


m80_seq.Sequencer(steps(), log_file=REPORT.replace(".json", "_errore.txt"))
