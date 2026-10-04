"""Generate 67 full PCG houses sequentially in a ticking graphical editor."""
from pathlib import Path
import json
import time
import unreal

root = Path(unreal.Paths.project_dir())
target = "/Game/Levels/Mazzarino80_PCG_Quartieri_Batch01_FullPCG"
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_name() != target.rsplit("/", 1)[-1]:
    raise RuntimeError("Open FullPCG Batch01 map before generating")
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
catalog = json.loads((root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/full_pcg_points.json").read_text(encoding="utf-8"))
expected = {h["building_id"]: sum(len(x) for x in h["stage_points"].values())
            for h in catalog["houses"]}
lot_district = {lot: d["id"] for d in manifest["districts"][:3]
                for lot in d["lots"] if lot in expected}
actors = {a.get_actor_label().removeprefix("PCG_Building_"): a for a in
          unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
          if a.get_actor_label().startswith("PCG_Building_")}
if set(actors) != set(expected) or len(expected) != 67:
    raise RuntimeError("FullPCG actor inventory mismatch")
queue = sorted(expected, key=lambda lot: (lot_district[lot], lot))
out = root / "Pipeline/Unreal/first_pcg_batch_full_editor_generation.json"
state = {"map": target, "status": "running", "started": time.time(),
         "total_lots": len(queue), "completed_lots": 0, "completed_by_district": {},
         "expected_instances": sum(expected.values()), "actual_instances": 0,
         "current_lot": None, "lots": {}, "error": None, "saved": False}
handle = None
index = 0
started_lot = 0.0
last_check = 0.0

def count(lot):
    return sum(c.get_instance_count() for c in
               actors[lot].get_components_by_class(unreal.InstancedStaticMeshComponent))

def write():
    out.write_text(json.dumps(state, indent=2), encoding="utf-8")

def finish(error=None):
    global handle
    state["error"] = error
    state["status"] = "failed" if error else "generated_needs_gui_save"
    state["elapsed_seconds"] = round(time.time() - state["started"], 2)
    write()
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)

def start_lot():
    global index, started_lot
    if index >= len(queue):
        finish()
        return
    lot = queue[index]
    graph_path = "/Game/Mazzarino80/PCG/DistrictBatch01_Full/PCG_Building_" + lot
    graph = unreal.load_asset(graph_path)
    component = actors[lot].get_component_by_class(unreal.PCGComponent)
    if not graph or not component:
        raise RuntimeError("Missing graph or component " + lot)
    current = component.get_editor_property("graph_instance")
    current_graph = current.get_editor_property("graph") if current else None
    if current_graph != graph:
        component.set_graph(graph)
    state["current_lot"] = lot
    started_lot = time.time()
    if count(lot) != expected[lot]:
        component.generate(True)
    write()

def on_tick(delta_seconds):
    global index, last_check
    now = time.time()
    if now - last_check < 0.7:
        return
    last_check = now
    try:
        lot = queue[index]
        current = count(lot)
        if current == expected[lot]:
            state["lots"][lot] = {"district": lot_district[lot],
                                  "expected": expected[lot], "actual": current,
                                  "elapsed_seconds": round(now - started_lot, 2)}
            state["completed_lots"] += 1
            state["completed_by_district"][lot_district[lot]] = \
                state["completed_by_district"].get(lot_district[lot], 0) + 1
            state["actual_instances"] += current
            index += 1
            start_lot()
        elif now - started_lot > 180:
            finish("Generation timed out for " + lot + ": " + str(current) +
                   "/" + str(expected[lot]))
        else:
            write()
    except Exception as exc:
        finish(str(exc))

start_lot()
handle = unreal.register_slate_post_tick_callback(on_tick)
print("M80_FIRST_BATCH_FULL_EDITOR_STARTED", len(queue), state["expected_instances"])
