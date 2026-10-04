"""Read-only measurements for the 67 non-pilot buildings in the first batch."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
world = unreal.EditorLoadingAndSavingUtils.load_map(manifest["preview_map"])
if not world or world.get_name() != "Mazzarino80_PCG_Quartieri_Preview":
    raise RuntimeError("Expected the independent preview map")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
sources = {str(a.get_editor_property("building_id")): a for a in actors
           if isinstance(a, unreal.MazzarinoBuilding)}
result = {"map": manifest["preview_map"], "lots": {}, "errors": []}
for district in manifest["districts"][:3]:
    for lot in district["lots"]:
        if lot in district["approved_pcg_lots"]:
            continue
        actor = sources.get(lot)
        if not actor:
            result["errors"].append("Missing actor " + lot)
            continue
        spline = actor.get_editor_property("footprint")
        points = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
                  for i in range(spline.get_number_of_spline_points())]
        p = actor.get_actor_location()
        props = {}
        for key in ("floor_count", "floor_height_meters", "roof_rise_meters", "roof_terrace",
                    "front_edge_index", "detailed_facade", "detail_side_facades", "balcony_style",
                    "balcony_depth_meters", "facade_section_width_meters", "height_variation_meters",
                    "composition_seed", "window_spacing_meters", "window_width_meters",
                    "window_height_meters", "reconstruction_status", "geometry_error"):
            try:
                value = actor.get_editor_property(key)
                props[key] = value if isinstance(value, (str, bool, int, float)) else str(value)
            except Exception as exc:
                props[key] = "UNAVAILABLE: " + str(exc)
        for key in ("facade_material", "roof_material", "trim_material", "metal_material",
                    "shutter_material", "window_backing_material", "window_mesh", "door_mesh"):
            try:
                value = actor.get_editor_property(key)
                props[key] = value.get_path_name() if value else None
            except Exception as exc:
                props[key] = "UNAVAILABLE: " + str(exc)
        counts = {}
        for key in ("windows", "doors", "window_backings", "masonry_details", "metal_details", "shutters"):
            component = actor.get_editor_property(key)
            counts[key] = component.get_instance_count() if component else -1
        result["lots"][lot] = {
            "district": district["id"], "source_folder": district["source_folder"],
            "location_cm": [p.x, p.y, p.z],
            "footprint_world_cm": [[v.x, v.y, v.z] for v in points],
            "properties": props, "existing_instance_counts": counts,
        }
result["count"] = len(result["lots"])
path = root / "Pipeline/Unreal/first_pcg_batch_source_audit.json"
path.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_FIRST_PCG_BATCH_SOURCE_AUDIT", result["count"], len(result["errors"]))
if result["count"] != 67 or result["errors"]:
    raise RuntimeError("Unexpected first-batch source inventory")
