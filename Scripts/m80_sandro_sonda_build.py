"""Probe before making Sandro the player: is MHC_Sandro rigged and buildable, what the build API takes, what the
current player Blueprint is made of.
Out: Saved/Mazzarino80/Player/sonda_build.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_sandro_sonda_build.py
"""
import json
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Player"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)


def props(obj):
    out = {}
    for n in dir(obj):
        if n.startswith("_"):
            continue
        try:
            v = getattr(obj, n)
        except Exception as e:  # noqa: BLE001
            out[n] = repr(e)[:80]
            continue
        out[n] = "(method)" if callable(v) else str(v)[:300]
    return out


def main():
    r = {}
    c = unreal.load_asset("/Game/Mazzarino80/Personaggi/Sandro/MHC_Sandro")
    SUB.try_add_object_to_edit(c)
    r["status"] = unreal.M80EditorLibrary.get_meta_human_build_status(c)
    r["can_build"] = SUB.can_build_meta_human(c, False)
    r["subsystem"] = [n for n in dir(SUB) if not n.startswith("_")]
    for cls in ("MetaHumanCharacterEditorBuildParameters", "MetaHumanCharacterEditorPipeline", "MetaHumanDefaultPipelineBase",
                "MetaHumanCharacterPaletteProjectSettings"):
        t = getattr(unreal, cls, None)
        r[cls] = props(t()) if t and not cls.endswith("Pipeline") and not cls.endswith("Base") else (str(t) if t else None)
    r["pipeline_classes"] = [n for n in dir(unreal) if "Pipeline" in n and "MetaHuman" in n]
    coll = SUB.get_preview_collection(c) if hasattr(SUB, "get_preview_collection") else None
    if coll:
        r["collection"] = props(coll)
        try:
            r["pipeline"] = str(coll.get_editor_property("pipeline"))
            r["pipeline_props"] = props(coll.get_editor_property("pipeline"))
        except Exception as e:  # noqa: BLE001
            r["pipeline"] = repr(e)
    bp = unreal.load_asset("/Game/Mazzarino80/Player/BP_M80_Giocatore")
    gen = unreal.EditorAssetLibrary.load_blueprint_class("/Game/Mazzarino80/Player/BP_M80_Giocatore")
    cdo = unreal.get_default_object(gen)
    r["player_parent"] = str(unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp)) if bp else None
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    rows = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
        row = {"name": str(o.get_name()) if o else None, "class": o.get_class().get_name() if o else None}
        if isinstance(o, unreal.SkeletalMeshComponent):
            m = o.get_editor_property("skeletal_mesh_asset") if hasattr(o, "get_editor_property") else None
            row["mesh"] = m.get_path_name() if m else None
            ac = o.get_editor_property("anim_class")
            row["anim_class"] = ac.get_path_name() if ac else None
            row["mode"] = str(o.get_editor_property("animation_mode"))
            try:
                lp = o.get_editor_property("leader_pose_component")
                row["leader"] = lp.get_name() if lp else None
            except Exception:  # noqa: BLE001
                pass
        rows.append(row)
    r["player_components"] = rows
    SUB.remove_object_to_edit(c)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda_build.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda_build_errore.txt").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    unreal.SystemLibrary.quit_editor()
