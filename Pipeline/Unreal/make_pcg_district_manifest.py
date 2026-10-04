"""Inventory the existing Panoramica sectors in reproducible batches of three.

This is a visibility/workload manifest, not a claim that all footprints have
been converted to PCG. The first batch contains the 18 approved PCG lots.
"""
from collections import defaultdict
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "Pipeline/Unreal/panoramica_district_audit.json"
APPROVED = ROOT / "Research/Mazzarino80/PCG/BakedSource/approved_modules.json"
OUT = ROOT / "Pipeline/Unreal/pcg_district_manifest.json"

inventory = json.loads(AUDIT.read_text(encoding="utf-8"))["buildings"]
approved = set(json.loads(APPROVED.read_text(encoding="utf-8"))["houses"])
by_folder = defaultdict(list)
for lot, record in inventory.items():
    by_folder[record["folder"]].append((lot, record))

first = [
    "Mazzarino80/Edifici/Isolato_campione",
    "Mazzarino80/Edifici/Centro_Corso/Settore_04_00",
    "Mazzarino80/Edifici/Centro_Corso/Settore_05_00",
]
if not all(path in by_folder for path in first):
    raise RuntimeError("Missing one of the three existing central sectors")
center = [sum(inventory[i]["position_cm"][axis] for i in approved) / len(approved)
          for axis in (0, 1)]

def sort_key(path):
    rows = by_folder[path]
    xy = [sum(r["position_cm"][axis] for _, r in rows) / len(rows)
          for axis in (0, 1)]
    return (math.dist(xy, center), path)

paths = first + sorted((p for p in by_folder if p not in first), key=sort_key)
districts = []
for n, path in enumerate(paths, 1):
    rows = by_folder[path]
    lots = sorted(lot for lot, _ in rows)
    pilot = sorted(approved.intersection(lots))
    xs = [r["position_cm"][0] for _, r in rows]
    ys = [r["position_cm"][1] for _, r in rows]
    districts.append({"order": n, "batch": (n - 1) // 3 + 1,
                      "id": f"Q{n:03d}", "source_folder": path,
                      "building_count": len(lots), "lots": lots,
                      "approved_pcg_lots": pilot,
                      "bounds_cm": [min(xs), min(ys), max(xs), max(ys)],
                      "centroid_cm": [sum(xs) / len(xs), sum(ys) / len(ys)],
                      "pcg_status": "approved_lots_only" if pilot else "not_converted"})

if sum(d["building_count"] for d in districts) != len(inventory):
    raise RuntimeError("A building was dropped from the district index")
if set().union(*(set(d["approved_pcg_lots"]) for d in districts)) != approved:
    raise RuntimeError("Approved PCG lots are missing from Panoramica")

report = {"source_map": "/Game/Levels/Mazzarino80_Panoramica",
          "preview_map": "/Game/Levels/Mazzarino80_PCG_Quartieri_Preview",
          "description": "Existing editor sectors; three at a time. Not named historical quarters.",
          "sector_count": len(districts), "footprint_count": len(inventory),
          "approved_pcg_count": len(approved),
          "batches": (len(districts) + 2) // 3,
          "first_batch": [d["id"] for d in districts[:3]],
          "districts": districts}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"M80_DISTRICTS {len(districts)} sectors, {len(inventory)} footprints, "
      f"{len(approved)} approved PCG lots, {report['batches']} batches")
