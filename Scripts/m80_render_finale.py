"""Overview renders of everything in the town that is not a procedural house, under a temporary daylight (nothing
saved): the skyline of the whole town from the air; for each church, Palazzo Bartoli, the square and the other
hand-made buildings a view from the air, two from the street at eye height and one from close by looking up; the
models not placed yet (Poste with its mast, bank, hospital, phone booth) away from the houses, from the air and
at eye height.
Street views stand on the town's road splines (Saved/Mazzarino80/Chiese/Siti/strade.json) and are kept only if a
trace finds street under the feet (not a roof), open sky over the head (not inside a house or under a balcony) and
most of the building in sight; the editor viewport goes to each view first so Nanite streams it in.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_render_finale.py -ForceLit -TimeoutMinutes 90
Out: Saved/Mazzarino80/Render/<Subject>_<view>.png, viste.json
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
OUT = ROOT / "Saved/Mazzarino80/Render"
ROADS = ROOT / "Saved/Mazzarino80/Chiese/Siti/strade.json"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
W, H = 1920, 1080
EYE = 170.0
WAIT = 200
# Subject -> actor label prefixes (a church is its walls and its details).
SUBJECTS = {k: ["Chiesa_" + k] for k in ("Immacolata", "Lacrima", "SantaLucia", "SpiritoSanto", "SantIgnazio", "Olmo", "SanGiuseppe")}
SUBJECTS.update({"PalazzoBartoli": ["Bartoli_"], "Matrice": ["M80_Recuperato_Matrice"], "Comune": ["M80_Recuperato_ComuneCompleto"],
                 "SanDomenico": ["M80_Recuperato_A_SanDomenico"], "ScuolaMatrice": ["ScuolaMatrice"], "Castello": ["CastelCompleted"],
                 "Madonna": ["A_Madonna"], "Salesiane": ["A_Salesiane"], "Liardo": ["A_Liardo"], "Agip": ["A_Agip"],
                 "ZzaRita": ["A_ZzaRita"], "Neoclassica_1": ["NeoClassic_Casa_1249054471"], "Neoclassica_2": ["NeoClassic_Casa_1249082258"]})
# Things a trace may pass through: wires, lamps, signs, posters, the sky dome.
THIN = ("Lampione", "Cartello", "Targa", "Manifesto", "M80_FiliStrada", "Orizzonte", "Atmosfera")
GROUND = ("Landscape", "LandscapeStreamingProxy", "M80Road", "M80Sidewalk", "M80Stairs", "MazzarinoRoadSpline")
SPOT = unreal.Vector(-300000, -300000, 60000)
UNPLACED = {"Poste": [("/Game/Mazzarino80/Buildings/Poste/SM_M80_Poste", (0, 0, 0)),
                      ("/Game/Mazzarino80/Buildings/Poste/SM_M80_Poste_Antenna", (-1864.1, -1911.6, 16.5))],
            "Banca": [("/Game/Mazzarino80/Buildings/Banca/SM_M80_Banca", (0, 0, 0))],
            "Ospedale": [("/Game/Mazzarino80/Buildings/Ospedale/SM_M80_Ospedale", (0, 0, 0))],
            "Cabina": [("/Game/Mazzarino/CabinaSIP/Cabina/SK_CS_Cabina_SIP", (0, 0, 0))]}


def label(a):
    return a.get_actor_label() if a else ""


def cls(a):
    return a.get_class().get_name() if a else ""


def trace(world, a, b, ignore):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                               unreal.DrawDebugTrace.NONE, True)
    if not h:
        return None
    t = h.to_tuple()
    return (t[4], t[9]) if t[0] else None


def first_solid(world, a, b):
    """First hit along a->b that is not a thin thing (lamps, signs, wires)."""
    ignore = []
    for _ in range(12):
        hit = trace(world, a, b, ignore)
        if not hit:
            return None
        # Houses switched off for a hand-made building keep their actor: they are not there.
        if hit[1] and (label(hit[1]).startswith(THIN) or cls(hit[1]) == "M80House" and hit[1].get_editor_property("disabled")):
            ignore.append(hit[1])
            continue
        return hit
    return None


def owned(actor, prefixes):
    return label(actor).startswith(tuple(prefixes))


def street_eye(world, x, y, top, prefixes):
    """Eye height over (x, y) if it stands on a street under open sky, else None."""
    hit = first_solid(world, unreal.Vector(x, y, top), unreal.Vector(x, y, top - 60000))
    if not hit or cls(hit[1]) not in GROUND and not label(hit[1]).startswith(("3_Lastra", "Marciapiede", "5_Muretto")):
        return None
    eye = unreal.Vector(x, y, hit[0].z + EYE)
    if first_solid(world, eye, eye + unreal.Vector(0, 0, 3000)):
        return None
    return eye


def seen(world, eye, lo, hi, prefixes):
    """Share of 12 points on the building's box (its side towards the eye, three heights) the eye sees."""
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    n = ok = 0
    for fz in (0.25, 0.55, 0.85):
        for f in (-0.35, -0.12, 0.12, 0.35):
            dx, dy = eye.x - cx, eye.y - cy
            d = math.hypot(dx, dy) or 1
            ux, uy = dx / d, dy / d
            # On the side facing the eye, spread across it.
            px = cx + ux * (hi.x - lo.x) * 0.45 - uy * (hi.x - lo.x) * f * 2
            py = cy + uy * (hi.y - lo.y) * 0.45 + ux * (hi.y - lo.y) * f * 2
            p = unreal.Vector(px, py, lo.z + (hi.z - lo.z) * fz)
            hit = first_solid(world, eye, p)
            n += 1
            if not hit or owned(hit[1], prefixes) or (hit[0] - p).length() < 150:
                ok += 1
    return ok / float(n)


def box_dist(x, y, lo, hi):
    return math.hypot(max(lo.x - x, 0, x - hi.x), max(lo.y - y, 0, y - hi.y))


def daylight(at):
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, at + unreal.Vector(0, 0, 30000))
    sun.set_actor_rotation(unreal.Rotator(pitch=-40.0, yaw=-115.0, roll=0.0), False)
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("atmosphere_sun_light", True)
    c.set_intensity(7.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, at + unreal.Vector(0, 0, 20000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight) and a != sun:
            a.get_component_by_class(unreal.DirectionalLightComponent).set_visibility(False)
    return [sun, sky]


def shoot(name, eye, target, fov, log):
    rot = unreal.MathLibrary.find_look_at_rotation(eye, target)
    m80_seq.set_view(eye, rot)
    yield WAIT
    cap = m80_seq.ViewCapture(W, H, fov)
    cap.capture(eye, rot, OUT / ("%s.png" % name))
    cap.destroy()
    log[name] = {"eye": [round(eye.x), round(eye.y), round(eye.z)], "target": [round(target.x), round(target.y), round(target.z)], "fov": fov}
    yield 3


def street_views(world, key, lo, hi, prefixes, roads):
    """Best two street views (apart by 60 degrees or more) and a close one looking up."""
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    height = hi.z - lo.z
    top = hi.z + 3000
    far, close = [], []
    # Besides the road splines (lanes and squares are often not on them), a ring of points around the box.
    hx, hy = (hi.x - lo.x) / 2, (hi.y - lo.y) / 2
    ring = [(cx + math.cos(a) * (abs(math.cos(a)) * hx + abs(math.sin(a)) * hy + d), cy + math.sin(a) * (abs(math.cos(a)) * hx + abs(math.sin(a)) * hy + d))
            for d in (500, 900, 1400, 2100, 3000) for a in (math.radians(k * 15) for k in range(24))]
    for x, y in list(roads) + ring:
        d = box_dist(x, y, lo, hi)
        if 300 <= d <= max(4500, 1.6 * height):
            (close if d <= 1800 else far).append((d, x, y))
    found = []
    for group in (far, close):
        group.sort()
        step = max(1, len(group) // 60)
        for d, x, y in group[::step]:
            eye = street_eye(world, x, y, top, prefixes)
            if not eye:
                continue
            s = seen(world, eye, lo, hi, prefixes)
            if s >= 0.4:
                found.append((s, d, eye))
    views = []
    best = sorted(found, key=lambda v: (-round(v[0], 1), abs(v[1] - max(1500, 1.1 * height))))
    for s, d, eye in best:
        ang = math.atan2(eye.y - cy, eye.x - cx)
        if all(abs((ang - a + math.pi) % (2 * math.pi) - math.pi) > math.radians(60) for a, _ in views):
            views.append((ang, eye))
        if len(views) == 2:
            break
    up = min((v for v in found if v[1] <= 1800), key=lambda v: v[1], default=None)
    return [e for _, e in views], (up[2] if up else None), len(found)


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    log = {}
    roads = [tuple(p) for r in json.loads(ROADS.read_text(encoding="utf-8")) for p in r["points"]]
    only = [k for k in os.environ.get("M80_RENDER", "").split(",") if k]
    want = lambda k: not only or k in only  # noqa: E731
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    # Loading the whole town at once runs the editor out of memory: the landscape stays, each subject loads its
    # surroundings and lets them go afterwards; the skyline shows the HLOD shells of what is not loaded.
    descs = m80_seq.actor_descs()
    land = m80_seq.actor_descs("LandscapeStreamingProxy")
    m80_seq.load(land)
    yield 300
    m80_seq.console("r.TextureStreaming 0")
    world = m80_seq.editor_world()
    actors = EAS.get_all_level_actors()
    lights = daylight(unreal.Vector(70000, 0, 0))
    yield 120

    # The whole town from the air: from the four sides and from the skyline camera of the map.
    houses = [m80_seq.desc_center(d) for d in descs if m80_seq.desc_class_is(d, "M80House")]
    xs, ys, zs = sorted(c.x for c in houses), sorted(c.y for c in houses), sorted(c.z for c in houses)
    mid = unreal.Vector(xs[len(xs) // 2], ys[len(ys) // 2], zs[len(zs) // 2])
    span = max(xs[int(len(xs) * 0.95)] - xs[int(len(xs) * 0.05)], ys[int(len(ys) * 0.95)] - ys[int(len(ys) * 0.05)])
    for side, ang in (("sud", -90), ("est", 0), ("nord", 90), ("ovest", 180)) if want("Skyline") else ():
        a = math.radians(ang)
        eye = mid + unreal.Vector(math.cos(a) * span * 0.85, math.sin(a) * span * 0.85, span * 0.32)
        yield from shoot("Skyline_" + side, eye, mid + unreal.Vector(0, 0, -span * 0.03), 62, log)
    if want("Skyline"):
        yield from shoot("Skyline_alto", mid + unreal.Vector(-span * 0.35, -span * 0.45, span * 0.9), mid, 60, log)

    # Each hand-made building: from the air, two street views, one looking up.
    boxes = {}
    for key, prefixes in SUBJECTS.items():
        if not want(key) and not (want("Piazza") and key in ("Matrice", "PalazzoBartoli")):
            continue
        own = [d for d in descs if str(d.get_editor_property("label")).startswith(tuple(prefixes))]
        if not own:
            log[key] = "not in the map"
            continue
        cs = [m80_seq.desc_center(d) for d in own]
        c0 = unreal.Vector(sum(c.x for c in cs) / len(cs), sum(c.y for c in cs) / len(cs), 0)
        around = m80_seq.near(descs, c0.x, c0.y, 9000 + max(d.get_editor_property("bounds").max.x - d.get_editor_property("bounds").min.x for d in own))
        around = [d for d in around if not m80_seq.desc_class_is(d, "WorldPartitionHLOD", "LandscapeStreamingProxy")]
        m80_seq.load(around)
        yield 240
        actors = EAS.get_all_level_actors()
        mine = [a for a in actors if owned(a, prefixes)]
        lo = unreal.Vector(1e9, 1e9, 1e9)
        hi = unreal.Vector(-1e9, -1e9, -1e9)
        for a in mine:
            o, e = a.get_actor_bounds(False)
            lo = unreal.Vector(min(lo.x, o.x - e.x), min(lo.y, o.y - e.y), min(lo.z, o.z - e.z))
            hi = unreal.Vector(max(hi.x, o.x + e.x), max(hi.y, o.y + e.y), max(hi.z, o.z + e.z))
        boxes[key] = (lo, hi)
        c = (lo + hi) * 0.5
        R = max(hi.x - lo.x, hi.y - lo.y) * 0.5
        street, up, n = street_views(world, key, lo, hi, prefixes, roads)
        log[key + "_candidati"] = n
        side = (street[0] - c) if street else unreal.Vector(1, -1, 0)
        side.z = 0
        side = side.normal()
        eye = c + side * (1.6 * R + 1500) + unreal.Vector(0, 0, 1.1 * R + 1800)
        yield from shoot(key + "_aereo", eye, c, 60, log)
        for i, eye in enumerate(street):
            target = unreal.Vector(c.x, c.y, lo.z + (hi.z - lo.z) * 0.42)
            yield from shoot("%s_strada_%d" % (key, i + 1), eye, target, 72, log)
        if up:
            target = unreal.Vector(c.x, c.y, hi.z - (hi.z - lo.z) * 0.1)
            yield from shoot(key + "_dal_basso", up, target, 84, log)
        if key in ("Matrice", "PalazzoBartoli"):
            continue  # the square between them is shot further on, with both loaded
        m80_seq.unload(around)
        unreal.SystemLibrary.collect_garbage()
        yield 60

    # The square between the Matrice and Palazzo Bartoli, at eye height from its middle.
    if want("Piazza") and "Matrice" in boxes and "PalazzoBartoli" in boxes:
        # The subjects shot after them let their surroundings go: the square's are loaded again.
        mc = (boxes["Matrice"][0] + boxes["Matrice"][1]) * 0.5
        m80_seq.load([d for d in m80_seq.near(descs, mc.x, mc.y, 14000) if not m80_seq.desc_class_is(d, "WorldPartitionHLOD", "LandscapeStreamingProxy")])
        yield 300
        actors = EAS.get_all_level_actors()
        m = (boxes["Matrice"][0] + boxes["Matrice"][1]) * 0.5
        piazza = next((a for a in actors if label(a) == "Bartoli_D_Piazza"), None)
        b = piazza.get_actor_bounds(False)[0] if piazza else (boxes["PalazzoBartoli"][0] + boxes["PalazzoBartoli"][1]) * 0.5
        best = None
        pm = (m + b) * 0.5
        for r in (0, 300, 600, 1000, 1500):
            for k in range(12 if r else 1):
                a = math.radians(k * 30)
                eye = street_eye(world, pm.x + math.cos(a) * r, pm.y + math.sin(a) * r, max(m.z, b.z) + 5000, [])
                if eye:
                    best = eye
                    break
            if best:
                break
        if best:
            yield from shoot("Piazza_verso_Matrice", best, unreal.Vector(m.x, m.y, best.z + 600), 78, log)
            yield from shoot("Piazza_verso_Bartoli", best, unreal.Vector(b.x, b.y, best.z + 500), 78, log)
            for k in ("Comune", "ScuolaMatrice"):
                if k in boxes:
                    t = (boxes[k][0] + boxes[k][1]) * 0.5
                    yield from shoot("Piazza_verso_" + k, best, unreal.Vector(t.x, t.y, best.z + 500), 78, log)
        pm = (m + b) * 0.5
        yield from shoot("Piazza_aereo", pm + unreal.Vector(-3500, -4200, 4200), pm, 65, log)

    # The models not placed yet, one at a time away from the houses, on a temporary floor.
    for a in lights:
        a.destroy_actor()
    lights = daylight(SPOT)
    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), SPOT - unreal.Vector(0, 0, 5))
    floor.set_actor_scale3d(unreal.Vector(600, 600, 1))
    yield 60
    for key, parts in UNPLACED.items():
        if not want(key):
            continue
        spawned = []
        for path, off in parts:
            asset = unreal.load_asset(path)
            if asset:
                spawned.append(EAS.spawn_actor_from_object(asset, SPOT + unreal.Vector(*off)))
        if not spawned:
            continue
        yield 120
        lo = unreal.Vector(1e9, 1e9, 1e9)
        hi = unreal.Vector(-1e9, -1e9, -1e9)
        for sp in spawned:
            o, e = sp.get_actor_bounds(False)
            lo = unreal.Vector(min(lo.x, o.x - e.x), min(lo.y, o.y - e.y), min(lo.z, o.z - e.z))
            hi = unreal.Vector(max(hi.x, o.x + e.x), max(hi.y, o.y + e.y), max(hi.z, o.z + e.z))
        # Framed on the main piece (the Poste building, not its mast 27 m away).
        o, e = spawned[0].get_actor_bounds(False)
        lo, hi = o - e, o + e
        c = (lo + hi) * 0.5
        R = max(hi.x - lo.x, hi.y - lo.y) * 0.5
        tall = max(hi.z - lo.z, 250)
        yield from shoot(key + "_aereo", c + unreal.Vector(R * 1.3 + 800, -R * 1.1 - 800, R * 0.9 + 1200), c, 60, log)
        d = R + max(R * 0.6, 700)
        for i, ang in enumerate((-60, 120)):
            a = math.radians(ang)
            eye = unreal.Vector(c.x + math.cos(a) * d, c.y + math.sin(a) * d, SPOT.z + EYE)
            yield from shoot("%s_strada_%d" % (key, i + 1), eye, unreal.Vector(c.x, c.y, SPOT.z + tall * 0.4), 72, log)
        a = math.radians(-30)
        dc = R + max(R * 0.15, 300)
        eye = unreal.Vector(c.x + math.cos(a) * dc, c.y + math.sin(a) * dc, SPOT.z + EYE)
        yield from shoot(key + "_dal_basso", eye, unreal.Vector(c.x, c.y, SPOT.z + tall * 0.95), 84, log)
        for s in spawned:
            s.destroy_actor()
        yield 10
    (OUT / "viste.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
