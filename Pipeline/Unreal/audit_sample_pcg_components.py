"""Inspect the generated component composition of approved sample houses."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
unreal.EditorLoadingAndSavingUtils.load_map("/Game/Levels/Mazzarino80_CaseStoriche_Campione")
rows = {}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    label = actor.get_actor_label()
    if label.startswith("BP_ProceduralBuilding_"):
        lot = label.rsplit("_", 1)[-1]
        meshes = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
        rows[lot] = [{"name": c.get_name(), "count": c.get_instance_count(),
                      "mesh": c.get_editor_property("static_mesh").get_path_name()
                      if c.get_editor_property("static_mesh") else None}
                     for c in meshes]
(root / "Pipeline/Unreal/sample_pcg_component_inventory.json").write_text(
    json.dumps(rows, indent=2), encoding="utf-8")
print("M80_PCG_COMPONENT_INVENTORY", len(rows))
