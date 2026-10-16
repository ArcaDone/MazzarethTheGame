"""Builds (assembles) MHC_Sandro into a game character: optimized pipeline, high quality, everything under
/Game/Mazzarino80/Personaggi/Sandro/Build (common assets in .../Personaggi/Common, so the sample's legacy
/Game/MetaHumans/Common is not touched). Then lists what the build made and the components of the built Blueprint.
Out: Saved/Mazzarino80/Player/sandro_build.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_sandro_build.py -TimeoutMinutes 120
"""
import json
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Player"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
BUILD = "/Game/Mazzarino80/Personaggi/Sandro/Build"
COMMON = "/Game/Mazzarino80/Personaggi/Common"


def components(bp):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    rows = []
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
        if not o:
            continue
        row = {"name": o.get_name(), "class": o.get_class().get_name()}
        for p in ("skeletal_mesh_asset", "asset", "groom_asset", "anim_class", "outfit_asset"):
            try:
                v = o.get_editor_property(p)
                row[p] = v.get_path_name() if v else None
            except Exception:  # noqa: BLE001
                pass
        rows.append(row)
    return rows


def main():
    r = {"enums": {"type": [str(x) for x in unreal.MetaHumanDefaultPipelineType.__members__] if hasattr(unreal.MetaHumanDefaultPipelineType, "__members__") else dir(unreal.MetaHumanDefaultPipelineType),
                   "quality": [str(x) for x in unreal.MetaHumanQualityLevel.__members__] if hasattr(unreal.MetaHumanQualityLevel, "__members__") else dir(unreal.MetaHumanQualityLevel)}}
    c = unreal.load_asset("/Game/Mazzarino80/Personaggi/Sandro/MHC_Sandro")
    SUB.try_add_object_to_edit(c)
    p = unreal.MetaHumanCharacterEditorBuildParameters()
    p.set_editor_property("absolute_build_path", BUILD)
    p.set_editor_property("common_folder_path", COMMON)
    p.set_editor_property("name_override", "Sandro")
    p.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.OPTIMIZED)
    p.set_editor_property("pipeline_quality", unreal.MetaHumanQualityLevel.HIGH)
    r["params"] = str(p)
    # Copying the face control rigs to COMMON logs "Cannot break link ... RerouteNode" errors, which Python raises
    # after the call: kept as warnings, the build goes on.
    try:
        r["built"] = str(SUB.build_meta_human(c, p))
    except Exception as e:  # noqa: BLE001
        r["built"] = "errors: " + str(e)[:3000]
    for folder in (BUILD, COMMON):
        if unreal.EditorAssetLibrary.does_directory_exist(folder):
            r.setdefault("saved", {})[folder] = unreal.EditorAssetLibrary.save_directory(folder, False, True)
    SUB.remove_object_to_edit(c)
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reg.scan_paths_synchronous([BUILD, COMMON], True)
    r["assets"] = sorted("%s (%s)" % (d.package_name, d.asset_class_path.asset_name) for d in reg.get_assets_by_path(BUILD, recursive=True))
    r["common"] = len(reg.get_assets_by_path(COMMON, recursive=True))
    for d in reg.get_assets_by_path(BUILD, recursive=True):
        if str(d.asset_class_path.asset_name) == "Blueprint":
            r.setdefault("blueprints", {})[str(d.package_name)] = components(d.get_asset())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sandro_build.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sandro_build_errore.txt").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    unreal.SystemLibrary.quit_editor()
