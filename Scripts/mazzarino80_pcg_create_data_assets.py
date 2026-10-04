"""Create per-lot PCG point assets from the editable catalog compiler output."""
import json
import os
import traceback
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
INPUT = ROOT / os.environ.get("M80_PCG_INPUT", "Research/Mazzarino80/PCG/Buildings_Test18_PCGPoints.json")
STYLE_MAP = json.loads((ROOT / "Pipeline/Unreal/visual_style_map.json").read_text(encoding="utf-8"))
OUT = ROOT / os.environ.get("M80_PCG_OUTPUT", "Saved/Mazzarino80/PCG/create_data_assets.json")
ASSET_ROOT = os.environ.get("M80_PCG_ASSET_ROOT", "/Game/Mazzarino80/PCG/Buildings")
TEST_IDS = None


def make_asset(house, world):
    lot = house["building_id"]
    style = STYLE_MAP.get(lot, house.get("visual_style", "DISTRICT_DETAIL"))
    name = "PCGDA_Building_" + lot
    path = ASSET_ROOT + "/" + name
    asset = unreal.load_asset(path)
    if not asset:
        exporter = unreal.PCGLevelToAsset()
        exporter.set_world(world)
        params = unreal.PCGAssetExporterParameters()
        params.asset_name = name
        params.asset_path = ASSET_ROOT
        params.open_save_dialog = False
        params.save_on_export_ended = False
        unreal.PCGAssetExporterUtils.create_asset(exporter, params)
        asset = unreal.load_asset(path)
    if not asset:
        raise RuntimeError("Failed to create " + path)
    tagged_data = []
    counts = {}
    for stage, specs in house["stage_points"].items():
        data = unreal.new_object(unreal.PCGPointData, outer=asset)
        metadata = data.mutable_metadata()
        metadata.create_soft_object_path_attribute("Mesh", unreal.SoftObjectPath(), False)
        metadata.create_soft_object_path_attribute("Material", unreal.SoftObjectPath(), False)
        metadata.create_string_attribute("LotID", "", False)
        metadata.create_string_attribute("Role", "", False)
        metadata.create_string_attribute("VisualStyle", "", False)
        points = []
        for spec in specs:
            point = unreal.PCGPoint()
            if "rotation_quat" in spec:
                x, y, z, w = spec["rotation_quat"]
                rotation = unreal.MathLibrary.quat_rotator(unreal.Quat(x=x, y=y, z=z, w=w))
            else:
                pitch, yaw, roll = spec["rotation_deg"]
                rotation = unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll)
            point.transform = unreal.Transform(
                location=unreal.Vector(*spec["location_cm"]),
                rotation=rotation,
                scale=unreal.Vector(*spec["scale"]),
            )
            point.seed = spec["seed"]
            point.set_soft_object_path_attribute(metadata, "Mesh", unreal.SoftObjectPath(spec["mesh"]))
            point.set_soft_object_path_attribute(metadata, "Material", unreal.SoftObjectPath(spec["material"]))
            point.set_string_attribute(metadata, "LotID", lot)
            point.set_string_attribute(metadata, "Role", spec["role"])
            point.set_string_attribute(metadata, "VisualStyle", style)
            points.append(point)
        data.set_points(points)
        tagged = unreal.PCGTaggedData()
        tagged.data = data
        tagged.pin = "Out"
        tagged.tags = {stage}
        tagged_data.append(tagged)
        counts[stage] = data.get_num_points()
    asset.modify()
    collection = asset.get_editor_property("data")
    collection.tagged_data = tagged_data
    asset.name = "Building " + lot
    asset.description = unreal.Text("PCG placements from " + INPUT.name)
    saved = unreal.EditorAssetLibrary.save_loaded_asset(asset)
    return {"path": path, "saved": saved, "style": style, "counts": counts,
            "tagged_count": len(asset.get_editor_property("data").tagged_data)}


def main():
    houses = json.loads(INPUT.read_text(encoding="utf-8"))["houses"]
    if {house["building_id"] for house in houses} != set(STYLE_MAP):
        raise RuntimeError("Visual style map must cover exactly the point catalog")
    world = unreal.new_object(unreal.World, name="M80_PCG_CatalogExportWorld")
    result = {"assets": {}, "errors": {}}
    for house in houses:
        lot = house["building_id"]
        if TEST_IDS is not None and lot not in TEST_IDS:
            continue
        try:
            result["assets"][lot] = make_asset(house, world)
        except Exception:
            result["errors"][lot] = traceback.format_exc()
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    unreal.log("M80_PCG_DATA_ASSETS " + str(OUT))


if __name__ == "__main__":
    main()
