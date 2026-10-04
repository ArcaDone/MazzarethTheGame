"""Inspect modern OSM features against the existing Unreal church anchors."""

import json
import math
from pathlib import Path


SOURCE = Path(r"D:\UE5Projects\GameAnimationSample\Research\Mazzarino80\Mazzarino_OSM_strade_chiese_2026.geojson")
OUT = Path(r"D:\UE5Projects\GameAnimationSample\Saved\Mazzarino80\georef_diagnostic.json")


def center(feature):
    geometry = feature["geometry"]
    if geometry["type"] == "Point":
        return geometry["coordinates"][:2]
    coords = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        coords = coords[0]
    elif geometry["type"] == "MultiPolygon":
        coords = coords[0][0]
    elif geometry["type"] == "LineString":
        pass
    else:
        return None
    return [sum(v[0] for v in coords) / len(coords), sum(v[1] for v in coords) / len(coords)]


features = json.loads(SOURCE.read_text(encoding="utf-8-sig"))["features"]
selected = []
for f in features:
    p = f.get("properties", {})
    name = p.get("name") or ""
    if ("domenico" in name.lower() or "maria della neve" in name.lower()
            or "del carmine" in name.lower() or "del mazzarro" in name.lower()
            or "municip" in name.lower() or "comune" in name.lower()
            or p.get("amenity") == "townhall"):
        selected.append({"name": name, "properties": p, "center": center(f)})

# Two point registration is diagnostic only: blueprint pivots differ from church centers.
matrice_geo = next(v["center"] for v in selected if v["name"] == "Chiesa di Santa Maria della Neve")
domenico_geo = next(v["center"] for v in selected if v["name"] == "Chiesa di San Domenico")
matrice_ue = (823.7388, -40.0640)
domenico_ue = (942.8937, -23.2593)
metres_lon = 111320 * math.cos(math.radians(matrice_geo[1]))
metres_lat = 111132
dg = ((domenico_geo[0] - matrice_geo[0]) * metres_lon,
      (domenico_geo[1] - matrice_geo[1]) * metres_lat)
du = (domenico_ue[0] - matrice_ue[0], domenico_ue[1] - matrice_ue[1])
scale = math.hypot(*dg) / math.hypot(*du)
angle = math.atan2(dg[1], dg[0]) - math.atan2(du[1], du[0])


def geo_to_ue(coord):
    east = (coord[0] - matrice_geo[0]) * metres_lon
    north = (coord[1] - matrice_geo[1]) * metres_lat
    return [round(matrice_ue[0] + (east * math.cos(angle) + north * math.sin(angle)) / scale, 2),
            round(matrice_ue[1] + (-east * math.sin(angle) + north * math.cos(angle)) / scale, 2)]


roads = []
for f in features:
    p = f.get("properties", {})
    if "Vittorio Emanuele" not in (p.get("name") or ""):
        continue
    if f["geometry"]["type"] != "LineString":
        continue
    points = [geo_to_ue(coord) for coord in f["geometry"]["coordinates"]]
    if any(400 < point[0] < 1050 for point in points):
        roads.append({"name": p["name"], "osm_id": p.get("@id"), "points_ue_m": points})

diagnostic = {"anchors": selected, "two_point_scale": scale,
              "two_point_rotation_deg": math.degrees(angle), "corso_segments": roads}
diagnostic["third_point_checks"] = {
    v["name"]: geo_to_ue(v["center"])
    for v in selected if v["name"] in ("Chiesa del Carmine", "Chiesa di Maria Santissima del Mazzarro")
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"scale": scale, "rotation_deg": math.degrees(angle),
                  "third_point_checks": diagnostic["third_point_checks"],
                  "corso_segments": roads}, ensure_ascii=False, indent=2))
