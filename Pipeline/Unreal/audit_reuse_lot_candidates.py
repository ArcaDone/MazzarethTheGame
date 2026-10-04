"""Read back all candidate PCG assets and check their live UE point metadata."""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = json.loads((ROOT / "Research/Mazzarino80/PCG/Buildings_Test18_ReuseCandidate_PCGPoints.json").read_text(encoding="utf-8"))
BASE = "/Game/Mazzarino80/ReuseKit/PCG/Lots"
rows = []
issues = []
rail_total = 0
roof_paths = set()
for house in SOURCE["houses"]:
    lot = house["building_id"]
    asset = unreal.EditorAssetLibrary.load_asset(BASE + "/PCGDA_Building_" + lot)
    graph = unreal.EditorAssetLibrary.load_asset(BASE + "/PCG_Building_" + lot)
    if asset is None or not isinstance(graph, unreal.PCGGraph):
        issues.append(lot + ": missing data asset or graph")
        continue
    stages = {}
    for tagged in asset.get_editor_property("data").tagged_data:
        stage = next(iter(tagged.tags))
        points = tagged.data.get_points()
        metadata = tagged.data.mutable_metadata()
        stages[stage] = len(points)
        for point in points:
            role = point.get_string_attribute(metadata, "Role")
            soft_path = point.get_soft_object_path_attribute(metadata, "Mesh")
            mesh = soft_path.export_text()
            style = point.get_string_attribute(metadata, "VisualStyle")
            if style != house["visual_style"]:
                issues.append(lot + ": style mismatch in " + stage)
            if role == "balcony_rail":
                rail_total += 1
                if "Cast_Iron_Fence_09_LOD1" not in mesh:
                    issues.append(lot + ": balcony rail uses wrong mesh " + mesh)
            if role == "roof_slab":
                roof_paths.add(mesh)
    expected = {stage: len(specs) for stage, specs in house["stage_points"].items()}
    if stages != expected:
        issues.append(lot + ": stage counts differ")
    rows.append({"lot": lot, "style": house["visual_style"], "stages": stages})
if len(rows) != 18 or rail_total != 20 or len(roof_paths) != 18:
    issues.append("Expected 18 lots, 20 kit rails and 18 distinct roof meshes")
out = {"lots": rows, "rail_points": rail_total,
       "distinct_roof_meshes": len(roof_paths),
       "issues": issues}
(ROOT / "Pipeline/Unreal/reuse_lot_candidate_audit.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("M80_REUSE_LOTS_AUDIT", len(rows), rail_total, len(roof_paths), len(issues))
if issues:
    raise RuntimeError("Candidate audit found issues; inspect report")
