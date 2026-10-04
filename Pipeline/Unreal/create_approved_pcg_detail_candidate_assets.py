"""Create independent per-lot PCG data and graph assets for visual review."""
from pathlib import Path
import importlib
import json
import sys
import traceback

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Research/Mazzarino80/PCG/Candidates/approved_detail_material_v1.json"
OUT = ROOT / "Pipeline/Unreal/approved_pcg_detail_candidate_assets_result.json"
ASSET_ROOT = "/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1"
MASTER_GRAPH = "/Game/Mazzarino80/PCG/Graphs/PCG_Building_Master"
sys.path.insert(0, str(ROOT / "Scripts"))
import mazzarino80_pcg_create_data_assets as data_assets
data_assets = importlib.reload(data_assets)
data_assets.ASSET_ROOT = ASSET_ROOT

houses = json.loads(SOURCE.read_text(encoding="utf-8"))["houses"]
master = unreal.EditorAssetLibrary.load_asset(MASTER_GRAPH)
if not isinstance(master, unreal.PCGGraph):
    raise RuntimeError("Missing existing five-stage PCG master")
world = unreal.new_object(unreal.World, name="M80_ApprovedDetailCandidateExportWorld")
result = {"source": str(SOURCE), "asset_root": ASSET_ROOT,
          "shared_five_stage_graph": MASTER_GRAPH, "lots": {}, "errors": {}}
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
for lot, house in houses.items():
    try:
        info = data_assets.make_asset({"building_id": lot,
                                       "stage_points": house["stage_points"]}, world)
        if not info["saved"]:
            raise RuntimeError("PCG data asset not saved")
        data = unreal.EditorAssetLibrary.load_asset(info["path"])
        path = ASSET_ROOT + "/PCG_Building_" + lot
        graph = unreal.EditorAssetLibrary.load_asset(path)
        if graph is None:
            graph = asset_tools.create_asset("PCG_Building_" + lot, ASSET_ROOT,
                                             unreal.PCGGraph, unreal.PCGGraphFactory())
        if not isinstance(graph, unreal.PCGGraph):
            raise RuntimeError("PCG wrapper graph not created")
        if not list(graph.get_editor_property("nodes")):
            loader, settings = graph.add_node_of_type(unreal.PCGLoadDataAssetSettings)
            settings.asset = data
            node, subsettings = graph.add_node_of_type(unreal.PCGSubgraphSettings)
            subsettings.get_editor_property("subgraph_instance").set_editor_property("graph", master)
            graph.add_edge(loader, "Out", node, "In")
            graph.add_edge(node, "Out", graph.get_output_node(), "Out")
        if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
            raise RuntimeError("PCG wrapper graph not saved")
        result["lots"][lot] = {"data": info, "graph": path,
                               "points": sum(info["counts"].values())}
    except Exception:
        result["errors"][lot] = traceback.format_exc()
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_APPROVED_DETAIL_ASSETS", len(result["lots"]), len(result["errors"]))
if result["errors"]:
    raise RuntimeError("Candidate PCG assets have errors; see result JSON")
