"""Add detail-only PCG to 67 lots in an independent first-batch map."""
from hashlib import sha256
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
plan = {row["id"]: row for row in json.loads(
    (root / "Research/Mazzarino80/building_footprint_plan.json").read_text(encoding="utf-8"))}
source = manifest["preview_map"]
target = "/Game/Levels/Mazzarino80_PCG_Quartieri_Batch01"
out = root / "Pipeline/Unreal/first_pcg_batch_map_result.json"
protected = {
    "panorama": root / "Content/Levels/Mazzarino80_Panoramica.umap",
    "sample": root / "Content/Levels/Mazzarino80_CaseStoriche_Campione.umap",
    "preview": root / "Content/Levels/Mazzarino80_PCG_Quartieri_Preview.umap",
}
before = {name: sha256(path.read_bytes()).hexdigest() for name, path in protected.items()}
if unreal.EditorAssetLibrary.does_asset_exist(target):
    raise RuntimeError("Batch01 map exists; refusing to overwrite reviewed work")
if not unreal.EditorAssetLibrary.duplicate_asset(source, target):
    raise RuntimeError("Could not duplicate district preview")
world = unreal.EditorLoadingAndSavingUtils.load_map(target)
if not world or world.get_name() != "Mazzarino80_PCG_Quartieri_Batch01":
    raise RuntimeError("Wrong map loaded after duplication")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = actors.get_all_level_actors()
sources = {str(a.get_editor_property("building_id")): a for a in all_actors
           if isinstance(a, unreal.MazzarinoBuilding)}
expected = set().union(*(set(d["lots"]) - set(d["approved_pcg_lots"])
                         for d in manifest["districts"][:3]))
if len(expected) != 67 or not expected <= set(sources):
    raise RuntimeError("Unexpected first-batch footprint inventory")
report = {"map": target, "source": source, "lots": {}, "errors": [],
          "detailed_facades_enabled": [], "source_hashes_before": before}
for district in manifest["districts"][:3]:
    for lot in district["lots"]:
        if lot not in expected:
            continue
        original = sources[lot]
        graph_path = "/Game/Mazzarino80/PCG/DistrictBatch01_Details/PCG_Detail_" + lot
        graph = unreal.load_asset(graph_path)
        if not isinstance(graph, unreal.PCGGraph):
            report["errors"].append("Missing detail graph " + lot)
            continue
        spline = original.get_editor_property("footprint")
        coords = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
                  for i in range(spline.get_number_of_spline_points())]
        if len(coords) < 3:
            report["errors"].append("Invalid spline " + lot)
            continue
        minx, maxx = min(v.x for v in coords), max(v.x for v in coords)
        miny, maxy = min(v.y for v in coords), max(v.y for v in coords)
        base = min(v.z for v in coords)
        height = original.get_editor_property("floor_count") * \
                 original.get_editor_property("floor_height_meters") * 100
        center = unreal.Vector((minx + maxx) * 0.5, (miny + maxy) * 0.5,
                               base + height * 0.5)
        volume = actors.spawn_actor_from_class(unreal.PCGVolume, center, unreal.Rotator())
        if not volume:
            report["errors"].append("Could not spawn detail volume " + lot)
            continue
        volume.set_actor_label("PCG_Detail_" + lot)
        volume.set_folder_path("Mazzarino80/Quartieri_PCG/" + district["id"] + "/Dettagli_PCG")
        volume.set_actor_scale3d(unreal.Vector(max(2, (maxx-minx)/1000+1),
                                               max(2, (maxy-miny)/1000+1),
                                               max(2, height/1000+1)))
        component = volume.get_component_by_class(unreal.PCGComponent)
        if not component:
            report["errors"].append("PCG component absent " + lot)
            continue
        component.set_editor_property("is_component_partitioned", False)
        component.set_graph(graph)
        # Existing wall and roof are retained. For plain provisional volumes,
        # use the same MazzarinoBuilding facade generator already on 44 peers.
        enabled = False
        if not original.get_editor_property("detailed_facade"):
            original.modify()
            library = "/Game/Mazzarino80/Library/Comune"
            assignments = {
                "window_mesh": library + "/SoulCity/Environment/Meshes/Building_Slum/SM_Slums_Window_01a",
                "door_mesh": library + "/OldWestAssets/OldWestVol6/VOL6/Meshes/SM_Door_06c",
                "window_backing_material": "/Game/Mazzarino80/Buildings/Materials/M80_Vetri_Scuri",
                "trim_material": "/Game/Mazzarino80/Buildings/Materials/M80_Cornici_Pietra",
                "metal_material": "/Game/Mazzarino80/Buildings/Materials/M80_Ferro_Brunito",
                "shutter_material": "/Game/Mazzarino80/Buildings/Materials/M80_Persiane_" + str(int(lot) % 3),
            }
            for prop, path in assignments.items():
                asset = unreal.load_asset(path)
                if not asset:
                    raise RuntimeError("Missing existing facade asset: " + path)
                original.set_editor_property(prop, asset)
            original.set_editor_property("front_edge_index", int(plan[lot]["front_edge"]))
            original.set_editor_property("detailed_facade", True)
            original.rebuild_building()
            enabled = True
            report["detailed_facades_enabled"].append(lot)
        report["lots"][lot] = {
            "district": district["id"], "graph": graph_path,
            "volume": volume.get_actor_label(), "facade_enabled": enabled,
            "doors": original.get_editor_property("doors").get_instance_count(),
            "windows": original.get_editor_property("windows").get_instance_count(),
            "geometry_error": str(original.get_editor_property("geometry_error")),
        }
if len(report["lots"]) != 67 or len(report["detailed_facades_enabled"]) != 23:
    report["errors"].append("Actor or facade count mismatch")
for lot, item in report["lots"].items():
    if item["geometry_error"]:
        report["errors"].append("Geometry error " + lot + ": " + item["geometry_error"])
    if item["facade_enabled"] and item["doors"] == 0:
        report["errors"].append("No doorway after enabling facade " + lot)
if report["errors"]:
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    raise RuntimeError("First batch map invalid: " + repr(report["errors"][:3]))
if not unreal.EditorLoadingAndSavingUtils.save_map(world, target):
    raise RuntimeError("Could not save first batch map")
after = {name: sha256(path.read_bytes()).hexdigest() for name, path in protected.items()}
report["source_hashes_after"] = after
report["source_maps_unchanged"] = before == after
report["saved"] = True
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
if before != after:
    raise RuntimeError("Protected source map changed")
print("M80_FIRST_PCG_BATCH_MAP", len(report["lots"]), len(report["detailed_facades_enabled"]))
