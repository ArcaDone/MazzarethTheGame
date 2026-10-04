"""Generate first three PCG sectors in a ticking Unreal graphical editor.

Run via Tools > Execute Python Script with the preview level already open.
The commandlet cannot finish PCG's asynchronous generation.
"""
from pathlib import Path
import json
import time
import unreal

ROOT = Path(unreal.Paths.project_dir())
MANIFEST = json.loads((ROOT / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
SOURCE = json.loads((ROOT / "Pipeline/Unreal/sample_pcg_actor_inventory.json").read_text(encoding="utf-8"))
OUT = ROOT / "Pipeline/Unreal/pcg_district_editor_generation.json"
APPROVED_GRAPH_ROOT = "/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1"
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_name() != "Mazzarino80_PCG_Quartieri_Preview":
    raise RuntimeError("Open the independent PCG district preview before running this script")
actors = {a.get_actor_label().rsplit("_", 1)[-1]: a for a in
          unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
          if a.get_actor_label().startswith("BP_ProceduralBuilding_")}
if set(actors) != set(SOURCE):
    raise RuntimeError("Preview actor IDs do not match the 18 approved lots")
state = {"map": MANIFEST["preview_map"], "phase": 0, "started": time.time(),
         "phase_started": time.time(), "status": "running", "sectors": [],
         "error": None, "saved": False}
handle = None
last_check = 0.0

def count(lot):
    return sum(c.get_instance_count() for c in
               actors[lot].get_components_by_class(unreal.InstancedStaticMeshComponent))

def write():
    OUT.write_text(json.dumps(state, indent=2), encoding="utf-8")

def finish(error=None):
    global handle
    state["error"] = error
    state["status"] = "failed" if error else "complete"
    state["elapsed_seconds"] = round(time.time() - state["started"], 2)
    write()
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)

def start_sector(index):
    sector = MANIFEST["districts"][index]
    lots = sector["approved_pcg_lots"]
    state["phase"] = index + 1
    state["phase_started"] = time.time()
    state["sectors"].append({"id": sector["id"], "lots": lots,
                             "expected_instances": sum(SOURCE[x]["instances"] for x in lots),
                             "actual_instances": 0, "status": "generating"})
    for lot in lots:
        component = actors[lot].get_component_by_class(unreal.PCGComponent)
        if not component:
            raise RuntimeError("PCG component missing on " + lot)
        graph = unreal.load_asset(APPROVED_GRAPH_ROOT + "/PCG_Building_" + lot)
        if not graph:
            raise RuntimeError("Approved detail graph missing for " + lot)
        graph_instance = component.get_editor_property("graph_instance")
        current = graph_instance.get_editor_property("graph") if graph_instance else None
        if current != graph or count(lot) != SOURCE[lot]["instances"]:
            component.set_graph(graph)
            component.generate(True)
    write()

def on_tick(delta_seconds):
    global last_check
    now = time.time()
    if now - last_check < 0.7:
        return
    last_check = now
    try:
        sector = MANIFEST["districts"][state["phase"] - 1]
        lots = sector["approved_pcg_lots"]
        row = state["sectors"][-1]
        row["actual_instances"] = sum(count(x) for x in lots)
        complete = all(count(x) == SOURCE[x]["instances"] for x in lots)
        if complete:
            row["status"] = "complete"
            row["elapsed_seconds"] = round(now - state["phase_started"], 2)
            write()
            if state["phase"] < 3:
                start_sector(state["phase"])
            else:
                finish()
        elif now - state["phase_started"] > 300:
            finish("PCG generation timed out in " + sector["id"])
        else:
            write()
    except Exception as exc:
        finish(str(exc))

start_sector(0)
handle = unreal.register_slate_post_tick_callback(on_tick)
print("M80_PCG_DISTRICT_EDITOR_STARTED", MANIFEST["first_batch"])
