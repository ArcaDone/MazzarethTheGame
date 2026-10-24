"""Blender 5.2: Santa Maria di Gesù (Corso Vittorio Emanuele) with the old hospital beside it and the convent ruins
behind, built from scratch on the OSM footprints, as they were in the 1980s.

Run: blender -b --factory-startup --python m80_santa_maria_gesu.py -- [foto_dir]
Saves D:/Mazzarino80_Sorgenti/Edifici/SantaMariaGesu/SantaMariaGesu.blend (refuses to overwrite it without
M80_SOVRASCRIVI=1: the user may have edited it). Three collections, one mesh each in Unreal
(m80_prepare_vehicle.py key SantaMariaGesu): SMG_Chiesa, SMG_Ospedale, SMG_Ruderi.

Where (Research/Mazzarino80/building_footprint_plan.json, world cm of L_M80_Paese_WP):
- church = OSM way 372575840, 10.3 x 37 m; facade on the short east side, on the square at the end of the Corso; the
  north flank along Viale della Repubblica, which runs down towards Via Stivala;
- old hospital = way 372575833 (rebuilt today): its front continues the line of the church's facade for 36 m, as
  far as Via Vincenzo Monti; 13.5-14.7 m deep, with a short wing towards the cloister;
- ruins = way 372575839, the convent's wings round the cloister (OSM "ruins").
The model is drawn in a local frame: origin at the facade's south corner (where the hospital starts), x along the
facade towards the Viale (the hospital is at x < 0), y into the church, z up in metres above the sea like the town
(world z / 100). FRAME turns it into Blender's world: x = world x / 100, y = -world y / 100, so Unreal's import puts
every piece back on its lot.
Ground: Saved/Mazzarino80/SantaMariaGesu/rilievo.json (Scripts/m80_smg_rilievo.py, 1 m grid of the town's terrain);
without it the ground is flat at the OSM plan's height.

From the photos (D:/PerGioco/Santa maria di gesu):
- facade: plastered field between two corner pilasters of rusticated golden stone on tall pedestals, entablature,
  triangular pediment with a cross and two ball finials; stone portal (arched door between pilasters, entablature)
  and a window with an eared stone frame above; the door closed;
- flank: rubble limestone with a tiled coping, two tall blind arches with a small door at their foot, a downpipe;
  above it, set back, the plastered upper wall of the nave with flat panels and a low tiled roof; an octagonal
  plastered drum with windows and a pyramid roof over the presbytery; a battered stone plinth along the street,
  which goes down towards the west;
- old hospital (photo of the 1970s-80s): two storeys of rubble masonry with the render fallen in patches, small
  windows with stone frames, doors up a few steps, a stone portal with an oval window above it next to the church,
  an enclosed wooden balcony on brackets, quoins at the far corner, a hipped tiled roof;
- ruins: rubble walls broken at different heights, empty windows, no roof.
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FOTO = ARGS[0] if ARGS else ""
ROOT = "D:/UE5Projects/GameAnimationSample"
DST = r"D:/Mazzarino80_Sorgenti/Edifici/SantaMariaGesu/SantaMariaGesu.blend"
TEX = "D:/Mazzarino80_Sorgenti/Edifici/SantaMariaGesu/tex/"
BB = "D:/BitBucket/mazzareththegame/Assets/"
RILIEVO = ROOT + "/Saved/Mazzarino80/SantaMariaGesu/rilievo.json"
random.seed(80)

# ---------------------------------------------------------------- frame (world cm of the town, OSM corners)
A_W = Vector((5127.18, 30927.61))     # facade, north corner (Viale della Repubblica)
C_W = Vector((5590.47, 31849.97))     # facade, south corner (the hospital starts here)
E1 = (C_W - A_W).normalized()         # along the frontage, towards the hospital's far end
E2 = Vector((-E1.y, E1.x))            # into the church
PLAN_Z = 158.88                       # ground at the church in the OSM plan (m)


def to_world_cm(x, y):
    """Local (x, y) in metres -> town world cm."""
    return C_W + (-E1 * x + E2 * y) * 100.0


def to_local(xw, yw):
    d = Vector((xw, yw)) - C_W
    return (-d.dot(E1) / 100.0, d.dot(E2) / 100.0)


# local -> Blender world: x_b = X / 100, y_b = -Y / 100 (a rotation: the town's frame is mirrored, and so is ours)
_c = to_world_cm(0, 0)
FRAME = Matrix(((-E1.x, E2.x, 0, _c.x / 100), (E1.y, -E2.y, 0, -_c.y / 100), (0, 0, 1, 0), (0, 0, 0, 1)))

# ---------------------------------------------------------------- footprints (local metres, from the OSM rings)
W = 10.32                             # church width (facade)
L = 37.0                              # church length
HOSP = [(0.0, 0.0), (-36.04, 0.62), (-35.7, 14.68), (-28.8, 14.63), (-28.74, 21.3), (-23.58, 21.26), (-23.43, 14.1),
        (0.01, 13.48)]
HOSP_MAIN = [(0.0, 0.0), (-36.04, 0.62), (-35.7, 14.68), (0.01, 13.48)]
HOSP_WING = [(-28.8, 14.63), (-28.74, 21.3), (-23.58, 21.26), (-23.43, 14.1)]   # long sides first (hip_roof)
RUINS = [(-35.73, 34.67), (-35.2, 56.84), (-22.38, 56.61), (-22.7, 39.99), (-7.74, 39.72), (0.55, 39.57), (0.5, 37.01),
         (0.33, 27.46), (-3.42, 27.52), (-3.4, 34.08), (-23.58, 34.44)]
RUIN_SKIP = {6}                       # the edge along the church's own wall


# ---------------------------------------------------------------- ground
class Ground:
    def __init__(self):
        self.grid = None
        if os.path.exists(RILIEVO):
            r = json.load(open(RILIEVO, encoding="utf-8"))
            self.x0, self.x1, self.y0, self.y1 = r["box_cm"]
            self.step = r["step_cm"]
            g = []
            for row in r["grid"]:
                g.append([(c[1][0] if c[1] else (c[0][0] if c[0] else None)) for c in row])
            self.grid = g
            print("M80 rilievo", len(g), "x", len(g[0]))
        else:
            print("M80 nessun rilievo: terreno piatto a", PLAN_Z)

    def at(self, x, y):
        if not self.grid:
            return PLAN_Z
        p = to_world_cm(x, y)
        fi = (p.x - self.x0) / self.step
        fj = (p.y - self.y0) / self.step
        i0, j0 = int(math.floor(fi)), int(math.floor(fj))
        vals, ws = 0.0, 0.0
        for dj in (0, 1):
            for di in (0, 1):
                i, j = i0 + di, j0 + dj
                if 0 <= j < len(self.grid) and 0 <= i < len(self.grid[0]) and self.grid[j][i] is not None:
                    w = (1 - abs(fi - i)) * (1 - abs(fj - j))
                    vals += self.grid[j][i] / 100.0 * w
                    ws += w
        return vals / ws if ws > 0 else PLAN_Z


G = Ground()
Z0 = G.at(W / 2, -4.0) + 0.15          # church floor: the square in front of the door, one step up
Z_LOW_CH = min(G.at(x, y) for x in (-0.5, W + 1.0) for y in range(0, 39, 2)) - 0.6
H1 = Z0 + 10.2                        # top of the flanks' rubble walls (coping)
H2 = Z0 + 12.6                        # top of the nave's plastered upper wall
Z_ENT = Z0 + 10.2                     # entablature: architrave bottom
Z_COR = Z0 + 11.5                     # cornice top
Z_APEX = Z0 + 14.6
PIL = 1.45                            # corner pilaster width
PIL_OUT = 0.45                        # how far the pilasters stand out of the facade
PED_H = 3.4                           # pedestal height


# ---------------------------------------------------------------- materials
def tex_material(name, image, tint=(1, 1, 1, 1), rough=0.85, metal=0.0, normal=None, flat=0.0):
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


def materials():
    M = {}
    M["pietrame"] = tex_material("SMG_Pietrame", TEX + "pietrame_diff.jpg", rough=0.95, normal=TEX + "broken_wall_nor_gl_4k.jpg")
    M["conci"] = tex_material("SMG_Conci", TEX + "conci_diff.jpg", (0.95, 0.95, 0.92, 1), 0.9,
                              normal=TEX + "sandstone_blocks_05_nor_gl_4k.jpg")
    # plain carved stone (cornices, frames): the same sandstone with the joints washed out
    # the flat stone and the lime plaster have their own textures (the sandstone and the old render washed towards a
    # plain colour): Unreal's import takes texture x colour and nothing in between
    M["pietra"] = tex_material("SMG_Pietra", TEX + "pietra_liscia_diff.jpg", rough=0.9)
    M["intonaco"] = tex_material("SMG_Intonaco", TEX + "intonaco_bianco_diff.jpg", rough=0.92)
    M["intonaco_vecchio"] = tex_material("SMG_IntonacoVecchio", TEX + "intonaco_vecchio_diff.jpg", (1.0, 0.94, 0.84, 1), 0.95,
                                         normal=TEX + "rough_plaster_03_nor_dx_4k.jpg")
    M["tegole"] = tex_material("SMG_Tegole", BB + "texture2/roof_3_4k/roof_tiles_14_4k/textures/roof_tiles_14_diff_4k.jpg",
                               (0.85, 0.7, 0.6, 1), 0.85)
    M["legno"] = tex_material("SMG_Legno", BB + "texture2/rough_wood_diff_4k.jpg", (0.42, 0.3, 0.2, 1), 0.75)
    M["portone"] = tex_material("SMG_Portone", BB + "texture2/rough_wood_diff_4k.jpg", (0.14, 0.16, 0.13, 1), 0.7)
    M["vetro"] = tex_material("SMG_Vetro", None, (0.06, 0.08, 0.09, 1), 0.15)
    M["vetro_chiaro"] = tex_material("SMG_VetroChiaro", None, (0.45, 0.58, 0.62, 1), 0.15)
    M["ferro"] = tex_material("SMG_Ferro", None, (0.03, 0.03, 0.03, 1), 0.5, 0.8)
    M["buio"] = tex_material("SMG_Buio", None, (0.03, 0.025, 0.02, 1), 1.0)
    return M


# ---------------------------------------------------------------- mesh building (as m80_chiesa_comune.py)
class MB:
    """A bmesh in the local frame; finish() makes the object with box-projected UVs (1 UV = tex metres)."""

    def __init__(self, name, tex=2.0):
        self.name = name
        self.tex = tex
        self.bm = bmesh.new()
        self.mats = []

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
        c, u, v, w = Vector(c), Vector(u), Vector(v), Vector(w)
        P = [c + u * (su * hu) + v * (sv * hv) + w * (sw * hw) for sw in (-1, 1) for sv in (-1, 1) for su in (-1, 1)]
        q = [((0, 1, 3, 2), -w), ((4, 5, 7, 6), w), ((0, 1, 5, 4), -v), ((2, 3, 7, 6), v), ((0, 2, 6, 4), -u), ((1, 3, 7, 5), u)]
        for idx, out in q:
            self.face([P[i] for i in idx], m, out)

    def prism(self, pts2d, z0, z1, m, top=True, bottom=True):
        """Vertical prism on a plan polygon (counter-clockwise or not)."""
        P = [Vector((x, y, 0)) for x, y in pts2d]
        n = len(P)
        cen = sum(P, Vector()) / n
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            mid = (a + b) / 2
            self.face([(a.x, a.y, z0), (b.x, b.y, z0), (b.x, b.y, z1), (a.x, a.y, z1)], m, mid - cen)
        if top:
            self.face([(p.x, p.y, z1) for p in P], m, (0, 0, 1))
        if bottom:
            self.face([(p.x, p.y, z0) for p in P], m, (0, 0, -1))

    def sweep(self, path, axis_a, axis_b, profile, m, caps=True, closed=False):
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
            self.face(rings[0], m, -(path[1] - path[0]))
            self.face(rings[-1], m, path[-1] - path[-2])

    def lathe(self, cx, cy, profile, m, segs=16, z0=0.0):
        rings = [[Vector((cx + r * math.cos(2 * math.pi * s / segs), cy + r * math.sin(2 * math.pi * s / segs), z0 + z))
                  for s in range(segs)] for r, z in profile]
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

    def finish(self, coll):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-4)
        uv = self.bm.loops.layers.uv.new("UVMap")
        for f in self.bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for lp in f.loops:
                c = lp.vert.co
                lp[uv].uv = ((c.x, c.y) if ax == 2 else ((c.y, c.z) if ax == 0 else (c.x, c.z)))
                lp[uv].uv /= self.tex
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        ob.matrix_world = FRAME
        coll.objects.link(ob)
        return ob


def frame(u):
    """Wall frame for a facade direction u (horizontal): outward normal = right of u."""
    u = Vector(u).normalized()
    return u, Vector((u.y, -u.x, 0))


def wall(mb, origin, u, length, z0, z1, m, holes=(), thick=0.6, reveal_m=None, back=True, z0_end=None):
    """Wall from origin along u (outward normal on the right of u), holes (uc, w, zb, zt, arched). z0_end: the bottom
    at the far end when it slopes (a wall standing on a sloping street)."""
    u, n = frame(u)
    O = Vector(origin)
    up = Vector((0, 0, 1))
    reveal_m = reveal_m or m

    def P(s, z, d=0.0):
        return O + u * s + Vector((0, 0, z)) - n * d

    def bot(s):
        return z0 if z0_end is None else z0 + (z0_end - z0) * s / length

    def top(h, s):
        uc, w, zb, zt, arched = h
        if not arched:
            return zt
        r = w / 2
        return zt - r + math.sqrt(max(r * r - (s - uc) ** 2, 0.0))

    cuts = {0.0, length}
    for h in holes:
        k = 12 if h[4] else 1
        for i in range(k + 1):
            cuts.add(h[0] - h[1] / 2 + h[1] * i / k)
    cuts = sorted(c for c in cuts if 0 <= c <= length)
    sides = [(0.0, n)] + ([(thick, -n)] if back else [])
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2
        stack = sorted((h for h in holes if h[0] - h[1] / 2 <= mid <= h[0] + h[1] / 2), key=lambda h: h[2])
        za, zb_ = bot(a), bot(b)
        for h in stack:
            if h[2] > max(za, zb_) + 1e-4:
                for d, out in sides:
                    mb.face([P(a, za, d), P(b, zb_, d), P(b, h[2], d), P(a, h[2], d)], m, out)
                mb.face([P(a, h[2], 0), P(b, h[2], 0), P(b, h[2], thick), P(a, h[2], thick)], reveal_m, up)
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


def ashlar(mb, origin, u, length, z0, z1, m, course=0.45, proud=0.06, gap=0.02, short=0.55, long=1.2, alt=0.0):
    """Rusticated blocks on a wall face; alt > 0 makes alternate courses shorter by alt (quoins)."""
    u, n = frame(u)
    O = Vector(origin)
    z, row = z0, 0
    while z < z1 - 0.05:
        h = min(course * random.uniform(0.92, 1.08), z1 - z)
        span = length - (alt if row % 2 else 0.0)
        s = 0.0
        while s < span - 0.02:
            Lb = min(random.uniform(short, long), span - s)
            if span - s - Lb < 0.25:
                Lb = span - s
            pr = proud + random.uniform(-0.015, 0.015)
            c = O + u * (s + Lb / 2) + Vector((0, 0, z + h / 2)) + n * (pr / 2)
            mb.obox(c, u, n, (0, 0, 1), (Lb - gap) / 2, pr / 2 + 0.01, (h - gap) / 2, m)
            s += Lb
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
            k = 1 + ns[0].dot(ns[1])
            mvec = (ns[0] + ns[1]) / k if k > 1e-3 else ns[1]
        else:
            mvec = ns[0]
        A.append(mvec)
    mb.sweep(P, A, [Vector((0, 0, 1))] * len(P), profile, m, caps)


def sweep_outline(mb, pts2d, origin, u, profile, m, closed=False):
    """Moulding round an outline drawn on a wall [(s, z)]; profile [(out of the wall, towards the outline's right)]."""
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


def arch_pts(uc, w, zs, n=12):
    r = w / 2
    return [(uc - r * math.cos(math.pi * i / n), zs + r * math.sin(math.pi * i / n)) for i in range(n + 1)]


def hip_roof(mb, quad, z, pitch, m, over=0.45, thick=0.18):
    """Hipped roof on a plan quadrilateral [f0, f1, b1, b0] (f0-f1 and b0-b1 the long sides), eaves at z."""
    f0, f1, b1, b0 = [Vector((p[0], p[1], 0)) for p in quad]
    cen = (f0 + f1 + b1 + b0) / 4
    pts = [p + (p - cen).normalized() * over * 1.41 for p in (f0, f1, b1, b0)]
    f0, f1, b1, b0 = pts
    m0, m1 = (f0 + b0) / 2, (f1 + b1) / 2
    d = (m1 - m0).normalized()
    hd = ((f0 - b0).length + (f1 - b1).length) / 4
    rise = hd * math.tan(math.radians(pitch))
    r0 = m0 + d * hd + Vector((0, 0, z + rise))
    r1 = m1 - d * hd + Vector((0, 0, z + rise))
    e = [p + Vector((0, 0, z)) for p in (f0, f1, b1, b0)]
    up = Vector((0, 0, 1))
    for poly in ([e[0], e[1], r1, r0], [e[2], e[3], r0, r1], [e[3], e[0], r0], [e[1], e[2], r1]):
        mb.face(poly, m, up)
    # eave fascia and soffit
    for i in range(4):
        a, b = e[i], e[(i + 1) % 4]
        out = ((a + b) / 2 - cen - Vector((0, 0, z))).normalized()
        mb.face([a, b, b - Vector((0, 0, thick)), a - Vector((0, 0, thick))], m, out)
    mb.face([p - Vector((0, 0, thick)) for p in e], m, -up)


# ---------------------------------------------------------------- the church
def church(coll, M):
    st = MB("SMG_Chiesa_Pietrame", tex=3.0)       # rubble
    cn = MB("SMG_Chiesa_Conci", tex=2.0)          # pilasters, quoins, carved stone
    pl = MB("SMG_Chiesa_Intonaco", tex=3.0)       # plaster
    rf = MB("SMG_Chiesa_Tetto", tex=2.0)
    dt = MB("SMG_Chiesa_Dettagli", tex=1.5)       # doors, glass, iron, small things
    zb = Z_LOW_CH
    north_holes = []
    ARCHES = (8.2, 18.0)                           # blind arches along the flank (y of their axis)
    # --- rubble walls of the nave (north: outer skin with the blind arches, then the back of the recesses)
    for yc in ARCHES:
        north_holes.append((yc, 2.7, Z0 + 0.0, Z0 + 8.4, True))
    wall(st, (W, 0.0, 0), (0, 1, 0), L, zb, H1, M["pietrame"], holes=north_holes, thick=0.4, reveal_m=M["pietrame"])
    for yc in ARCHES:
        wall(st, (W - 0.4, yc - 1.35, 0), (0, 1, 0), 2.7, zb, Z0 + 8.4, M["pietrame"], back=False,
             holes=[(1.35, 1.5, Z0 + 0.25, Z0 + 2.85, False)], thick=0.25)
        # the small door at the foot of the arch, a sheet canopy above it
        dt.box(W - 0.66, W - 0.6, yc - 0.75, yc + 0.75, Z0 + 0.25, Z0 + 2.85, M["legno"])
        dt.box(W - 0.4, W + 0.25, yc - 0.95, yc + 0.95, Z0 + 2.95, Z0 + 3.0, M["ferro"])
        st.box(W - 0.4, W, yc - 1.35, yc + 1.35, Z0 - 0.02, Z0 + 0.25, M["pietrame"])   # threshold step
    wall(st, (0.0, L, 0), (0, -1, 0), L, zb, H1, M["pietrame"], thick=0.9)              # south, to the cloister
    wall(st, (W, L, 0), (-1, 0, 0), W, zb, H1, M["pietrame"], thick=0.9)                # west end
    # tiled coping on the rubble (a one-tile slope outwards) and the plastered upper wall, set back
    for x0, x1, out in ((W - 0.55, W + 0.12, 1), (-0.12, 0.55, -1)):
        lo, hi = (x1, x0) if out > 0 else (x0, x1)
        rf.face([(hi, 0.0, H1 + 0.25), (hi, L, H1 + 0.25), (lo, L, H1), (lo, 0.0, H1)], M["tegole"], (out * 0.3, 0, 1))
    up_holes = []
    wall(pl, (W - 0.55, 0.3, 0), (0, 1, 0), L - 0.3, H1, H2, M["intonaco"], thick=0.3)
    wall(pl, (0.55, L, 0), (0, -1, 0), L - 0.3, H1, H2, M["intonaco"], thick=0.3)
    for y in [3.0 + 4.5 * i for i in range(8)]:                                         # flat lesenes = panels
        for x, out in ((W - 0.55, 1), (0.55, -1)):
            pl.box(x - (0.0 if out > 0 else 0.08), x + (0.08 if out > 0 else 0.0), y - 0.3, y + 0.3, H1, H2, M["intonaco"])
    for x, out in ((W - 0.55, 1), (0.55, -1)):
        sweep_h(pl, [(x, 0.3), (x, L)] if out > 0 else [(x, L), (x, 0.3)], H2 - 0.25,
                [(0.0, 0.0), (0.12, 0.0), (0.12, 0.25), (0.0, 0.25)], M["intonaco"])
    # downpipes from the upper roof to the street
    for yp in (23.5, 4.5):
        dt.lathe(W + 0.12, yp, [(0.06, G.at(W + 0.2, yp) - Z0 + 0.0), (0.06, H2 - Z0 - 0.2)], M["ferro"], segs=8, z0=Z0)
    # low tiled roof of the nave
    rise = (W / 2 - 0.4) * math.tan(math.radians(18))
    for x_eave, xr in ((W - 0.3, W / 2), (0.3, W / 2)):
        rf.face([(x_eave, 0.8, H2), (x_eave, L + 0.3, H2), (xr, L + 0.3, H2 + rise), (xr, 0.8, H2 + rise)],
                M["tegole"], (0, 0, 1))
    rf.face([(0.3, L + 0.3, H2), (W - 0.3, L + 0.3, H2), (W / 2, L + 0.3, H2 + rise)], M["intonaco"], (0, 1, 0))

    # --- battered stone plinth along the Viale, which goes down towards the west
    for i in range(int(L) + 1):
        y0, y1 = float(i), min(float(i + 1), L + 0.5)
        g = min(G.at(W + 0.9, y0), G.at(W + 0.9, y1)) - 0.3
        if Z0 - 0.05 - g > 0.15:
            cn.face([(W + 0.75, y0, g), (W + 0.75, y1, g), (W + 0.4, y1, Z0 + 0.1), (W + 0.4, y0, Z0 + 0.1)], M["pietrame"], (1, 0, 0.4))
            cn.face([(W + 0.4, y0, Z0 + 0.1), (W + 0.4, y1, Z0 + 0.1), (W, y1, Z0 + 0.1), (W, y0, Z0 + 0.1)], M["pietra"], (0, 0, 1))

    # --- facade: plastered field with the door and the window, the pilasters, entablature and pediment
    DOOR_W, DOOR_T = 2.2, Z0 + 4.6
    WIN_W, WIN_B, WIN_T = 1.2, Z0 + 7.5, Z0 + 9.6
    pl_holes = [(W / 2, DOOR_W, Z0, DOOR_T, True), (W / 2, WIN_W, WIN_B, WIN_T, False)]
    wall(pl, (0.0, 0.0, 0), (1, 0, 0), W, Z0 - 0.4, Z_ENT, M["intonaco"], holes=pl_holes, thick=0.9, reveal_m=M["pietra"])
    cn.box(0.0, W, -0.25, 0.0, zb, Z0 + 0.35, M["conci"])                               # stone base course
    # corner pilasters: tall pedestal, shaft of rusticated blocks; the north one also wraps the corner
    for x0, x1, wrap in ((0.0, PIL, False), (W - PIL, W, True)):
        cn.box(x0 - 0.12, x1 + 0.12, -PIL_OUT - 0.15, 0.0, zb, Z0 + PED_H, M["conci"])
        sweep_h(cn, [(x0 - 0.12, 0.0), (x0 - 0.12, -PIL_OUT - 0.15), (x1 + 0.12, -PIL_OUT - 0.15), (x1 + 0.12, 0.0)],
                Z0 + PED_H, [(0.0, 0.0), (0.12, 0.08), (0.12, 0.22), (0.2, 0.3), (0.0, 0.3)], M["pietra"])
        cn.box(x0, x1, -PIL_OUT, 0.0, Z0 + PED_H + 0.3, Z_ENT, M["pietrame"])
        ashlar(cn, (x0, -PIL_OUT, 0), (1, 0, 0), x1 - x0, Z0 + PED_H + 0.3, Z_ENT, M["conci"], alt=0.25)
        if wrap:
            cn.box(W, W + PIL_OUT, -PIL_OUT, 1.3, zb, Z0 + PED_H, M["conci"])
            cn.box(W, W + 0.3, -PIL_OUT, 1.1, Z0 + PED_H + 0.3, Z_ENT, M["pietrame"])
            ashlar(cn, (W + 0.3, -PIL_OUT, 0), (0, 1, 0), 1.55, Z0 + PED_H + 0.3, Z_ENT, M["conci"], alt=0.3)
    # entablature: architrave and frieze in plain stone, the cornice returning along the flank
    cn.box(-0.1, W + 0.15, -PIL_OUT - 0.05, 0.0, Z_ENT, Z_COR - 0.45, M["pietra"])
    cor = [(0.0, 0.0), (0.12, 0.0), (0.12, 0.12), (0.3, 0.2), (0.3, 0.32), (0.55, 0.36), (0.55, 0.45), (0.0, 0.45)]
    sweep_h(cn, [(-0.1, 0.0), (-0.1, -PIL_OUT - 0.05), (W + 0.15, -PIL_OUT - 0.05), (W + 0.15, 1.6)], Z_COR - 0.45, cor,
            M["pietra"])
    # pediment: plastered tympanum, raking cornices with dentils, finials and the cross
    yt = -0.2
    pl.face([(-0.2, yt, Z_COR), (W + 0.2, yt, Z_COR), (W / 2, yt, Z_APEX - 0.3)], M["intonaco"], (0, -1, 0))
    pl.face([(-0.2, 1.0, Z_COR), (W + 0.2, 1.0, Z_COR), (W / 2, 1.0, Z_APEX - 0.3)], M["intonaco"], (0, 1, 0))
    for xa, xb in ((-0.2, W / 2), (W / 2, W + 0.2)):
        za, zb2 = (Z_COR, Z_APEX - 0.3) if xa < W / 2 else (Z_APEX - 0.3, Z_COR)
        pl.face([(xa, yt, za), (xb, yt, zb2), (xb, 1.0, zb2), (xa, 1.0, za)], M["intonaco"], (0, 0, 1))
    half = W / 2 + 0.25
    slope = math.atan2(Z_APEX - Z_COR, half)
    for side in (-1, 1):
        base = Vector((W / 2 + side * half, -PIL_OUT - 0.05, Z_COR))
        apex = Vector((W / 2, -PIL_OUT - 0.05, Z_APEX))
        d = (apex - base).normalized()
        path = [base, apex]
        nrm = Vector((0, -1, 0))
        upv = d.cross(nrm) if side > 0 else nrm.cross(d)
        if upv.z < 0:
            upv = -upv
        prof = [(0.0, -0.05), (0.2, 0.0), (0.2, 0.15), (0.45, 0.22), (0.45, 0.4), (0.0, 0.4)]
        cn.sweep(path, [nrm, nrm], [upv, upv], prof, M["pietra"])
        k = 0.45
        while k < (apex - base).length - 0.6:
            c = base + d * k + upv * (-0.08) + nrm * 0.12
            cn.obox(c, d, nrm, upv, 0.06, 0.08, 0.07, M["pietra"])
            k += 0.28
    for x in (-0.05, W + 0.05):
        cn.box(x - 0.3, x + 0.3, -PIL_OUT - 0.05, 0.25, Z_COR, Z_COR + 0.45, M["pietra"])
        cn.lathe(x, -0.1, [(0.0, 0.0), (0.18, 0.02), (0.3, 0.3), (0.28, 0.45), (0.0, 0.62)], M["pietra"], z0=Z_COR + 0.45)
    dt.box(W / 2 - 0.05, W / 2 + 0.05, -0.35, -0.25, Z_APEX - 0.2, Z_APEX + 1.3, M["ferro"])
    dt.box(W / 2 - 0.4, W / 2 + 0.4, -0.35, -0.25, Z_APEX + 0.8, Z_APEX + 0.9, M["ferro"])

    # --- portal: pilasters each side of the arched door, entablature, broken pediment; the closed door
    pw = 0.55
    for xc in (W / 2 - DOOR_W / 2 - 0.45 - pw / 2, W / 2 + DOOR_W / 2 + 0.45 + pw / 2):
        cn.box(xc - pw / 2 - 0.05, xc + pw / 2 + 0.05, -0.38, 0.0, Z0 - 0.4, Z0 + 0.9, M["pietra"])
        cn.box(xc - pw / 2, xc + pw / 2, -0.3, 0.0, Z0 + 0.9, Z0 + 5.4, M["conci"])
        sweep_h(cn, [(xc - pw / 2, 0.0), (xc - pw / 2, -0.3), (xc + pw / 2, -0.3), (xc + pw / 2, 0.0)], Z0 + 5.2,
                [(0.0, 0.0), (0.08, 0.06), (0.08, 0.2), (0.0, 0.2)], M["pietra"])
    sweep_outline(cn, [(W / 2 - DOOR_W / 2, Z0)] + arch_pts(W / 2, DOOR_W, DOOR_T - DOOR_W / 2)[0:] +
                  [(W / 2 + DOOR_W / 2, Z0)], (0.0, 0.0, 0), (1, 0, 0),
                  [(0.0, -0.4), (0.18, -0.4), (0.18, -0.12), (0.1, 0.0), (0.0, 0.0)], M["pietra"])
    x0p, x1p = W / 2 - DOOR_W / 2 - 1.15, W / 2 + DOOR_W / 2 + 1.15
    cn.box(x0p, x1p, -0.42, 0.0, Z0 + 5.4, Z0 + 6.0, M["pietra"])
    sweep_h(cn, [(x0p, 0.0), (x0p, -0.42), (x1p, -0.42), (x1p, 0.0)], Z0 + 6.0,
            [(0.0, 0.0), (0.15, 0.08), (0.25, 0.25), (0.0, 0.25)], M["pietra"])
    for side in (-1, 1):                                        # the two halves of the broken pediment
        xa = W / 2 + side * (DOOR_W / 2 + 1.0)
        xb = W / 2 + side * 0.75
        du = Vector((xb - xa, 0, 0.6)).normalized()
        dw = Vector((-du.z, 0, du.x)) if du.x > 0 else Vector((du.z, 0, -du.x))
        cn.obox(((xa + xb) / 2, -0.25, Z0 + 6.35), du, (0, 1, 0), dw, abs(xb - xa) / 2 / abs(du.x), 0.2, 0.14, M["pietra"])
    cn.box(W / 2 - 0.5, W / 2 + 0.5, -0.3, 0.0, Z0 + 6.25, Z0 + 7.1, M["conci"])  # cartouche
    door = [(W / 2 - DOOR_W / 2, Z0)] + arch_pts(W / 2, DOOR_W, DOOR_T - DOOR_W / 2) + [(W / 2 + DOOR_W / 2, Z0)]
    dt.face([(x, 0.55, z) for x, z in door], M["portone"], (0, -1, 0))
    dt.box(W / 2 - 0.02, W / 2 + 0.02, 0.5, 0.55, Z0, DOOR_T - 0.1, M["ferro"])
    for z in (Z0 + 1.2, Z0 + 2.6):
        dt.box(W / 2 - DOOR_W / 2, W / 2 + DOOR_W / 2, 0.5, 0.55, z, z + 0.08, M["portone"])
    # window: eared stone frame, sill, dark glass
    wx0, wx1 = W / 2 - WIN_W / 2, W / 2 + WIN_W / 2
    sweep_outline(cn, [(wx0, WIN_B), (wx0, WIN_T), (wx1, WIN_T), (wx1, WIN_B)], (0.0, 0.0, 0), (1, 0, 0),
                  [(0.0, -0.3), (0.16, -0.3), (0.16, 0.0), (0.0, 0.0)], M["pietra"], closed=True)
    for x in (wx0 - 0.42, wx1 + 0.12):
        cn.box(x, x + 0.3, -0.18, 0.0, WIN_T + 0.05, WIN_T + 0.35, M["pietra"])          # the "ears"
    cn.box(wx0 - 0.4, wx1 + 0.4, -0.25, 0.0, WIN_T + 0.3, WIN_T + 0.6, M["pietra"])
    cn.box(wx0 - 0.25, wx1 + 0.25, -0.22, 0.0, WIN_B - 0.15, WIN_B, M["pietra"])
    dt.box(wx0, wx1, 0.3, 0.34, WIN_B, WIN_T, M["vetro"])
    # --- octagonal drum over the presbytery, plastered, with windows and a pyramid roof
    cx, cy, r = W / 2, 28.5, 2.9
    pl.box(cx - 3.1, cx + 3.1, cy - 3.1, cy + 3.1, H2 - 0.5, H2 + 1.2, M["intonaco"])
    oct_pts = [(cx + r * math.cos(math.radians(22.5 + 45 * i)), cy + r * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
    zt = H2 + 6.0
    for i in range(8):
        a, b = Vector(oct_pts[i]), Vector(oct_pts[(i + 1) % 8])
        side = (b - a).length
        holes = [(side / 2, 0.9, H2 + 2.6, H2 + 4.6, False)] if i % 2 == 0 else []
        wall(pl, (a.x, a.y, 0), (b - a).normalized().to_3d(), side, H2 + 1.2, zt, M["intonaco"], holes=holes,
             thick=0.35, back=False)
        if holes:
            mid = (a + b) / 2
            nrm = Vector((mid.x - cx, mid.y - cy)).normalized()
            g = mid - nrm * 0.2
            u = (b - a).normalized()
            dt.obox((g.x, g.y, H2 + 3.6), u.to_3d(), nrm.to_3d(), (0, 0, 1), 0.45, 0.02, 1.0, M["vetro_chiaro"])
    sweep_h(pl, oct_pts + [oct_pts[0]], zt - 0.3, [(0.0, 0.0), (0.18, 0.1), (0.18, 0.3), (0.0, 0.3)], M["intonaco"])
    pl.face([(x, y, zt) for x, y in oct_pts], M["intonaco"], (0, 0, -1))
    ro = [(cx + (r + 0.45) * math.cos(math.radians(22.5 + 45 * i)), cy + (r + 0.45) * math.sin(math.radians(22.5 + 45 * i)))
          for i in range(8)]
    for i in range(8):
        rf.face([(ro[i][0], ro[i][1], zt), (ro[(i + 1) % 8][0], ro[(i + 1) % 8][1], zt), (cx, cy, zt + 2.0)], M["tegole"], (0, 0, 1))
    return [m.finish(coll) for m in (st, cn, pl, rf, dt)]


# ---------------------------------------------------------------- the old hospital
def hospital(coll, M):
    wl = MB("SMG_Ospedale_Muri", tex=3.0)
    cn = MB("SMG_Ospedale_Pietra", tex=1.5)
    rf = MB("SMG_Ospedale_Tetto", tex=2.0)
    dt = MB("SMG_Ospedale_Dettagli", tex=1.5)
    front_a, front_b = Vector(HOSP[0]), Vector(HOSP[1])
    flen = (front_b - front_a).length
    u = (front_b - front_a).normalized()
    # ground floor: the street's middle height along the front (the town's terrain is rough here: the doors get steps
    # where it drops, the wall goes down to the lowest ground)
    g_front = sorted(G.at(*(front_a + u * s + Vector((0, -2.5)))) for s in range(1, int(flen), 2))
    zf = g_front[len(g_front) // 2] + 0.1
    zl = min(G.at(x, y) for x, y in HOSP) - 0.6
    zeave = zf + 9.2
    f1 = zf + 4.8                                   # first floor
    # front along the street: ground floor doors and windows, first floor windows, the oval over the portal
    holes = [(2.4, 1.6, zf, zf + 3.0, True), (6.3, 1.2, zf, zf + 2.6, False), (9.9, 1.0, zf, zf + 2.7, False)]
    for s in (13.6, 17.2, 20.8, 24.4, 28.0, 31.6):
        holes.append((s, 0.7, zf + 1.4, zf + 2.4, False))
    for s in (6.6, 14.2, 17.8, 21.4, 25.0, 28.6, 32.2):
        holes.append((s, 0.95, f1 + 0.6, f1 + 2.5, False))
    holes.append((10.5, 1.1, f1 + 0.2, f1 + 2.6, False))          # door onto the wooden balcony
    # the front wall faces -y: travel from the far end back to the church (outward normal on the right)
    wall(wl, (front_b.x, front_b.y, 0), -u.to_3d(), flen, zl, zeave, M["intonaco_vecchio"],
         holes=[(flen - s, w, zb, zt, ar) for s, w, zb, zt, ar in holes], thick=0.7, reveal_m=M["intonaco_vecchio"])
    # the other sides: the back on the cloister with a row of windows, the end and the short wing
    for i in range(1, len(HOSP)):
        a, b = Vector(HOSP[i]), Vector(HOSP[(i + 1) % len(HOSP)])
        if i == len(HOSP) - 1:
            continue                                               # along the church's wall
        d = b - a
        Ls = d.length
        hs = []
        if Ls > 8:
            n_w = int(Ls // 3.6)
            for k in range(n_w):
                s = Ls * (k + 0.5) / n_w
                hs += [(s, 0.8, zf + 1.3, zf + 2.4, False), (s, 0.9, f1 + 0.6, f1 + 2.3, False)]
        # the ring runs clockwise: walking it backwards keeps the outside on the right
        wall(wl, (b.x, b.y, 0), (-d).normalized().to_3d(), Ls, zl, zeave, M["intonaco_vecchio"], holes=hs, thick=0.7)
    # stone frames and sills of the front openings, glass and shutters set in
    for s, w, zb, zt, ar in holes:
        p = front_a + u * s
        n = Vector((u.y, -u.x))                                    # out of the front (towards the street, -y)
        if n.y > 0:
            n = -n
        if ar:
            pts = [(-w / 2, zb)] + [(x, z) for x, z in arch_pts(0.0, w, zt - w / 2)] + [(w / 2, zb)]
            sweep_outline(cn, pts, (p.x, p.y, 0), u.to_3d() * -1, [(0.0, -0.32), (0.14, -0.32), (0.14, 0.0), (0.0, 0.0)],
                          M["pietra"])
            # the oval window over the portal, in a heavy stone ring
            oc = Vector((p.x, p.y, f1 + 1.2))
            ring = [(0.95 * math.cos(2 * math.pi * k / 20), 1.2 + 0.7 * math.sin(2 * math.pi * k / 20)) for k in range(20)]
            sweep_outline(cn, [(x, f1 + z) for x, z in ring], (p.x, p.y, 0), u.to_3d() * -1,
                          [(0.0, -0.3), (0.2, -0.3), (0.2, 0.0), (0.0, 0.0)], M["pietra"], closed=True)
            dt.face([(p.x - u.x * x + n.x * 0.03, p.y - u.y * x + n.y * 0.03, f1 + z) for x, z in ring], M["vetro"], n.to_3d())
            door = [(-w / 2, zb)] + arch_pts(0.0, w, zt - w / 2) + [(w / 2, zb)]
            dt.face([(p.x - u.x * x - n.x * 0.35, p.y - u.y * x - n.y * 0.35, z) for x, z in door], M["legno"], n.to_3d())
            continue
        sweep_outline(cn, [(-w / 2, zb), (-w / 2, zt), (w / 2, zt), (w / 2, zb)], (p.x, p.y, 0), u.to_3d() * -1,
                      [(0.0, -0.22), (0.1, -0.22), (0.1, 0.0), (0.0, 0.0)], M["pietra"], closed=zb > zf + 0.1)
        is_door = zb <= zf + 0.01
        c = Vector((p.x, p.y, (zb + zt) / 2)) - n.to_3d() * 0.4
        dt.obox(c, u.to_3d(), n.to_3d(), (0, 0, 1), w / 2, 0.03, (zt - zb) / 2, M["legno"] if is_door else M["vetro"])
        if not is_door:
            cn.obox(Vector((p.x, p.y, zb - 0.06)) + n.to_3d() * 0.08, u.to_3d(), n.to_3d(), (0, 0, 1), w / 2 + 0.12, 0.16, 0.06,
                    M["pietra"])
        else:
            # steps up from the street
            gs = G.at(p.x + n.x * 1.2, p.y + n.y * 1.2) - 0.1
            k = 0
            z = zb
            while z - gs > 0.12 and k < 6:
                cn.obox(Vector((p.x, p.y, (z + gs) / 2)) + n.to_3d() * (0.15 + 0.3 * k), u.to_3d(), n.to_3d(), (0, 0, 1),
                        w / 2 + 0.25, 0.15, (z - gs) / 2, M["pietra"])
                z -= 0.17
                k += 1
    # quoins at the far corner and along the church's pilaster
    ashlar(cn, (front_b.x, front_b.y, 0), -u.to_3d(), 0.9, zl, zeave, M["conci"], course=0.4, proud=0.05, alt=0.3)
    # enclosed wooden balcony on two brackets
    p = front_a + u * 10.5
    n = Vector((u.y, -u.x))
    if n.y > 0:
        n = -n
    U, N = u.to_3d(), n.to_3d()
    base = Vector((p.x, p.y, f1 + 0.2)) + N * 0.55
    dt.obox(base, U, N, (0, 0, 1), 1.0, 0.55, 0.08, M["legno"])
    for side in (-1, 1):
        dt.obox(base + U * (side * 0.95) + N * 0.0 + Vector((0, 0, 1.15)), U, N, (0, 0, 1), 0.05, 0.55, 1.1, M["legno"])
        dt.obox(Vector((p.x, p.y, f1 - 0.45)) + U * (side * 0.7) + N * 0.3, U, (N + Vector((0, 0, 1))).normalized(),
                (Vector((0, 0, 1)) - N).normalized(), 0.06, 0.5, 0.06, M["legno"])
    dt.obox(base + N * 0.5 + Vector((0, 0, 1.15)), U, N, (0, 0, 1), 1.0, 0.04, 1.1, M["legno"])
    for k in (-0.5, 0.0, 0.5):
        dt.obox(base + N * 0.55 + U * k + Vector((0, 0, 1.45)), U, N, (0, 0, 1), 0.2, 0.01, 0.4, M["vetro"])
    Z = Vector((0, 0, 1))
    dt.obox(base + N * 0.2 + Vector((0, 0, 2.35)), U, (N + Z * 0.5).normalized(), (Z - N * 0.5).normalized(),
            1.15, 0.6, 0.04, M["legno"])
    # eaves cornice and hipped roofs
    sweep_h(cn, [HOSP[1], HOSP[0]], zeave - 0.3, [(0.0, 0.0), (0.2, 0.1), (0.3, 0.3), (0.0, 0.3)], M["pietra"])
    hip_roof(rf, HOSP_MAIN, zeave, 24, M["tegole"])
    hip_roof(rf, HOSP_WING, zeave - 0.4, 24, M["tegole"])
    return [m.finish(coll) for m in (wl, cn, rf, dt)]


# ---------------------------------------------------------------- the ruins
def ruins(coll, M):
    st = MB("SMG_Ruderi_Muri", tex=3.0)
    zl = min(G.at(x, y) for x, y in RUINS) - 0.6
    n = len(RUINS)
    cen = Vector((sum(p[0] for p in RUINS) / n, sum(p[1] for p in RUINS) / n))
    for i in range(n):
        if i in RUIN_SKIP:
            continue
        a, b = Vector(RUINS[i]), Vector(RUINS[(i + 1) % n])
        d = b - a
        Ls = d.length
        if Ls < 0.5:
            continue
        u = d.normalized()
        # the outward normal must point away from the ring's inside: pick the travel direction accordingly
        nrm = Vector((u.y, -u.x))
        mid = (a + b) / 2
        if nrm.dot(mid - cen) < 0:
            a, b, u = b, a, -u
        ruin_wall(st, a, b, zl, M["pietrame"], seed=i)
    return [st.finish(coll)]


def ruin_wall(mb, a, b, zl, m, seed=0, thick=0.65, step=0.7):
    """A broken rubble wall from a to b (outside on the right): the top follows slow waves with sudden breaks, and
    where it stands high enough an empty window is left in it."""
    u = (b - a).normalized()
    n = Vector((u.y, -u.x))
    Ls = (b - a).length
    k = max(2, int(Ls / step))
    base = random.uniform(3.0, 6.0)
    ph = random.uniform(0, 6.28)
    tops = []
    for j in range(k + 1):
        s = Ls * j / k
        h = base + 1.6 * math.sin(s / 3.1 + ph) + 0.8 * math.sin(s / 1.3 + seed) + random.uniform(-0.35, 0.35)
        if random.random() < 0.12:
            h -= random.uniform(1.0, 2.2)                     # a breach
        tops.append(max(0.8, h))
    tops[0] = tops[-1] = min(tops[0], tops[-1], 2.5) + 0.5     # the corners are worn down too
    pts = [a + u * (Ls * j / k) for j in range(k + 1)]
    gz = [G.at(p.x, p.y) for p in pts]
    up = Vector((0, 0, 1))
    N, U = n.to_3d(), u.to_3d()
    win = None
    for j in range(1, k - 2):
        if tops[j] > 4.6 and tops[j + 1] > 4.6 and tops[j + 2] > 4.6 and win is None and j % 4 == 2:
            win = j
    for j in range(k):
        p0, p1 = pts[j].to_3d(), pts[j + 1].to_3d()
        t0, t1 = gz[j] + tops[j], gz[j + 1] + tops[j + 1]
        if win is not None and win <= j <= win + 1:
            # empty window: wall below and above the opening, reveals
            zb, zt = max(gz[j], gz[j + 1]) + 2.0, max(gz[j], gz[j + 1]) + 3.4
            for d, out in ((0.0, N), (thick, -N)):
                o = -N * d
                mb.face([p0 + o + up * zl, p1 + o + up * zl, p1 + o + up * zb, p0 + o + up * zb], m, out)
                mb.face([p0 + o + up * zt, p1 + o + up * zt, p1 + o + up * t1, p0 + o + up * t0], m, out)
            mb.face([p0 + up * zb, p1 + up * zb, p1 - N * thick + up * zb, p0 - N * thick + up * zb], m, up)
            mb.face([p0 + up * zt, p1 + up * zt, p1 - N * thick + up * zt, p0 - N * thick + up * zt], m, -up)
            if j == win:
                mb.face([p0 + up * zb, p0 + up * zt, p0 - N * thick + up * zt, p0 - N * thick + up * zb], m, U)
            else:
                mb.face([p1 + up * zb, p1 + up * zt, p1 - N * thick + up * zt, p1 - N * thick + up * zb], m, -U)
        else:
            for d, out in ((0.0, N), (thick, -N)):
                o = -N * d
                mb.face([p0 + o + up * zl, p1 + o + up * zl, p1 + o + up * t1, p0 + o + up * t0], m, out)
        mb.face([p0 + up * t0, p1 + up * t1, p1 - N * thick + up * t1, p0 - N * thick + up * t0], m, up)
    for p, t, out in ((pts[0].to_3d(), gz[0] + tops[0], -U), (pts[-1].to_3d(), gz[-1] + tops[-1], U)):
        mb.face([p + up * zl, p + up * t, p - N * thick + up * t, p - N * thick + up * zl], m, out)


# ---------------------------------------------------------------- views
def views(out_dir, objs):
    sc = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1500, 1000
    sc.world = sc.world or bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.65, 0.75, 0.9, 1)
    bg.inputs[1].default_value = 1.2
    sun = bpy.data.objects.new("M80_Sole", bpy.data.lights.new("M80_Sole", "SUN"))
    sun.data.energy = 4
    sun.rotation_euler = (math.radians(45), 0, math.radians(200))
    sc.collection.objects.link(sun)
    # ground: a plane through the survey
    me = bpy.data.meshes.new("M80_Suolo")
    bm = bmesh.new()
    vs = {}
    for i in range(-50, 25):
        for j in range(-8, 62):
            vs[i, j] = bm.verts.new(FRAME @ Vector((float(i), float(j), G.at(float(i), float(j)) - 0.05)))
    for i in range(-50, 24):
        for j in range(-8, 61):
            bm.faces.new([vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]])
    bm.to_mesh(me)
    gnd = bpy.data.objects.new("M80_Suolo", me)
    gm = bpy.data.materials.new("M80_Suolo")
    gm.diffuse_color = (0.45, 0.43, 0.4, 1)
    me.materials.append(gm)
    sc.collection.objects.link(gnd)
    cam = bpy.data.objects.new("M80_Cam", bpy.data.cameras.new("M80_Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    shots = {   # local (x, y, height above the ground there), local target
        "facciata": ((W / 2 + 4, -22, 1.7), (W / 2, 2, Z0 + 7)),
        "angolo_viale": ((W + 14, -10, 1.7), (W / 2, 10, Z0 + 7)),
        "fianco_viale": ((W + 9, 22, 1.7), (W / 2, 20, Z0 + 7)),
        "ospedale": ((-2, -12, 1.7), (-24, 3, None)),
        "ospedale_lontano": ((-40, -14, 1.7), (-8, 4, None)),
        "alto": ((-35, -45, 60), (-8, 20, None)),
        "ruderi_alto": ((-50, 70, 40), (-15, 40, None)),
    }
    for name, ((x, y, h), (tx, ty, tz)) in shots.items():
        cam.data.lens = 22
        loc = FRAME @ Vector((x, y, G.at(x, y) + h))
        tgt = FRAME @ Vector((tx, ty, tz if tz is not None else G.at(tx, ty) + 5))
        cam.location = loc
        cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out_dir, name + ".png")
        bpy.ops.render.render(write_still=True)
    for o in (cam, sun, gnd):
        bpy.data.objects.remove(o)


def main():
    if os.path.exists(DST) and os.environ.get("M80_SOVRASCRIVI") != "1":
        print("M80 SantaMariaGesu.blend esiste gia': M80_SOVRASCRIVI=1 per rifarlo")
        return
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    M = materials()
    objs = []
    for cname, fn in (("SMG_Chiesa", church), ("SMG_Ospedale", hospital), ("SMG_Ruderi", ruins)):
        c = bpy.data.collections.new(cname)
        bpy.context.scene.collection.children.link(c)
        objs += fn(c, M)
    for o in objs:
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print("M80", o.name, tris, "triangoli")
    print("M80 Z0", round(Z0, 2), "terreno", "rilievo" if G.grid else "piatto")
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=DST)
    if FOTO:
        views(FOTO, objs)


main()
