"""Probe of a crowd character's built Blueprint (m80_folla_build.py): its components as the build made them (tree, class,
mesh and skeleton, animation class, groom and binding, leader pose settings), to dress AM80Pedone the same way.
Env M80_CHI=Anziano2. Out: Saved/Mazzarino80/Folla/sonda_bp.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_sonda_bp.py
"""
import json
import os
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Folla"
KEY = os.environ.get("M80_CHI", "Anziano2")


def prop(o, name):
    try:
        v = o.get_editor_property(name)
    except Exception:  # noqa: BLE001
        return None
    return v.get_path_name() if hasattr(v, "get_path_name") else str(v)[:200]


def main():
    path = "/Game/Mazzarino80/Personaggi/Folla/Build/%s/BP_%s" % (KEY, KEY)
    bp = unreal.load_asset(path)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    rows = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
        if not o:
            continue
        row = {"name": o.get_name(), "class": o.get_class().get_name()}
        if isinstance(o, unreal.SceneComponent):
            row["attach_parent"] = o.get_attach_parent().get_name() if o.get_attach_parent() else None
            row["socket"] = str(o.get_attach_socket_name())
            row["rel"] = str(o.get_editor_property("relative_location")) + " " + str(o.get_editor_property("relative_rotation"))
        if isinstance(o, unreal.SkinnedMeshComponent):
            mesh = o.get_editor_property("skinned_asset")
            row["mesh"] = mesh.get_path_name() if mesh else None
            if isinstance(mesh, unreal.SkeletalMesh):
                sk = mesh.get_editor_property("skeleton")
                row["skeleton"] = sk.get_path_name() if sk else None
                row["bones"] = o.get_num_bones()
            for n in ("leader_pose_component", "anim_class", "animation_mode", "visibility_based_anim_tick_option",
                      "b_use_bounds_from_leader_pose_component", "override_materials", "forced_lod_model"):
                row[n] = prop(o, n)
        if o.get_class().get_name().startswith("Groom"):
            for n in ("groom_asset", "binding_asset", "physics_asset", "b_use_cards", "source_skeletal_mesh"):
                row[n] = prop(o, n)
        if o.get_class().get_name() == "LODSyncComponent":
            for n in ("num_lods", "forced_lod", "components_to_sync", "custom_lod_mapping"):
                row[n] = prop(o, n)
        rows.append(row)
    gen = unreal.EditorAssetLibrary.load_blueprint_class(path)
    r = {"bp": path, "parent": str(unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp)), "components": rows,
         "class": str(gen)}
    try:
        r["ubergraph"] = [str(g.get_name()) for g in bp.get_editor_property("ubergraph_pages")]
    except Exception as e:  # noqa: BLE001
        r["ubergraph"] = repr(e)[:200]
    face = unreal.load_asset("/Game/Mazzarino80/Personaggi/Common/Face/ABP_Face")
    r["abp_face"] = face.get_path_name() if face else None
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda_bp.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda_bp_errore.txt").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    unreal.SystemLibrary.quit_editor()
