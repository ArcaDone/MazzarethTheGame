"""Create one persistent PCG point-data asset to verify Python/UE serialization."""
import json
import traceback
from pathlib import Path

import unreal

log = {}
try:
    path = "/Game/Mazzarino80/PCG/Validation"
    name = "PCGDA_TestStructure"
    log["package_api"] = {x: str(getattr(unreal, x).__doc__)[:500] for x in ("create_package", "new_object", "PCGAssetExporterUtils", "PCGLevelToAsset") if hasattr(unreal, x)}
    world = unreal.new_object(unreal.World, name="M80_PCG_TransientWorld")
    exporter = unreal.PCGLevelToAsset()
    exporter.set_world(world)
    params = unreal.PCGAssetExporterParameters()
    params.asset_name = name
    params.asset_path = path
    params.open_save_dialog = False
    params.save_on_export_ended = False
    log["create_package"] = str(unreal.PCGAssetExporterUtils.create_asset(exporter, params))
    asset = unreal.load_asset(path + "/" + name)
    if not asset:
        raise RuntimeError("PCG exporter did not create an asset")
    log["asset"] = str(asset)
    point_data = unreal.new_object(unreal.PCGPointData, outer=asset, name="StructurePoints")
    point = unreal.PCGPoint()
    point.transform = unreal.Transform(location=unreal.Vector(100, 200, 300), scale=unreal.Vector(3, 1, 2))
    point.seed = 2357
    for method in ("set_soft_object_path_attribute", "set_string_attribute", "set_integer64_attribute", "initialize_metadata"):
        log[method + "_doc"] = str(getattr(point, method).__doc__)[:1200]
    log["metadata_fields"] = [x for x in dir(point_data.mutable_metadata()) if not x.startswith("_") and x not in dir(unreal.Object)]
    point_data.set_points([point])
    tagged = unreal.PCGTaggedData()
    tagged.data = point_data
    tagged.pin = "Out"
    collection = unreal.PCGDataCollection()
    collection.tagged_data = [tagged]
    try:
        live_collection = asset.get_editor_property("data")
        live_collection.tagged_data = [tagged]
        log["assignment"] = "nested_collection"
    except Exception as exc:
        log["assignment_error"] = str(exc)
    log["tagged_count_before_save"] = len(asset.get_editor_property("data").tagged_data)
    log["save"] = unreal.EditorAssetLibrary.save_loaded_asset(asset)
    loaded = unreal.load_asset(path + "/" + name)
    log["tagged_count_after_reload"] = len(loaded.get_editor_property("data").tagged_data)
    if loaded.get_editor_property("data").tagged_data:
        reloaded_points = loaded.get_editor_property("data").tagged_data[0].data
        log["point_count_after_reload"] = reloaded_points.get_num_points()
except Exception:
    log["error"] = traceback.format_exc()

out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_asset_test.json"
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_ASSET_TEST " + str(out))
