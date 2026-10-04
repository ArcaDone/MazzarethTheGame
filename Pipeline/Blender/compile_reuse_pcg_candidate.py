"""Prepare a reversible 18-lot PCG candidate using a sized reuse-kit railing.

Every original footprint, wall, opening, and per-lot roof point is preserved.
The candidate lives beside the approved point catalog for visual inspection.
"""
from copy import deepcopy
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18_PCGPoints.json"
OUTPUT = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18_ReuseCandidate_PCGPoints.json"
REPORT = ROOT / "Pipeline/Unreal/reuse_lot_candidate_report.json"
IMPORT = ROOT / "Pipeline/Unreal/reuse_import_result.json"
PIVOTS = ROOT / "Pipeline/Unreal/module_pivot_probe.json"
STYLES = ROOT / "Pipeline/Unreal/visual_style_map.json"
GEOMETRY = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export/geometry_findings.json"

original = json.loads(SOURCE.read_text(encoding="utf-8"))
data = deepcopy(original)
imports = json.loads(IMPORT.read_text(encoding="utf-8"))
pivots = json.loads(PIVOTS.read_text(encoding="utf-8"))
styles = json.loads(STYLES.read_text(encoding="utf-8"))
geometry = json.loads(GEOMETRY.read_text(encoding="utf-8"))
name = "/Game/Mazzarino80/ReuseKit/Modules/SM_M80_FENCE__Cast_Iron_Fence_09_LOD1"
record = next(row for row in imports["modules"] if row["asset"] == name)
pivot = next(row for row in pivots if row["asset"] == name)
dims = record["dimensions_cm"]
center = pivot["origin_cm"]
if not (245 <= dims[0] <= 265 and 155 <= dims[2] <= 175):
    raise RuntimeError("Railing dimensions do not match the validated module")

edits = []
for house in data["houses"]:
    lot = house["building_id"]
    house["visual_style"] = styles[lot]
    for point in house["stage_points"]["Details"]:
        if point["role"] != "balcony_rail":
            continue
        if point["mesh"] != "/Engine/BasicShapes/Cube.Cube":
            raise RuntimeError("Unexpected non-proxy railing in " + lot)
        pitch, yaw, roll = point["rotation_deg"]
        if abs(pitch) > 1e-5 or abs(roll) > 1e-5:
            raise RuntimeError("Railing needs non-yaw alignment in " + lot)
        old_location = point["location_cm"][:]
        old_size = [100.0 * value for value in point["scale"]]
        scale = [old_size[i] / dims[i] for i in range(3)]
        offset = [center[i] * scale[i] for i in range(3)]
        angle = math.radians(yaw)
        dx = math.cos(angle) * offset[0] - math.sin(angle) * offset[1]
        dy = math.sin(angle) * offset[0] + math.cos(angle) * offset[1]
        point["location_cm"] = [round(old_location[0] - dx, 3),
                                round(old_location[1] - dy, 3),
                                round(old_location[2] - offset[2], 3)]
        point["scale"] = [round(value, 6) for value in scale]
        point["mesh"] = name + ".SM_M80_FENCE__Cast_Iron_Fence_09_LOD1"
        point["material"] = "/Game/Mazzarino80/ReuseKit/Materials/MI_M80_Iron.MI_M80_Iron"
        point["reuse_kit_module"] = "FENCE__Cast Iron Fence 09_LOD1"
        edits.append({"lot": lot, "seed": point["seed"],
                      "old_location_cm": old_location,
                      "new_location_cm": point["location_cm"],
                      "new_scale": point["scale"]})

before = {h["building_id"]: h for h in original["houses"]}
assert set(before) == {h["building_id"] for h in data["houses"]} == set(styles)
assert len(edits) == 20, "Expected 20 provisional balcony rails"
roof_meshes = set()
for house in data["houses"]:
    lot = house["building_id"]
    for stage in house["stage_points"]:
        a = before[lot]["stage_points"][stage]
        b = house["stage_points"][stage]
        assert len(a) == len(b), (lot, stage)
        if stage != "Details":
            assert a == b, (lot, stage)
    roof_meshes.update(point["mesh"] for point in house["stage_points"]["Roofs"]
                       if point["role"] == "roof_slab")
assert len(roof_meshes) == 18, "Per-lot roofs must stay distinct"
rail_triangles = next(row["triangles"] for row in geometry
                      if row["object"] == "FENCE__Cast Iron Fence 09_LOD1")

data["schema_version"] = 2
data["source"] = SOURCE.name
data["candidate_note"] = "20 fitted reuse-kit balcony rails; original 18 irregular roofs retained"
OUTPUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
REPORT.write_text(json.dumps({"candidate": str(OUTPUT), "lots": len(data["houses"]),
                              "railing_replacements": edits,
                              "railing_triangles_per_instance_before_export_cleanup": rail_triangles,
                              "candidate_railing_triangles_total": rail_triangles * len(edits),
                              "distinct_irregular_roof_meshes": len(roof_meshes),
                              "original_stage_point_counts_preserved": True},
                             indent=2), encoding="utf-8")
print("M80_REUSE_LOT_CANDIDATE", len(data["houses"]), "lots", len(edits),
      "fitted rails", len(roof_meshes), "distinct roofs")
