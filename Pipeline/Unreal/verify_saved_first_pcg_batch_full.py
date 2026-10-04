"""Reload the saved Batch01 FullPCG map and verify its committed editor state."""
from hashlib import sha256
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
level = "/Game/Levels/Mazzarino80_PCG_Quartieri_Batch01_FullPCG"
protected = {
    name: root / ("Content/Levels/" + name + ".umap")
    for name in ("Mazzarino80_Panoramica", "Mazzarino80_CaseStoriche_Campione",
                 "Mazzarino80_PCG_Quartieri_Preview", "Mazzarino80_PCG_Quartieri_Batch01")
}
before = {name: sha256(path.read_bytes()).hexdigest() for name, path in protected.items()}
world = unreal.EditorLoadingAndSavingUtils.load_map(level)
if not world or world.get_name() != level.rsplit("/", 1)[-1]:
    raise RuntimeError("Could not reload saved FullPCG map")

exec(compile((root / "Pipeline/Unreal/audit_first_pcg_batch_full_in_editor.py").read_text(encoding="utf-8"),
             "audit_first_pcg_batch_full_in_editor.py", "exec"))
audit = json.loads((root / "Pipeline/Unreal/first_pcg_batch_full_editor_audit.json").read_text(encoding="utf-8"))
sample = json.loads((root / "Pipeline/Unreal/sample_pcg_actor_inventory.json").read_text(encoding="utf-8"))
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
approved = {a.get_actor_label().rsplit("_", 1)[-1]: a for a in actors
            if a.get_actor_label().startswith("BP_ProceduralBuilding_")}
approved_instances = {lot: sum(c.get_instance_count() for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent))
                      for lot, actor in approved.items()}
approved_wrong = {lot: [sample[lot]["instances"], approved_instances.get(lot)] for lot in sample
                  if approved_instances.get(lot) != sample[lot]["instances"]}
after = {name: sha256(path.read_bytes()).hexdigest() for name, path in protected.items()}
report = {"map": level, "source_maps_unchanged": before == after,
          "new_pcg_houses": audit["pcg_count"], "new_instances": sum(h["actual"] for h in audit["houses"].values()),
          "approved_pcg_houses": len(approved), "approved_instances": sum(approved_instances.values()),
          "original_footprints": audit["source_count"],
          "new_house_errors": audit["errors"], "approved_house_errors": approved_wrong,
          "all_replaced_placeholders_hidden": all(h["source_hidden_in_game"] and h["source_visible_components"] == 0
                                              for h in audit["houses"].values())}
(root / "Pipeline/Unreal/first_pcg_batch_full_saved_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_SAVED_VERIFY", report["new_pcg_houses"], report["new_instances"],
      report["approved_pcg_houses"], report["approved_instances"])
if (not report["source_maps_unchanged"] or report["new_house_errors"] or report["approved_house_errors"] or
        not report["all_replaced_placeholders_hidden"] or report["new_pcg_houses"] != 67 or
        report["approved_pcg_houses"] != 18 or report["original_footprints"] != 3216):
    raise RuntimeError("Saved Batch01 FullPCG verification failed")
