"""Blender 5.2: the church next to the Comune (its .blend was lost), rebuilt from photos inside the Comune's own file.

Run: blender -b "D:/Mazzarino80_Sorgenti/Edifici/Comune/comune - Copia.blend" --python m80_chiesa_comune.py -- [foto_dir]
Opens the Comune (never saved over), adds the collection "Chiesa" east of it (its facade on the same street, -Y) and
saves D:/Mazzarino80_Sorgenti/Edifici/Comune/ComuneConChiesa.blend. An existing ComuneConChiesa.blend is overwritten
only with M80_SOVRASCRIVI=1 (the user may have edited it by hand). With foto_dir: EEVEE views like the reference photos.

The church, from the photos (units of the Comune's file, metres before the final scale):
- bell tower in stone blocks against the Comune, its bell stage above the main cornice (one arch per side, rusticated
  corners, cornice, iron railing, finials);
- plastered facade framed by the tower and a stone corner pilaster; string course; main entablature with modillions
  across tower and facade, returning along the east side; iron railing on top;
- portal: columns on pedestals, arched opening with a stone frame, entablature, volutes, window with a stone frame and
  the coat of arms above; bronze door, closed;
- in front, the landing: half a cylinder of stone blocks centred on the door, and the two stairs along the facade from
  its sides, each closed on the street side by a sloping stone parapet ending in a newel;
- no railing on the landing and the stairs: it has to be the Comune's original one, placed by the user; the curves in
  Chiesa_Percorsi_Ringhiere mark where it goes (round the cylinder, along the parapets);
- nave behind with plain walls and a low tiled roof (only the outside: the door stays closed).
Materials: the Comune's (Main2 stone, Metal01 railings, Roof tiles, Marble) plus a few new ones (plaster, mortar,
bronze, wood, glass); every texture path of the file is pointed to D:/BitBucket (the file's relative paths were broken).
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FOTO = ARGS[0] if ARGS else ""
DST = r"D:/Mazzarino80_Sorgenti/Edifici/Comune/ComuneConChiesa.blend"

# ---------------------------------------------------------------- layout (metres in the Comune's file, facade at -Y)
X_COMUNE = 12.25          # the Comune's east wall
TOWER_X1 = 19.75          # tower 7.5 m wide
FACADE_X1 = 29.75         # plastered field 10 m
PIL_X1 = 31.95            # corner pilaster 2.2 m
SIDE_X = 31.55            # nave east wall (the pilaster stands 0.4 proud of it)
Y_TOWER = -23.60          # tower front
Y_FACADE = -23.20         # plaster plane
Y_PIL = -23.70            # corner pilaster front
Y_BACK = 12.0             # nave back wall
TOWER_Y1 = -14.1          # tower depth
DOOR_X = (TOWER_X1 + FACADE_X1) / 2
ENT_H = 2.6               # main entablature height
TOP_ABOVE_G = 18.4        # entablature top above the street at the door
LANDING_H = 2.2           # 13 steps of 17 cm
STEP_R, STEP_T = 0.17, 0.32
Y_STAIRS = -26.95         # street side of the Comune's east stair: the church's stairs end on the same line
STAIR_W = Y_FACADE - Y_STAIRS
LAND_R = STAIR_W - 0.14   # half a cylinder centred on the door: blocks and coping end on the same line
PARAPET = 0.35            # the stairs' stone parapets on the street side
BELL_IN = 0.4             # bell stage set back from the tower faces
BELL_H = 7.2

random.seed(80)
scene = bpy.context.scene
PLANE = bpy.data.objects.get("Plane")


def ground(x, y):
    """Height of the Comune's street plane under (x, y)."""
    if not PLANE:
        return 2.0
    inv = PLANE.matrix_world.inverted()
    o = inv @ Vector((x, y, 300.0))
    d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, _n, _i = PLANE.ray_cast(o, d)
    return (PLANE.matrix_world @ loc).z if hit else 2.0


G0 = ground(DOOR_X, Y_FACADE - LAND_R - 0.5)
Z_TOP = G0 + TOP_ABOVE_G
Z_ENT = Z_TOP - ENT_H
LZ = G0 + LANDING_H
Z_LOW = min(ground(x, y) for x in (X_COMUNE, DOOR_X, PIL_X1 + 1) for y in (Y_PIL - 4, Y_BACK)) - 0.6


# ---------------------------------------------------------------- materials
def fix_paths():
    for img in bpy.data.images:
        p = img.filepath.replace("\\", "/")
        if p.startswith("//BitBucket/"):
            img.filepath = "D:/" + p[2:]
            img.reload()


def tex_material(name, image, tint, rough=0.85, metal=0.0, normal=None, per_block=False, flat=0.0):
    """Texture x tint; flat > 0 blends the texture towards the plain tint (a lime plaster that only keeps a trace of
    the stone's grain)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if image and os.path.exists(image):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(image, check_existing=True)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(t.outputs["Color"], mix.inputs["A"])
        mix.inputs["B"].default_value = tint
        result = mix.outputs["Result"]
        if flat:
            mixf = nt.nodes.new("ShaderNodeMix")
            mixf.data_type = "RGBA"
            mixf.inputs["Factor"].default_value = flat
            nt.links.new(result, mixf.inputs["A"])
            mixf.inputs["B"].default_value = tint
            result = mixf.outputs["Result"]
        if per_block:
            attr = nt.nodes.new("ShaderNodeAttribute")
            attr.attribute_name = "Col"
            mix2 = nt.nodes.new("ShaderNodeMix")
            mix2.data_type = "RGBA"
            mix2.blend_type = "MULTIPLY"
            mix2.inputs["Factor"].default_value = 1.0
            nt.links.new(result, mix2.inputs["A"])
            nt.links.new(attr.outputs["Color"], mix2.inputs["B"])
            result = mix2.outputs["Result"]
        nt.links.new(result, bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = tint
    if normal and os.path.exists(normal):
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = bpy.data.images.load(normal, check_existing=True)
        tn.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return m


TX = "D:/BitBucket/mazzareththegame/Assets/"
SANDSTONE = TX + "NewTexture/sandstone_cracks_4k/textures/sandstone_cracks_"
CONCRETE = TX + "NewTexture/concrete_wall_003_4k/textures/concrete_wall_003_"


def materials():
    fix_paths()
    M = {}
    M["pietra"] = tex_material("Chiesa_Pietra", SANDSTONE + "diff_4k.jpg", (0.98, 0.84, 0.62, 1), 0.9,
                               normal=SANDSTONE + "nor_gl_4k.jpg", per_block=True)
    M["malta"] = tex_material("Chiesa_Malta", SANDSTONE + "diff_4k.jpg", (0.62, 0.52, 0.40, 1), 0.95)
    M["intonaco"] = tex_material("Chiesa_Intonaco", SANDSTONE + "diff_4k.jpg", (0.80, 0.71, 0.64, 1), 0.92, flat=0.7)
    M["intonaco_lato"] = tex_material("Chiesa_IntonacoLato", SANDSTONE + "diff_4k.jpg", (0.86, 0.76, 0.62, 1), 0.92)
    M["bronzo"] = tex_material("Chiesa_Bronzo", None, (0.07, 0.085, 0.075, 1), 0.6, metal=0.3)
    M["campana"] = tex_material("Chiesa_Campana", None, (0.35, 0.26, 0.12, 1), 0.4, metal=1.0)
    M["legno"] = tex_material("Chiesa_Legno", TX + "texture2/rough_wood_diff_4k.jpg", (0.55, 0.36, 0.2, 1), 0.7)
    M["vetro"] = tex_material("Chiesa_Vetro", None, (0.05, 0.07, 0.08, 1), 0.1)
    M["buio"] = tex_material("Chiesa_Buio", None, (0.02, 0.02, 0.02, 1), 1.0)
    M["ferro"] = bpy.data.materials.get("Metal01") or tex_material("Chiesa_Ferro", None, (0.03, 0.03, 0.03, 1), 0.5, 0.8)
    M["tegole"] = bpy.data.materials.get("Roof") or tex_material("Chiesa_Tegole", None, (0.5, 0.25, 0.15, 1), 0.8)
    M["marmo"] = bpy.data.materials.get("Marble") or tex_material("Chiesa_Marmo", None, (0.9, 0.9, 0.88, 1), 0.3)
    return M


# ---------------------------------------------------------------- mesh building
class MB:
    """A bmesh in world coordinates; finish() makes the object with box-projected UVs (1 UV = TEX metres)."""
    TEX = 2.0

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []
        self.col = self.bm.loops.layers.float_color.new("Col")
        self.tint = (1.0, 1.0, 1.0, 1.0)

    def mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def face(self, pts, m, out=None):
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = self.mi(m)
        for l in f.loops:
            l[self.col] = self.tint
        if out is not None:
            f.normal_update()
            if f.normal.dot(Vector(out)) < 0:
                f.normal_flip()
        return f

    def box(self, x0, x1, y0, y1, z0, z1, m):
        P = [Vector((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        q = [((0, 1, 3, 2), (0, 0, -1)), ((4, 5, 7, 6), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)),
             ((2, 3, 7, 6), (0, 1, 0)), ((0, 2, 6, 4), (-1, 0, 0)), ((1, 3, 7, 5), (1, 0, 0))]
        for idx, out in q:
            self.face([P[i] for i in idx], m, out)

    def obox(self, c, u, v, w, hu, hv, hw, m):
        """Box centred at c with half sizes along the orthonormal axes u, v, w."""
        c, u, v, w = Vector(c), Vector(u), Vector(v), Vector(w)
        P = [c + u * (su * hu) + v * (sv * hv) + w * (sw * hw) for sw in (-1, 1) for sv in (-1, 1) for su in (-1, 1)]
        q = [((0, 1, 3, 2), -w), ((4, 5, 7, 6), w), ((0, 1, 5, 4), -v), ((2, 3, 7, 6), v), ((0, 2, 6, 4), -u), ((1, 3, 7, 5), u)]
        for idx, out in q:
            self.face([P[i] for i in idx], m, out)

    def sweep(self, path, axis_a, axis_b, profile, m, caps=True, closed=False):
        """Profile [(a, b)] (open, interior on its left) swept along path; axis_a/axis_b per path point."""
        rings = [[p + a * pa + b * pb for (pa, pb) in profile] for p, a, b in zip(path, axis_a, axis_b)]
        n = len(path)
        segs = n if closed else n - 1
        for i in range(segs):
            r0, r1 = rings[i], rings[(i + 1) % n]
            a, b = (axis_a[i] + axis_a[(i + 1) % n]).normalized(), (axis_b[i] + axis_b[(i + 1) % n]).normalized()
            for k in range(len(profile) - 1):
                (a0, b0), (a1, b1) = profile[k], profile[k + 1]
                out = a * (b1 - b0) - b * (a1 - a0)
                self.face([r0[k], r0[k + 1], r1[k + 1], r1[k]], m, out)
        if caps and not closed:
            d0 = path[1] - path[0]
            d1 = path[-1] - path[-2]
            self.face(rings[0], m, -d0)
            self.face(rings[-1], m, d1)

    def lathe(self, cx, cy, profile, m, segs=24, z0=0.0):
        """Profile [(r, z)] from bottom to top around the vertical axis at (cx, cy)."""
        rings = []
        for r, z in profile:
            rings.append([Vector((cx + r * math.cos(2 * math.pi * s / segs), cy + r * math.sin(2 * math.pi * s / segs), z0 + z))
                          for s in range(segs)])
        for k in range(len(profile) - 1):
            for s in range(segs):
                s1 = (s + 1) % segs
                mid = (rings[k][s] + rings[k + 1][s1]) / 2
                out = Vector((mid.x - cx, mid.y - cy, 0))
                dr = profile[k + 1][0] - profile[k][0]
                out = out.normalized() * (profile[k + 1][1] - profile[k][1]) - Vector((0, 0, dr))
                if out.length < 1e-6:
                    out = Vector((0, 0, 1 if profile[k + 1][1] >= profile[k][1] else -1))
                self.face([rings[k][s], rings[k][s1], rings[k + 1][s1], rings[k + 1][s]], m, out)
        if profile[0][0] > 1e-4:
            self.face(rings[0], m, (0, 0, -1))
        if profile[-1][0] > 1e-4:
            self.face(rings[-1], m, (0, 0, 1))

    def finish(self, coll, bevel=0.0, smooth=False):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-4)
        uv = self.bm.loops.layers.uv.new("UVMap")
        for f in self.bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                l[uv].uv = (c.x, c.y) if ax == 2 else ((c.y, c.z) if ax == 0 else (c.x, c.z))
                l[uv].uv /= self.TEX
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        if bevel:
            bv = ob.modifiers.new("Spigoli", "BEVEL")
            bv.width = bevel
            bv.segments = 1
            bv.limit_method = "ANGLE"
            bv.harden_normals = True
        return ob


def frame(u):
    """Wall frame for a facade direction u (horizontal): outward normal = right of u."""
    u = Vector(u).normalized()
    return u, Vector((u.y, -u.x, 0))


def wall(mb, origin, u, length, z0, z1, m, holes=(), thick=0.6, reveal_m=None, back=True):
    """Wall from origin along u (outward normal on the right of u), with holes (uc, w, zb, zt, arched)."""
    u, n = frame(u)
    O = Vector(origin)
    up = Vector((0, 0, 1))
    reveal_m = reveal_m or m

    def P(s, z, d=0.0):
        return O + u * s + Vector((0, 0, z)) - n * d

    def top(h, s):
        uc, w, zb, zt, arched = h
        if not arched:
            return zt
        r = w / 2
        return zt - r + math.sqrt(max(r * r - (s - uc) ** 2, 0.0))

    cuts = {0.0, length}
    for h in holes:
        uc, w = h[0], h[1]
        k = 16 if h[4] else 1
        for i in range(k + 1):
            cuts.add(uc - w / 2 + w * i / k)
    cuts = sorted(c for c in cuts if 0 <= c <= length)
    sides = [(0.0, n)] + ([(thick, -n)] if back else [])
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2
        # every hole in this slice, bottom to top (a door with a window above it share the same slices)
        stack = sorted((h for h in holes if h[0] - h[1] / 2 <= mid <= h[0] + h[1] / 2), key=lambda h: h[2])
        za = zb_ = z0
        for h in stack:
            if h[2] > max(za, zb_) + 1e-4:
                for d, out in sides:
                    mb.face([P(a, za, d), P(b, zb_, d), P(b, h[2], d), P(a, h[2], d)], m, out)
                mb.face([P(a, h[2], 0), P(b, h[2], 0), P(b, h[2], thick), P(a, h[2], thick)], reveal_m, up)
            # reveal head: flat, or the arch's intrados in slices
            ta, tb = top(h, a), top(h, b)
            mb.face([P(a, ta, 0), P(b, tb, 0), P(b, tb, thick), P(a, ta, thick)], reveal_m,
                    -up if not h[4] else (Vector((0, 0, h[3] - h[1] / 2)) + u * h[0] - (u * mid + up * (ta + tb) / 2)))
            za, zb_ = ta, tb
        if z1 > min(za, zb_) + 1e-4:
            for d, out in sides:
                mb.face([P(a, za, d), P(b, zb_, d), P(b, z1, d), P(a, z1, d)], m, out)
    for h in holes:
        uc, w, zb, zt, arched = h
        zs = zt - w / 2 if arched else zt
        for s, out in ((uc - w / 2, u), (uc + w / 2, -u)):
            mb.face([P(s, zb, 0), P(s, zs, 0), P(s, zs, thick), P(s, zb, thick)], reveal_m, out)


def ashlar(mb, origin, u, length, z0, z1, m, course=0.42, skip=(), proud=0.03, gap=0.014, short=0.65, long=1.45,
           corner_out=False):
    """Stone blocks on a wall face (proud of it), staggered courses; skip = [(u0, u1, za, zb)] left free."""
    u, n = frame(u)
    O = Vector(origin)
    z = z0
    row = 0
    while z < z1 - 0.05:
        h = min(course * random.uniform(0.9, 1.1), z1 - z)
        s = -random.uniform(0, short) if row % 2 else 0.0
        while s < length - 0.02:
            L = random.uniform(short, long)
            a, b = max(s, 0.0), min(s + L, length)
            s += L
            if b - a < 0.12:
                continue
            if any(a < k[1] and b > k[0] and z < k[3] and z + h > k[2] for k in skip):
                continue
            pr = proud + random.uniform(-0.008, 0.012)
            c = O + u * ((a + b) / 2) + Vector((0, 0, z + h / 2)) + n * (pr / 2 - 0.02)
            k = random.uniform(0.78, 1.08)
            mb.tint = (k * random.uniform(0.97, 1.03), k, k * random.uniform(0.88, 1.0), 1.0)
            mb.obox(c, u, n, (0, 0, 1), (b - a - gap) / 2, (pr + 0.04) / 2, (h - gap) / 2, m)
            mb.tint = (1.0, 1.0, 1.0, 1.0)
        z += h
        row += 1


def sweep_h(mb, pts, z, profile, m, caps=True):
    """Horizontal moulding along a plan polyline [(x, y)]; profile [(out, up)], out to the right of travel."""
    P = [Vector((x, y, z)) for x, y in pts]
    A = []
    for i in range(len(P)):
        dirs = []
        if i > 0:
            dirs.append((P[i] - P[i - 1]).normalized())
        if i < len(P) - 1:
            dirs.append((P[i + 1] - P[i]).normalized())
        ns = [Vector((d.y, -d.x, 0)) for d in dirs]
        if len(ns) == 2:
            mvec = ns[0] + ns[1]
            mvec = mvec / (1 + ns[0].dot(ns[1])) if 1 + ns[0].dot(ns[1]) > 1e-3 else ns[1]
        else:
            mvec = ns[0]
        A.append(mvec)
    mb.sweep(P, A, [Vector((0, 0, 1))] * len(P), profile, m, caps)


def sweep_outline(mb, pts2d, origin, u, profile, m, closed=False):
    """Moulding around an outline drawn on a wall [(s, z)] (s along u); profile [(out of wall, towards the outline's
    right side in the wall plane)]."""
    u, n = frame(u)
    O = Vector(origin)
    P = [O + u * s + Vector((0, 0, z)) for s, z in pts2d]
    B = []
    cnt = len(P)
    for i in range(cnt):
        dirs = []
        if i > 0 or closed:
            dirs.append((P[i] - P[i - 1]).normalized())
        if i < cnt - 1 or closed:
            dirs.append((P[(i + 1) % cnt] - P[i]).normalized())
        ns = [d.cross(n).normalized() for d in dirs]
        if len(ns) == 2:
            k = 1 + ns[0].dot(ns[1])
            mvec = (ns[0] + ns[1]) / k if k > 1e-3 else ns[1]
        else:
            mvec = ns[0]
        B.append(mvec)
    mb.sweep(P, [n] * cnt, B, profile, m, caps=not closed, closed=closed)


def arch_pts(uc, w, zs, n=16):
    r = w / 2
    return [(uc - r * math.cos(math.pi * i / n), zs + r * math.sin(math.pi * i / n)) for i in range(n + 1)]


# ---------------------------------------------------------------- the church
def build(coll, M):
    objs = []
    gx = lambda x: ground(x, Y_PIL - 1.0)

    # ---- tower: mortar backing + blocks
    mb = MB("Chiesa_Torre")
    wall(mb, (X_COMUNE, Y_TOWER, 0), (1, 0, 0), TOWER_X1 - X_COMUNE, Z_LOW, Z_ENT, M["malta"], back=False)
    wall(mb, (TOWER_X1, Y_TOWER, 0), (0, 1, 0), Y_FACADE - Y_TOWER, Z_LOW, Z_ENT, M["malta"], back=False)
    # two small windows (dark slits) and the marble plaque
    tc = (X_COMUNE + TOWER_X1) / 2
    for zc in (G0 + 11.0, G0 + 13.6):
        mb.box(tc - 0.175, tc + 0.175, Y_TOWER - 0.05, Y_TOWER + 0.3, zc, zc + 0.45, M["buio"])
    mb.box(tc - 0.8, tc + 0.8, Y_TOWER - 0.08, Y_TOWER + 0.1, G0 + 3.0, G0 + 5.4, M["marmo"])
    # bell stage
    bx0, bx1 = X_COMUNE + BELL_IN, TOWER_X1 - BELL_IN
    by0, by1 = Y_TOWER + BELL_IN, Y_TOWER + BELL_IN + (bx1 - bx0)
    bz0, bz1 = Z_TOP, Z_TOP + BELL_H
    side = bx1 - bx0
    hole = (side / 2, 2.5, bz0 + 0.9, bz0 + 5.7, True)
    corners = [((bx0, by0), (1, 0, 0)), ((bx1, by0), (0, 1, 0)), ((bx1, by1), (-1, 0, 0)), ((bx0, by1), (0, -1, 0))]
    for (cx, cy), u in corners:
        wall(mb, (cx, cy, 0), u, side, bz0, bz1, M["malta"], holes=[hole], thick=0.9, reveal_m=M["pietra"])
    mb.box(bx0 + 0.9, bx1 - 0.9, by0 + 0.9, by1 - 0.9, bz0 + 0.85, bz0 + 0.9, M["pietra"])   # belfry floor
    objs.append(mb.finish(coll))

    mb = MB("Chiesa_Conci")
    ashlar(mb, (X_COMUNE, Y_TOWER, 0), (1, 0, 0), TOWER_X1 - X_COMUNE, Z_LOW, Z_ENT, M["pietra"],
           skip=[((TOWER_X1 - X_COMUNE) / 2 - 0.9, (TOWER_X1 - X_COMUNE) / 2 + 0.9, G0 + 2.9, G0 + 5.5),
                 ((TOWER_X1 - X_COMUNE) / 2 - 0.27, (TOWER_X1 - X_COMUNE) / 2 + 0.27, G0 + 10.9, G0 + 11.55),
                 ((TOWER_X1 - X_COMUNE) / 2 - 0.27, (TOWER_X1 - X_COMUNE) / 2 + 0.27, G0 + 13.5, G0 + 14.15)])
    ashlar(mb, (FACADE_X1, Y_PIL, 0), (1, 0, 0), PIL_X1 - FACADE_X1, Z_LOW, Z_ENT, M["pietra"])
    ashlar(mb, (PIL_X1, Y_PIL, 0), (0, 1, 0), 2.2, Z_LOW, Z_ENT, M["pietra"])
    ashlar(mb, (FACADE_X1, Y_FACADE, 0), (0, -1, 0), Y_FACADE - Y_PIL, Z_LOW, Z_ENT, M["pietra"], short=0.2, long=0.5)
    # bell stage: rusticated corners (alternating long and short blocks) and the arch voussoirs
    for (cx, cy), u in corners:
        uu, nn = frame(u)
        z = bz0
        k = 0
        while z < bz1 - 0.1:
            h = min(0.48, bz1 - z)
            for s0, L in ((0.0, 1.3 if k % 2 else 0.9), (side - (1.3 if k % 2 else 0.9), 1.3 if k % 2 else 0.9)):
                c = Vector((cx, cy, 0)) + uu * (s0 + L / 2) + Vector((0, 0, z + h / 2)) + nn * 0.05
                mb.obox(c, uu, nn, (0, 0, 1), (L - 0.02) / 2, 0.09, (h - 0.03) / 2, M["pietra"])
            z += h
            k += 1
        uc, w, zb, zt, _ = hole
        r = w / 2
        for i in range(9):
            a0, a1 = math.pi * i / 9, math.pi * (i + 1) / 9
            am = (a0 + a1) / 2
            rad = Vector((-math.cos(am), 0, math.sin(am)))
            cpos = Vector((cx, cy, 0)) + uu * (uc - (r + 0.32) * math.cos(am)) + Vector((0, 0, zt - r + (r + 0.32) * math.sin(am))) + nn * 0.06
            tang = uu * math.sin(am) + Vector((0, 0, math.cos(am)))
            radial = uu * rad.x + Vector((0, 0, rad.z))
            mb.obox(cpos, tang.normalized(), nn, radial.normalized(), (r + 0.32) * (a1 - a0) / 2 - 0.012, 0.1,
                    0.3 + (0.08 if i % 2 else 0.0), M["pietra"])
    objs.append(mb.finish(coll, bevel=0.012))

    # ---- facade (plaster) with the door and the window, nave walls
    mb = MB("Chiesa_Facciata")
    win_w, win_zb, win_zt = 1.35, LZ + 8.35, LZ + 10.55
    door = (DOOR_X - TOWER_X1, 2.6, LZ, LZ + 5.1, True)
    win = (DOOR_X - TOWER_X1, win_w, win_zb, win_zt, False)
    wall(mb, (TOWER_X1, Y_FACADE, 0), (1, 0, 0), FACADE_X1 - TOWER_X1, Z_LOW, Z_ENT, M["intonaco"], holes=[door, win],
         thick=1.2, reveal_m=M["pietra"], back=False)
    wall(mb, (SIDE_X, Y_FACADE + 1.5, 0), (0, 1, 0), Y_BACK - Y_FACADE - 1.5, Z_LOW, Z_TOP - 0.3, M["intonaco_lato"],
         holes=[(9.0, 1.6, G0 + 9.5, G0 + 13.5, True), (21.0, 1.6, G0 + 9.5, G0 + 13.5, True)], thick=0.8, back=False)
    wall(mb, (SIDE_X, Y_BACK, 0), (-1, 0, 0), SIDE_X - X_COMUNE, Z_LOW, Z_TOP - 0.3, M["intonaco_lato"], back=False)
    wall(mb, (X_COMUNE, Y_BACK, 0), (0, -1, 0), Y_BACK - TOWER_Y1, Z_LOW, Z_TOP - 0.3, M["intonaco_lato"], back=False)
    # the corner pilaster's front between the blocks and the side wall
    mb.box(FACADE_X1, PIL_X1 - 0.02, Y_PIL + 0.02, Y_FACADE + 1.5, Z_LOW, Z_ENT, M["malta"])
    # dark interior behind the openings (the door is closed but the window glass shows depth)
    mb.box(TOWER_X1 + 0.5, FACADE_X1 - 0.5, Y_FACADE + 1.2, Y_FACADE + 1.3, LZ, Z_ENT, M["buio"])
    # stone plinth along the facade behind the landing and the pilaster's moulded base
    sweep_h(mb, [(TOWER_X1, Y_FACADE), (FACADE_X1, Y_FACADE)], Z_LOW,
            [(0.0, 0.0), (0.12, 0.0), (0.12, LZ - Z_LOW + 0.25), (0.05, LZ - Z_LOW + 0.35), (0.0, LZ - Z_LOW + 0.35)], M["pietra"])
    sweep_h(mb, [(FACADE_X1 - 0.15, Y_PIL), (PIL_X1, Y_PIL), (PIL_X1, Y_PIL + 2.6)], Z_LOW,
            [(0.0, 0.0), (0.25, 0.0), (0.25, gx(PIL_X1) - Z_LOW + 2.1), (0.12, gx(PIL_X1) - Z_LOW + 2.3),
             (0.12, gx(PIL_X1) - Z_LOW + 2.45), (0.0, gx(PIL_X1) - Z_LOW + 2.55)], M["pietra"])
    objs.append(mb.finish(coll))

    # ---- mouldings: string course, main entablature, modillions, bell stage cornice
    mb = MB("Chiesa_Cornici")
    front = [(X_COMUNE, Y_TOWER), (TOWER_X1, Y_TOWER), (TOWER_X1, Y_FACADE), (FACADE_X1, Y_FACADE), (FACADE_X1, Y_PIL),
             (PIL_X1, Y_PIL), (PIL_X1, Y_PIL + 2.2)]
    sweep_h(mb, front, G0 + 9.0, [(0.0, 0.0), (0.12, 0.02), (0.18, 0.12), (0.18, 0.28), (0.1, 0.34), (0.0, 0.36)], M["pietra"])
    ent = [(X_COMUNE, Y_FACADE), (SIDE_X, Y_FACADE), (SIDE_X, Y_BACK)]
    prof = [(0.0, 0.0), (0.55, 0.0), (0.55, 0.32), (0.6, 0.36), (0.6, 0.7), (0.66, 0.76), (0.62, 0.82),   # architrave
            (0.5, 0.82), (0.5, 1.75),                                                                    # frieze
            (0.58, 1.8), (0.66, 1.92), (0.7, 2.0), (1.15, 2.08), (1.25, 2.2), (1.3, 2.35), (1.3, 2.5),    # cornice
            (1.2, 2.55), (1.0, ENT_H), (0.0, ENT_H)]
    sweep_h(mb, ent, Z_ENT, prof, M["pietra"])
    # modillions in the frieze, over the front and the tower
    x = X_COMUNE + 0.6
    while x < SIDE_X - 0.3:
        mb.box(x - 0.16, x + 0.16, Y_FACADE - 0.72, Y_FACADE - 0.45, Z_ENT + 1.0, Z_ENT + 1.72, M["pietra"])
        x += 1.1
    bell_ring = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1), (bx0, by0), (bx1, by0)]
    sweep_h(mb, bell_ring, bz1, [(0.0, 0.0), (0.15, 0.05), (0.2, 0.2), (0.45, 0.32), (0.5, 0.5), (0.4, 0.58), (0.0, 0.6)],
            M["pietra"], caps=False)
    sweep_h(mb, bell_ring, bz0, [(0.0, 0.0), (0.3, 0.0), (0.3, 0.35), (0.15, 0.45), (0.0, 0.5)], M["pietra"], caps=False)
    # roof slab of the bell stage and the flat roof behind the facade's railing
    mb.box(bx0 + 0.3, bx1 - 0.3, by0 + 0.3, by1 - 0.3, bz1 + 0.4, bz1 + 0.55, M["pietra"])
    objs.append(mb.finish(coll, bevel=0.01))

    # ---- portal: columns, pilasters, frame, entablature, volutes, window frame, coat of arms
    mb = MB("Chiesa_Portale")
    yf = Y_FACADE
    for sgn in (-1, 1):
        cx = DOOR_X + sgn * 2.05
        mb.box(cx - 0.45, cx + 0.45, yf - 0.85, yf, LZ, LZ + 1.15, M["pietra"])          # pedestal
        mb.box(cx - 0.5, cx + 0.5, yf - 0.9, yf, LZ + 1.15, LZ + 1.3, M["pietra"])
        mb.box(cx - 0.32 + sgn * 0.5, cx + 0.32 + sgn * 0.5, yf - 0.12, yf, LZ + 1.3, LZ + 6.25, M["pietra"])  # pilaster
        col = [(0.34, 0.0), (0.36, 0.06), (0.3, 0.14), (0.28, 0.2), (0.25, 0.3), (0.255, 2.0), (0.235, 4.3),
               (0.26, 4.36), (0.24, 4.42), (0.3, 4.62), (0.36, 4.8), (0.38, 4.88)]
        mb.lathe(cx, yf - 0.43, col, M["pietra"], segs=20, z0=LZ + 1.3)
        mb.box(cx - 0.42, cx + 0.42, yf - 0.85, yf, LZ + 6.18, LZ + 6.35, M["pietra"])  # abacus
        # carved flutes: thin vertical ribs on the shaft
        for k in range(8):
            a = 2 * math.pi * k / 8
            mb.obox((cx + 0.255 * math.cos(a), yf - 0.43 + 0.255 * math.sin(a), LZ + 1.3 + 2.3), (math.cos(a), math.sin(a), 0),
                    (-math.sin(a), math.cos(a), 0), (0, 0, 1), 0.02, 0.025, 1.9, M["pietra"])
    # door frame (moulded jambs and arch)
    pts = [(DOOR_X - TOWER_X1 - 1.3, LZ)] + [(s, z) for s, z in arch_pts(DOOR_X - TOWER_X1, 2.6, LZ + 3.8)] + [(DOOR_X - TOWER_X1 + 1.3, LZ)]
    sweep_outline(mb, list(reversed(pts)), (TOWER_X1, yf, 0), (1, 0, 0),
                  [(0.0, 0.0), (0.18, 0.0), (0.2, 0.08), (0.2, 0.3), (0.12, 0.38), (0.0, 0.42)], M["pietra"])
    # keystone
    mb.box(DOOR_X - 0.28, DOOR_X + 0.28, yf - 0.32, yf, LZ + 4.75, LZ + 5.55, M["pietra"])
    # portal entablature over the columns
    ex0, ex1 = DOOR_X - 2.75, DOOR_X + 2.75
    mb.box(ex0, ex1, yf - 0.9, yf, LZ + 6.35, LZ + 6.8, M["pietra"])                     # architrave
    mb.box(ex0 + 0.05, ex1 - 0.05, yf - 0.85, yf, LZ + 6.8, LZ + 7.2, M["pietra"])       # frieze
    mb.box(ex0 - 0.08, ex1 + 0.08, yf - 1.0, yf, LZ + 7.2, LZ + 7.32, M["pietra"])       # cornice
    mb.box(ex0 - 0.02, ex1 + 0.02, yf - 0.95, yf, LZ + 7.32, LZ + 7.55, M["pietra"])
    # window frame with "ears" and the small cornice above it
    wl, wr = DOOR_X - TOWER_X1 - win_w / 2, DOOR_X - TOWER_X1 + win_w / 2
    sweep_outline(mb, [(wl, win_zb), (wr, win_zb), (wr, win_zt), (wl, win_zt)], (TOWER_X1, yf, 0), (1, 0, 0),
                  [(0.0, 0.0), (0.14, 0.0), (0.16, 0.1), (0.16, 0.28), (0.0, 0.3)], M["pietra"], closed=True)
    for sx in (-1, 1):
        mb.box(DOOR_X + sx * (win_w / 2 + 0.22) - 0.12, DOOR_X + sx * (win_w / 2 + 0.22) + 0.12, yf - 0.16, yf,
               win_zt - 0.05, win_zt + 0.3, M["pietra"])
    mb.box(DOOR_X - 1.15, DOOR_X + 1.15, yf - 0.35, yf, win_zt + 0.3, win_zt + 0.55, M["pietra"])
    # volutes above the columns (scrolls lying on the entablature, flanking the window)
    for sgn in (-1, 1):
        cx = DOOR_X + sgn * 2.05
        spiral = []
        # an S scroll: big curl down on the entablature, small curl up against the window frame
        for i in range(60):
            t = i / 59
            if t < 0.5:
                tt = t / 0.5
                ang = math.pi * (1.0 + 2.2 * (1 - tt))
                rr = 0.42 * (0.35 + 0.65 * tt)
                cx2, cz2 = 0.0, LZ + 7.55 + 0.42
            else:
                tt = (t - 0.5) / 0.5
                ang = math.pi * (0.0 - 2.0 * tt)
                rr = 0.28 * (1 - 0.6 * tt)
                cx2, cz2 = -0.7, LZ + 7.55 + 1.1
            spiral.append((cx - TOWER_X1 + sgn * (cx2 + rr * math.cos(ang)), cz2 + rr * math.sin(ang)))
        sweep_outline(mb, spiral, (TOWER_X1, yf - 0.6, 0), (1, 0, 0),
                      [(0.0, -0.09), (0.3, -0.09), (0.3, 0.09), (0.0, 0.09), (0.0, -0.09)], M["pietra"])
        mb.box(cx - 0.35, cx + 0.35, yf - 0.95, yf - 0.25, LZ + 7.55, LZ + 7.65, M["pietra"])
    # coat of arms: shield with a crown
    shield = []
    for i in range(21):
        t = i / 20
        x = -0.38 + 0.76 * t
        z = -0.55 * (1 - (2 * t - 1) ** 2) ** 0.5 if 0.0 < t < 1.0 else 0.0
        shield.append((DOOR_X + x, z))
    zc = win_zt + 1.25
    pts3 = [Vector((x, yf - 0.25, zc + z)) for x, z in shield] + [Vector((DOOR_X + 0.38, yf - 0.25, zc + 0.45)),
                                                                   Vector((DOOR_X - 0.38, yf - 0.25, zc + 0.45))]
    mb.face(pts3, M["pietra"], (0, -1, 0))
    back = [p + Vector((0, 0.25, 0)) for p in pts3]
    for i in range(len(pts3)):
        mb.face([pts3[i], pts3[(i + 1) % len(pts3)], back[(i + 1) % len(pts3)], back[i]], M["pietra"],
                ((pts3[i] + pts3[(i + 1) % len(pts3)]) / 2 - Vector((DOOR_X, yf - 0.25, zc))))
    mb.box(DOOR_X - 0.45, DOOR_X + 0.45, yf - 0.3, yf, zc + 0.45, zc + 0.62, M["pietra"])
    for k in range(5):
        x = DOOR_X - 0.36 + 0.18 * k
        mb.box(x - 0.04, x + 0.04, yf - 0.28, yf, zc + 0.62, zc + 0.82 + (0.06 if k % 2 == 0 else 0), M["pietra"])
    objs.append(mb.finish(coll, bevel=0.008))

    # ---- door (closed, bronze) and the window's shutters
    mb = MB("Chiesa_Portone")
    yd = yf + 0.35
    outline = [(DOOR_X - 1.3, LZ)] + [(TOWER_X1 + s, z) for s, z in arch_pts(DOOR_X - TOWER_X1, 2.6, LZ + 3.8)] + [(DOOR_X + 1.3, LZ)]
    poly = [Vector((x, yd, z)) for x, z in outline]
    mb.face(poly, M["bronzo"], (0, -1, 0))
    for sx in (-1, 1):
        for k in range(3):
            z0 = LZ + 0.35 + k * 1.15
            x0 = DOOR_X + sx * 0.15 if sx > 0 else DOOR_X - 1.1
            mb.box(x0, x0 + 0.95, yd - 0.06, yd, z0, z0 + 0.95, M["bronzo"])
    # the round relief in the lunette
    ring = [Vector((DOOR_X + 0.85 * math.cos(2 * math.pi * k / 32), yd - 0.07, LZ + 3.8 + 0.85 * math.sin(2 * math.pi * k / 32)))
            for k in range(32)]
    mb.face(ring, M["bronzo"], (0, -1, 0))
    for k in range(32):
        a, b = ring[k], ring[(k + 1) % 32]
        mb.face([a, b, b + Vector((0, 0.07, 0)), a + Vector((0, 0.07, 0))], M["bronzo"], (a + b) / 2 - Vector((DOOR_X, yd, LZ + 3.8)))
    mb.box(DOOR_X - 0.03, DOOR_X + 0.03, yd - 0.08, yd, LZ, LZ + 4.3, M["bronzo"])
    # window: dark glass and wooden shutters, half closed
    mb.box(DOOR_X - win_w / 2, DOOR_X + win_w / 2, yf + 0.5, yf + 0.55, win_zb, win_zt, M["vetro"])
    for sx in (-1, 1):
        mb.box(DOOR_X + (0.02 if sx > 0 else -win_w / 2), DOOR_X + (win_w / 2 if sx > 0 else -0.02), yf + 0.38, yf + 0.45,
               win_zb + 0.02, win_zt - 0.02, M["legno"])
    # side windows of the nave: glass
    for yc in (Y_FACADE + 1.5 + 9.0, Y_FACADE + 1.5 + 21.0):
        mb.box(SIDE_X - 0.5, SIDE_X - 0.45, yc - 0.8, yc + 0.8, G0 + 9.5, G0 + 13.5, M["vetro"])
    objs.append(mb.finish(coll))

    # ---- bell
    mb = MB("Chiesa_Campana")
    bcx, bcy = (bx0 + bx1) / 2, (by0 + by1) / 2
    bell = [(0.0, 0.0), (0.52, 0.0), (0.5, 0.08), (0.42, 0.3), (0.34, 0.62), (0.3, 0.86), (0.2, 0.95), (0.0, 0.97)]
    mb.lathe(bcx, by0 + 0.45, bell, M["campana"], segs=24, z0=bz0 + 3.0)
    mb.box(bcx - 0.6, bcx + 0.6, by0 + 0.35, by0 + 0.55, bz0 + 3.97, bz0 + 4.17, M["legno"])
    objs.append(mb.finish(coll, smooth=True))

    # ---- landing: half a stone cylinder centred on the door, as deep as the stairs; the stairs run along the facade
    # from its sides, closed on the street side by sloping stone parapets that start inside the cylinder
    mb = MB("Chiesa_Sagrato")
    ys = Y_FACADE - STAIR_W
    R = LAND_R
    xp = math.sqrt(max(R * R - (R - PARAPET) ** 2, 0.0)) - 0.05   # where a parapet's inner face meets the cylinder
    xs0 = R * 0.87                                                   # first step, where the round front is half out

    def arc(r, a0, a1, n):
        return [(DOOR_X + r * math.cos(a0 + (a1 - a0) * i / n), Y_FACADE - r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

    front = arc(R, 0.0, math.pi, 40)
    mb.face([Vector((x, y, LZ)) for x, y in front], M["pietra"], (0, 0, 1))
    # mortar behind the blocks of the round front, then the blocks course by course
    for (x0, y0), (x1, y1) in zip(front, front[1:]):
        mb.face([Vector((x0, y0, Z_LOW)), Vector((x1, y1, Z_LOW)), Vector((x1, y1, LZ - 0.22)), Vector((x0, y0, LZ - 0.22))],
                M["malta"], ((x0 + x1) / 2 - DOOR_X, (y0 + y1) / 2 - Y_FACADE, 0))
    z = Z_LOW
    row = 0
    while z < LZ - 0.25:
        h = min(0.46, LZ - 0.22 - z)
        a = -(0.06 if row % 2 else 0.0)
        while a < math.pi - 0.01:
            da = random.uniform(0.55, 1.0) / R
            a0, a1 = max(a, 0.0), min(a + da, math.pi)
            a += da
            if a1 - a0 < 0.03:
                continue
            am = (a0 + a1) / 2
            radial = Vector((math.cos(am), -math.sin(am), 0))
            tang = Vector((-math.sin(am), -math.cos(am), 0))
            c = Vector((DOOR_X, Y_FACADE, z + h / 2)) + radial * (R + 0.01)
            k = random.uniform(0.8, 1.08)
            mb.tint = (k, k, k * random.uniform(0.88, 1.0), 1.0)
            mb.obox(c, tang, radial, (0, 0, 1), R * (a1 - a0) / 2 - 0.007, 0.03, h / 2 - 0.007, M["pietra"])
            mb.tint = (1.0, 1.0, 1.0, 1.0)
        z += h
        row += 1
    # coping ring at the top of the cylinder
    sweep_h(mb, front, LZ - 0.22, [(0.0, 0.0), (0.1, 0.0), (0.12, 0.04), (0.12, 0.2), (0.06, 0.22), (0.0, 0.22)], M["pietra"])
    ends = {}
    for d in (-1, 1):
        x0 = DOOR_X + d * xs0
        # top of the stair behind the parapet, between the cylinder and the first step
        xa, xb = sorted((DOOR_X + d * xp * 0.6, x0))
        mb.box(xa, xb, ys + PARAPET, Y_FACADE, Z_LOW, LZ, M["pietra"])
        x = x0
        zt = LZ
        k = 0
        while zt > ground(x, ys) + 0.06 and k < 24:
            z1 = max(zt - STEP_R, ground(x + d * STEP_T, ys))
            xa, xb = sorted((x, x + d * STEP_T))
            mb.box(xa, xb, ys + PARAPET, Y_FACADE, Z_LOW, z1, M["pietra"])
            x += d * STEP_T
            zt = z1
            k += 1
        xe = x
        # parapet: from inside the cylinder down to the foot of the stair, top 0.3 above the step noses
        pa = DOOR_X + d * xp
        n = 12
        top = []
        for i in range(n + 1):
            xi = pa + (xe - pa) * i / n
            t = min(max((xi - x0) * d / max((xe - x0) * d, 1e-3), 0.0), 1.0)
            top.append((xi, max(LZ + 0.3 - (LZ - zt) * t, ground(xi, ys) + 0.55)))
        for (xa_, za_), (xb_, zb_) in zip(top, top[1:]):
            for yy, out in ((ys, (0, -1, 0)), (ys + PARAPET, (0, 1, 0))):
                mb.face([Vector((xa_, yy, Z_LOW)), Vector((xb_, yy, Z_LOW)), Vector((xb_, yy, zb_)), Vector((xa_, yy, za_))],
                        M["pietra"], out)
            mb.face([Vector((xa_, ys, za_)), Vector((xb_, ys, zb_)), Vector((xb_, ys + PARAPET, zb_)),
                     Vector((xa_, ys + PARAPET, za_))], M["pietra"], (0, 0, 1))

        def topz(xq):
            for (xa_, za_), (xb_, zb_) in zip(top, top[1:]):
                if min(xa_, xb_) - 1e-6 <= xq <= max(xa_, xb_) + 1e-6:
                    return za_ + (zb_ - za_) * (xq - xa_) / (xb_ - xa_)
            return top[-1][1]

        # blocks on the street face, the top course cut along the slope under the coping
        z = Z_LOW
        row = 0
        lo_x, hi_x = sorted((pa, xe))
        while z < max(t[1] for t in top) - 0.1:
            h = 0.44
            s = lo_x - (random.uniform(0.2, 0.5) if row % 2 else 0.0)
            while s < hi_x - 0.05:
                L = random.uniform(0.6, 1.1)
                a_, b_ = max(s, lo_x), min(s + L, hi_x)
                s += L
                ta, tb = min(z + h, topz(a_) - 0.06), min(z + h, topz(b_) - 0.06)
                if b_ - a_ < 0.1 or max(ta, tb) < z + 0.08:
                    continue
                ta, tb = max(ta, z + 0.02), max(tb, z + 0.02)
                k = random.uniform(0.8, 1.08)
                mb.tint = (k, k, k * random.uniform(0.88, 1.0), 1.0)
                y0_, y1_ = ys - 0.03, ys + 0.02
                g = 0.007
                P = [Vector((a_ + g, y0_, z + g)), Vector((b_ - g, y0_, z + g)), Vector((b_ - g, y0_, tb - g)), Vector((a_ + g, y0_, ta - g))]
                Q = [Vector((v.x, y1_, v.z)) for v in P]
                mb.face(P, M["pietra"], (0, -1, 0))
                for i in range(4):
                    j = (i + 1) % 4
                    mb.face([P[i], P[j], Q[j], Q[i]], M["pietra"], (P[i] + P[j]) / 2 - (P[0] + P[2]) / 2 + Vector((0, -0.001, 0)))
                mb.tint = (1.0, 1.0, 1.0, 1.0)
            z += h
            row += 1
        # small newel at the foot: the parapet's end block, a little higher, with a thin cap
        xn0, xn1 = sorted((xe - d * 0.05, xe + d * 0.35))
        gz = ground((xn0 + xn1) / 2, ys + PARAPET / 2)
        zn = top[-1][1] + 0.12
        mb.box(xn0, xn1, ys, ys + PARAPET, Z_LOW, zn, M["pietra"])
        mb.box(xn0 - 0.03, xn1 + 0.03, ys - 0.03, ys + PARAPET + 0.03, zn, zn + 0.07, M["pietra"])
        ends[d] = {"top": top, "first_step": x0, "newel": ((xn0 + xn1) / 2, zn + 0.07)}
    objs.append(mb.finish(coll, bevel=0.01))
    return objs, {"ys": ys, "xp": xp, "ends": ends}, (bx0, bx1, by0, by1, bz1)


# ---------------------------------------------------------------- railings
def path_curve(name, coll, pts, corners=()):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for i, q in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = Vector(q)
        kind = "VECTOR" if i in corners or i in (0, len(pts) - 1) else "AUTO"
        bp.handle_left_type = bp.handle_right_type = kind
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    return ob


def iron_railing(mb, pts, z, h, m, spacing=0.14):
    """Light railing for the roofs: two rails and square bars."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        a, b = Vector((x0, y0, z)), Vector((x1, y1, z))
        d = (b - a)
        L = d.length
        u = d.normalized()
        n = Vector((u.y, -u.x, 0))
        for zz, t in ((0.08, 0.03), (h - 0.04, 0.045)):
            mb.obox((a + b) / 2 + Vector((0, 0, zz)), u, n, (0, 0, 1), L / 2, t / 2, t / 2, m)
        k = max(1, int(L / spacing))
        for i in range(k + 1):
            p = a + u * (L * i / k)
            mb.obox(p + Vector((0, 0, h / 2)), u, n, (0, 0, 1), 0.009, 0.009, h / 2, m)
        for i in range(int(L) + 1):
            p = a + u * min(i, L)
            mb.obox(p + Vector((0, 0, h / 2)), u, n, (0, 0, 1), 0.025, 0.025, h / 2 + 0.03, m)


def railings(coll, M, sag, bell):
    """Where the Comune's railing goes (the user places it): round the cylinder between the parapets, along the
    parapets' coping down to the newels. Bezier curves for an Array (fit to curve) + Curve modifier."""
    objs = []
    guides = bpy.data.collections.new("Chiesa_Percorsi_Ringhiere")
    coll.children.link(guides)
    ys, xp = sag["ys"], sag["xp"]
    r = LAND_R - 0.15
    pa = math.acos(min(xp / r, 1.0))
    arc_pts = [(DOOR_X + r * math.cos(pa + (math.pi - 2 * pa) * i / 8), Y_FACADE - r * math.sin(pa + (math.pi - 2 * pa) * i / 8), LZ)
               for i in range(9)]
    objs.append(path_curve("Chiesa_Percorso_Sagrato", guides, arc_pts))
    for d, e in sag["ends"].items():
        top = e["top"]
        zf = min(top, key=lambda t: abs(t[0] - e["first_step"]))[1]
        pts = [(top[0][0], ys + PARAPET / 2, top[0][1]), (e["first_step"], ys + PARAPET / 2, zf),
               (e["newel"][0], ys + PARAPET / 2, e["newel"][1])]
        objs.append(path_curve("Chiesa_Percorso_Scala" + ("Sinistra" if d < 0 else "Destra"), guides, pts, corners=(1,)))
    bx0, bx1, by0, by1, bz1 = bell
    mb = MB("Chiesa_RinghiereTetto")
    iron_railing(mb, [(TOWER_X1, Y_FACADE - 0.75), (SIDE_X + 0.9, Y_FACADE - 0.75), (SIDE_X + 0.9, Y_FACADE + 3.0)], Z_TOP, 1.0, M["ferro"])
    iron_railing(mb, [(X_COMUNE + 0.3, Y_FACADE - 0.75), (bx0, Y_FACADE - 0.75)], Z_TOP, 1.0, M["ferro"])
    e = 0.25
    iron_railing(mb, [(bx0 - e, by0 - e), (bx1 + e, by0 - e), (bx1 + e, by1 + e), (bx0 - e, by1 + e), (bx0 - e, by0 - e)],
                 bz1 + 0.6, 1.0, M["ferro"])
    # small finials on the bell stage corners
    for cx, cy in ((bx0 - e, by0 - e), (bx1 + e, by0 - e), (bx1 + e, by1 + e), (bx0 - e, by1 + e)):
        mb.lathe(cx, cy, [(0.0, 0.0), (0.12, 0.0), (0.12, 0.15), (0.06, 0.25), (0.09, 0.4), (0.03, 0.7), (0.0, 0.75)],
                 M["pietra"], segs=12, z0=bz1 + 0.6)
    objs.append(mb.finish(coll))
    return objs


# ---------------------------------------------------------------- roof
def roof(coll, M):
    mb = MB("Chiesa_Tetto")
    x0, x1 = X_COMUNE, SIDE_X + 0.4
    y0, y1 = Y_FACADE + 0.6, Y_BACK + 0.4
    rx = (x0 + x1) / 2
    zr = Z_TOP + 1.3
    ze = Z_TOP - 0.35
    mb.face([Vector((x0, y0, ze)), Vector((x0, y1, ze)), Vector((rx, y1, zr)), Vector((rx, y0, zr))], M["tegole"], (-0.3, 0, 1))
    mb.face([Vector((rx, y0, zr)), Vector((rx, y1, zr)), Vector((x1, y1, ze)), Vector((x1, y0, ze))], M["tegole"], (0.3, 0, 1))
    mb.face([Vector((x0, y0, ze)), Vector((rx, y0, zr)), Vector((x1, y0, ze))], M["intonaco_lato"], (0, -1, 0))
    mb.face([Vector((x0, y1, ze)), Vector((x1, y1, ze)), Vector((rx, y1, zr))], M["intonaco_lato"], (0, 1, 0))
    # the tower's roof between its walls and the bell stage
    mb.box(X_COMUNE, TOWER_X1, Y_TOWER, TOWER_Y1, Z_TOP - 0.1, Z_TOP, M["pietra"])
    return [mb.finish(coll)]


# ---------------------------------------------------------------- views
def views(out_dir, coll):
    os.makedirs(out_dir, exist_ok=True)
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    world = bpy.data.worlds.new("Chiesa_Cielo")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.55, 0.7, 0.95, 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    for o in list(scene.objects):
        if o.type == "LIGHT":
            o.hide_render = True
    sun = bpy.data.objects.new("Chiesa_Sole", bpy.data.lights.new("Chiesa_Sole", "SUN"))
    sun.data.energy = 4.0
    sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("Chiesa_Cam", bpy.data.cameras.new("Chiesa_Cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.clip_end = 1000
    shots = {
        "1_fronte": ((DOOR_X, Y_FACADE - 26, G0 + 1.7), (DOOR_X, Y_FACADE, G0 + 10.5), 24),
        "2_da_sinistra": ((DOOR_X - 24, Y_FACADE - 22, G0 + 1.7), (DOOR_X - 1, Y_FACADE, G0 + 10), 24),
        "3_da_destra": ((DOOR_X + 18, Y_FACADE - 18, G0 + 1.7), (DOOR_X - 2, Y_FACADE, G0 + 11), 22),
        "4_portale": ((DOOR_X + 3, Y_FACADE - 11, G0 + 1.7), (DOOR_X, Y_FACADE, LZ + 5), 26),
        "5_alto": ((DOOR_X + 30, Y_FACADE - 45, G0 + 32), (DOOR_X - 8, Y_FACADE + 8, G0 + 8), 30),
        "6_comune_e_chiesa": ((X_COMUNE - 30, Y_FACADE - 40, G0 + 4), (X_COMUNE + 4, Y_FACADE, G0 + 10), 24),
        "7_scala_destra": ((DOOR_X + LAND_R + 6, Y_FACADE - 7, G0 + 1.7), (DOOR_X + LAND_R + 1, Y_FACADE - 1, G0 + 1.2), 24),
        "8_sagrato": ((DOOR_X - 4.5, Y_FACADE - 8.5, G0 + 1.6), (DOOR_X - 0.5, Y_FACADE - 2.0, LZ - 0.2), 26),
    }
    for name, (loc, at, lens) in shots.items():
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        scene.render.filepath = os.path.join(out_dir, name + ".png")
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.objects.remove(sun)


def main():
    if os.path.exists(DST) and os.environ.get("M80_SOVRASCRIVI") != "1":
        print("M80 ComuneConChiesa.blend esiste gia': M80_SOVRASCRIVI=1 per rifarlo")
        return
    M = materials()
    old = bpy.data.collections.get("Chiesa")
    if old:
        for o in list(old.all_objects):
            bpy.data.objects.remove(o)
        for c in list(old.children_recursive):
            bpy.data.collections.remove(c)
        bpy.data.collections.remove(old)
    coll = bpy.data.collections.new("Chiesa")
    scene.collection.children.link(coll)
    objs, sag, bell = build(coll, M)
    objs += railings(coll, M, sag, bell)
    objs += roof(coll, M)
    bpy.ops.wm.save_as_mainfile(filepath=DST, copy=False)
    tris = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in coll.all_objects:
        if o.type == "MESH":
            ev = o.evaluated_get(dg)
            tris += sum(len(p.vertices) - 2 for p in ev.data.polygons)
    print("M80 chiesa: G0 %.2f, landing %.2f, top %.2f, %d objects, %d triangles" % (G0, LZ, Z_TOP, len(coll.all_objects), tris))
    if FOTO:
        views(FOTO, coll)


main()
