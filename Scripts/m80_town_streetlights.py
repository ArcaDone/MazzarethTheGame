"""Street lamps of the town (World Partition map L_M80_Paese_WP), with "Lampione (Mazzarino)" actors.

- Wall lamps along every street: every SPACING metres, alternating sides, the facade of the nearest
  house beside the road (traced from the road centre) gets a lamp on its bracket at 4.2 m.
  A few lamps (5%) are broken, as in a real town.
- The old lamp posts of the squares (static meshes whose name says lamp/lampione/lantern/streetlight
  and taller than 3 m) get the cast-iron candelabra in their place; the old actor is hidden (not
  deleted), with "[sostituito]" in its label.
Lamps made by an earlier run (label "Lampione_*") are removed first; hand-placed ones are kept.
The streets are processed in 300 m tiles: only that tile is loaded. Env: M80_LAMP_SPACING (m, 28).
Report: Saved/Mazzarino80/streetlights_report.json.
"""
import json
import math
import os
import random
import re
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_LAMP_MAP", m80_seq.TOWN_MAP)
SPACING = float(os.environ.get("M80_LAMP_SPACING", "28")) * 100.0
MIN_GAP = SPACING * 0.5
HEIGHT = 420.0
REPORT = ROOT / "Saved/Mazzarino80/streetlights_report.json"
OLD_LAMP = re.compile(r"lamp|lampion|lantern|streetlight|street_light|lightpole|light_pole|lampadaire|farol", re.I)
FOLDER = "Lampioni"


def trace(world, start, end, ignore):
    r = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                               unreal.DrawDebugTrace.NONE, True)
    hit = r[1] if isinstance(r, tuple) else r
    f = hit.to_tuple() if hit else None
    return f if f and f[0] else None


def spawn_lamp(eas, location, yaw, kind, label, rng):
    lamp = eas.spawn_actor_from_class(unreal.M80StreetLight, location, unreal.Rotator(0, 0, yaw))
    lamp.set_editor_property("kind", kind)
    lamp.set_editor_property("broken", rng.random() < 0.05)
    lamp.set_actor_label(label)
    lamp.set_folder_path(FOLDER)
    return lamp


def run():
    report = {"spacing_m": SPACING / 100, "wall": 0, "old_posts_replaced": [], "tiles": 0}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 20
    world = m80_seq.editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    rng = random.Random(80)

    # Lamps of an earlier run.
    old = m80_seq.actor_descs("M80StreetLight")
    m80_seq.load(old)
    yield 5
    removed = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80StreetLight):
        if a.get_actor_label().startswith("Lampione_"):
            a.destroy_actor()
            removed += 1
    report["removed_previous"] = removed

    # Old lamp posts of the squares -> candelabra.
    smas = m80_seq.actor_descs("StaticMeshActor")
    m80_seq.load(smas)
    yield 10
    n_pole = 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
        mesh = a.static_mesh_component.get_editor_property("static_mesh")
        if not mesh or not OLD_LAMP.search(mesh.get_name()) or a.get_actor_label().startswith("[sostituito]"):
            continue
        origin, extent = a.get_actor_bounds(False)
        if extent.z * 2 < 300:
            continue
        loc = a.get_actor_location()
        n_pole += 1
        spawn_lamp(eas, unreal.Vector(loc.x, loc.y, origin.z - extent.z), a.get_actor_rotation().yaw,
                   unreal.M80LampKind.POLE, "Lampione_Palo_%d" % n_pole, rng)
        report["old_posts_replaced"].append(a.get_actor_label() + " (" + mesh.get_name() + ")")
        a.set_actor_hidden_in_game(True)
        a.set_actor_enable_collision(False)
        a.set_actor_label("[sostituito] " + a.get_actor_label())
    m80_seq.save_all()
    m80_seq.unload(smas)
    yield 5

    # Wall lamps along the streets, tile by tile.
    roads = m80_seq.actor_descs("MazzarinoRoadSpline")
    houses = m80_seq.actor_descs("M80House")
    ground = m80_seq.actor_descs("LandscapeStreamingProxy")
    placed = []
    n_wall = 0
    for tile in m80_seq.tiles(roads):
        xs = [m80_seq.desc_center(d).x for d in tile]
        ys = [m80_seq.desc_center(d).y for d in tile]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        reach = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 30000
        extra = m80_seq.near(houses, cx, cy, reach) + m80_seq.near(ground, cx, cy, reach + 60000)
        m80_seq.load(tile + extra)
        yield 5
        report["tiles"] += 1
        tile_roads = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.MazzarinoRoadSpline))
        for road in tile_roads:
            spline = road.get_editor_property("spline")
            length = spline.get_spline_length()
            half = road.get_editor_property("width_meters") * 50.0
            side = 1 if rng.random() < 0.5 else -1
            d = SPACING * 0.4
            while d < length:
                p = spline.get_location_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
                t = spline.get_direction_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
                d += SPACING
                side = -side
                g = trace(world, unreal.Vector(p.x, p.y, p.z + 3000), unreal.Vector(p.x, p.y, p.z - 3000), tile_roads)
                gz = g[5].z if g else p.z
                nx, ny = -t.y * side, t.x * side
                start = unreal.Vector(p.x, p.y, gz + 380)
                end = unreal.Vector(p.x + nx * (half + 900), p.y + ny * (half + 900), gz + 380)
                h = trace(world, start, end, tile_roads)
                if not h or not isinstance(h[9], unreal.M80House):
                    continue
                normal = h[7]
                if abs(normal.z) > 0.3 or normal.x * nx + normal.y * ny > -0.5:
                    continue
                at = h[5]
                if any(math.hypot(at.x - q[0], at.y - q[1]) < MIN_GAP for q in placed):
                    continue
                placed.append((at.x, at.y))
                n_wall += 1
                # The lamp's arm points along its local +Y: turn it to the facade normal.
                yaw = math.degrees(math.atan2(-normal.x, normal.y))
                spawn_lamp(eas, unreal.Vector(at.x + normal.x * 2, at.y + normal.y * 2, gz + HEIGHT), yaw,
                           unreal.M80LampKind.WALL, "Lampione_%d" % n_wall, rng)
            yield 1
        m80_seq.save_all()
        m80_seq.unload(tile + extra)
        unreal.SystemLibrary.collect_garbage()
        yield 2
    report["wall"] = n_wall
    report["poles"] = n_pole
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
