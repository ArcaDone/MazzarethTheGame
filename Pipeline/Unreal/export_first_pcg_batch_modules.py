"""Export all existing facade modules from the isolated Batch01 map.

This reads the 67 detailed MazzarinoBuilding actors; no source map is edited.
"""
from collections import Counter
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
target = "/Game/Levels/Mazzarino80_PCG_Quartieri_Batch01"
world = unreal.EditorLoadingAndSavingUtils.load_map(target)
if not world or world.get_name() != "Mazzarino80_PCG_Quartieri_Batch01":
    raise RuntimeError("Expected isolated Batch01 map")
expected = set().union(*(set(d["lots"]) - set(d["approved_pcg_lots"])
                         for d in manifest["districts"][:3]))
sources = {str(a.get_editor_property("building_id")): a for a in
           unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if isinstance(a, unreal.MazzarinoBuilding)}
def vec(v):
    return [round(v.x, 6), round(v.y, 6), round(v.z, 6)]
def quat(q):
    return [round(q.x, 8), round(q.y, 8), round(q.z, 8), round(q.w, 8)]
def path(asset):
    return asset.get_path_name() if asset else None
result = {"map": target, "houses": {}, "counts": {}, "errors": []}
totals = Counter()
mapping = {
    "Finestre": "Openings", "Porte": "Openings", "Vetri": "Openings",
    "Persiane": "Openings", "CorniciBalconiTerrazze": "Facades",
    "Ringhiere": "Details",
}
for lot in sorted(expected):
    actor = sources.get(lot)
    if not actor:
        result["errors"].append("Missing " + lot)
        continue
    points = []
    materials = {}
    for attr, stage in (("windows", "Openings"), ("doors", "Openings"),
                        ("window_backings", "Openings"), ("shutters", "Openings"),
                        ("masonry_details", "Facades"), ("metal_details", "Details")):
        component = actor.get_editor_property(attr)
        mesh = path(component.get_editor_property("static_mesh"))
        material = path(component.get_material(0))
        count = component.get_instance_count()
        materials[attr] = {"mesh": mesh, "material": material, "count": count}
        if count and (not mesh or not material):
            result["errors"].append("Missing module mesh/material " + lot + "/" + attr)
            continue
        totals[attr] += count
        for index in range(count):
            tr = component.get_instance_transform(index, world_space=True)
            points.append({"role": attr, "stage": stage,
                           "location_cm": vec(tr.translation), "rotation_quat": quat(tr.rotation),
                           "scale": vec(tr.scale3d), "mesh": mesh, "material": material,
                           "seed": (int(lot) % 1000000) * 10000 + len(points)})
    surface = actor.get_editor_property("building_surface")
    surface_materials = [path(surface.get_material(i)) for i in range(3)]
    spline = actor.get_editor_property("footprint")
    poly = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
            for i in range(spline.get_number_of_spline_points())]
    result["houses"][lot] = {
        "district": next(d["id"] for d in manifest["districts"][:3] if lot in d["lots"]),
        "location_cm": vec(actor.get_actor_location()),
        "footprint_world_cm": [vec(p) for p in poly],
        "floor_count": int(actor.get_editor_property("floor_count")),
        "floor_height_cm": float(actor.get_editor_property("floor_height_meters")) * 100,
        "roof_rise_cm": float(actor.get_editor_property("roof_rise_meters")) * 100,
        "roof_ridge_angle_degrees": float(actor.get_editor_property("roof_ridge_angle_degrees")),
        "roof_terrace": bool(actor.get_editor_property("roof_terrace")),
        "height_variation_cm": float(actor.get_editor_property("height_variation_meters")) * 100,
        "facade_section_width_cm": float(actor.get_editor_property("facade_section_width_meters")) * 100,
        "composition_seed": int(actor.get_editor_property("composition_seed")),
        "front_edge": int(actor.get_editor_property("front_edge_index")),
        "texture_meters": float(actor.get_editor_property("texture_meters")),
        "surface_materials": surface_materials,
        "modules": materials, "module_points": points,
    }
result["counts"] = dict(totals)
result["house_count"] = len(result["houses"])
result["instance_count"] = sum(totals.values())
dest = root / "Pipeline/Unreal/first_pcg_batch_module_export.json"
dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_FIRST_PCG_BATCH_MODULE_EXPORT", result["house_count"], result["instance_count"], len(result["errors"]))
if len(result["houses"]) != 67 or result["errors"]:
    raise RuntimeError("Module export incomplete")
