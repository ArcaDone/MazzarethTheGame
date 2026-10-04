"""Build an indicative 3D town overview from saved open map and DEM data."""

import json
import math
from pathlib import Path

from PIL import Image


ROOT = Path(r"D:\UE5Projects\GameAnimationSample")
DATA = ROOT / "Research" / "Mazzarino80"
OUT = DATA / "generated"
OUT.mkdir(exist_ok=True)

south, west, north, east = 37.296, 14.204, 37.313, 14.227
anchor_lon, anchor_lat = 14.217436414285714, 37.30538766666667
anchor_x, anchor_y, anchor_z = 823.7388, -40.0640, 171.0
scale = 0.9146386458910881
rotation = math.radians(-8.470194039716004)
metres_lon = 111320 * math.cos(math.radians(anchor_lat))
metres_lat = 111132
dem = Image.open(DATA / "Copernicus_GLO30_N37_E014.tif")


def elevation(lon, lat):
    # Tile pixels are 1/3600 degree; interpolate between the neighbouring samples.
    u = max(1, min(3597, (lon - 14) * 3600 - 0.5))
    v = max(1, min(3597, (38 - lat) * 3600 - 0.5))
    x, y = int(u), int(v)
    a, b = u - x, v - y
    return sum(
        dem.getpixel((x + i, y + j)) * (a if i else 1 - a) * (b if j else 1 - b)
        for i in (0, 1) for j in (0, 1)
    )


anchor_height = elevation(anchor_lon, anchor_lat)


def point(lon, lat, offset=0, drape=False):
    e = (lon - anchor_lon) * metres_lon
    n = (lat - anchor_lat) * metres_lat
    x = (e * math.cos(rotation) + n * math.sin(rotation)) / scale
    y = (-e * math.sin(rotation) + n * math.cos(rotation)) / scale
    z = (terrain_elevation(lon, lat) if drape else elevation(lon, lat)) - anchor_height + offset
    return (x * 100, y * 100, z * 100)


class Obj:
    def __init__(self, name, material):
        self.name = name
        self.material = material
        self.vertices = []
        self.faces = []

    def add(self, coords):
        start = len(self.vertices) + 1
        self.vertices.extend(coords)
        return list(range(start, start + len(coords)))

    def face(self, indices):
        self.faces.append(indices)

    def save(self):
        path = OUT / (self.name + ".obj")
        with path.open("w", encoding="ascii") as f:
            f.write("mtllib Mazzarino80_Overview.mtl\n")
            f.write("o " + self.name + "\nusemtl " + self.material + "\n")
            for x, y, z in self.vertices:
                f.write(f"v {x:.2f} {y:.2f} {z:.2f}\n")
            for face in self.faces:
                f.write("f " + " ".join(str(i) for i in face) + "\n")
        return path


terrain = Obj("M80_Terreno", "M80_Terreno")
nx, ny = 94, 72
grid = [[elevation(west + (east - west) * i / nx,
                   south + (north - south) * j / ny)
         for i in range(nx + 1)] for j in range(ny + 1)]


def terrain_elevation(lon, lat):
    u = max(0, min(nx - 0.000001, (lon - west) / (east - west) * nx))
    v = max(0, min(ny - 0.000001, (lat - south) / (north - south) * ny))
    i, j = int(u), int(v)
    du, dv = u - i, v - j
    a, b = grid[j][i], grid[j][i + 1]
    c, d = grid[j + 1][i], grid[j + 1][i + 1]
    if du >= dv:
        return (1 - du) * a + (du - dv) * b + dv * d
    return (1 - dv) * a + du * d + (dv - du) * c


for j in range(ny + 1):
    lat = south + (north - south) * j / ny
    for i in range(nx + 1):
        lon = west + (east - west) * i / nx
        terrain.add([point(lon, lat)])
for j in range(ny):
    for i in range(nx):
        a = j * (nx + 1) + i + 1
        terrain.face([a, a + 1, a + nx + 2])
        terrain.face([a, a + nx + 2, a + nx + 1])

roads = Obj("M80_Strade", "M80_Strade")
geo = json.loads((DATA / "Mazzarino_OSM_strade_chiese_2026.geojson").read_text(encoding="utf-8-sig"))
widths = {"primary": 8, "secondary": 7, "tertiary": 6, "residential": 5, "unclassified": 4.5,
          "service": 3.5, "pedestrian": 4, "footway": 1.8, "steps": 1.5, "track": 3}
road_count = 0
for feature in geo["features"]:
    if feature["geometry"]["type"] != "LineString":
        continue
    highway = feature.get("properties", {}).get("highway")
    if highway not in widths:
        continue
    line = feature["geometry"]["coordinates"]
    width = widths[highway] * 50  # half width in centimetres
    for a_geo, b_geo in zip(line, line[1:]):
        if not (west <= a_geo[0] <= east and south <= a_geo[1] <= north and
                west <= b_geo[0] <= east and south <= b_geo[1] <= north):
            continue
        ax, ay, az = point(*a_geo, offset=0.8, drape=True)
        bx, by, bz = point(*b_geo, offset=0.8, drape=True)
        length = math.hypot(bx - ax, by - ay)
        if length < 20:
            continue
        px, py = -(by - ay) * width / length, (bx - ax) * width / length
        ids = roads.add([(ax + px, ay + py, az), (ax - px, ay - py, az),
                         (bx - px, by - py, bz), (bx + px, by + py, bz)])
        roads.face(ids)
    road_count += 1


buildings = Obj("M80_Edifici", "M80_Edifici")
osm = json.loads((DATA / "Mazzarino_OSM_edifici_2026.json").read_text(encoding="utf-8-sig"))
building_count = 0
for element in osm["elements"]:
    ring = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
    if len(ring) < 4:
        continue
    if ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3 or not all(west <= lon <= east and south <= lat <= north for lon, lat in ring):
        continue
    tag = element.get("tags", {}).get("building", "yes")
    if tag in ("roof", "shed", "garage"):
        height = 3.2
    elif tag in ("church", "cathedral"):
        height = 13
    else:
        height = 6.5 + (element["id"] % 4) * 1.2
    # A single foundation height prevents walls from following DSM roof noise.
    base = min(point(lon, lat, drape=True)[2] for lon, lat in ring) - 30
    bottom = [(point(lon, lat)[0], point(lon, lat)[1], base) for lon, lat in ring]
    top = [(x, y, base + height * 100) for x, y, _ in bottom]
    b_ids = buildings.add(bottom)
    t_ids = buildings.add(top)
    for k in range(len(ring)):
        nxt = (k + 1) % len(ring)
        buildings.face([b_ids[k], b_ids[nxt], t_ids[nxt], t_ids[k]])
    # Triangle fan is adequate for the distant massing view; detailed roofs come later.
    for k in range(1, len(ring) - 1):
        buildings.face([t_ids[0], t_ids[k], t_ids[k + 1]])
    building_count += 1

(OUT / "Mazzarino80_Overview.mtl").write_text(
    "newmtl M80_Terreno\nKd 0.39 0.49 0.33\n"
    "newmtl M80_Strade\nKd 0.72 0.68 0.58\n"
    "newmtl M80_Edifici\nKd 0.77 0.73 0.65\n", encoding="ascii")
paths = [terrain.save(), roads.save(), buildings.save()]
report = {"bbox": [west, south, east, north], "dem_anchor_m": anchor_height,
          "buildings": building_count, "roads": road_count,
          "vertices": {x.name: len(x.vertices) for x in (terrain, roads, buildings)},
          "faces": {x.name: len(x.faces) for x in (terrain, roads, buildings)},
          "files": [str(p) for p in paths],
          "placement_cm": [anchor_x * 100, anchor_y * 100, anchor_z * 100]}
(OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
