"""Publish complete per-lot PCG point data and five-stage graphs."""
from pathlib import Path
import importlib
import json
import sys
import traceback
import unreal

root = Path(unreal.Paths.project_dir())
source = root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/full_pcg_points.json"
houses = json.loads(source.read_text(encoding="utf-8"))["houses"]
if len(houses) != 67 or len({h["building_id"] for h in houses}) != 67:
    raise RuntimeError("Full PCG source must contain exactly 67 unique lots")
master = unreal.load_asset("/Game/Mazzarino80/PCG/Graphs/PCG_Building_Master")
if not isinstance(master, unreal.PCGGraph):
    raise RuntimeError("Five-stage master graph missing")
sys.path.insert(0, str(root / "Scripts"))
import mazzarino80_pcg_create_data_assets as data_assets
data_assets = importlib.reload(data_assets)
data_assets.ASSET_ROOT = "/Game/Mazzarino80/PCG/DistrictBatch01_Full"
data_assets.INPUT = source
world = unreal.new_object(unreal.World, name="M80_DistrictBatch01FullExportWorld")
tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"source": str(source), "asset_root": data_assets.ASSET_ROOT,
          "houses": {}, "errors": {}}
checked_assets = {}
for house in houses:
    lot = house["building_id"]
    try:
        for points in house["stage_points"].values():
            for point in points:
                for key in ("mesh", "material"):
                    path = point[key]
                    if path not in checked_assets:
                        checked_assets[path] = bool(unreal.load_asset(path))
                    if not checked_assets[path]:
                        raise RuntimeError("Missing " + key + " " + path)
        data = data_assets.make_asset(house, world)
        if not data["saved"]:
            raise RuntimeError("Full PCG point data not saved")
        graph_path = data_assets.ASSET_ROOT + "/PCG_Building_" + lot
        graph = unreal.load_asset(graph_path)
        if not graph:
            graph = tools.create_asset("PCG_Building_" + lot, data_assets.ASSET_ROOT,
                                       unreal.PCGGraph, unreal.PCGGraphFactory())
        if not isinstance(graph, unreal.PCGGraph):
            raise RuntimeError("Could not create full PCG graph")
        if not list(graph.get_editor_property("nodes")):
            loader, settings = graph.add_node_of_type(unreal.PCGLoadDataAssetSettings)
            settings.asset = unreal.load_asset(data["path"])
            node, subsettings = graph.add_node_of_type(unreal.PCGSubgraphSettings)
            subsettings.get_editor_property("subgraph_instance").set_editor_property("graph", master)
            graph.add_edge(loader, "Out", node, "In")
            graph.add_edge(node, "Out", graph.get_output_node(), "Out")
        if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
            raise RuntimeError("Full PCG graph not saved")
        report["houses"][lot] = {"data": data["path"], "graph": graph_path,
                                  "points": sum(len(x) for x in house["stage_points"].values())}
    except Exception:
        report["errors"][lot] = traceback.format_exc()
dest = root / "Pipeline/Unreal/first_pcg_batch_full_assets_result.json"
dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_FULL_ASSETS", len(report["houses"]), len(report["errors"]))
if report["errors"]:
    raise RuntimeError("Full PCG assets have errors")
