"""Bougainvilleas among the procedural houses of L_M80_Paese_WP: a share of the houses (M80_BGV_QUOTA) gets a plant
rooted at the foot of its main facade, near a corner, where the wall is plain (no door or window recess). Where another house faces it across the street at 2.5-13 m (from its main facade or a side wall), the
plant may (M80_BGV_PASSAGGI) climb its wall and cross the street on a support cable to the facing facade, at least
4.7 m above the highest ground under it (street, both doorsteps), lower than both walls' tops, with nothing in the way;
its free branches never hang below 4 m over the ground. Otherwise it climbs 3-4.8 m (below balconies and the eaves)
and runs along the facade; free branches stop at 2.2 m. Each plant is baked (M80EditorLibrary.BakeBougainvillea:
static mesh with three LODs in Vegetazione/Bouganvillea/Piante, HLOD-ready) and saved alone, so the houses' files are
never rewritten. Houses that already have a plant within 4 m are skipped and plants without their baked mesh (baked
meshes are not in Git) are baked again: the script can be run again, also on another checkout.
Env: M80_BGV_QUOTA (0.05), M80_BGV_PASSAGGI (0.5), M80_BGV_SEED (80), M80_BGV_MAX (no limit),
M80_BGV_CENTRO="x,y,r" (only houses within r cm), M80_BGV_TRIANGOLI (40000 per plant, thinned above), M80_BGV_FOTO=1 (a street photo of each new plant), M80_BGV_PROVA=1
(nothing saved), M80_BGV_SISTEMA=1 (no new plants: the ones there get unique names and are baked again).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bouganvillea_paese.py -ForceLit -TimeoutMinutes 240
Out: Saved/Mazzarino80/Bouganvillea/paese.json (and Paese/<label>.png with M80_BGV_FOTO)
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
OUT = ROOT / "Saved/Mazzarino80/Bouganvillea"
FOLDER = "/Game/Mazzarino80/Vegetazione/Bouganvillea/Piante"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector
QUOTA = float(os.environ.get("M80_BGV_QUOTA", "0.05"))
PASSAGGI = float(os.environ.get("M80_BGV_PASSAGGI", "0.5"))
SEED = int(os.environ.get("M80_BGV_SEED", "80"))
MAX = int(os.environ.get("M80_BGV_MAX", "0") or 0)
CENTRO = os.environ.get("M80_BGV_CENTRO") or None   # "x,y,r" or "fitta" (the densest 100 m of houses, r 80 m)
FOTO = os.environ.get("M80_BGV_FOTO") == "1"
BUDGET = int(os.environ.get("M80_BGV_TRIANGOLI", "40000"))   # full-detail triangles per plant at most
PROVA = os.environ.get("M80_BGV_PROVA") == "1"   # nothing saved
SISTEMA = os.environ.get("M80_BGV_SISTEMA") == "1"   # no new plants: rename and bake again the ones there
C = unreal.M80BougainvilleaColour
COLOURS = [(C.MAGENTA, 0.45), (C.VIOLA, 0.25), (C.ARANCIONE, 0.15), (C.ROSSO, 0.15)]
CROSS_CLEAR = 470.0     # cable height above the highest ground under it (cm)
CROSS_HANG = 400.0      # free branches over the street stop here
WALL_HANG = 220.0       # free branches of a wall plant stop here
GAP = 12.0              # stem off the wall


def gid(g):
    return unreal.GuidLibrary.conv_guid_to_string(g)


def trace(a, b, ignore=()):
    h = unreal.SystemLibrary.line_trace_single(m80_seq.editor_world(), a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True,
                                               list(ignore), unreal.DrawDebugTrace.NONE, True)
    if not h:
        return None
    t = h.to_tuple()
    return (t[4], t[6], t[9]) if t[0] else None   # location, impact normal, actor


def ground(x, y, z_from, ignore=()):
    """Street or doorstep under (x, y); the houses (balconies) in ignore are passed through."""
    h = trace(V(x, y, z_from + 400), V(x, y, z_from - 2500), ignore)
    return h[0].z if h else None


def facade(house, i=None):
    """Edge i of the house footprint (default: its main facade) with its outward normal."""
    fp = house.get_footprint_world2d()
    if len(fp) < 3:
        return None
    if i is None:
        i = max(0, min(house.get_editor_property("resolved_front_edge"), len(fp) - 1))
    a, b = fp[i], fp[(i + 1) % len(fp)]
    ux, uy = b.x - a.x, b.y - a.y
    length = math.hypot(ux, uy)
    if length < 250:
        return None
    ux, uy = ux / length, uy / length
    return {"house": house, "a": (a.x, a.y), "u": (ux, uy), "n": (uy, -ux), "len": length, "z": house.get_actor_location().z}


def wall_at(f, t, z):
    """Hit on the facade f at fraction t and height z, traced from the street: (point, normal) or None."""
    ax, ay = f["a"]
    ux, uy = f["u"]
    nx, ny = f["n"]
    px, py = ax + ux * f["len"] * t, ay + uy * f["len"] * t
    h = trace(V(px + nx * 90, py + ny * 90, z), V(px - nx * 60, py - ny * 60, z))
    if not h or h[2] != f["house"]:
        return None
    return h[0], h[1]


def wall_top(f, t, z0):
    """Height of the facade's top above z0 at fraction t (the wall ends where the trace stops hitting it)."""
    top = None
    z = z0 + 250
    while z < z0 + 2500:
        if not wall_at(f, t, z):
            break
        top = z
        z += 50
    return top


def solid(f, t, g0):
    """True when the facade is a plain wall around fraction t up to 2 m: no door or window recess there."""
    nx, ny = f["n"]
    ax, ay = f["a"]
    depths = []
    for off in (-40.0, 0.0, 40.0):
        tt = t + off / f["len"]
        if tt < 0.02 or tt > 0.98:
            return False
        for z in (100.0, 170.0):
            w = wall_at(f, tt, g0 + z)
            if not w:
                return False
            depths.append((w[0].x - ax) * nx + (w[0].y - ay) * ny)
    # Plinths and corner stones stand out a few cm; a door or a shop window is set back more.
    return max(depths) - min(depths) < 10.0


def pick_site(f, rng, existing):
    """(t, ground, wall hit) near a corner of facade f where the wall is plain (no door or shop window), away from
    other plants; None if there is none."""
    for _ in range(6):
        t = rng.uniform(0.12, 0.35) if rng.random() < 0.5 else rng.uniform(0.65, 0.88)
        ax, ay = f["a"]
        px, py = ax + f["u"][0] * f["len"] * t, ay + f["u"][1] * f["len"] * t
        if any(math.hypot(e.x - px, e.y - py) < 400 for e in existing):
            continue
        g0 = ground(px + f["n"][0] * 60, py + f["n"][1] * 60, f["z"] + 200, [f["house"]])
        if g0 is not None and solid(f, t, g0):
            w = wall_at(f, t, g0 + 150)
            if w:
                return t, g0, w
    return None


def clear(a, b, ignore=()):
    return trace(a, b, ignore) is None


def plan_cross(f, t, g0, w, faces, rng, why):
    """A crossing from facade f (at fraction t, ground g0, wall point w) to a facing wall, or None (why counts the reasons)."""
    wx, wy = w[0].x, w[0].y
    nx, ny = f["n"]
    best = None
    nearest = None
    for f2 in faces:
        if f2["house"] == f["house"]:
            continue
        # Foot of the perpendicular from w on the other facade's line.
        ax, ay = f2["a"]
        ux, uy = f2["u"]
        s = (wx - ax) * ux + (wy - ay) * uy
        if s < 0.06 * f2["len"] or s > 0.94 * f2["len"]:
            continue
        qx, qy = ax + ux * s, ay + uy * s
        d = math.hypot(qx - wx, qy - wy)
        if d < 1:
            continue
        dx, dy = (qx - wx) / d, (qy - wy) / d
        n2x, n2y = f2["n"]
        if nx * dx + ny * dy < 0.6 or -(n2x * dx + n2y * dy) < 0.6:
            continue
        nearest = d if nearest is None else min(nearest, d)
        if d < 250 or d > 1300:
            continue
        if best is None or d < best[0]:
            best = (d, f2, s / f2["len"], (dx, dy))
    if not best:
        why.setdefault("distanze_muro_di_fronte_cm", []).append(round(nearest) if nearest else None)
        why["nessun muro di fronte a 2,5-13 m"] = why.get("nessun muro di fronte a 2,5-13 m", 0) + 1
        return None
    d, f2, t2, (dx, dy) = best
    g2 = ground(f2["a"][0] + f2["u"][0] * f2["len"] * t2 + f2["n"][0] * 60, f2["a"][1] + f2["u"][1] * f2["len"] * t2 + f2["n"][1] * 60, f2["z"] + 200, [f2["house"]])
    gm = ground(wx + dx * d * 0.5, wy + dy * d * 0.5, max(g0, f2["z"]) + 200, [f["house"], f2["house"]])
    if g2 is None or gm is None:
        why["terreno non trovato"] = why.get("terreno non trovato", 0) + 1
        return None
    high = max(g0, g2, gm)
    h = high + CROSS_CLEAR + rng.uniform(0, 60)
    top1, top2 = wall_top(f, t, g0), wall_top(f2, t2, g2)
    if not top1 or not top2 or h > min(top1, top2) - 40:
        why["muri troppo bassi"] = why.get("muri troppo bassi", 0) + 1
        return None
    w2 = wall_at(f2, t2, h)
    if not w2:
        why["muro di fronte non trovato"] = why.get("muro di fronte non trovato", 0) + 1
        return None
    a = V(wx + nx * GAP, wy + ny * GAP, h)
    b = V(w2[0].x + f2["n"][0] * GAP, w2[0].y + f2["n"][1] * GAP, h)
    root = V(wx + nx * GAP, wy + ny * GAP, g0)
    # Nothing across the street at that height, nothing (balconies) on the way up the wall.
    if not clear(a, b) or not clear(root + V(0, 0, 40), a):
        why["ostacolo (balconi, fili)"] = why.get("ostacolo (balconi, fili)", 0) + 1
        return None
    mid = (a + b) * 0.5 - V(0, 0, 12)
    pts = [root, root + V(0, 0, (h - g0) * 0.55), a - V(0, 0, 25), a + V(dx * 40, dy * 40, 0), mid, b - V(dx * 40, dy * 40, 0), b - V(0, 0, 35)]
    return {"points": pts, "clear": high + CROSS_HANG - g0, "wire": True, "width_m": round(d / 100, 1), "height_m": round((h - high) / 100, 2),
            "n": f["n"], "u": (dx, dy)}


def plan_wall(f, t, g0, w, rng):
    wx, wy = w[0].x, w[0].y
    nx, ny = f["n"]
    ux, uy = f["u"]
    top = wall_top(f, t, g0)
    if not top:
        return None
    h = min(top - 60, g0 + rng.uniform(300, 480))
    root = V(wx + nx * GAP, wy + ny * GAP, g0)
    hit = trace(root + V(0, 0, 40), root + V(0, 0, h - g0))
    if hit:
        h = hit[0].z - 35   # under a balcony
    if h - g0 < 200:
        return None
    # Along the facade, towards its middle, as far as nothing is in the way.
    side = 1 if t < 0.5 else -1
    run = min(rng.uniform(100, 280), (0.92 - t if side > 0 else t - 0.08) * f["len"])
    a = root + V(0, 0, h - g0)
    b = a + V(ux * side * run, uy * side * run, 10)
    hit = trace(a, b)
    if hit:
        run = max(0, (hit[0] - a).length() - 30)
        b = a + V(ux * side * run, uy * side * run, 10)
    pts = [root, root + V(ux * side * 6, uy * side * 6, (h - g0) * 0.5), a]
    if run > 60:
        pts += [a + V(ux * side * run * 0.5, uy * side * run * 0.5, 15), b]
    return {"points": pts, "clear": WALL_HANG, "wire": False, "n": f["n"], "u": f["u"]}


def plant_label(lot, root):
    """Unique name (also of the baked mesh): the houses of a row share their lot, so the root position is added."""
    return "Bouganvillea_%s_%d_%d" % (lot, int(round(root.x)) % 100000, int(round(root.y)) % 100000)


def lot_of(label):
    parts = label.split("_")
    return parts[1] if len(parts) > 1 else "x"


def spawn(plan, label, rng):
    root = plan["points"][0]
    plant = EAS.spawn_actor_from_class(unreal.M80Bougainvillea, root)
    plant.set_actor_label(label)
    plant.set_folder_path("Mazzarino80/Vegetazione/Bouganvillea")
    plant.tags = ["M80Bouganvillea"]
    r, acc = rng.random(), 0.0
    for colour, w in COLOURS:
        acc += w
        if r <= acc:
            plant.set_editor_property("colour", colour)
            break
    plant.set_editor_property("seed", rng.randint(1, 100000))
    plant.set_editor_property("clear_height", plan["clear"])
    plant.set_editor_property("support_wire", plan["wire"])
    plant.set_editor_property("branch_length", rng.uniform(110, 160))
    plant.set_editor_property("flower_amount", rng.uniform(0.7, 1.2))
    plant.get_editor_property("stem").set_spline_points([p - root for p in plan["points"]], unreal.SplineCoordinateSpace.LOCAL, True)
    plant.rebuild()
    info = plant.get_editor_property("build_info")
    # Long plants (a crossing is 15-20 m of stem) are thinned to the triangle budget.
    for _ in range(3):
        tris = int(re.search(r"(\d+) triangoli", info).group(1))
        if tris <= BUDGET:
            break
        k = math.sqrt(BUDGET / float(tris))
        for prop, low in (("branches_per_metre", 1.0), ("leaf_amount", 0.3), ("flower_amount", 0.3)):
            plant.set_editor_property(prop, max(low, plant.get_editor_property(prop) * k))
        plant.rebuild()
        info = plant.get_editor_property("build_info")
    mesh = unreal.M80EditorLibrary.bake_bougainvillea(plant, FOLDER)
    return plant, mesh, info


def photo(plant, plan, name):
    pts = plan["points"]
    root = pts[0]
    c = pts[len(pts) // 2] if plan["wire"] else (pts[0] + pts[-1]) * 0.5 + V(0, 0, 120)
    # A wall plant from across the street; a crossing from along the street, under it.
    if plan["wire"]:
        d = V(-plan["u"][1], plan["u"][0], 0)
        base = V(c.x, c.y, root.z + 170)
    else:
        d = V(plan["n"][0], plan["n"][1], 0)
        base = V(c.x, c.y, root.z + 170) + d * 30
    hit = trace(base, base + d * 1000, [plant])
    eye = base + d * (max(200.0, (hit[0] - base).length() - 60) if hit else 900.0)
    rot = unreal.MathLibrary.find_look_at_rotation(eye, c)
    m80_seq.set_view(eye, rot)
    yield 200
    cap = m80_seq.ViewCapture(1600, 1000, 70)
    cap.capture(eye, rot, OUT / "Paese" / (name + ".png"))
    cap.destroy()
    yield 3


def daylight():
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 30000))
    sun.set_actor_rotation(unreal.Rotator(pitch=-42.0, yaw=-110.0, roll=0.0), False)
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("atmosphere_sun_light", True)
    c.set_intensity(7.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 20000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight) and a != sun:
            a.get_component_by_class(unreal.DirectionalLightComponent).set_visibility(False)
    return [sun, sky]


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "Paese").mkdir(exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    houses = [d for d in descs if m80_seq.desc_class_is(d, "M80House")]
    if SISTEMA:
        # Only the places of the plants already there: rename them uniquely and bake them again.
        houses = [d for d in descs if m80_seq.desc_class_is(d, "M80Bougainvillea")]
    if CENTRO == "fitta":
        cells = {}
        for d in houses:
            c = m80_seq.desc_center(d)
            cells.setdefault((math.floor(c.x / 10000), math.floor(c.y / 10000)), []).append(c)
        best = max(cells.values(), key=len)
        houses = m80_seq.near(houses, sum(c.x for c in best) / len(best), sum(c.y for c in best) / len(best), 8000)
    elif CENTRO:
        cx, cy, cr = (float(x) for x in CENTRO.split(","))
        houses = m80_seq.near(houses, cx, cy, cr)
    existing = [m80_seq.desc_center(d) for d in descs if m80_seq.desc_class_is(d, "M80Bougainvillea")]
    m80_seq.load(m80_seq.actor_descs("LandscapeStreamingProxy"))
    yield 200
    lights = daylight() if FOTO else []
    m80_seq.console("r.TextureStreaming 0")
    report = {"plants": [], "skipped": 0}
    rng = random.Random(SEED)
    total = 0
    for tile in m80_seq.tiles(houses, 25000.0):
        if MAX and total >= MAX:
            break
        cs = [m80_seq.desc_center(d) for d in tile]
        cx, cy = sum(c.x for c in cs) / len(cs), sum(c.y for c in cs) / len(cs)
        radius = max(math.hypot(c.x - cx, c.y - cy) for c in cs) + 3000
        around = [d for d in m80_seq.near(descs, cx, cy, radius) if not m80_seq.desc_class_is(d, "LandscapeStreamingProxy")]
        m80_seq.load(around)
        yield 250
        guids = {gid(d.get_editor_property("guid")) for d in tile}
        loaded = [a for a in EAS.get_all_level_actors() if isinstance(a, unreal.M80House) and not a.is_excluded()]
        faces = [f for f in (facade(h) for h in loaded) if f]
        mine = [f for f in faces if gid(f["house"].get_editor_property("actor_guid")) in guids]
        # Any wall of any house may be the one across the street.
        walls = [f for f in (facade(h, i) for h in loaded for i in range(len(h.get_footprint_world2d()))) if f]
        report.setdefault("tiles", []).append({"houses": len(tile), "loaded": len(loaded), "mine": len(mine)})
        saved = []
        # Plants placed before whose baked mesh is not in this checkout (baked meshes are not in Git), or with an old
        # name shared with another plant (M80_BGV_SISTEMA): baked again.
        for plant in [a for a in EAS.get_all_level_actors() if isinstance(a, unreal.M80Bougainvillea)]:
            label = plant_label(lot_of(plant.get_actor_label()), plant.get_actor_location())
            if plant.is_baked() and not (SISTEMA and plant.get_actor_label() != label):
                continue
            plant.set_actor_label(label)
            plant.rebuild()
            mesh = unreal.M80EditorLibrary.bake_bougainvillea(plant, FOLDER)
            if mesh:
                saved += [plant.get_package(), mesh.get_package()]
                report["ricotte"] = report.get("ricotte", 0) + 1
            yield 2
        for f in ([] if SISTEMA else mine):
            if MAX and total >= MAX:
                break
            lot = f["house"].get_editor_property("lot_id") or f["house"].get_name()
            hr = random.Random("%d-%s-%s" % (SEED, lot, f["house"].get_name()))
            if hr.random() >= QUOTA:
                continue
            plan = None
            if hr.random() < PASSAGGI:
                # Across the street from any outer wall of the house (side alleys are the narrow ones), main facade first.
                n = len(f["house"].get_footprint_world2d())
                front = f["house"].get_editor_property("resolved_front_edge")
                for i in [front] + [k for k in range(n) if k != front]:
                    side = facade(f["house"], i)
                    site = side and pick_site(side, hr, existing)
                    if site:
                        plan = plan_cross(side, site[0], site[1], site[2], walls, hr, report.setdefault("passaggi_scartati", {}))
                        if plan:
                            break
            if not plan:
                site = pick_site(f, hr, existing)
                plan = site and plan_wall(f, site[0], site[1], site[2], hr)
            if not plan:
                report["skipped"] += 1
                continue
            label = plant_label(lot, plan["points"][0])
            plant, mesh, info = spawn(plan, label, hr)
            existing.append(plan["points"][0])
            saved += [plant.get_package()] + ([mesh.get_package()] if mesh else [])
            report["plants"].append({"label": label, "lot": lot, "root": [round(v) for v in (plan["points"][0].x, plan["points"][0].y, plan["points"][0].z)],
                                     "passaggio": plan["wire"], "larghezza_m": plan.get("width_m"), "altezza_libera_m": plan.get("height_m"),
                                     "colore": str(plant.get_editor_property("colour")), "info": info, "baked": bool(mesh)})
            total += 1
            yield 2
            if FOTO:
                yield from photo(plant, plan, label)
        if saved and not PROVA:
            unreal.EditorLoadingAndSavingUtils.save_packages(saved, False)
        (OUT / "paese.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        m80_seq.unload(around)
        unreal.SystemLibrary.collect_garbage()
        yield 30
    for a in lights:
        a.destroy_actor()
    report["total"] = total
    report["passaggi"] = sum(1 for p in report["plants"] if p["passaggio"])
    (OUT / "paese.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "paese_error.txt"))
