"""Read-only audit of the full-town context and its first three PCG sectors."""
from pathlib import Path
from hashlib import sha256
import json
import unreal

root = Path(unreal.Paths.project_dir())
manifest = json.loads((root / "Pipeline/Unreal/pcg_district_manifest.json").read_text(encoding="utf-8"))
sample = json.loads((root / "Pipeline/Unreal/sample_pcg_actor_inventory.json").read_text(encoding="utf-8"))
level = manifest["preview_map"]
world = unreal.EditorLoadingAndSavingUtils.load_map(level)
if not world or world.get_name() != level.rsplit("/", 1)[-1]:
    raise RuntimeError("Cannot load district preview")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
buildings = {str(a.get_editor_property("building_id")): a for a in actors
             if isinstance(a, unreal.MazzarinoBuilding)}
pcg = {a.get_actor_label().rsplit("_", 1)[-1]: a for a in actors
       if a.get_actor_label().startswith("BP_ProceduralBuilding_")}
errors = []
rows = {}
grouped = 0
if len(buildings) != manifest["footprint_count"] or set(pcg) != set(sample):
    errors.append("Actor counts or lot IDs differ from the sources")
for sector in manifest["districts"]:
    base = "Mazzarino80/Quartieri_PCG/" + sector["id"]
    for lot in sector["lots"]:
        actor = buildings.get(lot)
        if not actor or not str(actor.get_folder_path()).startswith(base):
            errors.append("Missing sector assignment: " + lot)
        else:
            grouped += 1
for lot, source in sample.items():
    actor = pcg.get(lot)
    old = buildings.get(lot)
    if not actor or not old:
        continue
    comp = actor.get_component_by_class(unreal.PCGComponent)
    gi = comp.get_editor_property("graph_instance") if comp else None
    graph = gi.get_editor_property("graph") if gi else None
    count = sum(c.get_instance_count() for c in
                actor.get_components_by_class(unreal.InstancedStaticMeshComponent))
    expected_graph = ("/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1/"
                      "PCG_Building_" + lot + ".PCG_Building_" + lot)
    rows[lot] = {"instances": count, "expected_instances": source["instances"],
                 "graph": graph.get_path_name() if graph else None,
                 "expected_graph": expected_graph,
                 "generated": bool(comp.get_editor_property("generated")) if comp else False,
                 "original_hidden_in_game": bool(old.get_editor_property("hidden")),
                 "original_visible_components": sum(
                     bool(c.get_editor_property("visible")) for c in
                     old.get_components_by_class(unreal.PrimitiveComponent))}
    if rows[lot]["graph"] != expected_graph or not rows[lot]["original_hidden_in_game"]:
        errors.append("Graph binding or original visibility invalid: " + lot)
    if count != source["instances"]:
        errors.append("Generated instance count differs from approved sample: " + lot)
    if rows[lot]["original_visible_components"]:
        errors.append("Original building still has visible components: " + lot)
report = {"map": level, "all_footprints": len(buildings), "pcg_houses": len(pcg),
          "districts": len(manifest["districts"]), "footprints_grouped": grouped,
          "expected_pcg_instances": sum(x["instances"] for x in sample.values()),
          "actual_pcg_instances": sum(x["instances"] for x in rows.values()),
          "houses": rows,
          "protected_source_hashes": {
              name: sha256((root / path).read_bytes()).hexdigest()
              for name, path in {
                  "sample": "Content/Levels/Mazzarino80_CaseStoriche_Campione.umap",
                  "panorama": "Content/Levels/Mazzarino80_Panoramica.umap"}.items()},
          "errors": errors}
(root / "Pipeline/Unreal/pcg_district_preview_verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8")
print("M80_PCG_DISTRICT_VERIFY", len(buildings), len(pcg),
      report["actual_pcg_instances"], len(errors))
