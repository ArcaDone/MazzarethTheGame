"""PCG proof for the four Blender assemblies, isolated from the town catalog.

The source modules remain separate Static Mesh assets. The stage meshes used
here are QA assemblies only, so they must never replace irregular lot geometry.
"""
from pathlib import Path
import json
import traceback

import unreal

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export/export_manifest.json").read_text(encoding="utf-8"))
OUT = ROOT / "Pipeline/Unreal/reuse_pcg_pilots.json"
BASE = "/Game/Mazzarino80/ReuseKit/PCG"
STAGES = ("Structure", "Facades", "Openings", "Roofs", "Details")
PILOTS = (("STYLE_01", "1249069204"), ("STYLE_02", "1249068307"),
          ("STYLE_03", "1249069200"), ("STYLE_04", "1249069228"))
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def graph_asset(name):
    path = BASE + "/" + name
    graph = unreal.EditorAssetLibrary.load_asset(path)
    if graph is None:
        graph = TOOLS.create_asset(name, BASE, unreal.PCGGraph, unreal.PCGGraphFactory())
    if not isinstance(graph, unreal.PCGGraph):
        raise RuntimeError("Could not create graph " + path)
    return graph


def subgraph_node(graph, target):
    node, settings = graph.add_node_of_type(unreal.PCGSubgraphSettings)
    settings.get_editor_property("subgraph_instance").set_editor_property("graph", target)
    return node


stage_graphs = {}
for stage in STAGES:
    graph = graph_asset("PCG_ReuseKit_" + stage)
    if not list(graph.get_editor_property("nodes")):
        filter_node, filter_settings = graph.add_node_of_type(unreal.PCGFilterByTagSettings)
        filter_settings.selected_tags = stage
        spawner, settings = graph.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
        settings.set_mesh_selector_type(unreal.PCGMeshSelectorByAttribute)
        settings.mesh_selector_parameters.attribute_name = "Mesh"
        settings.mesh_selector_parameters.use_attribute_material_overrides = False
        graph.add_edge(graph.get_input_node(), "In", filter_node, "In")
        graph.add_edge(filter_node, "InsideFilter", spawner, "In")
        graph.add_edge(spawner, "Out", graph.get_output_node(), "Out")
        unreal.EditorAssetLibrary.save_loaded_asset(graph)
    stage_graphs[stage] = graph

master = graph_asset("PCG_ReuseKit_Master")
if not list(master.get_editor_property("nodes")):
    for stage, graph in stage_graphs.items():
        node = subgraph_node(master, graph)
        node.node_title = stage
        master.add_edge(master.get_input_node(), "In", node, "In")
        master.add_edge(node, "Out", master.get_output_node(), "Out")
    unreal.EditorAssetLibrary.save_loaded_asset(master)

world = unreal.new_object(unreal.World, name="M80_ReuseKit_CatalogWorld")
results = {"stage_graphs": [BASE + "/PCG_ReuseKit_" + s for s in STAGES],
           "master": BASE + "/PCG_ReuseKit_Master", "pilots": {}, "errors": {}}
for index, (style, lot) in enumerate(PILOTS):
    try:
        name = "PCGDA_ReuseKit_" + lot
        path = BASE + "/" + name
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset is None:
            exporter = unreal.PCGLevelToAsset()
            exporter.set_world(world)
            params = unreal.PCGAssetExporterParameters()
            params.asset_name = name
            params.asset_path = BASE
            params.open_save_dialog = False
            params.save_on_export_ended = False
            unreal.PCGAssetExporterUtils.create_asset(exporter, params)
            asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset is None:
            raise RuntimeError("Could not create " + path)
        tagged_data = []
        for stage in STAGES:
            rows = [r for r in MANIFEST["pilot_stages"]
                    if r["lot"] == lot and r["stage"] == stage]
            if not rows:
                continue
            mesh_name = Path(rows[0]["file"]).stem
            mesh_path = "/Game/Mazzarino80/ReuseKit/PilotStages/" + mesh_name
            if not isinstance(unreal.EditorAssetLibrary.load_asset(mesh_path), unreal.StaticMesh):
                raise RuntimeError("Missing stage mesh " + mesh_path)
            data = unreal.new_object(unreal.PCGPointData, outer=asset)
            metadata = data.mutable_metadata()
            metadata.create_soft_object_path_attribute("Mesh", unreal.SoftObjectPath(), False)
            metadata.create_string_attribute("LotID", "", False)
            metadata.create_string_attribute("VisualStyle", "", False)
            point = unreal.PCGPoint()
            point.transform = unreal.Transform(location=unreal.Vector(index * 950, 0, 0),
                                               rotation=unreal.Rotator(),
                                               scale=unreal.Vector(1, 1, 1))
            point.seed = 1000 + index * 10 + STAGES.index(stage)
            point.set_soft_object_path_attribute(
                metadata, "Mesh", unreal.SoftObjectPath(mesh_path + "." + mesh_name))
            point.set_string_attribute(metadata, "LotID", lot)
            point.set_string_attribute(metadata, "VisualStyle", style)
            data.set_points([point])
            tagged = unreal.PCGTaggedData()
            tagged.data = data
            tagged.pin = "Out"
            tagged.tags = {stage}
            tagged_data.append(tagged)
        asset.modify()
        asset.get_editor_property("data").tagged_data = tagged_data
        asset.name = "Reuse kit pilot " + lot
        asset.description = unreal.Text("QA only: assembled kit in five PCG stages")
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset):
            raise RuntimeError("Could not save " + path)
        graph = graph_asset("PCG_ReuseKit_" + lot)
        if not list(graph.get_editor_property("nodes")):
            loader, settings = graph.add_node_of_type(unreal.PCGLoadDataAssetSettings)
            settings.asset = asset
            node = subgraph_node(graph, master)
            graph.add_edge(loader, "Out", node, "In")
            graph.add_edge(node, "Out", graph.get_output_node(), "Out")
            unreal.EditorAssetLibrary.save_loaded_asset(graph)
        results["pilots"][lot] = {"style": style, "data": path,
                                  "graph": BASE + "/PCG_ReuseKit_" + lot,
                                  "stages": [stage for stage in STAGES
                                             if any(r["lot"] == lot and r["stage"] == stage
                                                    for r in MANIFEST["pilot_stages"])],
                                  "world_x_cm": index * 950}
    except Exception:
        results["errors"][lot] = traceback.format_exc()

OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
print("M80_REUSE_PCG_PILOTS", len(results["pilots"]), "errors", len(results["errors"]))
if results["errors"]:
    raise RuntimeError("PCG pilots incomplete; inspect " + str(OUT))
