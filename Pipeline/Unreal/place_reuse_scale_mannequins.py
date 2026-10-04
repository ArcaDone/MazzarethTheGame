"""Place 1.8 m reference mannequins by the four real pilot lot entrances."""
from pathlib import Path
import json
import math

import unreal

ROOT = Path(__file__).resolve().parents[2]
POINTS = json.loads((ROOT / "Research/Mazzarino80/PCG/Buildings_Test18_PCGPoints.json").read_text(encoding="utf-8"))
FOOTPRINTS = json.loads((ROOT / "Research/Mazzarino80/PCG/Buildings_Test18.json").read_text(encoding="utf-8"))
PILOTS = {"1249069204", "1249068307", "1249069200", "1249069228"}
MAPS = ("/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_4Lots_QA",
        "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_18Lots_QA")
mesh = unreal.EditorAssetLibrary.load_asset(
    "/Game/Characters/UE5_Mannequins/Meshes/SKM_Manny_Simple")
if mesh is None:
    raise RuntimeError("Missing Manny scale reference")
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
polygons = [[(point[0], point[1]) for point in building["footprint_world_cm"]]
            for building in FOOTPRINTS["buildings"]]


def inside(x, y, polygon):
    result = False
    for i, (ax, ay) in enumerate(polygon):
        bx, by = polygon[i - 1]
        if (ay > y) != (by > y):
            cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < cross:
                result = not result
    return result


report = {}
for map_path in MAPS:
    world = unreal.EditorLoadingAndSavingUtils.load_map(map_path)
    if not world:
        raise RuntimeError("Could not load " + map_path)
    existing = {actor.get_actor_label(): actor
                for actor in actor_subsystem.get_all_level_actors()}
    records = []
    for house in POINTS["houses"]:
        lot = house["building_id"]
        if lot not in PILOTS:
            continue
        label = "Manichino 1.8m lotto " + lot
        door = next(point for point in house["stage_points"]["Openings"]
                    if point["role"] == "door_leaf")
        yaw = door["rotation_deg"][1]
        angle = math.radians(yaw)
        x, y, _ = door["location_cm"]
        options = []
        for distance in (145, 110, 80):
            for sign in (1, -1):
                px = x + sign * distance * math.sin(angle)
                py = y - sign * distance * math.cos(angle)
                if not any(inside(px, py, polygon) for polygon in polygons):
                    options.append((px, py, sign, distance))
        if not options:
            raise RuntimeError("No exterior scale-reference location by " + lot)
        px, py, sign, distance = options[0]
        position = unreal.Vector(px, py, house["base_z_cm"])
        actor = existing.get(label)
        if actor is None:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.SkeletalMeshActor, position,
                unreal.Rotator(0, yaw + (180 if sign > 0 else 0), 0))
            actor.set_actor_label(label)
            actor.skeletal_mesh_component.set_skeletal_mesh(mesh)
        else:
            actor.set_actor_location(position, False, False)
        records.append({"lot": lot, "location_cm": [position.x, position.y, position.z],
                        "distance_from_door_cm": distance, "side": sign})
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, map_path):
        raise RuntimeError("Could not save " + map_path)
    report[map_path] = records
(ROOT / "Pipeline/Unreal/reuse_scale_mannequins.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8")
print("M80_REUSE_SCALE_MANNY", len(report), "maps")
