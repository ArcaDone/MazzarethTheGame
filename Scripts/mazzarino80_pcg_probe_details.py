"""Record the PCG graph and node API exposed by this exact Unreal build."""
import json
from pathlib import Path

import unreal

types = (
    "PCGGraph", "PCGGraphFactory", "PCGNode", "PCGGraphInputOutputSettings",
    "PCGDataFromActorSettings", "PCGGetActorPropertySettings", "PCGGetSplineSettings",
    "PCGSplineSamplerSettings", "PCGSubgraphSettings", "PCGStaticMeshSpawnerSettings",
    "PCGSpawnActorSettings", "PCGCreatePointsSettings", "PCGTransformPointsSettings",
    "PCGBlueprintSettings", "PCGComponent",
)
methods = (
    "add_node_of_type", "add_edge", "set_graph", "generate", "get_editor_property",
)
result = {}
for name in types:
    cls = getattr(unreal, name, None)
    if cls is None:
        continue
    item = {"class_doc": (cls.__doc__ or "")[:1000], "methods": {}}
    for method in methods:
        fn = getattr(cls, method, None)
        if fn:
            item["methods"][method] = (fn.__doc__ or "")[:2400]
    try:
        obj = cls()
        item["instance_fields"] = [field for field in dir(obj) if not field.startswith("_") and field not in dir(unreal.Object)]
    except Exception as exc:
        item["construct_error"] = str(exc)
    result[name] = item

out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_python_details.json"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_PCG_API_DETAILS " + str(out))
