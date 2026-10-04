"""Town map details from the shared "Comune" assets (L_M80_Paese):

1. Road signs (once: the swapped signs keep the M80Sign tag of m80_signs_setup.py): the Blender signs that have a worn equivalent in /Game/Migrated/Signals (no entry, no
   stopping, one way, no trucks) are swapped for those (pole + rusty plate); stop and yield keep their
   shape but get rust (M_M80_Sign "Rust").
2. Old posters (Decals_mazza, M_Cartelloni_*) glued on flat stretches of the street fronts, sometimes in
   rows (MI_Decal_Dirt_Manifesto is not used: its Megapack mask renders as a dark square). Each decal is attached to its house, so it disappears
   with it (exclusion zones, "Disattiva").
3. Neoclassic palaces (NeoClassic_house, built from the NeoclassicBuilding tiles) on a few long lots of
   the main streets: the procedural houses under the palace are switched off ("Disattiva").
4. Parked along the Corso: the drivable Fiat 126 and Ape (MazzarinoVehicles) and the old car (prop).
Placed actors carry the tag M80CommonProp and are replaced on every run.
Env: M80_PROPS_MAP, M80_POSTER_CHANCE (0.22), M80_NEO_MAX (6).
"""
import json
import math
import os
import random
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_PROPS_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
POSTER_CHANCE = float(os.environ.get("M80_POSTER_CHANCE", "0.22"))
NEO_MAX = int(os.environ.get("M80_NEO_MAX", "6"))
OUT = ROOT / "Saved/Mazzarino80/props_report.json"
TAG = "M80CommonProp"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
SIGN_MASTER = "/Game/Mazzarino80/Kit/Signs/M_M80_Sign"
WORN = {"NoEntry": "StreetSign_NoEntry", "NoParking": "StreetSign_NoStopping", "OneWay": "StreetSign_Left", "NoTransit": "StreetSign_Truck"}
WORN_FRONT = (0.0, 1.0)  # the Migrated sign plates face +Y, the pole is behind them
NEO_CLASS = "/Game/Migrated/Case/NeoClassic_house"
NEO_SCALE = float(os.environ.get("M80_NEO_SCALE", "0.9"))
NEO_BOX = (-133.0, -2446.0, 2233.0, 128.0)  # local XY bounds; the main front (door, round window) faces -Y
# Drivable classes from the MazzarinoVehicles plugin, the old car is a parked prop.
CARS = ["M80CarFiat126", "M80CarApe", "/Game/Drive/AutoFake/OldCar"]


def trace(world, start, end):
    r = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                               unreal.DrawDebugTrace.NONE, True)
    hit = r[1] if isinstance(r, tuple) else r
    f = hit.to_tuple() if hit else None
    if not f or not f[0]:
        return None
    return {"point": f[5], "normal": f[7], "actor": f[9], "distance": f[3]}


def ground(world, x, y, z):
    """Landscape height (houses and props ignored)."""
    r = unreal.SystemLibrary.line_trace_multi_for_objects(world, unreal.Vector(x, y, z + 5000), unreal.Vector(x, y, z - 5000),
                                                          [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1], True, [], unreal.DrawDebugTrace.NONE, True)
    hits = r[1] if isinstance(r, tuple) else r
    for h in hits or []:
        f = h.to_tuple()
        if isinstance(f[9], unreal.LandscapeProxy):
            return f[5].z
    return z


def front_axis(mesh):
    box = mesh.get_bounding_box()
    ext = (box.max.x - box.min.x, box.max.y - box.min.y)
    if ext[0] < ext[1]:
        return (-1.0, 0.0) if abs(box.min.x) > abs(box.max.x) else (1.0, 0.0)
    return (0.0, -1.0) if abs(box.min.y) > abs(box.max.y) else (0.0, 1.0)


def rust_master():
    """Adds a "Rust" scalar (default 0, so nothing changes for existing instances) to M_M80_Sign."""
    m = unreal.load_asset(SIGN_MASTER)
    MEL.delete_all_material_expressions(m)

    def node(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(a, ao, b, bi):
        if not MEL.connect_material_expressions(a, ao, b, bi):
            raise RuntimeError("link failed " + bi)
    face = node(unreal.MaterialExpressionTextureSampleParameter2D, -900, 0, parameter_name="Face",
                texture=unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture"))
    tint = node(unreal.MaterialExpressionVectorParameter, -900, 250, parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    col = node(unreal.MaterialExpressionMultiply, -650, 50)
    link(face, "RGB", col, "A")
    link(tint, "", col, "B")
    rust = node(unreal.MaterialExpressionScalarParameter, -900, 400, parameter_name="Rust", default_value=0.0)
    uv = node(unreal.MaterialExpressionTextureCoordinate, -1200, 600, u_tiling=3.0, v_tiling=3.0)
    rust_tex = node(unreal.MaterialExpressionTextureSampleParameter2D, -900, 550, parameter_name="RustColor",
                    texture=unreal.load_asset("/Game/Migrated/T_Corrosion_Rust_03_C"))
    link(uv, "", rust_tex, "UVs")
    noise_tex = unreal.load_asset("/Game/Migrated/T_Perlin_Noise_M")
    noise = node(unreal.MaterialExpressionTextureSampleParameter2D, -900, 800, parameter_name="RustMask", texture=noise_tex,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
                 if noise_tex.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_MASKS
                 else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    link(uv, "", noise, "UVs")
    add = node(unreal.MaterialExpressionAdd, -650, 700)
    link(noise, "R", add, "A")
    link(rust, "", add, "B")
    sub = node(unreal.MaterialExpressionSubtract, -500, 700, const_b=1.0)
    link(add, "", sub, "A")
    mul = node(unreal.MaterialExpressionMultiply, -380, 700, const_b=5.0)
    link(sub, "", mul, "A")
    mask = node(unreal.MaterialExpressionSaturate, -260, 700)
    link(mul, "", mask, "")
    base = node(unreal.MaterialExpressionLinearInterpolate, -150, 100)
    link(col, "", base, "A")
    link(rust_tex, "RGB", base, "B")
    link(mask, "", base, "Alpha")
    MEL.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = node(unreal.MaterialExpressionScalarParameter, -400, 350, parameter_name="Roughness", default_value=0.6)
    rl = node(unreal.MaterialExpressionLinearInterpolate, -150, 350, const_b=0.95)
    link(rough, "", rl, "A")
    link(mask, "", rl, "Alpha")
    MEL.connect_material_property(rl, "", unreal.MaterialProperty.MP_ROUGHNESS)
    metal = node(unreal.MaterialExpressionScalarParameter, -400, 500, parameter_name="Metallic", default_value=0.0)
    MEL.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def spawn(eas, what, loc, rot, label, folder, tag=TAG):
    a = eas.spawn_actor_from_object(what, loc, rot) if isinstance(what, unreal.StaticMesh) else eas.spawn_actor_from_class(what, loc, rot)
    a.set_actor_label(label)
    a.set_folder_path(folder)
    a.tags = list(a.tags) + [unreal.Name(tag)]
    return a


def signs(world, eas, actors, rnd, report):
    master = rust_master()
    for kind in ("Stop", "Yield"):
        mesh = unreal.load_asset("/Game/Mazzarino80/Kit/Signs/SM_M80_Sign_" + kind)
        for i in range(len(mesh.static_materials)):
            mi = mesh.get_material(i)
            if isinstance(mi, unreal.MaterialInstanceConstant) and mi.get_base_material() == master:
                MEL.set_material_instance_scalar_parameter_value(mi, "Rust", 0.55)
                EAL.save_loaded_asset(mi)
    poles = [unreal.load_asset("/Game/Migrated/Signals/StreetSign_Pole_01"), unreal.load_asset("/Game/Migrated/Signals/StreetSign_Pole_02")]
    swapped = 0
    for a in actors:
        if not isinstance(a, unreal.StaticMeshActor) or str(a.get_folder_path()) != "Segnaletica":
            continue
        mesh = a.static_mesh_component.static_mesh
        name = mesh.get_name() if mesh else ""
        kind = name[len("SM_M80_Sign_"):] if name.startswith("SM_M80_Sign_") else None
        if kind not in WORN:
            continue
        fx, fy = front_axis(mesh)
        face = math.radians(a.get_actor_rotation().yaw) + math.atan2(fy, fx)
        loc = a.get_actor_location()
        plate = unreal.load_asset("/Game/Migrated/Signals/" + WORN[kind])
        yaw = math.degrees(face - math.atan2(WORN_FRONT[1], WORN_FRONT[0]))
        z = loc.z + 5
        pole = spawn(eas, rnd.choice(poles), unreal.Vector(loc.x, loc.y, z - 8), unreal.Rotator(rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), yaw),
                     "Palo_" + kind, "Segnaletica", "M80Sign")
        h = rnd.uniform(235, 262)
        spawn(eas, plate, unreal.Vector(loc.x + math.cos(face) * 5, loc.y + math.sin(face) * 5, z + h), unreal.Rotator(rnd.uniform(-4, 4), 0, yaw + rnd.uniform(-5, 5)),
              "Cartello_" + kind, "Segnaletica", "M80Sign").attach_to_actor(pole, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD,
                                                                 unreal.AttachmentRule.KEEP_WORLD, False)
        a.destroy_actor()
        swapped += 1
    report["signs_swapped"] = swapped


def posters(world, eas, houses, rnd, report):
    mats = []
    for i in range(1, 16):
        path = "/Game/Decals_mazza/M_Cartelloni" + ("" if i == 1 else "_%d" % i)
        tex = unreal.load_asset("/Game/Decals_mazza/manifesto_%03d" % i)
        if EAL.does_asset_exist(path) and tex:
            mats.append((unreal.load_asset(path), tex.blueprint_get_size_x() / max(1, tex.blueprint_get_size_y())))
    placed = 0
    for house in houses:
        if house.is_excluded() or rnd.random() > POSTER_CHANCE:
            continue
        poly = [(q.x, q.y) for q in house.get_footprint_world2d()]
        if len(poly) < 3:
            continue
        i = house.get_editor_property("resolved_front_edge") % len(poly)
        a, b = poly[i], poly[(i + 1) % len(poly)]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length < 300:
            continue
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        nx, ny = uy, -ux
        gz = ground(world, (a[0] + b[0]) / 2 + nx * 150, (a[1] + b[1]) / 2 + ny * 150, house.get_actor_location().z)
        count = rnd.choice([1, 1, 2, 2, 3])
        t = rnd.uniform(0.15, 0.6)
        x0 = t * length
        for k in range(count):
            mat, aspect = rnd.choice(mats)
            hgt = rnd.uniform(80, 120)
            wid = hgt * aspect
            if x0 + wid > length - 60:
                break
            cx, cy = a[0] + ux * (x0 + wid / 2), a[1] + uy * (x0 + wid / 2)
            cz = gz + rnd.uniform(150, 175) + hgt / 2
            hits = []
            for du, dz in ((0, 0), (-wid / 2 + 5, -hgt / 2 + 5), (wid / 2 - 5, -hgt / 2 + 5), (-wid / 2 + 5, hgt / 2 - 5), (wid / 2 - 5, hgt / 2 - 5)):
                px, py = cx + ux * du, cy + uy * du
                hit = trace(world, unreal.Vector(px + nx * 200, py + ny * 200, cz + dz), unreal.Vector(px - nx * 120, py - ny * 120, cz + dz))
                hits.append(hit)
            if any(h is None or h["actor"] != house for h in hits):
                x0 += wid + 30
                continue
            dists = [h["distance"] for h in hits]
            if max(dists) - min(dists) > 3.0:
                x0 += wid + 30
                continue
            p = hits[0]["point"]
            n = hits[0]["normal"]
            yaw = math.degrees(math.atan2(-n.y, -n.x))
            d = spawn(eas, unreal.DecalActor, unreal.Vector(p.x, p.y, p.z), unreal.Rotator(90 + rnd.uniform(-2.5, 2.5), 0, yaw), "Manifesto", "Mazzarino80/Manifesti")
            comp = d.get_component_by_class(unreal.DecalComponent)
            # Roll 90: the decal texture is otherwise turned on its side (local Y is up after the roll).
            comp.set_editor_property("decal_size", unreal.Vector(6, hgt / 2, wid / 2))
            comp.set_decal_material(mat)
            comp.set_editor_property("sort_order", 1)
            d.attach_to_actor(house, "", unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
            placed += 1
            x0 += wid + rnd.choice([2, 4, 40, 120])
    report["posters"] = placed


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def contains(poly, p):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[j]
        if (yi > p[1]) != (yj > p[1]) and p[0] < (xj - xi) * (p[1] - yi) / ((yj - yi) or 1e-9) + xi:
            inside = not inside
        j = i
    return inside


def neoclassic(world, eas, houses, actors, report):
    """A palace takes the street front of a long lot on a main street and as many lots behind and beside
    it as its footprint needs: every house it covers is switched off (and switched back on by a re-run)."""
    cls = EAL.load_blueprint_class(NEO_CLASS)
    s = NEO_SCALE
    bw, bd = (NEO_BOX[2] - NEO_BOX[0]) * s, (NEO_BOX[3] - NEO_BOX[1]) * s
    roads = []
    for r in actors:
        if r.get_class().get_name() != "MazzarinoRoadSpline":
            continue
        sp = r.get_component_by_class(unreal.SplineComponent)
        L = sp.get_spline_length()
        n = max(1, int(L / 300))
        pts = [sp.get_location_at_distance_along_spline(L * k / n, unreal.SplineCoordinateSpace.WORLD) for k in range(n + 1)]
        kind = str(r.get_folder_path()).split("/")[-1]
        roads.append(([(p.x, p.y) for p in pts], float(r.get_editor_property("width_meters")) * 50, kind in ("primary", "secondary", "tertiary") or "Corso" in kind))
    zones = [[(q.x, q.y) for q in z.get_outline_world2d()] for z in actors if isinstance(z, unreal.M80ExclusionZone) and z.get_editor_property("enabled")]
    polys = {h.get_name(): [(q.x, q.y) for q in h.get_footprint_world2d()] for h in houses}

    def road_dist(p, main_only=False):
        best = (1e9, 0)
        for pts, half, main in roads:
            if main_only and not main:
                continue
            for k in range(len(pts) - 1):
                d = seg_dist(p, pts[k], pts[k + 1]) - half
                if d < best[0]:
                    best = (d, half)
        return best[0]

    cands = []
    for h in houses:
        if h.is_excluded():
            continue
        poly = polys[h.get_name()]
        if len(poly) < 3:
            continue
        i = h.get_editor_property("resolved_front_edge") % len(poly)
        a, b = poly[i], poly[(i + 1) % len(poly)]
        lf = math.hypot(b[0] - a[0], b[1] - a[1])
        if lf < 900:
            continue
        ux, uy = (b[0] - a[0]) / lf, (b[1] - a[1]) / lf
        nx, ny = uy, -ux
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if road_dist((mid[0] + nx * 250, mid[1] + ny * 250), True) > 300:
            continue
        cands.append((-lf, h, mid, (ux, uy, nx, ny)))
    cands.sort(key=lambda c: c[0])
    placed = []
    for _, h, mid, (ux, uy, nx, ny) in cands:
        if len(placed) >= NEO_MAX:
            break
        if any(math.hypot(mid[0] - p["at"][0], mid[1] - p["at"][1]) < 12000 for p in placed):
            continue
        c = (mid[0] - nx * bd / 2, mid[1] - ny * bd / 2)
        # Inner points of the palace footprint: no road, no exclusion zone.
        inner = [(c[0] + ux * fu * (bw / 2 - 150) + nx * fn * (bd / 2 - 150), c[1] + uy * fu * (bw / 2 - 150) + ny * fn * (bd / 2 - 150))
                 for fu in (-1, 0, 1) for fn in (-1, 0, 1)]
        if any(road_dist(p) < 50 for p in inner) or any(contains(z, p) for z in zones for p in inner):
            continue
        rect = [(c[0] + ux * fu * bw / 2 + nx * fn * bd / 2, c[1] + uy * fu * bw / 2 + ny * fn * bd / 2) for fu, fn in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        shrunk = [(c[0] + (x - c[0]) * 0.97, c[1] + (y - c[1]) * 0.97) for x, y in rect]
        covered = []
        for o in houses:
            poly = polys[o.get_name()]
            if not poly or o.get_editor_property("disabled"):
                continue
            cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
            if contains(shrunk, (cx, cy)) or any(contains(shrunk, p) for p in poly):
                covered.append(o)
        theta = math.atan2(nx, -ny)  # local -Y (main front) -> outward street normal
        lcx, lcy = (NEO_BOX[0] + NEO_BOX[2]) / 2 * s, (NEO_BOX[1] + NEO_BOX[3]) / 2 * s
        ox = c[0] - (lcx * math.cos(theta) - lcy * math.sin(theta))
        oy = c[1] - (lcx * math.sin(theta) + lcy * math.cos(theta))
        z = min(ground(world, p[0], p[1], h.get_actor_location().z) for p in rect + [mid])
        for o in covered:
            o.set_editor_property("disabled", True)
            o.apply_exclusion()
        pal = spawn(eas, cls, unreal.Vector(ox, oy, z), unreal.Rotator(0, 0, math.degrees(theta)), "NeoClassic_" + h.get_actor_label(), "Mazzarino80/Edifici/NeoClassic")
        pal.set_actor_scale3d(unreal.Vector(s, s, s))
        pal.tags = list(pal.tags) + [unreal.Name("M80Lot:" + o.get_name()) for o in covered]
        placed.append({"lot": h.get_actor_label(), "houses_off": len(covered), "at": [round(mid[0]), round(mid[1])]})
    report["neoclassic"] = placed


def cars(world, eas, actors, report):
    corso = [r for r in actors if r.get_class().get_name() == "MazzarinoRoadSpline" and "Corso" in str(r.get_folder_path())]
    if not corso:
        report["cars"] = "no Corso spline"
        return
    road = max(corso, key=lambda r: r.get_component_by_class(unreal.SplineComponent).get_spline_length())
    polys = [[(q.x, q.y) for q in h.get_footprint_world2d()] for h in actors if isinstance(h, unreal.M80House) and not h.is_excluded()]
    sp = road.get_component_by_class(unreal.SplineComponent)
    half = float(road.get_editor_property("width_meters")) * 50
    length = sp.get_spline_length()
    out = []
    for i, path in enumerate(CARS):
        d = length * (0.35 + 0.05 * i)
        p = sp.get_location_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
        t = sp.get_direction_at_distance_along_spline(d, unreal.SplineCoordinateSpace.WORLD)
        rx, ry = -t.y, t.x
        off = max(0.0, half - 120)
        x, y = p.x + rx * off, p.y + ry * off
        while off > 0 and any(contains(poly, (x + dx, y + dy)) for poly in polys for dx, dy in ((0, 0), (rx * 100, ry * 100))):
            off -= 25
            x, y = p.x + rx * off, p.y + ry * off
        z = ground(world, x, y, p.z) + 40
        cls = EAL.load_blueprint_class(path) if path.startswith("/Game/") else getattr(unreal, path)
        car = spawn(eas, cls, unreal.Vector(x, y, z), unreal.Rotator(0, 0, math.degrees(math.atan2(t.y, t.x))),
                    "Auto_" + path.split("/")[-1], "Mazzarino80/Auto")
        out.append([car.get_actor_label(), round(x), round(y)])
    report["cars"] = out


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected {} open".format(MAP))
    yield 30
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    houses = [h for h in actors if isinstance(h, unreal.M80House)]
    # Undo the previous run: re-enable lots that held a palace, delete placed props.
    lots = set()
    for a in actors:
        if a.actor_has_tag(TAG):
            lots |= {str(t)[len("M80Lot:"):] for t in a.tags if str(t).startswith("M80Lot:")}
            a.destroy_actor()
    for h in houses:
        if h.get_name() in lots:
            h.set_editor_property("disabled", False)
            h.apply_exclusion()
    actors = eas.get_all_level_actors()
    report = {}
    rnd = random.Random(1980)
    signs(world, eas, actors, rnd, report)
    yield 10
    neoclassic(world, eas, houses, actors, report)
    yield 30
    posters(world, eas, houses, rnd, report)
    yield 10
    cars(world, eas, actors, report)
    yield 10
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
