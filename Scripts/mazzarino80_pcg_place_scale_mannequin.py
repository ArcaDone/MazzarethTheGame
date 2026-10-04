"""Place a true-height UE mannequin in the PCG validation map only."""
import json
import math
import traceback
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext"
LOT = "1249069202"
LABEL = "Reference_Mannequin_180cm_" + LOT
OUT = ROOT / "Saved/Mazzarino80/PCG/scale_mannequin.json"


def main():
    report = {"map": MAP, "lot": LOT, "label": LABEL}
    try:
        if not unreal.EditorLevelLibrary.load_level(MAP):
            raise RuntimeError("Could not load validation map")
        mesh = unreal.load_asset("/Game/Characters/UE5_Mannequins/Meshes/SKM_Manny_Simple")
        if not mesh:
            raise RuntimeError("Manny reference mesh unavailable")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        source = next(a for a in actors if isinstance(a, unreal.MazzarinoHistoricBuilding)
                      and a.get_editor_property("lot_id") == LOT)
        spline = source.get_editor_property("footprint")
        front = source.get_editor_property("front_edge")
        count = spline.get_number_of_spline_points()
        a = spline.get_location_at_spline_point(front, unreal.SplineCoordinateSpace.WORLD)
        b = spline.get_location_at_spline_point((front + 1) % count, unreal.SplineCoordinateSpace.WORLD)
        poly = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
                for i in range(count)]
        signed = sum(p.x * poly[(i + 1) % count].y - poly[(i + 1) % count].x * p.y
                     for i, p in enumerate(poly))
        dx, dy = b.x - a.x, b.y - a.y
        length = math.hypot(dx, dy)
        if length < 200:
            raise RuntimeError("Front edge too short for scale comparison")
        ox, oy = ((dy / length, -dx / length) if signed > 0
                  else (-dy / length, dx / length))
        x = (a.x + b.x) / 2 + ox * 150
        y = (a.y + b.y) / 2 + oy * 150
        road = source.get_editor_property("entrance_road")
        road_z = road.get_editor_property("spline").find_location_closest_to_world_location(
            unreal.Vector(x, y, a.z), unreal.SplineCoordinateSpace.WORLD).z
        actor = next((item for item in actors if item.get_actor_label() == LABEL), None)
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        if actor is None:
            actor = subsystem.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(x, y, road_z))
            actor.set_actor_label(LABEL)
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        component.set_editor_property("skeletal_mesh_asset", mesh)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        actor.set_actor_scale3d(unreal.Vector(1, 1, 1))
        actor.set_actor_location(unreal.Vector(x, y, road_z), False, False)
        ruler_label = "Reference_ExactHeight_180cm_" + LOT
        ruler = next((item for item in actors if item.get_actor_label() == ruler_label), None)
        if ruler is None:
            ruler = subsystem.spawn_actor_from_class(unreal.StaticMeshActor,
                unreal.Vector(x + 100, y, road_z + 90))
            ruler.set_actor_label(ruler_label)
        cube = unreal.load_asset("/Engine/BasicShapes/Cube")
        ruler.get_component_by_class(unreal.StaticMeshComponent).set_editor_property("static_mesh", cube)
        ruler.get_component_by_class(unreal.StaticMeshComponent).set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        ruler.set_actor_scale3d(unreal.Vector(.08, .08, 1.8))
        ruler.set_actor_location(unreal.Vector(x + 100, y, road_z + 90), False, False)
        report.update({"mesh": mesh.get_path_name(), "mannequin_scale": 1,
                       "exact_ruler_height_cm": 180,
                       "location_cm": [x, y, road_z],
                       "saved": unreal.EditorLevelLibrary.save_current_level()})
    except Exception:
        report["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("M80_SCALE_MANNEQUIN " + str(OUT))


main()
