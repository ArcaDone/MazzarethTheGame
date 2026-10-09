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
Run: blender -b --factory-startup --python m80_balcony_kit.py            (previews)
     blender -b --factory-startup --python m80_balcony_kit.py -- moduli [Lastra Mensola Decoro]
                                            (modules for Unreal; listing groups re-bakes only those)
Out: Previews/Balconi/<variant>_<view>.png, Saved/Mazzarino80/Balconi/balconi_alta.blend;
     modules: M80_Balconi.fbx + M80_Balconi.json (sizes and pivots), Textures/Balconi/T_M80_Balcone_*_{D,N,ORM}.
Modules: slabs (with their back plate) Volute / Mascheroni / Acanto; consoles Volute / Leone / Cane / Acanto;
motifs between consoles Riquadro / Giglio / Rosone; railings Dritta and PettoOca (goose-breast) at 180, 240,
300 cm - any railing goes with any stone set.
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
    "mascheroni": {"width": 2.6, "depth": 0.80, "thick": 0.13, "slab": "plain", "console": "beast", "n": 5, "h": 0.62,
                   "panel": "fleur", "railing": "straight", "posts": False, "stone": "gold"},
    # Palazzo Bartoli: volute consoles with the bellied railing.
    "volute_pettoca": {"width": 2.4, "depth": 0.80, "thick": 0.20, "slab": "moulded", "console": "volute", "n": 4, "h": 0.62,
                       "panel": "recessed", "railing": "bombe", "posts": True, "stone": "grey"},
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


def beast(bm, cut, uc, v, kind="lion", seed=1, size=1.0, out=0.0, neck=True):
    """A beast's head under the slab (top at v), jutting from the wall or, with out, from the front of a
    console whose body comes from console_body() (out = how far forward the head is moved, metres)."""
    rnd = random.Random(seed)

    def E(c, rad, rot=0.0, target=bm):
        ellipsoid(target, Vector((uc + c[0] * size, -(c[1] * size + out), v + c[2] * size)), [x * size for x in rad], rot)
    long_ = 1.0 if kind == "lion" else 1.35
    if neck:
        E((0, 0.14, -0.20), (0.13, 0.17, 0.19))                # neck block against the wall
        E((0, 0.08, -0.06), (0.17, 0.10, 0.07))                # shoulder under the slab
    else:
        E((0, 0.22, -0.20), (0.12, 0.12, 0.16))                # neck growing out of the console
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
# Parts of a balcony (facade frame; v = top of the slab)

def build_slab(F, name, stone, u0, u1, d, th, v, kind):
    bm = bmesh.new()
    K.box_bm(bm, u0, u1, -d, 0.0, v - th, v)
    solid(F, name + "_lastra", bm, stone, voxel=0.008, smooth=3, wear=0.9)
    if kind == "moulded":
        prof = K.profile_resample([(0.0, -0.025), (0.035, -0.025), ("arc", 0.035, -0.06, 0.035, 90, -90), (0.02, -0.095),
                                   (0.02, -0.11), (0.0, -th + 0.01), (0.0, -th)], 6)
        prof = [(o, v + z) for o, z in prof]
        bm = bmesh.new()
        sweep_plan(bm, [(u0, 0.0), (u0, -d), (u1, -d), (u1, 0.0)], prof)
        ob = K.bm_object(name + "_toro", bm, F.high, F.frame, stone)
        K.weather(ob, wear=1.3, bevel=0.0, subdiv=1)


def build_plate(F, name, stone, u0, u1, top, plate_h):
    """Back plate (frieze) against the wall under the slab, between and behind the consoles."""
    bm = bmesh.new()
    K.box_bm(bm, u0 + 0.06, u1 - 0.06, -0.07, 0.0, top - plate_h, top)
    ob = K.bm_object(name + "_fregio", bm, F.high, F.frame, stone)
    K.densify(ob, 0.06)
    K.weather(ob, wear=1.4, bevel=0.01, subdiv=2)


def decor(bm, kind, pc, pv, pw, plate_h):
    """Motif centred at (pc, pv) on the plate face (y = -0.07), in a bay pw wide."""
    if kind == "recessed":
        for (p0, p1, q0, q1) in ((pc - pw / 2, pc + pw / 2, pv + plate_h * 0.36, pv + plate_h * 0.42),
                                 (pc - pw / 2, pc + pw / 2, pv - plate_h * 0.42, pv - plate_h * 0.36),
                                 (pc - pw / 2, pc - pw / 2 + 0.05, pv - plate_h * 0.42, pv + plate_h * 0.42),
                                 (pc + pw / 2 - 0.05, pc + pw / 2, pv - plate_h * 0.42, pv + plate_h * 0.42)):
            K.box_bm(bm, p0, p1, -0.10, -0.07, q0, q1)
    elif kind == "fleur":
        fleur(bm, pc, -0.07, pv - 0.02, max(0.22, min(pw, plate_h)) * 0.95)
    else:
        rosette(bm, pc, -0.07, pv, min(pw, plate_h) * 0.33)


def build_decor(F, name, stone, bm):
    ob = K.bm_object(name, bm, F.high, F.frame, stone)
    K.densify(ob, 0.03)
    K.weather(ob, wear=0.8, bevel=0.004, subdiv=1)
    return ob


def build_console(F, nm, kind, uc, half, top, cd, h, stone, seed):
    """kind: volute | lion | dog | acanthus. Top of the console at `top` (under the slab), front at cd."""
    bm, cut = bmesh.new(), bmesh.new()
    if kind == "volute":
        console_body(bm, uc, half, top, cd, h)
        side_spirals(bm, uc, half, top, cd, h)
        at, r, rf, (x1, z1) = console_curve(cd, h)
        pendant(bm, uc, -(x1 + rf * 0.4), top - h)
        solid(F, nm, bm, stone, cut=cut, wear=0.9)
    elif kind in ("lion", "dog"):
        # A console like the others, reaching the edge of the slab, with a big beast's head at its front.
        console_body(bm, uc, half, top, cd, h)
        size = 0.88
        beast(bm, cut, uc, top + 0.03, kind=kind, seed=seed + 3, size=size, out=cd - 0.47 * size, neck=False)
        solid(F, nm, bm, stone, cut=cut, voxel=0.006, smooth=10, wear=0.7)
    else:
        body_h = h * 0.62
        console_body(bm, uc, half, top, cd, body_h)
        banded_roll(bm, uc, half, top, cd, body_h)
        # Block below with a grotesque mask.
        bh = h - body_h
        K.box_bm(bm, uc - half * 0.95, uc + half * 0.95, -0.10, 0.0, top - h, top - body_h + 0.03)
        mask(bm, cut, uc, -0.10, top - body_h - bh * 0.5, half * 1.7, bh, seed=seed + 11)
        solid(F, nm, bm, stone, cut=cut, wear=0.9)
        acanthus(F, nm + "_acanto", uc, half, top, cd, body_h, stone, seed=seed)


def build_railing(F, name, u0, u1, d, v, style, posts=True):
    """Iron railing on the slab: 'straight' or 'bombe' (petto d'oca); corner posts with ball finials."""
    M = A.mats()
    A.railing(F, name, u0 + 0.05, u1 - 0.05, -d + 0.05, v, 1.0, style)
    if posts:
        bm = bmesh.new()
        for pu in (u0 + 0.05, u1 - 0.05):
            K.box_bm(bm, pu - 0.018, pu + 0.018, -d + 0.05 - 0.018, -d + 0.05 + 0.018, v, v + 1.05)
            bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.035,
                                      matrix=Matrix.Translation((pu, -d + 0.05, v + 1.09)))
        K.bm_object(name + "_montanti", bm, F.detail, F.frame, M["iron"])


CONSOLE_HALF = {"volute": 0.11, "acanthus": 0.11, "lion": 0.095, "dog": 0.095}


def console_kinds(spec, k):
    c = spec["console"]
    return ("lion" if k % 2 == 0 else "dog") if c == "beast" else c


def plate_height(h):
    return min(h * 0.82, 0.62)


# ---------------------------------------------------------------------------------------------
# A whole balcony in front of a wall (previews)

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
    K.bm_object(name + "_muro", bm, F.detail, F.frame, A.stone_material("Muro_fondo", (0.50, 0.40, 0.26), (0.36, 0.28, 0.17)))
    bm = bmesh.new()
    K.box_bm(bm, uc_mid - 0.6, uc_mid + 0.6, -0.002, 0.0, v, v + 2.4)
    K.bm_object(name + "_portafinestra", bm, F.detail, F.frame, M["dark"])
    A.shutters(F, name + "_persiane", K.Opening(uc_mid - 0.6, uc_mid + 0.6, v, v + 2.4, kind="french"), True)

    build_slab(F, name, stone, u0, u1, d, th, v, spec["slab"])
    plate_h = plate_height(h)
    build_plate(F, name, stone, u0, u1, v - th, plate_h)
    n = spec["n"]
    kind0 = console_kinds(spec, 0)
    half = CONSOLE_HALF[kind0]
    xs = [u0 + 0.22 + (W - 0.44) * k / (n - 1) for k in range(n)]
    bm = bmesh.new()
    for a, b in zip(xs[:-1], xs[1:]):
        decor(bm, spec["panel"], (a + b) / 2, v - th - plate_h / 2, (b - a) - 2 * half - 0.10, plate_h)
    build_decor(F, name + "_decori", stone, bm)
    for k, uc in enumerate(xs):
        build_console(F, "%s_mensola%d" % (name, k), console_kinds(spec, k), uc, half, v - th, d - 0.05, h, stone, k)
    build_railing(F, name + "_ringhiera", u0, u1, d, v, spec["railing"], spec["posts"])
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


def use_gpu():
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
                return
    except Exception as e:  # noqa: BLE001
        print("GPU not available:", e)


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


# ---------------------------------------------------------------------------------------------
# Modules for Unreal: high-poly -> low-poly (slabs built clean, carved stone decimated) -> UV -> bake -> FBX

# Reference sizes (metres). The house builder scales the slab to the balcony and spaces the consoles.
MOD_DEPTH = 0.80
MOD_WIDTH = 2.4
RAIL_WIDTHS = (1.8, 2.4, 3.0)
SLABS = {"Volute": ("volute", 0.20, "moulded"), "Mascheroni": ("mascheroni", 0.13, "plain"), "Acanto": ("acanto", 0.17, "moulded")}
CONSOLES = {"Volute": ("volute", "volute"), "Leone": ("lion", "mascheroni"), "Cane": ("dog", "mascheroni"), "Acanto": ("acanthus", "acanto")}
DECORS = {"Riquadro": ("recessed", "volute"), "Giglio": ("fleur", "mascheroni"), "Rosone": ("rosette", "acanto")}
DECOR_BAY = 0.42
TEX_SIZE = {"Lastra": 2048, "Mensola": 1024, "Decoro": 512}
TEXTURES = os.path.join(HERE, "Textures", "Balconi")
FBX = os.path.join(HERE, "M80_Balconi.fbx")


def module_frame(name, k):
    return K.Facade(name, (k * 4.0, 30.0), (k * 4.0 + 3.0, 30.0), 0.0, 3.0)


def low_from_high(F, name, target_tris, attach):
    """Decimated copy of all the module's high-poly parts, joined, with its pivot at the attach point."""
    deps = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for ob in F.high.objects:
        if ob.type != "MESH":
            continue
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
        me.transform(ob.matrix_basis)            # parts are parented to the frame: keep frame-local coords
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    low = bpy.data.objects.new(name, me)
    K.link(low, F.low, F.frame)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    dec = low.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = min(1.0, target_tris / max(1, tris))
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(low.evaluated_get(deps))
    low.modifiers.clear()
    low.data = me2
    bpy.data.meshes.remove(me)
    me2.name = name
    mat = bpy.data.materials.new("M_" + name)
    me2.materials.append(mat)
    select_only([low], low)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0003)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.006, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.006, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    low["attach"] = list(attach)
    return low


def slab_profile(th, kind):
    """Edge of a slab, (out, z) from the top down: the moulding of build_slab with few arc segments, or plain."""
    if kind != "moulded":
        return [(0.0, 0.0), (0.0, -th)]
    pts = K.profile_resample([(0.0, 0.0), (0.0, -0.025), (0.035, -0.025), ("arc", 0.035, -0.06, 0.035, 90, -90),
                              (0.02, -0.095), (0.02, -0.11), (0.0, -th + 0.01), (0.0, -th)], 4)
    out = []
    for q in pts:
        if not out or (Vector(q) - Vector(out[-1])).length > 1e-5:
            out.append(q)
    return out


def slab_low(F, name, u0, u1, d, th, kind, plate_h):
    """Clean low poly of a slab with its back plate, built rather than decimated: top and bottom faces, the
    edge profile swept along the three free sides (one UV strip per side, mitred at the corners) and the
    plate (front, bottom, ends). Faces hidden against the wall or under the slab are left out."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")

    def face(pts, uvs, hint):
        f = bm.faces.new([bm.verts.new(p) for p in pts])
        for loop, t in zip(f.loops, uvs):
            loop[uv].uv = t
        f.normal_update()
        if f.normal.dot(Vector(hint)) < 0:
            f.normal_flip()

    # Top and bottom.
    face([(u0, 0, 0), (u1, 0, 0), (u1, -d, 0), (u0, -d, 0)], [(u0, 0), (u1, 0), (u1, -d), (u0, -d)], (0, 0, 1))
    face([(u0, 0, -th), (u1, 0, -th), (u1, -d, -th), (u0, -d, -th)],
         [(u0, 0), (u1, 0), (u1, d), (u0, d)], (0, 0, -1))
    # Edge profile along the sides: left (wall -> front), front, right (front -> wall).
    prof = slab_profile(th, kind)
    lens = [0.0]
    for a, b in zip(prof[:-1], prof[1:]):
        lens.append(lens[-1] + (Vector(b) - Vector(a)).length)
    corner = Vector((-1, -1)).normalized() * math.sqrt(2), Vector((1, -1)).normalized() * math.sqrt(2)
    sides = (((u0, 0), (u0, -d), Vector((-1, 0)), Vector((-1, 0)), corner[0]),
             ((u0, -d), (u1, -d), Vector((0, -1)), corner[0], corner[1]),
             ((u1, -d), (u1, 0), Vector((1, 0)), corner[1], Vector((1, 0))))
    for a, b, nrm, oa, ob in sides:
        a, b = Vector(a), Vector(b)
        along = (b - a).normalized()
        for (o0, z0), (o1, z1), l0, l1 in zip(prof[:-1], prof[1:], lens[:-1], lens[1:]):
            pa0, pb0 = a + oa * o0, b + ob * o0
            pa1, pb1 = a + oa * o1, b + ob * o1
            pts = [(pa0.x, pa0.y, z0), (pb0.x, pb0.y, z0), (pb1.x, pb1.y, z1), (pa1.x, pa1.y, z1)]
            uvs = [(pa0.dot(along), -l0), (pb0.dot(along), -l0), (pb1.dot(along), -l1), (pa1.dot(along), -l1)]
            # Outward normal of this band: the profile's normal turned into the side's direction.
            t = Vector((o1 - o0, z1 - z0)).normalized()
            hint = (nrm.x * -t.y, nrm.y * -t.y, t.x)
            if abs(t.y) < 1e-6 and abs(t.x) < 1e-6:
                continue
            face(pts, uvs, hint)
    # Back plate (frieze) under the slab.
    p0, p1, z1, z0 = u0 + 0.06, u1 - 0.06, -th, -th - plate_h
    face([(p0, -0.07, z0), (p1, -0.07, z0), (p1, -0.07, z1), (p0, -0.07, z1)],
         [(p0, z0), (p1, z0), (p1, z1), (p0, z1)], (0, -1, 0))
    face([(p0, 0, z0), (p1, 0, z0), (p1, -0.07, z0), (p0, -0.07, z0)],
         [(p0, 0), (p1, 0), (p1, -0.07), (p0, -0.07)], (0, 0, -1))
    for x, s in ((p0, -1), (p1, 1)):
        face([(x, 0, z0), (x, -0.07, z0), (x, -0.07, z1), (x, 0, z1)],
             [(0, z0), (-0.07, z0), (-0.07, z1), (0, z1)], (s, 0, 0))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(50))
    low = bpy.data.objects.new(name, me)
    K.link(low, F.low, F.frame)
    me.materials.append(bpy.data.materials.new("M_" + name))
    select_only([low], low)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    low["attach"] = [(u0 + u1) / 2, 0.0, 0.0]
    return low


def select_only(objs, active):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def bake(F, low, size):
    import numpy as np
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 64
    sc.render.bake.margin = 8
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.use_cage = False
    sc.render.bake.cage_extrusion = 0.02
    sc.render.bake.max_ray_distance = 0.06
    nodes = low.data.materials[0].node_tree.nodes if low.data.materials[0].use_nodes else None
    mat = low.data.materials[0]
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    high = [o for o in F.high.objects if o.type == "MESH"]
    images = {}

    def target(key, colour):
        img = bpy.data.images.new("%s_%s" % (low.name, key), size, size, alpha=False)
        img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        n = nodes.get("BakeTarget") or nodes.new("ShaderNodeTexImage")
        n.name = "BakeTarget"
        n.image = img
        nodes.active = n
        images[key] = img

    select_only(high + [low], low)
    target("D", True)
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    target("N", False)
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_clear=True)
    target("R", False)
    bpy.ops.object.bake(type="ROUGHNESS", use_clear=True)
    target("AO", False)
    bpy.ops.object.bake(type="AO", use_clear=True)
    px = {}
    for k in ("AO", "R"):
        arr = np.empty(size * size * 4, dtype=np.float32)
        images[k].pixels.foreach_get(arr)
        px[k] = arr
    orm = bpy.data.images.new(low.name + "_ORM", size, size, alpha=False)
    orm.colorspace_settings.name = "Non-Color"
    packed = np.ones(size * size * 4, dtype=np.float32)
    packed[0::4], packed[1::4], packed[2::4] = px["AO"][0::4], px["R"][0::4], 0.0
    orm.pixels.foreach_set(packed)
    os.makedirs(TEXTURES, exist_ok=True)
    settings = sc.render.image_settings
    settings.quality = 92
    base = low.name.replace("SM_", "T_")
    for key, img, fmt, ext in (("D", images["D"], "JPEG", "jpg"), ("N", images["N"], "PNG", "png"), ("ORM", orm, "JPEG", "jpg")):
        settings.file_format = fmt
        settings.color_mode = "RGB"
        img.save_render(os.path.join(TEXTURES, "%s_%s.%s" % (base, key, ext)), scene=sc)


def railing_mesh(F, name, attach):
    """The railing's curves and posts as one mesh (iron, no bake), pivot at the attach point."""
    deps = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for ob in list(F.detail.objects):
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
        me.transform(ob.matrix_basis)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials.get("M_M80_Balcone_Ferro") or bpy.data.materials.new("M_M80_Balcone_Ferro"))
    low = bpy.data.objects.new(name, me)
    K.link(low, F.low, F.frame)
    low["attach"] = list(attach)
    return low


def wants_bake(group):
    """`-- moduli Lastra Mensola` re-bakes only those groups (the others keep their textures: same UVs)."""
    args = sys.argv[sys.argv.index("--") + 2:] if "--" in sys.argv else []
    return not args or group in args


def modules():
    import json
    bpy.ops.wm.read_factory_settings(use_empty=True)
    use_gpu()
    S = stones()
    lows, manifest, k = [], {"units": "cm", "axes": "X along the wall, Y out of the wall, Z up; pivot = attach point",
                             "slabs": {}, "consoles": {}, "decors": {}, "railings": {}}, 0
    for key, (variant, th, kind) in SLABS.items():
        spec = VARIANTS[variant]
        F = module_frame("Lastra_" + key, k)
        k += 1
        stone = S[spec["stone"]]
        plate_h = plate_height(spec["h"])
        build_slab(F, F.name, stone, 0.0, MOD_WIDTH, MOD_DEPTH, th, 0.0, kind)
        build_plate(F, F.name, stone, 0.0, MOD_WIDTH, -th, plate_h)
        low = slab_low(F, "SM_M80_Balcone_Lastra_" + key, 0.0, MOD_WIDTH, MOD_DEPTH, th, kind, plate_h)
        if wants_bake("Lastra"):
            bake(F, low, TEX_SIZE["Lastra"])
        lows.append(low)
        manifest["slabs"][key] = {"mesh": low.name, "width": MOD_WIDTH * 100, "depth": MOD_DEPTH * 100,
                                  "thickness": th * 100, "plate_height": plate_h * 100,
                                  "note": "pivot at the wall, centre of the width, top of the slab; scale X and Y to the balcony"}
    for key, (kind, variant) in CONSOLES.items():
        spec = VARIANTS[variant]
        F = module_frame("Mensola_" + key, k)
        k += 1
        th = SLABS[{"volute": "Volute", "mascheroni": "Mascheroni", "acanto": "Acanto"}[variant]][1]
        build_console(F, F.name, kind, 0.0, CONSOLE_HALF[kind], 0.0, MOD_DEPTH - 0.05, spec["h"], S[spec["stone"]], k)
        low = low_from_high(F, "SM_M80_Balcone_Mensola_" + key, 7000, (0.0, 0.0, 0.0))
        if wants_bake("Mensola"):
            bake(F, low, TEX_SIZE["Mensola"])
        lows.append(low)
        manifest["consoles"][key] = {"mesh": low.name, "height": spec["h"] * 100, "depth": (MOD_DEPTH - 0.05) * 100,
                                     "width": CONSOLE_HALF[kind] * 200, "slab": variant, "slab_thickness": th * 100,
                                     "note": "pivot at the wall, centre of the console, under the slab"}
    for key, (kind, variant) in DECORS.items():
        spec = VARIANTS[variant]
        F = module_frame("Decoro_" + key, k)
        k += 1
        plate_h = plate_height(spec["h"])
        bm = bmesh.new()
        decor(bm, kind, 0.0, -plate_h / 2, DECOR_BAY, plate_h)
        build_decor(F, F.name, S[spec["stone"]], bm)
        low = low_from_high(F, "SM_M80_Balcone_Decoro_" + key, 2500, (0.0, 0.0, 0.0))
        if wants_bake("Decoro"):
            bake(F, low, TEX_SIZE["Decoro"])
        lows.append(low)
        manifest["decors"][key] = {"mesh": low.name, "bay": DECOR_BAY * 100, "plate_height": plate_h * 100,
                                   "note": "pivot on the wall at the centre of the bay, top of the plate (under the slab)"}
    for style, skey in (("straight", "Dritta"), ("bombe", "PettoOca")):
        for w in RAIL_WIDTHS:
            F = module_frame("Ringhiera_%s_%d" % (skey, w * 100), k)
            k += 1
            build_railing(F, F.name, 0.0, w, MOD_DEPTH, 0.0, style, posts=True)
            low = railing_mesh(F, "SM_M80_Balcone_Ringhiera_%s_%d" % (skey, w * 100), (w / 2, 0.0, 0.0))
            lows.append(low)
            manifest["railings"]["%s_%d" % (skey, w * 100)] = {"mesh": low.name, "width": w * 100, "depth": MOD_DEPTH * 100,
                                                               "style": skey, "note": "pivot at the wall, centre, top of the slab"}
    # Export: each module at the origin, pivot at its attach point, wall along X, outside towards -Y (Blender).
    for low in lows:
        mw = low.matrix_world.copy()
        low.parent = None
        low.matrix_world = mw
        a = Vector(low["attach"])
        low.data.transform(mathutils_translation(-a))
        low.matrix_world = mathutils_identity()
    select_only(lows, lows[0])
    bpy.ops.export_scene.fbx(filepath=FBX, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True)
    with open(FBX.replace(".fbx", ".json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    os.makedirs(SAVED, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAVED, "balconi_moduli.blend"))
    print("M80 balconies exported:", FBX)


def mathutils_translation(v):
    return Matrix.Translation(v)


def mathutils_identity():
    return Matrix.Identity(4)


def main():
    if "--" in sys.argv and "moduli" in sys.argv[sys.argv.index("--") + 1:]:
        modules()
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    frames = {}
    for k, (name, spec) in enumerate(VARIANTS.items()):
        frames[name] = (balcony("Balcone_" + name, k * 7.0, spec), spec)
    light()
    use_gpu()
    os.makedirs(SAVED, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SAVED, "balconi_alta.blend"))
    views(frames)


main()
