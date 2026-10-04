"""Compare the saved PCG instance transforms with their exported world points."""
from pathlib import Path
import json
import math
import statistics
import unreal

root = Path(unreal.Paths.project_dir())
world = unreal.EditorLoadingAndSavingUtils.load_map(
    "/Game/Levels/Mazzarino80_PCG_Quartieri_Batch01_FullPCG")
if not world or world.get_name() != "Mazzarino80_PCG_Quartieri_Batch01_FullPCG":
    raise RuntimeError("Could not load the isolated FullPCG preview map")
catalog = json.loads((root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/full_pcg_points.json").read_text(encoding="utf-8"))
houses = {h["building_id"]: h for h in catalog["houses"]}
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
pcg = {a.get_actor_label().removeprefix("PCG_Building_"): a for a in actors
       if a.get_actor_label().startswith("PCG_Building_")}
sources = {str(a.get_editor_property("building_id")): a for a in actors
           if isinstance(a, unreal.MazzarinoBuilding)}

def xyz(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]

def distance(a, b):
    return math.dist(a, b)

result = {"map": unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name(),
          "houses": {}}
for lot in ("1249054419", "1249067196", "1249067205"):
    actor = pcg[lot]
    source = sources[lot]
    specs = [p for points in houses[lot]["stage_points"].values() for p in points]
    by_mesh = {}
    for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        mesh = component.get_editor_property("static_mesh")
        if not mesh:
            continue
        entries = by_mesh.setdefault(mesh.get_path_name(), [])
        for index in range(component.get_instance_count()):
            tr = component.get_instance_transform(index, world_space=True)
            entries.append(xyz(tr.translation))
    roles = {}
    for role in sorted({p["role"] for p in specs}):
        subset = [p for p in specs if p["role"] == role]
        offsets = []
        examples = []
        for point in subset:
            candidates = by_mesh.get(point["mesh"], [])
            if not candidates:
                continue
            expected = point["location_cm"]
            actual = min(candidates, key=lambda v: distance(v, expected))
            offset = distance(actual, expected)
            offsets.append(offset)
            if len(examples) < 2:
                examples.append({"expected_cm": expected, "nearest_actual_cm": actual,
                                 "offset_cm": round(offset, 2)})
        roles[role] = {"expected": len(subset), "matched": len(offsets),
                       "median_offset_cm": round(statistics.median(offsets), 2) if offsets else None,
                       "max_offset_cm": round(max(offsets), 2) if offsets else None,
                       "examples": examples}
    result["houses"][lot] = {"pcg_location_cm": xyz(actor.get_actor_location()),
                             "pcg_rotation": str(actor.get_actor_rotation()),
                             "pcg_scale": xyz(actor.get_actor_scale3d()),
                             "source_location_cm": xyz(source.get_actor_location()),
                             "source_scale": xyz(source.get_actor_scale3d()),
                             "roles": roles}

out = root / "Pipeline/Unreal/first_pcg_batch_alignment_diagnosis.json"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_ALIGNMENT_DIAGNOSIS", str(out))
