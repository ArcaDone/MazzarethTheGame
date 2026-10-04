"""Compile the editable 18-lot catalog into deterministic PCG module placements.

This is a geometric prototype: source lot vertices and family values stay explicit.
All transforms are world-space centimetres for PCG Load Data Asset in UE 5.5.
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18.json"
OUTPUT = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18_PCGPoints.json"
ROOF_MANIFEST = ROOT / "Research/Mazzarino80/PCG/RoofMeshes_Source/manifest.json"
CUBE = "/Engine/BasicShapes/Cube.Cube"
STAGES = ("Structure", "Facades", "Openings", "Roofs", "Details")


def inside(poly, x, y):
    hit = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > y) != (b[1] > y):
            cross = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x < cross:
                hit = not hit
    return hit


def put(bucket, stage, label, center, size, material, yaw=0, pitch=0, roll=0, mesh=CUBE):
    if min(size) <= 1.0:
        return
    bucket[stage].append({
        "role": label,
        "location_cm": [round(v, 3) for v in center],
        "rotation_deg": [round(pitch, 3), round(yaw, 3), round(roll, 3)],
        "scale": [round(v / 100, 5) for v in size],
        "mesh": mesh,
        "material": material,
    })


def compile_house(record):
    rng = random.Random(record["variation_seed"])
    poly = [p[:2] for p in record["footprint_world_cm"]]
    base = min(p[2] for p in record["footprint_world_cm"])
    floors = int(record["primary_floors"])
    floor_h = float(record["floor_height_cm"])
    height = floors * floor_h
    thickness = float(record["wall_thickness_cm"])
    front = int(record["front_edge"])
    party = set(json.loads(record["party_wall_edges"]))
    m = record["materials"]
    wall_mat = m["plaster_material"]
    stone = m["stone_material"]
    wood = m["wood_material"]
    glass = m["glass_material"]
    iron = m["iron_material"]
    roof_mat = m["terrace_material"] if record["roof_type"] == "Terrace" else m["roof_material"]
    area2 = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    outward_sign = -1 if area2 > 0 else 1
    bucket = {stage: [] for stage in STAGES}
    openings = []
    edge_data = []
    for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 60:
            continue
        ux, uy = dx / length, dy / length
        ox, oy = outward_sign * uy, outward_sign * -ux
        yaw = math.degrees(math.atan2(uy, ux))
        edge_data.append((i, a, length, ux, uy, ox, oy, yaw))
        exterior = i not in party
        for floor in range(floors):
            z0 = base + floor * floor_h
            z1 = z0 + floor_h
            openings_here = []
            if exterior and (i == front or length > 700) and length > 320:
                count = max(1, min(4, int(length / (240 if i == front else 330))))
                for bay in range(count):
                    u = length * (bay + 0.5) / count
                    is_door = i == front and floor == 0 and bay == (count - 1) // 2
                    if floor == 0 and i != front and bay % 2 == 0:
                        continue
                    width = min(105 if is_door else 86, length / count * 0.48)
                    bottom = z0 + (0 if is_door else (86 if floor else 105))
                    top = min(z1 - 35, bottom + (225 if is_door else 125))
                    if top - bottom < 65:
                        continue
                    openings_here.append((u - width / 2, u + width / 2, bottom, top, is_door))
                    openings.append((i, a, u, ux, uy, ox, oy, yaw, width, bottom, top, is_door, floor))
            cuts = sorted({0.0, length, *(v for op in openings_here for v in op[:2])})
            for left, right in zip(cuts, cuts[1:]):
                if right - left < 5:
                    continue
                middle = (left + right) / 2
                blocked = sorted((op[2], op[3]) for op in openings_here if op[0] < middle < op[1])
                cursor = z0
                for low, high in blocked + [(z1, z1)]:
                    if low - cursor > 5:
                        put(bucket, "Structure", "masonry_wall", (a[0] + ux * middle, a[1] + uy * middle, (cursor + low) / 2), (right - left, thickness, low - cursor), wall_mat, yaw)
                    cursor = max(cursor, high)
        if exterior and length > 180:
            center = (a[0] + ux * length / 2 + ox * 8, a[1] + uy * length / 2 + oy * 8)
            put(bucket, "Facades", "stone_base", (*center, base + 28), (length, thickness + 16, 56), stone, yaw)
            put(bucket, "Facades", "cornice", (*center, base + height - 13), (length, thickness + 24, 24), stone, yaw)
            if floors > 1:
                put(bucket, "Facades", "floor_band", (*center, base + floor_h), (length, thickness + 11, 12), stone, yaw)

    for i, a, u, ux, uy, ox, oy, yaw, width, bottom, top, door, floor in openings:
        x, y = a[0] + ux * u + ox * (thickness * 0.43), a[1] + uy * u + oy * (thickness * 0.43)
        role = "door_leaf" if door else "dark_glass"
        put(bucket, "Openings", role, (x, y, (bottom + top) / 2), (width - 8, 8, top - bottom - 8), wood if door else glass, yaw)
        for side in (-1, 1):
            px, py = x + ux * side * (width / 2 + 5), y + uy * side * (width / 2 + 5)
            put(bucket, "Openings", "stone_jamb", (px, py, (bottom + top) / 2), (12, 15, top - bottom + 18), stone, yaw)
            if not door:
                sx, sy = x + ux * side * (width * 0.35), y + uy * side * (width * 0.35)
                put(bucket, "Openings", "shutter", (sx + ox * 7, sy + oy * 7, (bottom + top) / 2), (width * 0.24, 5, top - bottom - 10), wood, yaw)
        put(bucket, "Openings", "lintel", (x, y, top + 7), (width + 25, 20, 14), stone, yaw)
        if not door:
            put(bucket, "Openings", "sill", (x + ox * 5, y + oy * 5, bottom - 8), (width + 30, 24, 15), stone, yaw)
        if floor == 1 and i == front and record["family"] in {"PALAZZETTO", "EXTENDED", "CORNER"} and u / next(e[2] for e in edge_data if e[0] == front) < 0.65:
            bx, by = x + ox * 52, y + oy * 52
            put(bucket, "Details", "balcony_slab", (bx, by, bottom - 10), (width + 80, 105, 20), stone, yaw)
            put(bucket, "Details", "balcony_rail", (bx + ox * 49, by + oy * 49, bottom + 43), (width + 65, 7, 84), iron, yaw)

    # An exact local-space slab captures the irregular footprint; PCG instantiates it.
    front_edge = next((e for e in edge_data if e[0] == front), edge_data[0])
    _, a, length, ux, uy, ox, oy, yaw = front_edge
    roof_info = json.loads(ROOF_MANIFEST.read_text(encoding="utf-8"))[record["building_id"]]
    roof_mesh = "/Game/Mazzarino80/PCG/Modules/SM_PCG_Roof_{0}.SM_PCG_Roof_{0}".format(record["building_id"])
    put(bucket, "Roofs", "roof_slab", (*roof_info["center_xy_cm"], roof_info["roof_base_z_cm"]),
        (100, 100, 100), roof_mat, mesh=roof_mesh)
    if record["roof_type"] == "Terrace":
        for i, a, length, ux, uy, ox, oy, yaw in edge_data:
            if i in party:
                continue
            put(bucket, "Roofs", "terrace_parapet", (a[0] + ux * length / 2, a[1] + uy * length / 2, base + height + 27), (length, 25, 54), stone, yaw)
    if rng.random() < 0.9:
        i, a, length, ux, uy, ox, oy, yaw = front_edge
        px, py = a[0] + ux * min(55, length * 0.12) + ox * 20, a[1] + uy * min(55, length * 0.12) + oy * 20
        put(bucket, "Details", "downpipe", (px, py, base + height / 2), (8, 8, height), iron)

    for stage in STAGES:
        for n, point in enumerate(bucket[stage]):
            point["seed"] = record["variation_seed"] * 100000 + n
    return {"building_id": record["building_id"], "family": record["family"], "base_z_cm": base, "stage_points": bucket,
            "counts": {stage: len(bucket[stage]) for stage in STAGES}}


def main():
    catalog = json.loads(SOURCE.read_text(encoding="utf-8"))
    houses = [compile_house(record) for record in catalog["buildings"]]
    assert len(houses) == 18 and len({x["building_id"] for x in houses}) == 18
    assert all(h["counts"]["Structure"] and h["counts"]["Roofs"] for h in houses)
    OUTPUT.write_text(json.dumps({"schema_version": 1, "source": SOURCE.name, "houses": houses}, indent=2), encoding="utf-8")
    print(json.dumps({"houses": len(houses), "totals": {stage: sum(h["counts"][stage] for h in houses) for stage in STAGES}, "output": str(OUTPUT)}))


if __name__ == "__main__":
    main()
