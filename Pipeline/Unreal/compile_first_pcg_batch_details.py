"""Deterministic, detail-only PCG placements for the first 67 non-pilot lots.

The existing MazzarinoBuilding actors retain their footprint, walls and roofs.
Positions are derived from their saved front edge and floor measurements.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "Pipeline/Unreal/first_pcg_batch_source_audit.json"
MESHES = ROOT / "Pipeline/Unreal/first_batch_detail_mesh_audit.json"
DEST = ROOT / "Research/Mazzarino80/PCG/Candidates/district_batch01_details.json"
REPORT = ROOT / "Pipeline/Unreal/first_pcg_batch_detail_plan.json"
sources = json.loads(AUDIT.read_text(encoding="utf-8"))["lots"]
meshes = json.loads(MESHES.read_text(encoding="utf-8"))
plan = {row["id"]: row for row in json.loads(
    (ROOT / "Research/Mazzarino80/building_footprint_plan.json").read_text(encoding="utf-8"))}


def norm2(x, y):
    length = math.hypot(x, y)
    return (x / length, y / length, length) if length else (0.0, 0.0, 0.0)


def midpoint(a, b):
    return [(a[i] + b[i]) * 0.5 for i in range(3)]


def add(points, lot, role, mesh_role, material, location, scale, yaw, index):
    spec = meshes[mesh_role]
    if spec.get("missing"):
        raise RuntimeError("Required mesh is missing: " + mesh_role)
    points.append({
        "role": role, "stage": "Details",
        "location_cm": [round(v, 4) for v in location],
        "rotation_deg": [0.0, round(yaw, 4), 0.0],
        "scale": [round(v, 5) for v in scale],
        "mesh": spec["path"], "material": material,
        "seed": (int(lot) % 1000000) * 1000 + index,
    })


result = {"schema_version": 1, "source": str(AUDIT), "houses": []}
report = {"source_sha256": sha256(AUDIT.read_bytes()).hexdigest(),
          "mesh_audit_sha256": sha256(MESHES.read_bytes()).hexdigest(),
          "lots": {}, "skipped": {}, "roles": {}, "errors": []}
roles = Counter()
for lot, info in sorted(sources.items()):
    p = info["properties"]
    poly = info["footprint_world_cm"]
    if len(poly) < 3 or p["geometry_error"]:
        report["errors"].append({"lot": lot, "reason": "invalid footprint"})
        continue
    area2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    if abs(area2) < 10000:
        report["errors"].append({"lot": lot, "reason": "small signed area"})
        continue
    if not p["detailed_facade"]:
        row = plan[lot]
        if len(row["ring_cm"]) != len(poly):
            raise RuntimeError("Footprint point count differs from original plan: " + lot)
        error = max(math.hypot(v[0]-q[0], v[1]-q[1]) for v, q in zip(poly, row["ring_cm"]))
        if error > 1:
            raise RuntimeError("Footprint differs from original plan: " + lot)
        front = int(row["front_edge"]) % len(poly)
    else:
        front = int(p["front_edge_index"]) % len(poly)
    a, b = poly[front], poly[(front + 1) % len(poly)]
    ux, uy, length = norm2(b[0] - a[0], b[1] - a[1])
    if length < 250:
        # Existing short front edges are unsuitable as detail attachment spans.
        report["skipped"][lot] = "front edge below 250 cm"
        result["houses"].append({"building_id": lot, "visual_style": "DISTRICT_DETAIL",
                                 "stage_points": {"Details": []}})
        continue
    sign = 1 if area2 > 0 else -1
    ox, oy = sign * uy, -sign * ux
    yaw = math.degrees(math.atan2(-ox, oy))  # local +Y faces outward
    base = min(v[2] for v in poly)
    floor_h = float(p["floor_height_meters"]) * 100
    floors = int(p["floor_count"])
    wall_top = base + floors * floor_h
    points = []
    serial = 0

    # Modular 2.08 m copper drainage: bottom and upper ends meet at the wall.
    # Its measured +Y projection faces outward; it is not stretched in XY.
    pipe = meshes["rain_pipe"]
    pipe_h = pipe["box_max"][2] - pipe["box_min"][2]
    run = max(0.0, wall_top - base - 18)
    along = min(max(55.0, length * 0.09), length - 55.0)
    x = a[0] + ux * along + ox * 10
    y = a[1] + uy * along + oy * 10
    z = base
    while run > 15 and serial < 8:
        segment = min(pipe_h, run)
        add(points, lot, "rain_pipe_segment", "rain_pipe", pipe["materials"][0],
            (x, y, z + segment * 0.5), (1.0, 1.0, segment / pipe_h), yaw, serial)
        roles["rain_pipe_segment"] += 1
        serial += 1
        z += segment
        run -= segment

    # Only selected, adequately wide fronts get ivy. Measured bbox makes the
    # thin leaf plane parallel to the wall with its lowest leaf near the ground.
    if length >= 430 and int(lot) % 4 == 1:
        ivy = meshes["ivy"]
        s = 3.15 + (int(lot) % 3) * 0.15
        along = length * (0.83 if int(lot) % 2 else 0.17)
        center = [a[0] + ux * along + ox * 12,
                  a[1] + uy * along + oy * 12,
                  base + 18 + (ivy["origin"][2] - ivy["box_min"][2]) * s]
        radians = math.radians(yaw)
        rx = (ivy["origin"][0] * math.cos(radians) - ivy["origin"][1] * math.sin(radians)) * s
        ry = (ivy["origin"][0] * math.sin(radians) + ivy["origin"][1] * math.cos(radians)) * s
        location = (center[0] - rx, center[1] - ry, center[2] - ivy["origin"][2] * s)
        add(points, lot, "facade_ivy", "ivy", ivy["materials"][0],
            location, (s, s, s), yaw, serial)
        roles["facade_ivy"] += 1
        serial += 1

    # Reconstruct the existing balcony bay formula from MazzarinoBuilding.cpp.
    # Put one pot on the actual slab at first-floor height; no pot on empty air.
    if floors >= 2 and int(p["balcony_style"]) > 0 and length >= 300:
        spacing = max(150, float(p["window_spacing_meters"]) * 100)
        bay_count = max(1, min(30, math.floor(length / spacing)))
        seed = int(p["composition_seed"])
        eligible = [j for j in range(bay_count)
                    if int(p["balcony_style"]) == 2 or (j + 1 + seed) % 3 != 0]
        if eligible and int(lot) % 3 != 0:
            j = eligible[len(eligible) // 2]
            d = length * (j + 0.5) / bay_count
            depth = float(p["balcony_depth_meters"]) * 100
            pot = meshes["pot"]
            s = 3.2 + 0.12 * (int(lot) % 4)
            px = a[0] + ux * (d + min(24, length / bay_count * 0.13)) + ox * depth * 0.62
            py = a[1] + uy * (d + min(24, length / bay_count * 0.13)) + oy * depth * 0.62
            pz = base + floor_h + 2 - pot["box_min"][2] * s
            add(points, lot, "balcony_pot", "pot", pot["materials"][0],
                (px, py, pz), (s, s, s), yaw, serial)
            roles["balcony_pot"] += 1

    report["lots"][lot] = {"district": info["district"], "front_length_cm": round(length, 1),
                           "front_edge": front,
                           "floor_count": floors, "existing_detailed_facade": p["detailed_facade"],
                           "roles": dict(Counter(q["role"] for q in points)),
                           "points": len(points)}
    result["houses"].append({"building_id": lot, "visual_style": "DISTRICT_DETAIL",
                             "stage_points": {"Details": points}})

report["roles"] = dict(roles)
report["houses"] = len(result["houses"])
report["points"] = sum(len(h["stage_points"]["Details"]) for h in result["houses"])
if report["houses"] != 67 or report["errors"]:
    raise RuntimeError("First batch detail compiler failed: " + repr(report["errors"][:3]))
DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text(json.dumps(result, indent=2), encoding="utf-8")
REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_DETAIL_PLAN", report["houses"], report["points"], report["roles"])
