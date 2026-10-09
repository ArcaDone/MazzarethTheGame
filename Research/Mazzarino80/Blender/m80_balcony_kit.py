"""Balcony kit (Mazzarino 80): the "signorili" balconies of the old palazzi, from the user's street photos.

Three variants, high-poly first (for the user's approval, then low-poly + bake + FBX for Unreal):
  volute      thick moulded slab on double-scroll consoles (spirals carved on their sides, a drop below),
              recessed panels between them, straight railing with scrolls and ball finials.
  mascheroni  thin slab on heavy consoles carved as beasts' heads (lions, dogs), worn smooth by the weather,
              fleur-de-lis panels between them, plain railing.
  acanto      slab on consoles with a banded roll on top, a big acanthus leaf down the front and a grotesque
              mask on the block below, rosettes between them, bellied (petto d'oca) railing.

Each balcony is built in its own facade frame (X along the wall, -Y out of it, Z up; the slab top is at
V_TOP) in front of a stretch of wall with a French window, and rendered from below, from the side and close
up on one console.
Run: blender -b --factory-startup --python m80_balcony_kit.py
Out: Previews/Balconi/<variant>_<view>.png, Saved/Mazzarino80/Balconi/balconi_alta.blend
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(HERE)
import m80_arch_facade as A  # noqa: E402
import m80_arch_kit as K  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PREVIEWS = os.path.join(HERE, "Previews", "Balconi")
SAVED = os.path.join(ROOT, "Saved", "Mazzarino80", "Balconi")
V_TOP = 4.2

VARIANTS = {
    "volute": {"width": 2.4, "depth": 0.80, "thick": 0.20, "slab": "moulded", "console": "volute", "n": 4, "h": 0.62,
               "panel": "recessed", "railing": "straight", "posts": True, "stone": "grey"},
    "mascheroni": {"width": 2.6, "depth": 0.72, "thick": 0.13, "slab": "plain", "console": "beast", "n": 5, "h": 0.50,
                   "panel": "fleur", "railing": "straight", "posts": False, "stone": "gold"},
    "acanto": {"width": 2.4, "depth": 0.85, "thick": 0.17, "slab": "moulded", "console": "acanthus", "n": 4, "h": 0.95,
               "panel": "rosette", "railing": "bombe", "posts": False, "stone": "pale"},
}


def stones():
    return {
        # Grey limestone blackened in the hollows (first photo), orange sandstone (second), pale limestone (third).
        "grey": A.stone_material("Balcone_calcare_grigio", (0.47, 0.44, 0.38), (0.16, 0.15, 0.13), scale=5.0, pitting=0.5),
        "gold": A.stone_material("Balcone_arenaria", (0.55, 0.36, 0.17), (0.30, 0.19, 0.09), scale=4.0, pitting=0.55),
        "pale": A.stone_material("Balcone_calcare_chiaro", (0.62, 0.56, 0.45), (0.30, 0.27, 0.21), scale=5.0, pitting=0.45),
    }


# ---------------------------------------------------------------------------------------------
# Geometry helpers (facade frame: u along, y out of the wall is negative, v up)

def loft_x(bm, outline, x0, x1, slices=1, scale=None, centre=None):
    """Closed outline of (out, z) points extruded along X; scale(t) shrinks each slice about centre."""
    rings = []
    for i in range(slices + 1):
        t = i / slices
        s = scale(t) if scale else 1.0
        cy, cz = centre or (0.0, 0.0)
        x = x0 + (x1 - x0) * t
        rings.append([bm.verts.new((x, -(cy + (o - cy) * s), cz + (z - cz) * s)) for o, z in outline])
    n = len(outline)
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(n):
            bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def spiral_strip(cx, cz, R, turns=1.7, sign=-1, a0=90.0, n=70):
    """2D spiral band (out, z) winding in from radius R: the side view of a volute."""
    outer, inner = [], []
    for k in range(n + 1):
        t = k / n
        a = math.radians(a0 + sign * 360.0 * turns * t)
        r = R * (1 - 0.80 * t)
        th = R * 0.30 * (1 - 0.55 * t)
        outer.append((cx + r * math.cos(a), cz + r * math.sin(a)))
        inner.append((cx + (r - th) * math.cos(a), cz + (r - th) * math.sin(a)))
    return outer + inner[::-1]


def lathe(bm, cx, cy, cz, profile, seg=20):
    """Body of revolution about a vertical axis; profile is (radius, dz) from the top down."""
    rings = [[bm.verts.new((cx + r * math.cos(2 * math.pi * j / seg), cy + r * math.sin(2 * math.pi * j / seg), cz + dz))
              for j in range(seg)] for r, dz in profile]
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(seg):
            bm.faces.new((a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)


def sweep_plan(bm, path, profile, y_sign=-1):
    """A moulding (profile of (out, z) points) run along an open plan path of (u, y) points, mitred."""
    # Dense rings (every 5 cm): the weathering subdivision would otherwise round the long runs into the slab.
    pts = [Vector(p) for p in K.resample_path(path, 0.05)]
    rings = []
    for i, p in enumerate(pts):
        normals = []
        for a, b in ((pts[i - 1], p) if i > 0 else (None, None), (p, pts[i + 1]) if i + 1 < len(pts) else (None, None)):
            if a is None:
                continue
            d = (b - a).normalized()
            normals.append(Vector((d.y, -d.x)) * -y_sign)
        nrm = sum(normals, Vector((0, 0))).normalized()
        miter = 1.0 / max(0.3, nrm.dot(normals[0]))
        rings.append([bm.verts.new((p.x + nrm.x * o * miter, p.y + nrm.y * o * miter, z)) for o, z in profile])
    n = len(profile)
    for a, b in zip(rings[:-1], rings[1:]):
        for j in range(n - 1):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])


def ellipsoid(bm, centre, radii, rot=0.0):
    """Closed ellipsoid (u, y, v centre and radii), optionally turned about Z by rot radians."""
    m = Matrix.Translation(centre) @ Matrix.Rotation(rot, 4, "Z") @ Matrix.Diagonal((*radii, 1.0))
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=1.0, matrix=m)


def solid(F, name, bm, mat, voxel=0.006, cut=None, smooth=6, wear=1.0):
    """One carved stone out of overlapping closed shapes: fused by a voxel remesh (an even, dense mesh with
    no fan artifacts), hollows cut by the shapes in `cut`, softened like stone worn for centuries, weathered."""
    ob = K.bm_object(name, bm, F.high, F.frame, mat)
    r = ob.modifiers.new("Fondi", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel
    cutter = None
    if cut is not None and cut.verts:
        cutter = K.bm_object(name + "_scavo", cut, F.high, F.frame)
        b = ob.modifiers.new("Scava", "BOOLEAN")
        b.operation = "DIFFERENCE"
        b.solver = "EXACT"
        b.use_self = True
        b.object = cutter
        r2 = ob.modifiers.new("Rifondi", "REMESH")
        r2.mode = "VOXEL"
        r2.voxel_size = voxel
    elif cut is not None:
        cut.free()
    if smooth:
        sm = ob.modifiers.new("Consuma", "SMOOTH")
        sm.factor = 0.6
        sm.iterations = smooth
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)
    if cutter:
        bpy.data.objects.remove(cutter)
    me.materials.clear()
    me.materials.append(mat)
    me.shade_smooth()
    if wear:
        K.weather(ob, wear=wear, bevel=0.0, subdiv=0)
        # The pits of the generic weathering are sized for walls: shallower on carving.
        for m in ob.modifiers:
            if m.name == "Scheggiature":
                m.strength *= 0.35
    return ob


# ---------------------------------------------------------------------------------------------
# Carved parts (each adds closed shapes to a bmesh, fused later by solid())

def console_curve(depth, height):
    """Front S curve of a console under its top roll: (out, z) at t in [0, 1], plus the roll radii."""
    # Same rolls as A.bracket_outline(rich=True), which makes the console body.
    r = min(0.075, height * 0.14)
    rf = r * 0.7
    x0, z0 = depth - r, -2 * r
    x1, z1 = rf + 0.03, -height + 2 * rf

    def at(t):
        c = 0.5 - 0.5 * math.cos(math.pi * t)
        return x0 + (x1 - x0) * c, z0 + (z1 - z0) * t
    return at, r, rf, (x1, z1)


def console_body(bm, uc, half, v, depth, height):
    A.extrude_outline(bm, A.bracket_outline(depth, height, True), uc - half, uc + half, v)


def side_spirals(bm, uc, half, v, depth, height):
    """Volutes carved on both sides of a console: a spiral band standing proud of each face."""
    at, r, rf, (x1, z1) = console_curve(depth, height)
    for side in (-1, 1):
        xa = uc + side * (half - 0.01)
        xb = uc + side * (half + 0.02)
        for cx, cz, R, sg in ((depth - r, -r, r * 1.05, -1), (x1, z1 - rf, rf * 1.05, 1)):
            outline = [(o, v + z) for o, z in spiral_strip(cx, cz, R, sign=sg)]
            loft_x(bm, outline, min(xa, xb), max(xa, xb))


def banded_roll(bm, uc, half, v, depth, height):
    """The roll on top of an acanthus console, pinched in the middle and tied by two bands."""
    at, r, rf, _ = console_curve(depth, height)
    R = r * 1.3
    cx, cz = depth - R * 0.9, -R
    outline = [(o, v + z) for o, z in spiral_strip(cx, cz, R, turns=1.9, sign=-1)]

    def waist(t):
        s = 1.0 - 0.16 * math.sin(math.pi * t)
        for b in (0.28, 0.72):
            s += 0.12 * math.exp(-((t - b) / 0.04) ** 2)
        return s
    loft_x(bm, outline, uc - half - 0.025, uc + half + 0.025, slices=40, scale=waist, centre=(cx, v + cz))


def pendant(bm, u, y, v):
    """Drop under a volute console."""
    lathe(bm, u, y, v + 0.03, [(0.0, 0.0), (0.06, -0.01), (0.075, -0.06), (0.065, -0.10), (0.04, -0.14), (0.05, -0.16),
                               (0.035, -0.19), (0.014, -0.22), (0.0, -0.23)])


def acanthus(F, name, uc, half, v, depth, height, mat, seed=1):
    """Acanthus leaf down the front of a console: lobed and serrated, a midrib, tip curling out."""
    at, r, rf, _ = console_curve(depth, height)
    rnd = random.Random(seed)
    rows, cols = 70, 25
    lobes = 4.5
    bm = bmesh.new()
    grid = []
    for i in range(rows + 1):
        s = i / rows
        o, z = at(min(1.0, 0.08 + s * 0.92))
        o2, z2 = at(min(1.0, 0.08 + s * 0.92 + 0.01))
        tan = Vector((o2 - o, z2 - z)).normalized()
        nrm = Vector((tan.y, -tan.x))
        if nrm.x < 0:
            nrm = -nrm
        width = half * 1.35 * (0.30 + 0.70 * math.sin(math.pi * min(1.0, s * 1.05) ** 0.8))
        lobe = abs(math.cos(lobes * math.pi * s))
        edge = width * (0.70 + 0.30 * lobe ** 0.6) * (1 + 0.06 * ((s * 31) % 1.0))
        row = []
        for j in range(cols + 1):
            t = -1 + 2 * j / cols
            off = 0.016 + 0.03 * (1 - t * t) + 0.01 * math.exp(-(t / 0.07) ** 2)
            off -= 0.014 * abs(math.sin(lobes * math.pi * s)) * (1 - abs(t))
            off += 0.025 * abs(t) ** 4 * lobe
            if s > 0.80:
                off += 0.18 * ((s - 0.80) / 0.20) ** 2
            off += rnd.uniform(-0.002, 0.002)
            row.append(bm.verts.new((uc + t * edge, -(o + nrm.x * off), v + z + nrm.y * off)))
        grid.append(row)
    for a, b in zip(grid[:-1], grid[1:]):
        for j in range(cols):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    ob = K.bm_object(name, bm, F.high, F.frame, mat, smooth=True)
    so = ob.modifiers.new("Spessore", "SOLIDIFY")
    so.thickness = 0.016
    s = ob.modifiers.new("Sub", "SUBSURF")
    s.levels = s.render_levels = 1
    K.weather(ob, wear=0.25, bevel=0.0, subdiv=0)


def beast(bm, cut, uc, v, kind="lion", seed=1, size=1.0):
    """A console carved as a beast's head jutting from the wall under the slab (top at v)."""
    rnd = random.Random(seed)

    def E(c, rad, rot=0.0, target=bm):
        ellipsoid(target, Vector((uc + c[0] * size, -c[1] * size, v + c[2] * size)), [x * size for x in rad], rot)
    long_ = 1.0 if kind == "lion" else 1.35
    E((0, 0.14, -0.20), (0.13, 0.17, 0.19))                    # neck block against the wall
    E((0, 0.08, -0.06), (0.17, 0.10, 0.07))                    # shoulder under the slab
    E((0, 0.32, -0.21), (0.15, 0.14, 0.15))                    # skull
    E((0, 0.40 + 0.06 * (long_ - 1), -0.13), (0.12, 0.06, 0.045))  # brow
    E((0, 0.46 + 0.08 * (long_ - 1), -0.26), (0.085, 0.09 * long_, 0.07))   # muzzle
    E((0, 0.45 + 0.08 * (long_ - 1), -0.18), (0.04, 0.08 * long_, 0.04))    # bridge of the nose
    E((0, 0.53 + 0.16 * (long_ - 1), -0.235), (0.05, 0.03, 0.035))          # nose
    E((0, 0.43 + 0.06 * (long_ - 1), -0.35), (0.08, 0.07, 0.04))            # jaw
    for sd in (-1, 1):
        E((sd * 0.075, 0.44, -0.27), (0.06, 0.05, 0.05))                     # cheeks
        E((sd * 0.12, 0.27, -0.06), (0.04, 0.03, 0.06) if kind == "lion" else (0.035, 0.05, 0.08))  # ears
        E((sd * 0.055, 0.47 + 0.05 * (long_ - 1), -0.165), (0.026, 0.03, 0.022), target=cut)    # eye sockets
        E((sd * 0.02, 0.555 + 0.16 * (long_ - 1), -0.24), (0.012, 0.02, 0.012), target=cut)     # nostrils
    E((0, 0.50 + 0.08 * (long_ - 1), -0.31), (0.055, 0.04, 0.013), target=cut)                # mouth
    if kind == "lion":
        for k in range(14):
            a = 2 * math.pi * k / 14
            E((0.17 * math.cos(a), 0.31 + rnd.uniform(-0.03, 0.02), -0.21 + 0.17 * math.sin(a)),
              (rnd.uniform(0.045, 0.06), 0.06, rnd.uniform(0.06, 0.08)), rot=a)
    # Chunks lost to the weather.
    for _ in range(2):
        a = rnd.uniform(0, 2 * math.pi)
        E((0.15 * math.cos(a), rnd.uniform(0.3, 0.5), -0.21 + 0.15 * math.sin(a)), (0.04, 0.04, 0.04), target=cut)


def mask(bm, cut, uc, y_front, v, w, h, seed=1):
    """Grotesque face on the front of a block (front face at y_front, centre height v)."""
    rnd = random.Random(seed)

    def E(c, rad, target=bm):
        ellipsoid(target, Vector((uc + c[0], y_front - c[1], v + c[2])), rad)
    E((0, 0.0, 0), (w * 0.42, 0.05, h * 0.42))             # face
    E((0, 0.045, h * 0.17), (0.07, 0.03, 0.025))           # brow
    E((0, 0.06, 0.0), (0.025, 0.035, 0.05))                # nose
    for sd in (-1, 1):
        E((sd * 0.055, 0.035, -0.03), (0.04, 0.035, 0.035))    # cheeks
        E((sd * 0.045, 0.06, h * 0.09), (0.02, 0.025, 0.016), target=cut)   # eyes
        for k in range(3):                                      # leafy beard and hair
            E((sd * (0.07 + 0.025 * k), 0.015, -h * 0.22 - 0.035 * k), (0.03, 0.03, 0.035))
            E((sd * (0.05 + 0.035 * k), 0.015, h * 0.30 + 0.015 * k), (0.03, 0.03, 0.03))
    E((0, 0.06, -0.075), (0.04, 0.03, 0.012), target=cut)  # mouth
    for _ in range(2):
        E((rnd.uniform(-w * 0.3, w * 0.3), 0.05, rnd.uniform(-h * 0.3, h * 0.3)), (0.025, 0.025, 0.025), target=cut)


def fleur(bm, u, y, v, size, depth=0.022):
    """Fleur-de-lis in relief on a panel (front at y, facing -Y)."""
    def ext(points):
        pts = [(u + px * size, v + pz * size) for px, pz in points]
        f = [bm.verts.new((p[0], y, p[1])) for p in pts]
        b = [bm.verts.new((p[0], y - depth, p[1])) for p in pts]
        bm.faces.new(f)
        bm.faces.new(list(reversed(b)))
        n = len(pts)
        for i in range(n):
            bm.faces.new((f[i], f[(i + 1) % n], b[(i + 1) % n], b[i]))
    centre = [(0.0, 0.50)] + [(0.11 * math.sin(math.pi * t / 8), 0.50 - 0.62 * t / 8) for t in range(1, 8)] + [(0.0, -0.12)]
    centre += [(-x, z) for x, z in reversed(centre[1:-1])]
    ext(centre)
    for side in (-1, 1):
        petal = []
        for k in range(13):
            a = math.radians(200 - 190 * k / 12)
            petal.append((side * (0.20 + 0.16 * math.cos(a)), 0.02 + 0.22 * math.sin(a) * (0.6 + 0.4 * k / 12)))
        petal += [(side * 0.08, -0.05), (side * 0.06, 0.0)]
        if side < 0:
            petal = petal[::-1]
        ext(petal)
    ext([(-0.20, -0.08), (0.20, -0.08), (0.20, -0.16), (-0.20, -0.16)])
    ext([(-0.06, -0.16), (0.06, -0.16), (0.12, -0.34), (0.0, -0.26), (-0.12, -0.34)])


def rosette(bm, u, y, v, radius, depth=0.02, petals=8):
    for k in range(petals):
        a = 2 * math.pi * k / petals
        pts = []
        for j in range(12):
            b = 2 * math.pi * j / 12
            pr, px = radius * 0.5 * (1 + math.cos(b)) * 0.9 + radius * 0.1, radius * 0.22 * math.sin(b)
            pts.append((u + pr * math.cos(a) - px * math.sin(a), v + pr * math.sin(a) + px * math.cos(a)))
        f = [bm.verts.new((p[0], y, p[1])) for p in pts]
        bk = [bm.verts.new((p[0], y - depth, p[1])) for p in pts]
        bm.faces.new(f)
        bm.faces.new(list(reversed(bk)))
        for i in range(12):
            bm.faces.new((f[i], f[(i + 1) % 12], bk[(i + 1) % 12], bk[i]))
    K.box_bm(bm, u - radius * 0.18, u + radius * 0.18, y - depth * 1.8, y, v - radius * 0.18, v + radius * 0.18)


# ---------------------------------------------------------------------------------------------
# A balcony

def balcony(name, x0, spec):
    M = A.mats()
    stone = stones()[spec["stone"]]
    W, d, th, h = spec["width"], spec["depth"], spec["thick"], spec["h"]
    F = K.Facade(name, (x0, 0.0), (x0 + W + 1.6, 0.0), 0.0, V_TOP + 3)
    u0, u1 = 0.8, 0.8 + W
    uc_mid = (u0 + u1) / 2
    v = V_TOP

    # Wall behind and the French window.
    bm = bmesh.new()
    K.box_bm(bm, -0.6, W + 2.2, 0.0, 0.4, V_TOP - 3.2, V_TOP + 3.0)
    wall = K.bm_object(name + "_muro", bm, F.detail, F.frame, A.stone_material("Muro_fondo", (0.50, 0.40, 0.26), (0.36, 0.28, 0.17)))
    bm = bmesh.new()
    K.box_bm(bm, uc_mid - 0.6, uc_mid + 0.6, -0.002, 0.0, v, v + 2.4)
    K.bm_object(name + "_portafinestra", bm, F.detail, F.frame, M["dark"])
    A.shutters(F, name + "_persiane", K.Opening(uc_mid - 0.6, uc_mid + 0.6, v, v + 2.4, kind="french"), True)

    # Slab.
    bm = bmesh.new()
    K.box_bm(bm, u0, u1, -d, 0.0, v - th, v)
    solid(F, name + "_lastra", bm, stone, voxel=0.008, smooth=3, wear=0.9)
    if spec["slab"] == "moulded":
        prof = K.profile_resample([(0.0, -0.025), (0.035, -0.025), ("arc", 0.035, -0.06, 0.035, 90, -90), (0.02, -0.095),
                                   (0.02, -0.11), (0.0, -th + 0.01), (0.0, -th)], 6)
        prof = [(o, v + z) for o, z in prof]
        bm = bmesh.new()
        sweep_plan(bm, [(u0, 0.0), (u0, -d), (u1, -d), (u1, 0.0)], prof)
        ob = K.bm_object(name + "_toro", bm, F.high, F.frame, stone)
        K.weather(ob, wear=1.3, bevel=0.0, subdiv=1)

    # Back plate between the consoles and the motifs on it.
    plate_h = min(h * 0.82, 0.62)
    bm = bmesh.new()
    K.box_bm(bm, u0 + 0.06, u1 - 0.06, -0.07, 0.0, v - th - plate_h, v - th)
    ob = K.bm_object(name + "_fregio", bm, F.high, F.frame, stone)
    K.densify(ob, 0.06)
    K.weather(ob, wear=1.4, bevel=0.01, subdiv=2)
    n = spec["n"]
    half = 0.11 if spec["console"] != "beast" else 0.13
    xs = [u0 + 0.22 + (W - 0.44) * k / (n - 1) for k in range(n)]
    bm = bmesh.new()
    for a, b in zip(xs[:-1], xs[1:]):
        pc, pv = (a + b) / 2, v - th - plate_h / 2
        pw = (b - a) - 2 * half - 0.10
        if spec["panel"] == "recessed":
            for (p0, p1, q0, q1) in ((pc - pw / 2, pc + pw / 2, pv + plate_h * 0.36, pv + plate_h * 0.42),
                                     (pc - pw / 2, pc + pw / 2, pv - plate_h * 0.42, pv - plate_h * 0.36),
                                     (pc - pw / 2, pc - pw / 2 + 0.05, pv - plate_h * 0.42, pv + plate_h * 0.42),
                                     (pc + pw / 2 - 0.05, pc + pw / 2, pv - plate_h * 0.42, pv + plate_h * 0.42)):
                K.box_bm(bm, p0, p1, -0.10, -0.07, q0, q1)
        elif spec["panel"] == "fleur":
            fleur(bm, pc, -0.07, pv - 0.02, max(0.22, min(pw, plate_h)) * 0.95)
        else:
            rosette(bm, pc, -0.07, pv, min(pw, plate_h) * 0.33)
    if bm.verts:
        ob = K.bm_object(name + "_decori", bm, F.high, F.frame, stone)
        K.densify(ob, 0.03)
        K.weather(ob, wear=0.8, bevel=0.004, subdiv=1)
    else:
        bm.free()

    # Consoles.
    for k, uc in enumerate(xs):
        nm = "%s_mensola%d" % (name, k)
        cd = d - 0.05
        top = v - th
        bm, cut = bmesh.new(), bmesh.new()
        if spec["console"] == "volute":
            console_body(bm, uc, half, top, cd, h)
            side_spirals(bm, uc, half, top, cd, h)
            at, r, rf, (x1, z1) = console_curve(cd, h)
            pendant(bm, uc, -(x1 + rf * 0.4), top - h)
            solid(F, nm, bm, stone, cut=cut, wear=0.9)
        elif spec["console"] == "beast":
            beast(bm, cut, uc, top, kind="lion" if k % 2 == 0 else "dog", seed=k + 3, size=h / 0.5)
            solid(F, nm, bm, stone, cut=cut, voxel=0.007, smooth=14, wear=0.7)
        else:
            body_h = h * 0.62
            console_body(bm, uc, half, top, cd, body_h)
            banded_roll(bm, uc, half, top, cd, body_h)
            # Block below with a grotesque mask.
            bh = h - body_h
            K.box_bm(bm, uc - half * 0.95, uc + half * 0.95, -0.10, 0.0, top - h, top - body_h + 0.03)
            mask(bm, cut, uc, -0.10, top - body_h - bh * 0.5, half * 1.7, bh, seed=k + 11)
            solid(F, nm, bm, stone, cut=cut, wear=0.9)
            acanthus(F, nm + "_acanto", uc, half, top, cd, body_h, stone, seed=k)

    # Railing.
    A.railing(F, name + "_ringhiera", u0 + 0.05, u1 - 0.05, -d + 0.05, v, 1.0, spec["railing"])
    if spec["posts"]:
        bm = bmesh.new()
        for pu, py in ((u0 + 0.05, -d + 0.05), (u1 - 0.05, -d + 0.05)):
            K.box_bm(bm, pu - 0.018, pu + 0.018, py - 0.018, py + 0.018, v, v + 1.05)
        ob = K.bm_object(name + "_montanti", bm, F.detail, F.frame, M["iron"])
        for pu, py in ((u0 + 0.05, -d + 0.05), (u1 - 0.05, -d + 0.05)):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=F.frame.matrix_world @ Vector((pu, py, v + 1.09)))
            sp = bpy.context.active_object
            sp.data.materials.append(M["iron"])
            for c in sp.users_collection:
                c.objects.unlink(sp)
            K.link(sp, F.detail, None)
    return F


# ---------------------------------------------------------------------------------------------
# Renders

def light():
    sc = bpy.context.scene
    world = bpy.data.worlds.new("Cielo")
    world.use_nodes = True
    nt = world.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(40)
    sky.sun_intensity = 0.5
    nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0])
    nt.nodes["Background"].inputs["Strength"].default_value = 0.4
    sc.world = world
    sun = bpy.data.objects.new("Sole", bpy.data.lights.new("Sole", "SUN"))
    sun.data.energy = 3.4
    sun.data.angle = math.radians(1.0)
    # Light from the front-left and above, raking across the carving.
    sun.rotation_euler = Vector((0.55, 0.9, -0.75)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(sun)
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.6


def views(frames):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    os.makedirs(PREVIEWS, exist_ok=True)
    for name, (F, spec) in frames.items():
        W = spec["width"]
        u0, u1 = 0.8, 0.8 + W
        c = (u0 + u1) / 2
        shots = {
            "sotto": ((c - 1.6, -3.0, V_TOP - 2.0), (c, -0.2, V_TOP - 0.45), 42),
            "lato": ((u1 + 1.7, -1.9, V_TOP - 0.9), (u1 - 0.5, -0.35, V_TOP - 0.4), 40),
            "dettaglio": ((u0 + 0.22 + 0.95, -1.15, V_TOP - 0.95), (u0 + 0.22, -0.35, V_TOP - 0.45), 34),
        }
        M = F.frame.matrix_world
        for shot, (eye, target, fov) in shots.items():
            e, t = M @ Vector(eye), M @ Vector(target)
            cam.location = e
            cam.rotation_euler = (t - e).to_track_quat("-Z", "Y").to_euler()
            cam.data.lens_unit = "FOV"
            cam.data.angle = math.radians(fov)
            sc.render.filepath = os.path.join(PREVIEWS, "%s_%s.png" % (name, shot))
            bpy.ops.render.render(write_still=True)
            print("render", name, shot)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    frames = {}
    for k, (name, spec) in enumerate(VARIANTS.items()):
        frames[name] = (balcony("Balcone_" + name, k * 7.0, spec), spec)
    light()
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue
            prefs.get_devices()
            if any(dv.type == kind for dv in prefs.devices):
                for dv in prefs.devices:
                    dv.use = dv.type == kind
                bpy.context.scene.cycles.device = "GPU"
                break
    except Exception as e:  # noqa: BLE001
        print("GPU not available:", e)
    os.makedirs(SAVED, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAVED, "balconi_alta.blend"))
    views(frames)


main()
