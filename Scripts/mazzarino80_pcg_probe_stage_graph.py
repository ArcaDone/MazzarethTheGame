"""Inspect stage-filter and subgraph pins for deterministic graph generation."""
import json
import traceback
from pathlib import Path
import unreal

log = {}
try:
    graph = unreal.new_object(unreal.PCGGraph)
    label = lambda pin: str(pin.get_editor_property("properties").get_editor_property("label"))
    for kind, cls in (("filter", unreal.PCGFilterByTagSettings), ("subgraph", unreal.PCGSubgraphSettings)):
        node, settings = graph.add_node_of_type(cls)
        log[kind] = {
            "fields": [x for x in dir(settings) if not x.startswith("_") and x not in dir(unreal.Object)],
            "input": [label(x) for x in node.get_editor_property("input_pins")],
            "output": [label(x) for x in node.get_editor_property("output_pins")],
        }
        if kind == "subgraph":
            instance = settings.get_editor_property("subgraph_instance")
            log[kind]["instance"] = str(instance)
            log[kind]["instance_fields"] = [x for x in dir(instance) if not x.startswith("_") and x not in dir(unreal.Object)]
except Exception:
    log["error"] = traceback.format_exc()
out = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/pcg_stage_graph_api.json"
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_STAGE_GRAPH_API " + str(out))
