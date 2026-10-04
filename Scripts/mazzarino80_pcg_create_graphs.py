"""Build five reusable PCG stage graphs, a master, and per-lot wrappers."""
import json
import os
import traceback
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / os.environ.get("M80_PCG_GRAPH_OUTPUT", "Saved/Mazzarino80/PCG/create_graphs.json")
DATA_ROOT = os.environ.get("M80_PCG_ASSET_ROOT", "/Game/Mazzarino80/PCG/Buildings")
GRAPH_ROOT = "/Game/Mazzarino80/PCG/Graphs"
HOUSES_INPUT = ROOT / os.environ.get("M80_PCG_INPUT", "Research/Mazzarino80/PCG/Buildings_Test18_PCGPoints.json")
STAGES = ("Structure", "Facades", "Openings", "Roofs", "Details")
TEST_IDS = None


def graph_asset(path, name):
    full = path + "/" + name
    graph = unreal.load_asset(full)
    if not graph:
        graph = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, path, unreal.PCGGraph, unreal.PCGGraphFactory())
    if not graph:
        raise RuntimeError("Cannot create graph " + full)
    return graph


def subgraph_node(graph, target):
    node, settings = graph.add_node_of_type(unreal.PCGSubgraphSettings)
    instance = settings.get_editor_property("subgraph_instance")
    instance.set_editor_property("graph", target)
    return node


def build_stage(stage):
    graph = graph_asset(GRAPH_ROOT, "PCG_Building_" + stage)
    if list(graph.get_editor_property("nodes")):
        return graph
    graph.description = unreal.Text(stage + " modules filtered from per-lot PCG data")
    filter_node, filter_settings = graph.add_node_of_type(unreal.PCGFilterByTagSettings)
    filter_settings.selected_tags = stage
    spawner, settings = graph.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
    settings.set_mesh_selector_type(unreal.PCGMeshSelectorByAttribute)
    selector = settings.mesh_selector_parameters
    selector.attribute_name = "Mesh"
    selector.use_attribute_material_overrides = True
    selector.material_override_attributes = ["Material"]
    graph.add_edge(graph.get_input_node(), "In", filter_node, "In")
    graph.add_edge(filter_node, "InsideFilter", spawner, "In")
    graph.add_edge(spawner, "Out", graph.get_output_node(), "Out")
    if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
        raise RuntimeError("Failed saving stage " + stage)
    return graph


def build_master(stages):
    graph = graph_asset(GRAPH_ROOT, "PCG_Building_Master")
    if list(graph.get_editor_property("nodes")):
        return graph
    graph.description = unreal.Text("Complete house: structure, facades, openings, roofs, details")
    for stage, stage_graph in stages.items():
        node = subgraph_node(graph, stage_graph)
        node.node_title = stage
        graph.add_edge(graph.get_input_node(), "In", node, "In")
        graph.add_edge(node, "Out", graph.get_output_node(), "Out")
    if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
        raise RuntimeError("Failed saving master")
    return graph


def build_lot(lot, master):
    asset = unreal.load_asset(DATA_ROOT + "/PCGDA_Building_" + lot)
    if not asset:
        raise RuntimeError("Missing data asset for " + lot)
    graph = graph_asset(DATA_ROOT, "PCG_Building_" + lot)
    if list(graph.get_editor_property("nodes")):
        return graph
    loader, settings = graph.add_node_of_type(unreal.PCGLoadDataAssetSettings)
    settings.asset = asset
    node = subgraph_node(graph, master)
    graph.add_edge(loader, "Out", node, "In")
    graph.add_edge(node, "Out", graph.get_output_node(), "Out")
    if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
        raise RuntimeError("Failed saving lot graph " + lot)
    return graph


def main():
    result = {"stages": {}, "lots": {}, "errors": {}}
    stages = {}
    for stage in STAGES:
        try:
            stages[stage] = build_stage(stage)
            result["stages"][stage] = str(stages[stage])
        except Exception:
            result["errors"][stage] = traceback.format_exc()
    if len(stages) == len(STAGES):
        try:
            master = build_master(stages)
            result["master"] = str(master)
            houses = json.loads(HOUSES_INPUT.read_text(encoding="utf-8"))["houses"]
            for house in houses:
                lot = house["building_id"]
                if TEST_IDS is not None and lot not in TEST_IDS:
                    continue
                try:
                    result["lots"][lot] = str(build_lot(lot, master))
                except Exception:
                    result["errors"][lot] = traceback.format_exc()
        except Exception:
            result["errors"]["master"] = traceback.format_exc()
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    unreal.log("M80_PCG_GRAPHS " + str(OUT))


main()
