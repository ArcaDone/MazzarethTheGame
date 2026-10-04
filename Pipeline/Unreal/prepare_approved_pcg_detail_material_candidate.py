"""Stage material consolidation and a tiny detail-only clothing test.

The approved source, current PCG assets and sample map are never modified.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Research/Mazzarino80/PCG/BakedSource/approved_modules.json"
AUDIT = ROOT / "Pipeline/Unreal/approved_pcg_surface_audit.json"
MASTERS = ROOT / "Pipeline/Unreal/approved_pcg_surface_master_result.json"
OUT = ROOT / "Research/Mazzarino80/PCG/Candidates/approved_detail_material_v1.json"
REPORT = ROOT / "Pipeline/Unreal/approved_pcg_detail_material_candidate_report.json"

original_bytes = SOURCE.read_bytes()
source_sha = sha256(original_bytes).hexdigest()
original = json.loads(original_bytes)
candidate = deepcopy(original)
audit = json.loads(AUDIT.read_text(encoding="utf-8"))
new_materials = json.loads(MASTERS.read_text(encoding="utf-8"))["instances"]
material_audit = {m["path"]: m for m in audit["materials"]}

def replacement(path):
    if "/Historic/Materials/Case/MI_Calce_" in path:
        parent = material_audit[path]["parent"]
        index = int(re.search(r"M80_Calce_consumata_(\d+)", parent).group(1))
        return new_materials["Plaster_" + str(index)]
    if "/Historic/Materials/Case/MI_Pietra_" in path:
        parent = material_audit[path]["parent"]
        index = int(re.search(r"M80_Muratura_locale_(\d+)", parent).group(1))
        return new_materials["Stone_" + str(index)]
    name = path.split("/")[-1].split(".")[0]
    fixed = {
        "M80_Coppi_terracotta_3D": "Tile3D",
        "M80_Coppi_vecchi": "RoofSurface",
        "M80_Terrazza_calce": "Terrace",
        "M80_Pietra_modesta": "StoneTrim",
        "M80_Muratura_locale_0": "Stone_0",
        "M80_Muratura_locale_1": "Stone_1",
        "M80_Canaletta_pietra_opaca": "GutterStone",
        "M80_Legno_persiane_0": "Wood_0",
        "M80_Legno_persiane_1": "Wood_1",
        "M80_Legno_persiane_2": "Wood_2",
        "M80_Ferro_ossidato": "Iron",
        "M80_Vetro_ombra": "Glass",
        "M80_Vicolo_pietra_consumata": "Paving",
        "M80_Laterizio_rosso_macro": "BrickRed",
        "M80_Laterizio_giallo_macro": "BrickYellow",
    }
    return new_materials[fixed[name]] if name in fixed else path

material_changes = Counter()
detail_swaps = []
for lot, house in candidate["houses"].items():
    for stage, points in house["stage_points"].items():
        for index, point in enumerate(points):
            before = point["material"]
            point["material"] = replacement(before)
            if before != point["material"]:
                material_changes[stage] += 1
            # Only three existing suspended-cloth slots are tested. No wall,
            # roof, opening, balcony or gutter mesh changes in this candidate.
            if (lot == "1249069237" and stage == "Details" and
                    point["role"] == "Bucato_indumenti"):
                old_mesh = point["mesh"]
                point["mesh"] = "/Game/Megapack/Meshes/Favela/Mannequin/SM_Clothes_01.SM_Clothes_01"
                point["material"] = "/Game/Megapack/Material/Favela/MI_Clothes_01.MI_Clothes_01"
                detail_swaps.append({"lot": lot, "stage": stage, "index": index,
                                     "old_mesh": old_mesh, "new_mesh": point["mesh"]})

geometry_changes = []
point_count = 0
for lot, house in original["houses"].items():
    other = candidate["houses"][lot]
    for stage, points in house["stage_points"].items():
        modified = other["stage_points"][stage]
        if len(points) != len(modified):
            raise RuntimeError("Point count changed: " + lot + "/" + stage)
        point_count += len(points)
        for index, (a, b) in enumerate(zip(points, modified)):
            for key in ("role", "stage", "location_cm", "rotation_quat", "scale", "seed"):
                if a.get(key) != b.get(key):
                    geometry_changes.append((lot, stage, index, key))
            if a["mesh"] != b["mesh"] and (stage != "Details" or a["role"] != "Bucato_indumenti"):
                geometry_changes.append((lot, stage, index, "mesh"))
if geometry_changes:
    raise RuntimeError("Protected geometry changed: " + repr(geometry_changes[:5]))
if sha256(SOURCE.read_bytes()).hexdigest() != source_sha:
    raise RuntimeError("Approved source changed during staging")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(candidate, indent=2), encoding="utf-8")
old_paths = {p["material"] for h in original["houses"].values()
             for points in h["stage_points"].values() for p in points}
new_paths = {p["material"] for h in candidate["houses"].values()
             for points in h["stage_points"].values() for p in points}
report = {"source": str(SOURCE), "source_sha256": source_sha,
          "candidate": str(OUT), "houses": len(original["houses"]),
          "points": point_count, "material_paths_before": len(old_paths),
          "material_paths_after": len(new_paths),
          "material_changes_by_stage": dict(material_changes),
          "detail_mesh_swaps": detail_swaps,
          "protected_geometry_changes": geometry_changes,
          "sample_map_edited": False}
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_PCG_DETAIL_CANDIDATE", point_count, len(new_paths), len(detail_swaps))
