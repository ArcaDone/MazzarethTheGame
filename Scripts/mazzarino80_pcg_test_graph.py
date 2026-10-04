"""Build the first real PCG graph: saved points -> instanced structural mesh."""
import json
import traceback
from pathlib import Path

import unreal

log = {}
try:
    base = "/Game/Mazzarino80/PCG/Validation"
    asset = unreal.load_asset(base + "/PCGDA_TestStructure")
    if not asset:
        raise RuntimeError("Missing PCG point data asset")
    points = asset.get_editor_property("data").tagged_data[0].data
    metadata = points.mutable_metadata()
    point = points.get_point(0)
    mesh_path = "/Engine/BasicShapes/Cube.Cube"
    point.set_soft_object_path_attribute(metadata, "Mesh", unreal.SoftObjectPath(mesh_path))
    points.set_points([point])
    log["mesh_attribute"] = str(points.get_point(0).get_soft_object_path_attribute(metadata, "Mesh"))
    log["save_data"] = unreal.EditorAssetLibrary.save_loaded_asset(asset)

    factory = unreal.PCGGraphFactory()
    graph = unreal.AssetToolsHelpers.get_asset_tools().create_asset("PCG_TestStructure_V2", base, unreal.PCGGraph, factory)
    if not graph:
        graph = unreal.load_asset(base + "/PCG_TestStructure_V2")
    if not graph:
        raise RuntimeError("Could not create PCG graph")
    loader, loader_settings = graph.add_node_of_type(unreal.PCGLoadDataAssetSettings)
    loader_settings.asset = asset
    spawner, spawner_settings = graph.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
    spawner_settings.set_mesh_selector_type(unreal.PCGMeshSelectorByAttribute)
    selector = spawner_settings.mesh_selector_parameters
    selector.attribute_name = "Mesh"
    log["selector"] = str(selector)
    label = lambda pin: str(pin.get_editor_property("properties").get_editor_property("label"))
    log["input_pins"] = [label(x) for x in graph.get_input_node().get_editor_property("output_pins")]
    log["loader_in"] = [label(x) for x in loader.get_editor_property("input_pins")]
    log["loader_out"] = [label(x) for x in loader.get_editor_property("output_pins")]
    log["spawner_in"] = [label(x) for x in spawner.get_editor_property("input_pins")]
    log["spawner_out"] = [label(x) for x in spawner.get_editor_property("output_pins")]
    log["output_in"] = [label(x) for x in graph.get_output_node().get_editor_property("input_pins")]
    graph.add_edge(loader, log["loader_out"][0], spawner, log["spawner_in"][0])
    graph.add_edge(spawner, log["spawner_out"][0], graph.get_output_node(), log["output_in"][0])
    log["save_graph"] = unreal.EditorAssetLibrary.save_loaded_asset(graph)
    log["graph"] = str(graph)
except Exception:
    log["error"] = traceback.format_exc()

out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_graph_test.json"
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_GRAPH_TEST " + str(out))
