"""Generate the first catalog house in the isolated PCG validation level."""
import json
import math
import traceback
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
out = root / "Saved/Mazzarino80/PCG/pcg_spawn_test_house.json"
log = {}
try:
    lot = "1249069247"
    catalog = json.loads((root / "Research/Mazzarino80/PCG/Buildings_Test18.json").read_text(encoding="utf-8"))
    record = next(b for b in catalog["buildings"] if b["building_id"] == lot)
    pts = record["footprint_world_cm"]
    xmin, xmax = min(p[0] for p in pts), max(p[0] for p in pts)
    ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts)
    z = min(p[2] for p in pts) + record["primary_floors"] * record["floor_height_cm"] / 2
    center = unreal.Vector((xmin+xmax)/2, (ymin+ymax)/2, z)
    graph = unreal.load_asset("/Game/Mazzarino80/PCG/Buildings/PCG_Building_" + lot)
    if not graph:
        raise RuntimeError("Missing lot graph")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    label = "BP_ProceduralBuilding_" + lot
    volume = next((a for a in actors if a.get_actor_label() == label), None)
    if volume is None:
        volume = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.PCGVolume, center)
        volume.set_actor_label(label)
    volume.set_actor_location(center, False, False)
    volume.set_actor_scale3d(unreal.Vector(max(2, (xmax-xmin)/1000+1), max(2, (ymax-ymin)/1000+1), 2))
    pcg = volume.get_component_by_class(unreal.PCGComponent)
    pcg.cleanup(True)
    log["cache_flushed"] = unreal.PCGBlueprintHelpers.flush_pcg_cache()
    pcg.set_graph(graph)
    pcg.generate(True)
    log["actor"] = str(volume)
    log["graph"] = str(graph)
    log["center"] = [center.x, center.y, center.z]
    log["saved"] = unreal.EditorLevelLibrary.save_current_level()
except Exception:
    log["error"] = traceback.format_exc()
out.write_text(json.dumps(log, indent=2), encoding="utf-8")
unreal.log("M80_PCG_SPAWN_TEST_HOUSE " + str(out))
