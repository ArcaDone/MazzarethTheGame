"""Inspect PCG data and mesh-spawner APIs in the running UE 5.5 editor."""
import json
from pathlib import Path

import unreal

names = (
    "PCGDataAsset", "PCGDataCollection", "PCGTaggedData", "PCGPointData",
    "PCGPoint", "PCGLoadDataAssetSettings", "PCGStaticMeshSpawnerSettings",
    "PCGMeshSelectorWeighted", "PCGMeshSelectorByAttribute", "PCGWeightedMeshEntry",
    "PCGMeshSelectorWeightedEntry", "PCGStaticMeshSpawnerEntry",
    "DataAssetFactory", "PCGDataAssetFactory", "PCGPin", "PCGGraph",
    "PCGGraphFactory", "PCGMetadata", "PCGMetadataAttribute",
)
result = {}
for name in names:
    cls = getattr(unreal, name, None)
    if not cls:
        continue
    item = {"doc": (cls.__doc__ or "")[:16000]}
    try:
        obj = cls()
        item["fields"] = [x for x in dir(obj) if not x.startswith("_") and x not in dir(unreal.Object)]
        for field in ("tagged_data", "data", "mesh_selector_instance", "mesh_selector_parameters", "mesh_selector_type", "data_asset"):
            try:
                value = obj.get_editor_property(field)
                item[field] = {"type": str(type(value)), "repr": str(value)[:500]}
            except Exception as e:
                item[field + "_error"] = str(e)[:250]
    except Exception as e:
        item["construct_error"] = str(e)
    result[name] = item

out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_asset_api.json"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_PCG_ASSET_API " + str(out))
