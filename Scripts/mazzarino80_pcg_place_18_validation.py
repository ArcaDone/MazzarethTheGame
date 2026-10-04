"""Place every catalog house in the isolated validation map using its own PCG graph."""
import json
import traceback
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
catalog = json.loads((root / "Research/Mazzarino80/PCG/Buildings_Test18.json").read_text(encoding="utf-8"))
result = {"houses": {}, "errors": {}, "cache_flushed": False}
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.EditorLevelLibrary.get_editor_world()
result["world"] = str(world)
if "L_PCGBuildings_Validation" not in str(world):
    raise RuntimeError("Open L_PCGBuildings_Validation before placing catalog")
existing = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
result["cache_flushed"] = unreal.PCGBlueprintHelpers.flush_pcg_cache()
for record in catalog["buildings"]:
    lot = record["building_id"]
    try:
        graph = unreal.load_asset("/Game/Mazzarino80/PCG/Buildings/PCG_Building_" + lot)
        if not graph:
            raise RuntimeError("Missing graph")
        pts = record["footprint_world_cm"]
        xmin, xmax = min(p[0] for p in pts), max(p[0] for p in pts)
        ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts)
        z = min(p[2] for p in pts) + record["primary_floors"] * record["floor_height_cm"] / 2
        center = unreal.Vector((xmin+xmax)/2, (ymin+ymax)/2, z)
        label = "BP_ProceduralBuilding_" + lot
        volume = existing.get(label)
        if volume is None:
            volume = actors.spawn_actor_from_class(unreal.PCGVolume, center)
            volume.set_actor_label(label)
        volume.set_actor_location(center, False, False)
        volume.set_actor_scale3d(unreal.Vector(max(2, (xmax-xmin)/1000+1), max(2, (ymax-ymin)/1000+1), 2))
        pcg = volume.get_component_by_class(unreal.PCGComponent)
        pcg.cleanup(True)
        pcg.set_graph(graph)
        pcg.generate(True)
        result["houses"][lot] = {"actor": str(volume), "center": [center.x, center.y, center.z]}
    except Exception:
        result["errors"][lot] = traceback.format_exc()
result["saved"] = unreal.EditorLevelLibrary.save_current_level()
(root / "Saved/Mazzarino80/PCG/place_18_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_PCG_PLACE_18 " + str(len(result["houses"])) + " houses")
