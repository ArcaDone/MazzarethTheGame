"""Beauty shots of the town (houses V3, step 12): golden-hour light, warm grading, real street views.

Cameras follow the named OSM streets (Research/Mazzarino80/streets_world.json) where there are
houses: eye-level views along the street, a few from a first-floor balcony and some over the roofs.
The light and post-process changes are not saved. Env: M80_PHOTOS_MAP (default L_M80_Paese),
M80_PHOTOS_STREETS (comma separated names), M80_PHOTOS_MAX (default 14), M80_PHOTOS_SUN_PITCH (-11).
Output: Saved/Mazzarino80/Foto/<n>_<street>.png at 2560x1440.
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_PHOTOS_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
OUT = ROOT / "Saved/Mazzarino80/Foto"
STREETS = os.environ.get("M80_PHOTOS_STREETS", "Corso Vittorio Emanuele Secondo,Via Roma,Piazza Giuseppe Artale,Via Principe di Butera,"
                         "Via Concezione,Via Santa Lucia,Via Carini,Via San Giuseppe,Via Archimede,Via Bisenti").split(",")
MAX = int(os.environ.get("M80_PHOTOS_MAX", "16"))
SUN_PITCH = float(os.environ.get("M80_PHOTOS_SUN_PITCH", "-30"))
PREFIX = os.environ.get("M80_PHOTOS_PREFIX", "")


def look_at(eye, target):
    d = [t - e for t, e in zip(target, eye)]
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return unreal.Vector(*eye), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)


def trace_z(world, x, y, guess):
    result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, guess + 50000), unreal.Vector(x, y, guess - 50000),
                                                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    hit = result[1] if isinstance(result, tuple) else result
    f = hit.to_tuple() if hit else None
    return (f[5].z, f[0]) if f and f[0] else (guess, False)


def free_ground(world, x, y, guess, houses):
    """Ground under (x, y) ignoring houses; None when the point is inside a house."""
    result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, guess + 50000), unreal.Vector(x, y, guess - 50000),
                                                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
    hit = result[1] if isinstance(result, tuple) else result
    f = hit.to_tuple() if hit else None
    if not f or not f[0]:
        return None
    actor = f[9] if len(f) > 9 else None
    if actor and isinstance(actor, unreal.M80House):
        return None
    return f[5].z


def golden_hour(world):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in actors.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight):
            r = a.get_actor_rotation()
            a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=SUN_PITCH, yaw=r.yaw), False)
            comp = a.get_component_by_class(unreal.DirectionalLightComponent)
            comp.set_light_color(unreal.LinearColor(1.0, 0.86, 0.68, 1))
            comp.set_intensity(max(comp.intensity, 7.0))
    # Fill light for the narrow streets: a real-time sky light, and a light warm haze.
    if not [a for a in actors.get_all_level_actors() if isinstance(a, unreal.SkyLight)]:
        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 20000))
        sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(1.5)
    if not [a for a in actors.get_all_level_actors() if isinstance(a, unreal.ExponentialHeightFog)]:
        fog = actors.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 15000))
        fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
        fc.set_fog_density(0.012)
        fc.set_fog_inscattering_color(unreal.LinearColor(0.75, 0.62, 0.48, 1))
    ppv = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("priority", 100.0)
    s = ppv.get_editor_property("settings")
    for key, value in (("bloom_intensity", 0.7), ("vignette_intensity", 0.35), ("film_grain_intensity", 0.08),
                       ("color_saturation", unreal.Vector4(1.08, 1.06, 1.0, 1.0)), ("color_contrast", unreal.Vector4(1.06, 1.06, 1.06, 1.0)),
                       ("color_gain", unreal.Vector4(1.04, 1.0, 0.94, 1.0)), ("auto_exposure_bias", 0.5),
                       ("scene_fringe_intensity", 0.6), ("depth_of_field_focal_distance", 0.0)):
        try:
            s.set_editor_property("override_" + key, True)
            s.set_editor_property(key, value)
        except Exception:  # noqa: BLE001 - optional settings differ between versions
            pass
    ppv.set_editor_property("settings", s)
    return ppv


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    centres = [(h.get_actor_location().x, h.get_actor_location().y) for h in houses]
    streets = json.loads((ROOT / "Research/Mazzarino80/streets_world.json").read_text(encoding="utf-8"))["streets"]
    ppv = golden_hour(world)
    capture = m80_seq.ViewCapture(2560, 1440, 62.0)
    yield 900  # Lumen, distance fields and shaders after the light change
    views = []
    for name in STREETS:
        for s in (s for s in streets if s["name"] == name):
            pts = s["points_cm"]
            for frac in (0.3, 0.7):
                k = max(0, min(len(pts) - 2, int(frac * (len(pts) - 1))))
                a, b = pts[k], pts[k + 1]
                near = sum(1 for c in centres if math.hypot(c[0] - a[0], c[1] - a[1]) < 2500)
                if near < 4:
                    continue
                views.append((name, a, b))
            break
    shots = 0
    for idx, (name, a, b) in enumerate(views):
        if shots >= MAX:
            break
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        dx, dy = dx / n, dy / n
        gz = free_ground(world, a[0], a[1], house_z(houses, a), houses)
        if gz is None:
            continue
        kind = idx % 3
        if kind == 2:
            # Over the roofs, looking down the street.
            eye = (a[0] - dx * 600, a[1] - dy * 600, gz + 1800)
            target = (a[0] + dx * 3000, a[1] + dy * 3000, gz + 200)
        elif kind == 1:
            # From a first-floor balcony on one side.
            eye = (a[0] - dy * 250, a[1] + dx * 250, gz + 520)
            target = (a[0] + dx * 2500 + dy * 150, a[1] + dy * 2500 - dx * 150, gz + 380)
        else:
            eye = (a[0] - dy * 120, a[1] + dx * 120, gz + 165)
            target = (a[0] + dx * 2500, a[1] + dy * 2500, gz + 420)
        loc, rot = look_at(eye, target)
        slug = "".join(c if c.isalnum() else "_" for c in name)
        out = OUT / "{}{:02d}_{}.png".format(PREFIX, shots + 1, slug)
        capture.capture(loc, rot, out)
        yield 40
        capture.capture(loc, rot, out)
        yield 3
        shots += 1
    # Three-quarter views of single houses: facades always fill the frame.
    for k, house in enumerate(houses[::max(1, len(houses) // 10)]):
        if shots >= MAX + 10:
            break
        poly = [(q.x, q.y) for q in house.get_footprint_world2d()]
        i = house.get_editor_property("resolved_front_edge") % len(poly)
        a, b = poly[i], poly[(i + 1) % len(poly)]
        n = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        ux, uy = (b[0] - a[0]) / n, (b[1] - a[1]) / n
        nx, ny = uy, -ux
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        side = 1 if k % 2 else -1
        gz = free_ground(world, mx + nx * 250, my + ny * 250, house.get_actor_location().z, houses)
        if gz is None:
            continue
        dirx, diry = nx * 0.78 + ux * 0.62 * side, ny * 0.78 + uy * 0.62 * side
        # Stop the camera before the houses across the street.
        start = unreal.Vector(mx + nx * 60, my + ny * 60, gz + 230)
        end = unreal.Vector(mx + dirx * 1100, my + diry * 1100, gz + 230)
        hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                     unreal.DrawDebugTrace.NONE, True)
        hit = hit[1] if isinstance(hit, tuple) else hit
        f = hit.to_tuple() if hit else None
        dist = f[3] - 60 if f and f[0] else 1100
        if dist < 350:
            continue
        ex, ey = mx + dirx * dist, my + diry * dist
        loc, rot = look_at((ex, ey, gz + 230), (mx, my, gz + 420))
        out = OUT / "{}{:02d}_casa_{}.png".format(PREFIX, shots + 1, house.get_editor_property("lot_id"))
        capture.capture(loc, rot, out)
        yield 40
        capture.capture(loc, rot, out)
        yield 3
        shots += 1
    capture.destroy()
    ppv.destroy_actor()


def house_z(houses, p):
    best = min(houses, key=lambda h: math.hypot(h.get_actor_location().x - p[0], h.get_actor_location().y - p[1]))
    return best.get_actor_location().z


m80_seq.Sequencer(run(), log_file=str(OUT / "error.txt"))
