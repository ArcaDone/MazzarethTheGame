"""Named OSM streets in Unreal world cm (for street name plaques and road signs, houses V3 step 11).

The affine transform lon/lat -> world cm is fitted by least squares on the 3200 OSM buildings,
whose world centres are in building_footprint_plan.json (same OSM ids, current reflected frame).
Writes Research/Mazzarino80/streets_world.json. Plain Python, run outside Unreal.
"""
import json
from pathlib import Path

RESEARCH = Path(__file__).resolve().parent.parent / "Research/Mazzarino80"


def solve3(m, v):
    """Solves the 3x3 system m x = v (Cramer)."""
    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    out = []
    for i in range(3):
        mi = [row[:] for row in m]
        for r in range(3):
            mi[r][i] = v[r]
        out.append(det(mi) / d)
    return out


def main():
    osm = json.loads((RESEARCH / "Mazzarino_OSM_edifici_2026.json").read_text(encoding="utf-8-sig"))["elements"]
    plan = {str(b["id"]): b["center_cm"] for b in json.loads((RESEARCH / "building_footprint_plan.json").read_text(encoding="utf-8-sig"))}
    lon0, lat0 = 14.21, 37.30
    pairs = []
    for el in osm:
        if str(el.get("id")) in plan and el.get("geometry"):
            g = el["geometry"][:-1] if len(el["geometry"]) > 1 else el["geometry"]
            lon = sum(p["lon"] for p in g) / len(g) - lon0
            lat = sum(p["lat"] for p in g) / len(g) - lat0
            pairs.append(((lon, lat), plan[str(el["id"])][:2]))
    coeffs = []
    for axis in range(2):
        m = [[0.0] * 3 for _ in range(3)]
        v = [0.0] * 3
        for (x, y), w in pairs:
            row = (x, y, 1.0)
            for i in range(3):
                v[i] += row[i] * w[axis]
                for j in range(3):
                    m[i][j] += row[i] * row[j]
        coeffs.append(solve3(m, v))

    def to_world(lon, lat):
        x, y = lon - lon0, lat - lat0
        return [round(coeffs[0][0] * x + coeffs[0][1] * y + coeffs[0][2], 1), round(coeffs[1][0] * x + coeffs[1][1] * y + coeffs[1][2], 1)]

    err = sorted(((to_world(lon + lon0, lat + lat0)[0] - w[0]) ** 2 + (to_world(lon + lon0, lat + lat0)[1] - w[1]) ** 2) ** 0.5
                 for (lon, lat), w in pairs)
    streets = []
    features = json.loads((RESEARCH / "Mazzarino_OSM_strade_chiese_2026.geojson").read_text(encoding="utf-8-sig"))["features"]
    for f in features:
        p = f.get("properties", {})
        if not p.get("highway") or not p.get("name") or f["geometry"]["type"] != "LineString":
            continue
        streets.append({"name": p["name"], "highway": p["highway"], "oneway": p.get("oneway") == "yes",
                        "points_cm": [to_world(lon, lat) for lon, lat in f["geometry"]["coordinates"]]})
    out = {"fit_buildings": len(pairs), "fit_error_cm_median": round(err[len(err) // 2], 1), "fit_error_cm_p95": round(err[int(len(err) * 0.95)], 1),
           "streets": streets}
    (RESEARCH / "streets_world.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(out["fit_buildings"], out["fit_error_cm_median"], out["fit_error_cm_p95"], len(streets))


if __name__ == "__main__":
    main()
