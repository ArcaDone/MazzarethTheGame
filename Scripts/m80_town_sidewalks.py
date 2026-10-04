"""Sidewalks along the main streets of the town map (L_M80_Paese), as "Marciapiede (Mazzarino)" actors.

For every road spline wide enough (main roads: primary/secondary/tertiary and the Corso, or any road at
least M80_SW_MIN_ROAD_M wide) a sidewalk is laid on both sides, inside the road edge, with the curb
towards the road. Only inside the built-up area (houses nearby); it is interrupted at crossings, inside the exclusion zones and wherever it would run
into a house. The result is a starting point: every sidewalk is a normal spline actor (folder
Mazzarino80/Marciapiedi) to move, extend, delete or copy by hand; new ones can be dragged in from
Place Actors > "Marciapiede (Mazzarino)". Generated sidewalks (tag M80AutoSidewalk) are replaced on
every run, hand-made ones are kept.
Env: M80_SW_MAP, M80_SW_WIDTH_CM (150), M80_SW_MIN_ROAD_M (7), M80_SW_TYPES.
"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_SW_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
WIDTH = float(os.environ.get("M80_SW_WIDTH_CM", "150"))
MIN_ROAD = float(os.environ.get("M80_SW_MIN_ROAD_M", "7"))
TYPES = set(os.environ.get("M80_SW_TYPES", "primary,secondary,tertiary").split(","))
OUT = ROOT / "Saved/Mazzarino80/sidewalks_report.json"
FOLDER = "Mazzarino80/Marciapiedi"
TAG = "M80AutoSidewalk"
STEP = 100.0
SLAB_MAT = "/Game/Mazzarino80/Kit/Sidewalk/M_M80_Marciapiede"
MEL = unreal.MaterialEditingLibrary
TILES = {"Color": "/Game/Migrated/floor_tiles_09_diff_4k", "Normal": "/Game/Migrated/floor_tiles_09_nor_gl_4k",
         "Rough": "/Game/Migrated/floor_tiles_09_rough_4k"}


def slab_material():
    """Tiles of the hand-made "Marciapiede" material, mapped in world space so they never stretch."""
    if unreal.EditorAssetLibrary.does_asset_exist(SLAB_MAT):
        return unreal.load_asset(SLAB_MAT)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_M80_Marciapiede", SLAB_MAT.rsplit("/", 1)[0], unreal.Material, unreal.MaterialFactoryNew())

    def node(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e
    wp = node(unreal.MaterialExpressionWorldPosition, -1000, 0)
    xy = node(unreal.MaterialExpressionComponentMask, -850, 0, r=True, g=True)
    MEL.connect_material_expressions(wp, "", xy, "")
    tile = node(unreal.MaterialExpressionScalarParameter, -850, 120, parameter_name="TileCm", default_value=160.0)
    uv = node(unreal.MaterialExpressionDivide, -700, 0)
    MEL.connect_material_expressions(xy, "", uv, "A")
    MEL.connect_material_expressions(tile, "", uv, "B")
    out = {}
    for i, (k, path) in enumerate(TILES.items()):
        t = unreal.load_asset(path)
        st = unreal.MaterialSamplerType
        sampler = st.SAMPLERTYPE_NORMAL if k == "Normal" else (st.SAMPLERTYPE_COLOR if t.get_editor_property("srgb") else st.SAMPLERTYPE_LINEAR_COLOR)
        e = node(unreal.MaterialExpressionTextureSampleParameter2D, -450, -300 + i * 260, parameter_name=k, texture=t, sampler_type=sampler)
        MEL.connect_material_expressions(uv, "", e, "UVs")
        out[k] = e
    tint = node(unreal.MaterialExpressionVectorParameter, -450, 500, parameter_name="Tint", default_value=unreal.LinearColor(0.78, 0.72, 0.64, 1))
    col = node(unreal.MaterialExpressionMultiply, -200, -250)
    MEL.connect_material_expressions(out["Color"], "RGB", col, "A")
    MEL.connect_material_expressions(tint, "", col, "B")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(out["Normal"], "RGB", unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(out["Rough"], "R", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m
CELL = 2000.0


def contains(poly, p):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[j]
        if (yi > p[1]) != (yj > p[1]) and p[0] < (xj - xi) * (p[1] - yi) / ((yj - yi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


class Grid:
    def __init__(self):
        self.cells = defaultdict(list)

    def add_box(self, x0, y0, x1, y1, item):
        for i in range(int(math.floor(x0 / CELL)), int(math.floor(x1 / CELL)) + 1):
            for j in range(int(math.floor(y0 / CELL)), int(math.floor(y1 / CELL)) + 1):
                self.cells[(i, j)].append(item)

    def near(self, p):
        return self.cells.get((int(math.floor(p[0] / CELL)), int(math.floor(p[1] / CELL))), [])


def sample(spline):
    length = spline.get_spline_length()
    n = max(1, int(math.ceil(length / STEP)))
    out = []
    for k in range(n + 1):
        d = length * k / n
        p = spline.get_location_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
        t = spline.get_direction_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
        l = math.hypot(t.x, t.y) or 1.0
        out.append(((p.x, p.y, p.z), (-t.y / l, t.x / l)))
    return out


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected {} open".format(MAP))
    yield 30
    slab_mat = slab_material()
    slab_mesh = unreal.load_asset("/Engine/BasicShapes/Cube")
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    for a in actors:
        if isinstance(a, unreal.M80Sidewalk) and a.actor_has_tag(TAG):
            a.destroy_actor()
    roads = []
    seg_grid = Grid()
    for r in actors:
        if r.get_class().get_name() != "MazzarinoRoadSpline":
            continue
        sp = r.get_component_by_class(unreal.SplineComponent)
        pts = sample(sp)
        road = {"actor": r, "half": float(r.get_editor_property("width_meters")) * 50.0, "kind": str(r.get_editor_property("osm_highway")) or str(r.get_folder_path()).split("/")[-1],
                "name": str(r.get_editor_property("road_name")) or r.get_actor_label(), "pts": pts, "folder": str(r.get_folder_path())}
        roads.append(road)
        for k in range(len(pts) - 1):
            a, b = pts[k][0], pts[k + 1][0]
            reach = road["half"] + WIDTH + 100
            seg_grid.add_box(min(a[0], b[0]) - reach, min(a[1], b[1]) - reach, max(a[0], b[0]) + reach, max(a[1], b[1]) + reach, (id(road), a, b, road["half"]))
    house_grid = Grid()
    for h in actors:
        if isinstance(h, unreal.M80House):  # excluded ones too: their lot may hold a hand-made building
            poly = [(q.x, q.y) for q in h.get_footprint_world2d()]
            if len(poly) >= 3:
                xs, ys = [p[0] for p in poly], [p[1] for p in poly]
                house_grid.add_box(min(xs), min(ys), max(xs), max(ys), poly)
    zones = [[(q.x, q.y) for q in z.get_outline_world2d()] for z in actors if isinstance(z, unreal.M80ExclusionZone) and z.get_editor_property("enabled")]

    def in_town(q):
        """Houses within about 20-40 m: no sidewalks along the country roads."""
        i, j = int(math.floor(q[0] / CELL)), int(math.floor(q[1] / CELL))
        return any(house_grid.cells.get((i + di, j + dj)) for di in (-1, 0, 1) for dj in (-1, 0, 1))

    def free(q, own):
        if not in_town(q):
            return False
        for rid, a, b, half in seg_grid.near(q):
            if rid != own and seg_dist(q, a, b) < half + WIDTH / 2 + 60:
                return False
        if any(contains(poly, q) for poly in house_grid.near(q)):
            return False
        return not any(contains(z, q) for z in zones)

    report = {"sidewalks": 0, "length_m": 0, "streets": {}}
    for road in roads:
        main = road["kind"] in TYPES or "Corso" in road["folder"]
        if not main and road["half"] * 2 < MIN_ROAD * 100:
            continue
        if road["half"] * 2 < WIDTH * 2 + 250:
            continue  # too narrow for two sidewalks and a lane
        offset = road["half"] - WIDTH / 2
        for side in (1, -1):
            run_pts = []
            runs = []
            for (p, r) in road["pts"]:
                q = (p[0] + r[0] * offset * side, p[1] + r[1] * offset * side, p[2])
                if free(q, id(road)):
                    run_pts.append(q)
                else:
                    if len(run_pts) * STEP >= 400:
                        runs.append(run_pts)
                    run_pts = []
            if len(run_pts) * STEP >= 400:
                runs.append(run_pts)
            for pts in runs:
                pts = pts[::2] if len(pts) > 4 else pts
                sw = eas.spawn_actor_from_class(unreal.M80Sidewalk, unreal.Vector(*pts[0]))
                sw.set_actor_label("Marciapiede_{}_{}".format(road["name"].replace(" ", "_"), report["sidewalks"]))
                sw.set_folder_path(FOLDER)
                sw.tags = [unreal.Name(TAG), unreal.Name("M80IgnoreGround")]
                sw.set_editor_property("width_cm", WIDTH)
                sw.set_editor_property("slab_mesh", slab_mesh)
                sw.set_editor_property("slab_material", slab_mat)
                # The road centre is on the left of a right-hand sidewalk walking the same way.
                sw.set_editor_property("curb_side", unreal.M80CurbSide.LEFT if side == 1 else unreal.M80CurbSide.RIGHT)
                path = sw.get_editor_property("path")
                path.set_spline_points([unreal.Vector(*q) for q in pts], unreal.SplineCoordinateSpace.WORLD, True)
                sw.rebuild()
                report["sidewalks"] += 1
                length = len(pts) * STEP * 2
                report["length_m"] += round(length / 100)
                report["streets"][road["name"]] = report["streets"].get(road["name"], 0) + round(length / 100)
        yield 1
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
