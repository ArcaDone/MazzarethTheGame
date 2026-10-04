"""Create 67 independent detail-only PCG data assets and wrapper graphs."""
from pathlib import Path
import importlib
import json
import sys
import traceback
import unreal

root = Path(unreal.Paths.project_dir())
source = root / "Research/Mazzarino80/PCG/Candidates/district_batch01_details.json"
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
houses = json.loads(source.read_text(encoding="utf-8"))["houses"]
expected = set().union(*(set(d["lots"]) - set(d["approved_pcg_lots"])
                         for d in manifest["districts"][:3]))
if {h["building_id"] for h in houses} != expected or len(houses) != 67:
    raise RuntimeError("Detail plan no longer matches the first three districts")

sys.path.insert(0, str(root / "Scripts"))
import mazzarino80_pcg_create_data_assets as data_assets
data_assets = importlib.reload(data_assets)
data_assets.ASSET_ROOT = "/Game/Mazzarino80/PCG/DistrictBatch01_Details"
data_assets.INPUT = source
stage = unreal.load_asset("/Game/Mazzarino80/PCG/Graphs/PCG_Building_Details")
if not isinstance(stage, unreal.PCGGraph):
    raise RuntimeError("Approved detail stage graph not found")
world = unreal.new_object(unreal.World, name="M80_DistrictBatch01DetailExportWorld")
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
report = {"asset_root": data_assets.ASSET_ROOT, "source": str(source),
          "lots": {}, "errors": {}}
for house in houses:
    lot = house["building_id"]
    try:
        data = data_assets.make_asset(house, world)
        if not data["saved"]:
            raise RuntimeError("PCG point data was not saved")
        graph_path = data_assets.ASSET_ROOT + "/PCG_Detail_" + lot
        graph = unreal.load_asset(graph_path)
        if not graph:
            graph = asset_tools.create_asset("PCG_Detail_" + lot,
                data_assets.ASSET_ROOT, unreal.PCGGraph, unreal.PCGGraphFactory())
        if not isinstance(graph, unreal.PCGGraph):
            raise RuntimeError("Could not create detail graph")
        if not list(graph.get_editor_property("nodes")):
            loader, settings = graph.add_node_of_type(unreal.PCGLoadDataAssetSettings)
            settings.asset = unreal.load_asset(data["path"])
            node, subsettings = graph.add_node_of_type(unreal.PCGSubgraphSettings)
            subsettings.get_editor_property("subgraph_instance").set_editor_property("graph", stage)
            graph.add_edge(loader, "Out", node, "In")
            graph.add_edge(node, "Out", graph.get_output_node(), "Out")
        if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
            raise RuntimeError("Detail graph was not saved")
        report["lots"][lot] = {"data": data, "graph": graph_path,
                                "points": len(house["stage_points"]["Details"])}
    except Exception:
        report["errors"][lot] = traceback.format_exc()
dest = root / "Pipeline/Unreal/first_pcg_batch_detail_assets_result.json"
dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_DETAIL_ASSETS", len(report["lots"]), len(report["errors"]))
if report["errors"]:
    raise RuntimeError("Errors creating first-batch detail assets")
