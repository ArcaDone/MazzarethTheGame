"""Make complete five-stage PCG input for 67 irregular-footprint houses.

The MazzarinoBuilding volumes are only references. This compiler emits one
footprint-specific wall and one roof mesh per lot, then reuses the existing
opening, balcony and detail meshes as instanced PCG points.
"""
from collections import Counter
from pathlib import Path
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Pipeline/Unreal/first_pcg_batch_module_export.json"
DETAILS = ROOT / "Research/Mazzarino80/PCG/Candidates/district_batch01_details.json"
MASTERS = ROOT / "Pipeline/Unreal/approved_pcg_surface_master_result.json"
OUT_DIR = ROOT / "Research/Mazzarino80/PCG/DistrictBatch01_Full"
CATALOG = OUT_DIR / "full_pcg_points.json"
REPORT = ROOT / "Pipeline/Unreal/first_pcg_batch_full_plan.json"
sys.path.insert(0, str(ROOT / "Scripts"))
import mazzarino80_pcg_roof_meshes as roof_tools
roof_tools.OUT = OUT_DIR / "MeshSource"
roof_tools.OUT.mkdir(parents=True, exist_ok=True)

source = json.loads(SOURCE.read_text(encoding="utf-8"))["houses"]
details = {h["building_id"]: h for h in json.loads(DETAILS.read_text(encoding="utf-8"))["houses"]}
mi = json.loads(MASTERS.read_text(encoding="utf-8"))["instances"]
assert set(source) == set(details) and len(source) == 67
STAGES = ("Structure", "Facades", "Openings", "Roofs", "Details")


def wall_mesh(lot, row):
    poly = row["footprint_world_cm"]
    zbase = min(p[2] for p in poly)
    height = row["floor_count"] * row["floor_height_cm"]
    xy = [(p[0], p[1]) for p in poly]
    area = roof_tools.area(xy)
    xmin, xmax = min(p[0] for p in poly), max(p[0] for p in poly)
    ymin, ymax = min(p[1] for p in poly), max(p[1] for p in poly)
    cx, cy = (xmin + xmax) * 0.5, (ymin + ymax) * 0.5
    vertices, tex, faces = [], [], []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length < 1:
            continue
        start = len(vertices) + 1
        vertices.extend(((a[0]-cx, a[1]-cy, 0), (b[0]-cx, b[1]-cy, 0),
                         (b[0]-cx, b[1]-cy, height), (a[0]-cx, a[1]-cy, height)))
        tex.extend(((0, 0), (length/225, 0), (length/225, height/225), (0, height/225)))
        face = (start, start+1, start+2, start+3)
        faces.append(face if area > 0 else tuple(reversed(face)))
    path = roof_tools.OUT / ("SM_PCG_Walls_" + lot + ".obj")
    lines = ["o SM_PCG_Walls_" + lot]
    # UE's OBJ importer mirrors Y. Store the inverse so imported local-space
    # vertices match the world-space footprint and exported facade anchors.
    lines.extend("v %.5f %.5f %.5f" % (x, -y, z) for x, y, z in vertices)
    lines.extend("vt %.6f %.6f" % uv for uv in tex)
    lines.extend("f " + " ".join("%d/%d" % (i, i) for i in face) for face in faces)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"path": str(path), "center_xy_cm": [cx, cy], "base_z_cm": zbase,
            "faces": len(faces), "height_cm": height, "area_cm2": abs(area)}


def master_for_wall(row, lot):
    current = (row["surface_materials"][0] or "").lower()
    if "pietra" in current or "stone" in current:
        return mi["Stone_" + str(int(lot) % 2)]
    palette = ("Plaster_0", "Plaster_1", "Plaster_2", "Plaster_4", "Plaster_5")
    return mi[palette[int(lot) % len(palette)]]


def remap_module_material(role, path):
    if role == "masonry_details":
        return mi["StoneTrim"]
    if role == "metal_details":
        return mi["Iron"]
    if role == "shutters":
        return mi["Wood_" + str(sum(path.encode("utf-8")) % 3)]
    if role == "window_backings":
        return mi["Glass"]
    return path


OUT_DIR.mkdir(parents=True, exist_ok=True)
catalog = {"schema_version": 1, "coordinate_space": "world_cm", "houses": []}
report = {"houses": {}, "counts": {}, "errors": []}
stage_counts = Counter()
for lot, row in sorted(source.items()):
    groups = {stage: [] for stage in STAGES}
    wall = wall_mesh(lot, row)
    roof_record = {"building_id": lot,
                   "footprint_world_cm": row["footprint_world_cm"],
                   "front_edge": row["front_edge"] % len(row["footprint_world_cm"]),
                   "roof_type": "Terrace" if row["roof_rise_cm"] < 1 else "PitchedOrMixed",
                   "roof_rise_cm": row["roof_rise_cm"],
                   "primary_floors": row["floor_count"],
                   "floor_height_cm": row["floor_height_cm"]}
    roof = roof_tools.roof(roof_record, obj_y_flip=True)
    asset_root = "/Game/Mazzarino80/PCG/DistrictBatch01_Full/Meshes/"
    groups["Structure"].append({
        "role": "footprint_wall_surface", "stage": "Structure",
        "location_cm": [*wall["center_xy_cm"], wall["base_z_cm"]],
        "rotation_quat": [0, 0, 0, 1], "scale": [1, 1, 1],
        "mesh": asset_root + "SM_PCG_Walls_" + lot + ".SM_PCG_Walls_" + lot,
        "material": master_for_wall(row, lot), "seed": int(lot) % 100000000,
    })
    groups["Roofs"].append({
        "role": "footprint_roof_surface", "stage": "Roofs",
        "location_cm": [*roof["center_xy_cm"], roof["roof_base_z_cm"]],
        "rotation_quat": [0, 0, 0, 1], "scale": [1, 1, 1],
        "mesh": asset_root + "SM_PCG_Roof_" + lot + ".SM_PCG_Roof_" + lot,
        "material": mi["Terrace" if row["roof_rise_cm"] < 1 else "RoofSurface"],
        "seed": int(lot) % 100000000 + 1,
    })
    for index, old in enumerate(row["module_points"]):
        point = dict(old)
        point["material"] = remap_module_material(point["role"], point["material"])
        point["seed"] = (int(lot) % 100000) * 500 + index
        groups[point["stage"]].append(point)
    groups["Details"].extend(details[lot]["stage_points"]["Details"])
    for stage in STAGES:
        stage_counts[stage] += len(groups[stage])
    catalog["houses"].append({"building_id": lot,
                              "visual_style": "STYLE_" + str(int(lot) % 4 + 1).zfill(2),
                              "stage_points": groups})
    report["houses"][lot] = {
        "district": row["district"], "wall": wall, "roof": roof,
        "floors": row["floor_count"],
        "stages": {stage: len(points) for stage, points in groups.items()},
    }
report["counts"] = dict(stage_counts)
report["total_points"] = sum(stage_counts.values())
report["mesh_files"] = len(list(roof_tools.OUT.glob("*.obj")))
if len(catalog["houses"]) != 67 or report["mesh_files"] != 134:
    raise RuntimeError("Full PCG catalog or geometry count invalid")
CATALOG.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_FULL_PLAN", len(catalog["houses"]), report["total_points"], report["counts"])
