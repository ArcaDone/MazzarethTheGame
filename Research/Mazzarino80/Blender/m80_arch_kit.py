"""Architecture kit for Blender (Mazzarino 80): facades built twice, high-poly and low-poly, for baking.

Every facade is built in its own frame: X along the facade (u, metres from its left end), Z up (v, metres
above the street at the facade) and Y into the building, so the outside is -Y. The frame is an Empty
placed on the facade's left end; all parts are parented to it.

High-poly ("<Facade>_High" collection): real detail - rubble wall displaced stone by stone, ashlar blocks
with eroded edges, mouldings with many segments, fine relief in the material bump (it bakes into the
normal map too).
Low-poly ("<Facade>_Low"): clean retopology of the same shapes - flat wall with the openings cut, plain
boxes for ashlar, mouldings with few segments - unwrapped in one atlas and baked from the high-poly
(normal, ambient occlusion, colour, roughness).
Details that keep their own geometry and material in the game (glass, shutters, doors, iron railings)
go to "<Facade>_Detail".
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector


# ---------------------------------------------------------------------------------------------
# Scene and mesh helpers

def collection(name, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def link(ob, col, frame=None):
    col.objects.link(ob)
    if frame is not None:
        ob.parent = frame
    return ob


def bm_object(name, bm, col, frame=None, mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    if mat:
        me.materials.append(mat)
    return link(ob, col, frame)


def box_bm(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in f])
    return v


def add_bevel(ob, width, segments=2):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    return m


def apply_modifiers(ob):
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def weather(ob, wear=1.0, bevel=0.012, subdiv=2):
    """Centuries of weather on a stone element (high-poly only): irregular rounded edges, erosion at two
    scales and chipped edges. Displacements use global coordinates, so no two pieces wear alike."""
    if bevel:
        add_bevel(ob, bevel, 2)
    s = ob.modifiers.new("Subdiv", "SUBSURF")
    s.subdivision_type = "CATMULL_CLARK"
    s.levels = s.render_levels = subdiv
    s.use_creases = False
    big = bpy.data.textures.get("M80_Erosione") or bpy.data.textures.new("M80_Erosione", "CLOUDS")
    big.noise_scale = 0.12
    big.noise_depth = 2
    d = ob.modifiers.new("Erosione", "DISPLACE")
    d.texture = big
    d.strength = 0.010 * wear
    d.texture_coords = "GLOBAL"
    small = bpy.data.textures.get("M80_Grana") or bpy.data.textures.new("M80_Grana", "DISTORTED_NOISE")
    small.noise_scale = 0.025
    small.distortion = 1.5
    d = ob.modifiers.new("Grana", "DISPLACE")
    d.texture = small
    d.strength = 0.003 * wear
    d.texture_coords = "GLOBAL"
    chips = bpy.data.textures.get("M80_Scheggiature")
    if not chips:
        # Blotchy noise cut by a ramp: only the top few percent become chips (small pits).
        chips = bpy.data.textures.new("M80_Scheggiature", "CLOUDS")
        chips.noise_scale = 0.045
        chips.noise_depth = 1
        chips.use_color_ramp = True
        el = chips.color_ramp.elements
        el[0].position, el[0].color = 0.64, (0, 0, 0, 1)
        el[1].position, el[1].color = 0.70, (1, 1, 1, 1)
    d = ob.modifiers.new("Scheggiature", "DISPLACE")
    d.texture = chips
    d.strength = -0.012 * wear
    d.mid_level = 0.0
    d.texture_coords = "GLOBAL"
    return ob


def densify(ob, step):
    """Split every edge longer than step (grid-filled), so displacement has vertices to move."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    groups = {}
    for e in bm.edges:
        c = int(e.calc_length() / step)
        if c > 0:
            groups.setdefault(min(c, 150), []).append(e)
    for c, es in sorted(groups.items(), reverse=True):
        es = [e for e in es if e.is_valid]
        if es:
            bmesh.ops.subdivide_edges(bm, edges=es, cuts=c, use_grid_fill=True)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def resample_path(path, step, closed=False):
    """Insert points so no segment is longer than step (dense sweeps take displacement well)."""
    out = []
    n = len(path)
    segs = n if closed else n - 1
    for i in range(segs):
        a, b = Vector(path[i]), Vector(path[(i + 1) % n])
        k = max(1, int(math.ceil((b - a).length / step)))
        for j in range(k):
            p = a.lerp(b, j / k)
            out.append((p.x, p.y))
    if not closed:
        out.append(tuple(path[-1]))
    return out


def noise_displace(ob, strength, size, subdiv=0, seed=0):
    """Eroded stone: optional subdivision, then a cloud-noise displacement along the normals."""
    if subdiv:
        s = ob.modifiers.new("Subdiv", "SUBSURF")
        s.subdivision_type = "SIMPLE"
        s.levels = s.render_levels = subdiv
    tex = bpy.data.textures.new(ob.name + "_noise", "CLOUDS")
    tex.noise_scale = size
    tex.noise_depth = 2
    d = ob.modifiers.new("Erosion", "DISPLACE")
    d.texture = tex
    d.strength = strength
    d.mid_level = 0.5
    d.texture_coords = "GLOBAL"
    ob.location.x += seed * 0.0  # keeps the signature explicit; the global coords already vary per block


# ---------------------------------------------------------------------------------------------
# Frame of a facade

class Facade:
    def __init__(self, name, p0, p1, z0, height, outward_right=True):
        self.name = name
        a, b = Vector((p0[0], p0[1], 0)), Vector((p1[0], p1[1], 0))
        d = b - a
        self.width = d.length
        self.height = height
        self.dir = d.normalized()
        # Frame: X = along, Y = into the building, Z = up. "outward_right": the outside is on the right
        # walking from p0 to p1 (true for a facade traced with the building on its left).
        inward = Vector((-self.dir.y, self.dir.x, 0)) if outward_right else Vector((self.dir.y, -self.dir.x, 0))
        self.frame = bpy.data.objects.new(name + "_Frame", None)
        bpy.context.scene.collection.objects.link(self.frame)
        m = Matrix.Identity(4)
        m.col[0][:3] = self.dir
        m.col[1][:3] = inward
        m.col[2][:3] = (0, 0, 1) if outward_right else (0, 0, -1)
        if not outward_right:
            # Keep a right-handed frame: flip X instead of Z.
            m.col[0][:3] = -self.dir
            m.col[2][:3] = (0, 0, 1)
        m.col[3][:3] = (a.x, a.y, z0)
        self.frame.matrix_world = m
        self.high = collection(name + "_High")
        self.low = collection(name + "_Low")
        self.detail = collection(name + "_Detail")
        self.openings = []


# ---------------------------------------------------------------------------------------------
# Openings: rectangles, optionally with a round arch on top (semicircle or segmental)

class Opening:
    def __init__(self, u0, u1, v0, v1, arch=0.0, kind="window", depth=0.30):
        self.u0, self.u1, self.v0, self.v1 = u0, u1, v0, v1
        self.arch = arch          # rise of the arch above v1 (0 = flat head)
        self.kind = kind
        self.depth = depth

    @property
    def top(self):
        return self.v1 + self.arch

    def outline(self, seg=16):
        """Closed outline (u, v), counter-clockwise seen from outside (-Y)."""
        pts = [(self.u1, self.v0), (self.u1, self.v1)]
        if self.arch > 0:
            half = (self.u1 - self.u0) / 2
            r = (half * half + self.arch * self.arch) / (2 * self.arch)
            cu, cv = (self.u0 + self.u1) / 2, self.v1 + self.arch - r
            a0 = math.atan2(self.v1 - cv, half)
            for k in range(1, seg):
                t = a0 + (math.pi - 2 * a0) * k / seg
                pts.append((cu + r * math.cos(t), cv + r * math.sin(t)))
        pts += [(self.u0, self.v1), (self.u0, self.v0)]
        return pts

    def contains(self, u, v):
        """Vectorised point test (numpy arrays)."""
        inside = (u > self.u0) & (u < self.u1) & (v > self.v0) & (v < self.v1)
        if self.arch > 0:
            half = (self.u1 - self.u0) / 2
            r = (half * half + self.arch * self.arch) / (2 * self.arch)
            cu, cv = (self.u0 + self.u1) / 2, self.v1 + self.arch - r
            inside |= ((u - cu) ** 2 + (v - cv) ** 2 < r * r) & (v >= self.v1) & (u > self.u0) & (u < self.u1)
        return inside


# ---------------------------------------------------------------------------------------------
# Procedural noise and the rubble wall ("pietrame")

def _hash(i, j, s=0):
    h = (i.astype(np.int64) * 374761393 + j.astype(np.int64) * 668265263 + s * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def value_noise(u, v, scale, seed=0, octaves=3):
    out = np.zeros_like(u)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        x, y = u / scale, v / scale
        i, j = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
        fx, fy = x - i, y - j
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = _hash(i, j, seed + o), _hash(i + 1, j, seed + o)
        c, d = _hash(i, j + 1, seed + o), _hash(i + 1, j + 1, seed + o)
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
        tot += amp
        amp *= 0.5
        scale *= 0.5
    return out / tot


def rubble(u, v, cell=(0.21, 0.14), seed=7, mortar=0.016):
    """Irregular stones in thick mortar. Returns (height m, stone random 0-1, edge distance m)."""
    cu, cv = cell
    # Roughly coursed: every row of cells is shifted a little.
    i0 = np.floor(u / cu).astype(np.int64)
    j0 = np.floor(v / cv).astype(np.int64)
    f1 = np.full(u.shape, 9.0)
    f2 = np.full(u.shape, 9.0)
    sid = np.zeros(u.shape)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            i, j = i0 + di, j0 + dj
            px = (i + 0.15 + 0.7 * _hash(i, j, seed)) * cu
            py = (j + 0.15 + 0.7 * _hash(i, j, seed + 1)) * cv
            # Half euclidean, half chebyshev: angular, roughly squared stones rather than pebbles.
            dx, dy = np.abs(u - px) / 1.15, np.abs(v - py)
            dist = 0.5 * np.sqrt(dx * dx + dy * dy) + 0.5 * np.maximum(dx, dy)
            closer = dist < f1
            f2 = np.where(closer, f1, np.minimum(f2, dist))
            sid = np.where(closer, _hash(i, j, seed + 2), sid)
            f1 = np.minimum(f1, dist)
    edge = f2 - f1
    mortar = mortar + 0.010 * value_noise(u, v, 0.4, seed + 5, 2)
    dome = np.clip((edge - mortar) / 0.035, 0, 1) ** 0.35
    fine = value_noise(u, v, 0.025, seed + 9, 3)
    chip = value_noise(u, v, 0.07, seed + 13, 2)
    h = np.where(edge < mortar, 0.002 * fine,
                 0.010 + 0.016 * dome + 0.010 * sid + 0.006 * (fine - 0.5) * dome - 0.006 * (chip > 0.68) * dome)
    return h, sid, edge - mortar


# Stone colours (linear): warm limestone and sandstone of the Mazzarino area, a few grey stones;
# golden but sandy, less orange than the first cut, as in the street photos.
STONE = np.array([[0.52, 0.39, 0.205], [0.57, 0.445, 0.24], [0.60, 0.51, 0.35], [0.47, 0.36, 0.205],
                  [0.41, 0.38, 0.325], [0.55, 0.445, 0.285]])
MORTAR = np.array([0.58, 0.49, 0.35])


def rubble_albedo(u, v, h, sid, edge, seed=7):
    idx = np.minimum((sid * len(STONE) * 1.6).astype(int) % len(STONE), len(STONE) - 1)
    rare = sid > 0.93
    idx = np.where(rare, 4, idx)
    col = STONE[idx]
    tint = (0.78 + 0.30 * value_noise(u, v, 0.05, seed + 11, 3))[..., None]
    col = col * tint
    # Mortar darkens in the joints (dirt) and lightens on the flush parts.
    m = (edge < 0)[..., None]
    joint = np.clip(-edge / 0.02, 0, 1)[..., None]
    col = np.where(m, MORTAR * (0.85 + 0.12 * value_noise(u, v, 0.02, seed + 3, 2))[..., None] * (1 - 0.35 * joint), col)
    # Rising damp and grime near the street, sun-bleached top.
    damp = np.clip(1 - v / 1.2, 0, 1)[..., None] * 0.22
    col = col * (1 - damp)
    return np.clip(col, 0, 1)


# ---------------------------------------------------------------------------------------------
# Wall

def grid_mesh(name, W, H, step, height_fn, keep_fn, col, frame, mat):
    """Dense wall grid in the facade frame (X=u, Z=v), displaced outward (-Y) by height_fn."""
    nu, nv = int(round(W / step)) + 1, int(round(H / step)) + 1
    us = np.linspace(0, W, nu)
    vs = np.linspace(0, H, nv)
    U, V = np.meshgrid(us, vs)
    Hm = height_fn(U, V)
    co = np.stack([U, -Hm, V], axis=-1).reshape(-1, 3)
    # Faces: keep only those whose centre is on the wall (not in an opening).
    cu = (U[:-1, :-1] + U[1:, 1:]) / 2
    cv = (V[:-1, :-1] + V[1:, 1:]) / 2
    keep = keep_fn(cu, cv).reshape(-1)
    ii, jj = np.meshgrid(np.arange(nu - 1), np.arange(nv - 1))
    a = (jj * nu + ii).reshape(-1)
    quads = np.stack([a, a + 1, a + 1 + nu, a + nu], axis=-1)[keep]
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(co))
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.astype(np.int32).ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", (np.arange(len(quads)) * 4).astype(np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(quads), 4, np.int32))
    uv = me.uv_layers.new(name="UVMap")
    lu = (co[quads.ravel(), 0] / W).astype(np.float32)
    lv = (co[quads.ravel(), 2] / H).astype(np.float32)
    uv.data.foreach_set("uv", np.stack([lu, lv], -1).ravel())
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    return link(ob, col, frame)


def image_from_array(name, arr, colorspace="sRGB"):
    h, w = arr.shape[:2]
    img = bpy.data.images.get(name)
    if img and (img.size[0] != w or img.size[1] != h):
        bpy.data.images.remove(img)
        img = None
    img = img or bpy.data.images.new(name, w, h, alpha=False, float_buffer=False)
    img.colorspace_settings.name = colorspace
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :arr.shape[2]] = arr
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def flat_wall(name, W, H, openings, col, frame, mat, thickness=0.0):
    """Low-poly wall: the outline and the openings as edge loops, triangulated around the holes.

    (A boolean leaves n-gons bridged around the holes, which triangulate across the openings.)
    """
    bm = bmesh.new()

    def loop(pts):
        vs = [bm.verts.new((u, 0.0, v)) for u, v in pts]
        for i in range(len(vs)):
            bm.edges.new((vs[i], vs[(i + 1) % len(vs)]))

    loop([(0, 0), (W, 0), (W, H), (0, H)])
    for o in openings:
        loop(o.outline())
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=bm.edges[:], normal=(0, -1, 0))
    for f in bm.faces:
        if f.normal.y > 0:
            f.normal_flip()
    return bm_object(name, bm, col, frame, mat)


def opening_prism(name, o, y0, y1):
    pts = o.outline()
    bm = bmesh.new()
    a = [bm.verts.new((u, y0, v)) for u, v in pts]
    b = [bm.verts.new((u, y1, v)) for u, v in pts]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        bm.faces.new((a[i], b[i], b[(i + 1) % n], a[(i + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.hide_render = True
    return ob


def reveal(name, o, col, frame, mat, depth=None):
    """Jambs, head and sill inside an opening, from the wall face to the window."""
    depth = o.depth if depth is None else depth
    pts = o.outline()
    bm = bmesh.new()
    a = [bm.verts.new((u, 0.0, v)) for u, v in pts]
    b = [bm.verts.new((u, depth, v)) for u, v in pts]
    n = len(pts)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # Normals must point into the opening (towards its centre).
    cu, cv = (o.u0 + o.u1) / 2, (o.v0 + o.top) / 2
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((cu - c.x, 0, cv - c.z))) < 0:
            f.normal_flip()
    return bm_object(name, bm, col, frame, mat)


# ---------------------------------------------------------------------------------------------
# Sweeps: mouldings along a path in the wall plane

def sweep(name, path, profile, col, frame, mat, closed=False, plane_normal=None, smooth=False):
    """Sweep a profile along a path of (u, v) points on the wall plane.

    profile: list of (s, t): s = across the moulding in the wall plane (away from the path, to the left
    of the walking direction unless plane_normal is given per point), t = projection out of the wall.
    plane_normal: optional function(index) -> 2D vector in the wall plane overriding the side.
    """
    if name.endswith("_hi"):
        path = resample_path(path, 0.05, closed)
    P = [Vector((u, v)) for u, v in path]
    n = len(P)
    sides = []
    for i in range(n):
        if closed or 0 < i < n - 1:
            t0 = (P[i] - P[i - 1]).normalized()
            t1 = (P[(i + 1) % n] - P[i]).normalized()
            n0, n1 = Vector((-t0.y, t0.x)), Vector((-t1.y, t1.x))
            m = (n0 + n1)
            m = m.normalized() / max(0.25, m.normalized().dot(n0)) if m.length > 1e-6 else n0
        else:
            t = (P[1] - P[0]).normalized() if i == 0 else (P[-1] - P[-2]).normalized()
            m = Vector((-t.y, t.x))
        if plane_normal:
            m = plane_normal(i, m)
        sides.append(m)
    bm = bmesh.new()
    rings = []
    for i in range(n):
        ring = [bm.verts.new((P[i].x + sides[i].x * s, -t, P[i].y + sides[i].y * s)) for s, t in profile]
        rings.append(ring)
    segs = n if closed else n - 1
    for i in range(segs):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for k in range(len(profile) - 1):
            try:
                bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
            except ValueError:
                pass
    if not closed:
        for ring in (rings[0], rings[-1]):
            back = [bm.verts.new((v.co.x, 0.0, v.co.z)) for v in (ring[0], ring[-1])]
            try:
                bm.faces.new([*ring, back[1], back[0]])
            except ValueError:
                pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, col, frame, mat, smooth=smooth)


def profile_resample(points, segments):
    """Mouldings: list of (s, t) control points; arcs given as ('arc', cs, ct, r, a0, a1)."""
    out = []
    for p in points:
        if p[0] == "arc":
            _, cs, ct, r, a0, a1 = p
            for k in range(segments + 1):
                a = math.radians(a0 + (a1 - a0) * k / segments)
                out.append((cs + r * math.cos(a), ct + r * math.sin(a)))
        else:
            out.append(p)
    return out


# Mouldings (s across, t out of the wall), metres. High uses many arc segments, low only a few.
def frame_profile(width=0.17, proj=0.06, segments=6):
    return profile_resample([(-0.02, 0.0), (-0.02, proj), (width - 0.05, proj),
                             ("arc", width - 0.05, proj - 0.025, 0.025, 90, 0),
                             (width - 0.025, 0.02), (width, 0.02), (width, 0.0)], segments)


def cornice_profile(segments=6):
    # From the wall upwards: fascia, ovolo, fillet, corona, cyma recta; s = up, t = out.
    return profile_resample([(0.0, 0.0), (0.0, 0.05), (0.14, 0.05),
                             ("arc", 0.14, 0.17, 0.12, -90, 0),
                             (0.26, 0.19), (0.29, 0.19), (0.29, 0.42), (0.40, 0.42), (0.40, 0.44),
                             ("arc", 0.46, 0.44, 0.06, 180, 90),
                             (0.52, 0.52), (0.52, 0.0)], segments)


def sill_profile(proj=0.13, segments=4):
    return profile_resample([(0.0, 0.0), (0.0, proj), ("arc", -0.03, proj, 0.03, 90, 0), (-0.06, proj),
                             (-0.06, proj - 0.02), (-0.09, 0.0)], segments)


# ---------------------------------------------------------------------------------------------
# Ashlar strips (pilasters, quoins) and blocks

def ashlar_strip(name, u0, u1, v0, v1, proj, course, cols_high, cols_low, mat_high, mat_low, frame,
                 joint=0.007, seed=1, quoin=0.0):
    """A strip of squared blocks. High: each block bevelled and eroded. Low: one box."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    v = v0
    k = 0
    while v < v1 - 0.05:
        h = min(course * (0.85 + 0.3 * rnd.random()), v1 - v)
        w0, w1 = u0, u1
        if quoin:
            # Alternating long and short blocks at a corner.
            if k % 2:
                w1 = u1 - quoin
        box_bm(bm, w0 + joint / 2, w1 - joint / 2, -proj, 0.0, v + joint / 2, v + h - joint / 2)
        v += h
        k += 1
    hi = bm_object(name + "_hi", bm, cols_high, frame, mat_high)
    densify(hi, 0.08)
    weather(hi, wear=1.3, bevel=0.018, subdiv=2)
    bm = bmesh.new()
    box_bm(bm, u0, u1, -proj, 0.0, v0, v1)
    lo = bm_object(name, bm, cols_low, frame, mat_low)
    return hi, lo
