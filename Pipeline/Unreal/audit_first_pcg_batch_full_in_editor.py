"""Read-only check of generated meshes, actual material overrides and placeholders."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
catalog = json.loads((root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/full_pcg_points.json").read_text(encoding="utf-8"))
expected = {h["building_id"]: sum(len(v) for v in h["stage_points"].values()) for h in catalog["houses"]}
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
pcg = {a.get_actor_label().removeprefix("PCG_Building_"): a for a in actors if a.get_actor_label().startswith("PCG_Building_")}
sources = {str(a.get_editor_property("building_id")): a for a in actors if isinstance(a, unreal.MazzarinoBuilding)}
report = {"world": unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name(),
          "pcg_count": len(pcg), "source_count": len(sources), "houses": {}, "errors": []}
for lot in sorted(expected):
    actor = pcg.get(lot)
    source = sources.get(lot)
    if not actor or not source:
        report["errors"].append("Missing PCG or source " + lot)
        continue
    components = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    count = sum(c.get_instance_count() for c in components)
    primitives = source.get_components_by_class(unreal.PrimitiveComponent)
    row = {"expected": expected[lot], "actual": count,
           "source_visible_components": sum(bool(c.is_visible()) for c in primitives),
           "source_hidden_in_game": bool(source.get_editor_property("hidden")),
           "wall": [], "roof": []}
    for c in components:
        mesh = c.get_editor_property("static_mesh")
        if not mesh:
            continue
        path = mesh.get_path_name()
        if "SM_PCG_Walls_" not in path and "SM_PCG_Roof_" not in path:
            continue
        material = c.get_material(0)
        entry = {"mesh": path, "instances": c.get_instance_count(),
                 "material": material.get_path_name() if material else None}
        row["wall" if "SM_PCG_Walls_" in path else "roof"].append(entry)
    report["houses"][lot] = row
    if (count != expected[lot] or row["source_visible_components"] or
            not row["source_hidden_in_game"] or not row["wall"] or not row["roof"]):
        report["errors"].append("Invalid house " + lot)

out = root / "Pipeline/Unreal/first_pcg_batch_full_editor_audit.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_EDITOR_AUDIT", len(report["houses"]), len(report["errors"]))
