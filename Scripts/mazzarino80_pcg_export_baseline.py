"""Export the current 18-house sample without changing editor actors."""
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir())
OUTPUT = ROOT / "Saved/Mazzarino80/PCG/baseline_18.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == "Mazzarino80_CaseStoriche_Campione", world.get_name()


def vector(value):
    return [value.x, value.y, value.z]


def encode(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (list, tuple)):
        return [encode(item) for item in value]
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return vector(value)
    return str(value)


fields = [
    "family", "seed", "previous_family", "volume_variation", "facade_irregularity",
    "balcony_density", "decay", "floors_override", "floor_height", "wall_thickness",
    "entrance_lift", "balcony_depth", "roof_rise", "parapet_height",
    "courtyard_width", "courtyard_depth", "upper_setback", "step_riser", "step_tread",
    "drain_width", "sill_projection", "sill_thickness", "downpipe_diameter",
    "cable_diameter", "cable_sag", "show_roof_tiles", "tile_row_width",
    "tile_row_length", "tile_irregularity", "preserve_service_splines", "front_edge",
    "party_wall_edges", "follow_supports", "entrance_road", "ground_actor",
    "show_balconies", "show_roofs", "show_openings", "show_numbers", "show_shutters",
    "show_cornices", "show_aging", "show_life", "show_steps", "show_street_details",
    "plaster_material", "stone_material", "roof_material", "terrace_material",
    "iron_material", "wood_material", "glass_material", "damp_material",
    "repair_material", "cloth_material", "exposed_stone_material", "drain_material",
    "tile_material", "roof_tile_mesh", "cable_mesh", "balcony_module_mesh",
    "balcony_module_width", "use_balcony_modules", "door_mesh", "pot_mesh",
    "generated_volumes", "generated_openings", "generated_balconies", "geometry_error",
]

houses = []
for actor in editor.get_all_level_actors():
    if not isinstance(actor, unreal.MazzarinoHistoricBuilding):
        continue
    footprint = actor.get_editor_property("footprint")
    points = [
        vector(footprint.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD))
        for i in range(footprint.get_number_of_spline_points())
    ]
    values = {}
    for field in fields:
        try:
            values[field] = encode(actor.get_editor_property(field))
        except Exception as exc:
            values[field] = {"export_error": str(exc)}
    services = []
    for component in actor.get_components_by_class(unreal.SplineComponent):
        if component == footprint:
            continue
        services.append({
            "name": component.get_name(),
            "points_world_cm": [
                vector(component.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD))
                for i in range(component.get_number_of_spline_points())
            ],
        })
    houses.append({
        "id": actor.get_editor_property("lot_id"),
        "label": actor.get_actor_label(),
        "location_cm": vector(actor.get_actor_location()),
        "rotation": encode(actor.get_actor_rotation()),
        "footprint_world_cm": points,
        "properties": values,
        "service_splines": services,
    })

houses.sort(key=lambda row: row["id"])
assert len(houses) == 18, len(houses)
assert len({row["id"] for row in houses}) == 18
OUTPUT.write_text(json.dumps({"map": world.get_name(), "houses": houses}, indent=2), encoding="utf-8")
unreal.log("M80_PCG_BASELINE_EXPORTED " + str(OUTPUT))
