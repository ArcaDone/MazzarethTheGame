"""Blender 5.2: 1980s Sicilian clothes for the crowd's MetaHumans, modelled on their own bodies (parametric outfits).

Each garment is made on a source body (a MetaHuman full body exported by Scripts/m80_vestiti_sonda.py: head and body
merged, A pose, the same mesh the outfit's resizing starts from) and becomes, in Unreal, a cloth asset (render mesh
only, skin weights transferred from that body: no simulation, cheap for a crowd), then a resizable outfit that the
MetaHuman Creator fits to every other body.

Two ways of building, both from the body's own vertices (each knows its body part from its strongest bone):
- shell: the body's faces of the covered parts, smoothed (no muscles, navel, toes) and pushed out along the normals
  by the ease (how loose the cloth is, per part and height); for fitted pieces: shirts, jumpers, vests, trousers,
  shoes, the headscarf;
- loft: rings around the body's cross sections (convex hull of the covered parts at each height, so the cloth bridges
  the legs), from a top to a hem, with flare; for what hangs: skirts, jacket and coat tails, the shepherd's cloak.
UVs are cylindrical per part (around the torso, each arm, each leg), in metres, so stripes, checks and knits run
straight and the fabric textures tile at their real size.

Run: blender -b --factory-startup --python m80_vestiti.py -- [Key,Key...]
Out: Saved/Mazzarino80/Folla/Vestiti/<Key>/{SM_M80_<Key>.fbx, Textures/, <Key>.json}, anteprima_{fronte,retro}.png
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_folla_oggetti as common  # noqa: E402

ROOT = common.ROOT
BODIES = os.path.join(ROOT, "Saved", "Mazzarino80", "Folla", "Corpi")
OUT = os.path.join(ROOT, "Saved", "Mazzarino80", "Folla", "Vestiti")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = [k for k in (ARGS[0].split(",") if ARGS else []) if k]
TEX = 1024          # fabric texture size (px)
LODS = [6000, 3000, 1500, 700]   # triangles per garment piece and LOD (MetaHuman bodies have 4 LODs)

# Body part of a bone, by name prefix (MetaHuman body: many helper bones per joint).
PARTS = [("FACIAL", "head"), ("head", "head"), ("neck", "neck"), ("pelvis", "torso"), ("spine", "torso"),
         ("clavicle", "torso"), ("upperarm", "arm"), ("lowerarm", "forearm"), ("hand", "hand"), ("thumb", "hand"),
         ("index", "hand"), ("middle", "hand"), ("ring", "hand"), ("pinky", "hand"), ("thigh", "thigh"),
         ("calf", "calf"), ("foot", "foot"), ("ball", "foot"), ("big", "foot"), ("bigtoe", "foot"),
         ("indextoe", "foot"), ("middletoe", "foot"), ("ringtoe", "foot"), ("littletoe", "foot"), ("wrist", "forearm"), ("ankle", "calf")]


# --- the body ------------------------------------------------------------------------------------------------------

class Body:
    """A source body in metres, front towards -Y: vertices, normals, faces, part and side of each vertex, joints."""

    def __init__(self, key):
        common.reset()
        bpy.ops.import_scene.fbx(filepath=os.path.join(BODIES, key + "_FullBody.fbx"))
        mesh_ob = next(o for o in bpy.data.objects if o.type == "MESH")
        arm_ob = next(o for o in bpy.data.objects if o.type == "ARMATURE")
        me = mesh_ob.data.copy()
        me.transform(mesh_ob.matrix_world)
        # Unreal's FBX splits the vertices along UV seams and hard edges: welded back, or every shell opens there.
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bm.to_mesh(me)
        bm.free()
        self.key = key
        self.co = np.array([v.co[:] for v in me.vertices])
        self.normal = np.array([v.normal[:] for v in me.vertices])
        self.faces = [tuple(p.vertices) for p in me.polygons]
        names = [g.name for g in mesh_ob.vertex_groups]
        part_of = []
        for n in names:
            low = n.lower()
            part_of.append(next((p for pre, p in PARTS if low.startswith(pre.lower())), "torso"))
        self.part = []
        for v in me.vertices:
            best = max(v.groups, key=lambda g: g.weight, default=None)
            self.part.append(part_of[best.group] if best else "torso")
        self.part = np.array(self.part)
        # Side: +1 left (+X in Blender for a MetaHuman facing -Y), -1 right.
        self.side = np.sign(self.co[:, 0])
        self.joint = {b.name: (arm_ob.matrix_world @ b.head_local) for b in arm_ob.data.bones}
        self.joint = {k: np.array(v[:]) for k, v in self.joint.items()}
        self.height = float(self.co[:, 2].max())
        self.me = me
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o)
        # The body itself, for previews (clay).
        self.ob = bpy.data.objects.new("Corpo", me)
        bpy.context.scene.collection.objects.link(self.ob)
        me.materials.clear()
        me.materials.append(common.material("Pelle", color=(0.62, 0.45, 0.36), rough=0.6))
        self.bvh = BVHTree.FromPolygons([tuple(v) for v in self.co], self.faces)

    def j(self, name):
        return self.joint[name]


# --- building blocks -----------------------------------------------------------------------------------------------

def straighten_borders(bm, iterations):
    """Smooths the open borders of a mesh (a cut that follows edges goes in steps): each border vertex moves
    towards the middle of its two border neighbours."""
    for _ in range(iterations):
        moves = {}
        for v in bm.verts:
            if v.is_boundary:
                nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
                if len(nb) == 2:
                    moves[v] = (nb[0].co + nb[1].co) * 0.5
        for v, c in moves.items():
            v.co = v.co * 0.5 + c * 0.5


def keep_out(bm, body, margin):
    """Every vertex at least `margin` out of the body's surface, or the skin shows through the cloth."""
    for v in bm.verts:
        loc, nrm, _, _ = body.bvh.find_nearest(v.co)
        if loc is not None:
            out = (v.co - loc).dot(nrm)
            if out < margin:
                v.co += nrm * (margin - out)


def drape(bm, src, body, part, z_lo, z_hi, fall=0.35, side=0, band=0.012):
    """Cloth over the hollows of `part` (a part or a list) between z_lo and z_hi: per height band its vertices go out
    to the band's convex hull (no cleavage, no gap between the pecs, no hollow at the small of the back), and from
    the top down each band is at least as wide as the one above less `fall` per metre of drop (the cloth hangs from
    the chest instead of following under it; trouser legs fall straight from the thigh). side: +1/-1 one leg only."""
    parts = [part] if isinstance(part, str) else list(part)
    mid_x = float(body.j("pelvis")[0])
    verts = [v for v in bm.verts if body.part[v[src]] in parts and z_lo <= v.co.z <= z_hi
             and (side == 0 or (v.co.x - mid_x) * side > 0)]
    if not verts:
        return
    n = 72
    xy = np.array([(v.co.x, v.co.y) for v in verts])
    zs = np.array([v.co.z for v in verts])
    bands = []
    for top in np.arange(z_hi, z_lo - band, -band):
        idx = np.nonzero((zs <= top) & (zs > top - band))[0]
        if len(idx) >= 3:
            bands.append(idx)
    if len(bands) < 2:
        return
    # Centres and radii smoothed along the height (each band alone gave a quilted look), the radii never inside the
    # body's hull and hanging by `fall` from the band above.
    centres = np.array([xy[idx].mean(axis=0) for idx in bands])
    for _ in range(8):
        centres[1:-1] = (centres[:-2] + 2 * centres[1:-1] + centres[2:]) / 4
    raw = np.array([ring_radii(hull2d(xy[idx]), c, n) for idx, c in zip(bands, centres)])
    for i in range(1, len(raw)):
        raw[i] = np.maximum(raw[i], raw[i - 1] - fall * band)
    radii = raw.copy()
    for _ in range(3):
        for _ in range(6):
            radii[1:-1] = (radii[:-2] + 2 * radii[1:-1] + radii[2:]) / 4
        radii = (np.roll(radii, 1, 1) + 2 * radii + np.roll(radii, -1, 1)) / 4
        radii = np.maximum(radii, raw)
    for idx, centre, rad in zip(bands, centres, radii):
        for i in idx:
            d = xy[i] - centre
            r = float(np.linalg.norm(d))
            if r < 1e-6:
                continue
            a = math.atan2(d[1], d[0]) % (2 * math.pi) / (2 * math.pi) * n
            k = int(a) % n
            target = rad[k] + (rad[(k + 1) % n] - rad[k]) * (a - int(a))
            if target > r:
                verts[i].co.x, verts[i].co.y = centre + d / r * target


def shell(body, keep, ease, smooth=12, name="Shell", drapes=(), margin=0.006):
    """The body's faces whose vertices all pass keep(index array) -> bool array, smoothed, pushed out by ease(i);
    drapes: drape() arguments (part, z_lo, z_hi) where the cloth bridges the body's hollows."""
    sel = keep(np.arange(len(body.co)))
    bm = bmesh.new()
    src = bm.verts.layers.int.new("src")    # before any vertex: adding a layer invalidates them
    vmap = {}
    for i in np.nonzero(sel)[0]:
        vmap[i] = bm.verts.new(body.co[i])
        vmap[i][src] = int(i)
    for f in body.faces:
        if all(sel[i] for i in f):
            try:
                bm.faces.new([vmap[i] for i in f])
            except ValueError:
                pass
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    bm.verts.ensure_lookup_table()
    straighten_borders(bm, 6)
    # Smooth away the anatomy, keeping the borders (necklines, cuffs) where they are.
    inner = [v for v in bm.verts if not v.is_boundary]
    for _ in range(smooth):
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    for args in drapes:
        drape(bm, src, body, *args)
        for _ in range(3):
            bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    idx = np.array([v[src] for v in bm.verts])
    push = ease(idx)
    for v, d in zip(bm.verts, push):
        v.co += v.normal * float(d)
    # A second light pass evens out the offset where the ease changes.
    bmesh.ops.smooth_vert(bm, verts=[v for v in bm.verts if not v.is_boundary], factor=0.5,
                          use_axis_x=True, use_axis_y=True, use_axis_z=True)
    # Smoothing pulls the cloth into the body's hollows (the crotch, under the bust).
    keep_out(bm, body, margin)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob["src"] = idx.tolist()
    return ob


def hull2d(pts):
    """Convex hull (monotone chain) of 2D points, counter-clockwise."""
    pts = sorted(set(map(tuple, np.round(pts, 4))))
    if len(pts) < 3:
        return np.array(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def ring_radii(hull, centre, n):
    """Distance from centre to the hull along n directions (the hull as a polar curve)."""
    out = np.zeros(n)
    for k in range(n):
        a = 2 * math.pi * k / n
        d = np.array([math.cos(a), math.sin(a)])
        best = 0.0
        for p, q in zip(hull, np.roll(hull, -1, axis=0)):
            # Ray centre + t d against segment p-q.
            e = q - p
            den = d[0] * (-e[1]) - d[1] * (-e[0])
            if abs(den) < 1e-9:
                continue
            w = p - centre
            t = (w[0] * (-e[1]) - w[1] * (-e[0])) / den
            s = (d[0] * w[1] - d[1] * w[0]) / den
            if t > 0 and -1e-6 <= s <= 1 + 1e-6:
                best = max(best, t)
        out[k] = best
    return out


def loft(body, parts, z_top, z_hem, ease, n=40, dz=0.02, name="Loft", centre_xy=None, close_top=False, select=None):
    """Rings around the body's cross sections of `parts` (convex hull per height), from z_top down to z_hem.
    ease(z, angle) -> metres added to the radius. Below the lowest body slice the last ring is carried down.
    select: a vertex mask to use instead of `parts`."""
    mask = np.isin(body.part, parts) if select is None else select
    co = body.co[mask]
    zs = np.arange(z_top, z_hem - 1e-6, -dz)
    if zs[-1] > z_hem + 1e-4:
        zs = np.append(zs, z_hem)
    cxy = np.array(centre_xy) if centre_xy is not None else None
    rings = []
    last = None
    for z in zs:
        sl = co[np.abs(co[:, 2] - z) < dz * 0.75][:, :2]
        if len(sl) >= 3:
            h = hull2d(sl)
            c = cxy if cxy is not None else h.mean(0)
            r = ring_radii(h, c, n)
            last = (c, r)
        if last is None:
            continue
        c, r = last
        rings.append((z, c, r.copy()))
    # Smooth radii along the height and around, never inside the body's own hull (smoothing alone flattened the
    # buttocks into the skirt).
    raw = np.array([r for _, _, r in rings])
    rr = raw.copy()
    for _ in range(3):
        for _ in range(8):
            rr[1:-1] = (rr[:-2] + 2 * rr[1:-1] + rr[2:]) / 4
        for _ in range(2):
            rr = (np.roll(rr, 1, 1) + 2 * rr + np.roll(rr, -1, 1)) / 4
        rr = np.maximum(rr, raw)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    grid = []
    for (z, c, _), r in zip(rings, rr):
        row = []
        for k in range(n):
            a = 2 * math.pi * k / n
            rad = r[k] + ease(z, a)
            row.append(bm.verts.new((c[0] + rad * math.cos(a), c[1] + rad * math.sin(a), z)))
        grid.append(row)
    where = {v: (i, k) for i, row in enumerate(grid) for k, v in enumerate(row)}
    for i in range(len(grid) - 1):
        for k in range(n):
            f = bm.faces.new([grid[i][k], grid[i][(k + 1) % n], grid[i + 1][(k + 1) % n], grid[i + 1][k]])
            for loop in f.loops:
                ii, kk = where[loop.vert]
                if kk == 0 and k == n - 1:
                    kk = n
                # Metres around (at a nominal 25 cm radius) and down.
                loop[uv].uv = (kk / n * 2 * math.pi * 0.25, rings[ii][0])
    if close_top:
        bmesh.ops.contextual_create(bm, geom=grid[0])
    keep_out(bm, body, 0.008)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def cylinder_uv(ob, body):
    """UVs for a shell: around each part's own axis (torso: vertical through the spine; arms and legs: along their
    bones), in metres; one UV island per part."""
    src = np.array(ob["src"])
    part = body.part[src]
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers[0].data
    co = np.array([v.co[:] for v in me.vertices])
    axes = {}
    pelvis, neck = body.j("pelvis"), body.j("neck_01")
    for side, s in (("l", 1), ("r", -1)):
        axes[("arm", s)] = (body.j("upperarm_" + side), body.j("lowerarm_" + side))
        axes[("forearm", s)] = (body.j("lowerarm_" + side), body.j("hand_" + side))
        axes[("thigh", s)] = (body.j("thigh_" + side), body.j("calf_" + side))
        axes[("calf", s)] = (body.j("calf_" + side), body.j("foot_" + side))
    offsets = {"torso": 0.0, "neck": 0.0, "head": 0.0, "arm": 2.0, "forearm": 2.0, "thigh": 4.0, "calf": 4.0,
               "foot": 6.0, "hand": 8.0}
    vert_uv = np.zeros((len(co), 2))
    for i, p in enumerate(co):
        pt = part[i]
        s = 1 if p[0] >= 0 else -1
        if (pt, s) in axes:
            a, b = axes[(pt, s)]
            ax = (b - a) / np.linalg.norm(b - a)
            ref = np.array([0.0, -1.0, 0.0]) - ax * ax[1] * -1.0
            ref /= np.linalg.norm(ref)
            side_v = np.cross(ax, ref)
            d = p - a
            ang = math.atan2(d @ side_v, d @ ref)
            along = d @ ax
            vert_uv[i] = (ang * 0.06 + offsets[pt] + (0.5 if s < 0 else 0), -along - (0.5 if pt in ("forearm", "calf") else 0))
        else:
            c = pelvis + (neck - pelvis) * 0.5
            ang = math.atan2(p[0] - c[0], -(p[1] - c[1]))
            vert_uv[i] = (ang * 0.16, p[2])
    for loop in me.loops:
        uv[loop.index].uv = vert_uv[loop.vertex_index]
    # Fix the wrap-around seam: faces straddling +-pi get their low side shifted by one turn.
    for poly in me.polygons:
        us = [uv[li].uv[0] for li in poly.loop_indices]
        if max(us) - min(us) > 0.3:
            for li in poly.loop_indices:
                if uv[li].uv[0] < (max(us) + min(us)) / 2:
                    uv[li].uv[0] += 2 * math.pi * (0.16 if part[me.loops[li].vertex_index] in ("torso", "neck", "head") else 0.06)


def decimate(ob, tris):
    """Down to about `tris` triangles (the crowd's budget)."""
    n = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if n <= tris:
        return
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.ratio = tris / n
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier="dec")


# --- fabrics -------------------------------------------------------------------------------------------------------

def knit(n, col, rng, rib=False):
    """Wool knit: rows of small Vs (stocking stitch) or vertical ribs."""
    y, x = np.mgrid[0:n, 0:n]
    v = ((x % 8) - 4) * 0.5
    st = np.abs(((y + np.abs(v)) % 8) - 4) / 4
    tone = 0.82 + 0.18 * st
    if rib:
        tone = 0.8 + 0.2 * (np.abs((x % 10) - 5) / 5)
    return np.array(col) * tone[..., None] * (0.94 + 0.12 * common.noise(n, n, 32, rng)[..., None])


def weave(n, col, rng, scale=4, depth=0.08):
    """Plain cotton or wool weave."""
    y, x = np.mgrid[0:n, 0:n]
    w = (((x // scale) + (y // scale)) % 2) * depth
    return np.array(col) * (1 - w)[..., None] * (0.95 + 0.1 * common.noise(n, n, 48, rng)[..., None])


def stripes(n, cols, widths, rng, knit_base=True):
    """Horizontal stripes (rows of the texture), knitted."""
    rgb = np.zeros((n, n, 3))
    total = sum(widths)
    y = np.arange(n) / n * total
    acc = np.cumsum(widths)
    idx = np.searchsorted(acc, y % total, side="right")
    for i, c in enumerate(cols):
        rgb[idx == i] = c
    if knit_base:
        rgb *= (knit(n, (1, 1, 1), rng) / 1.0)
    return rgb


def denim(n, col, rng):
    """Denim: a diagonal twill of indigo warp over white weft, faded in patches."""
    y, x = np.mgrid[0:n, 0:n]
    twill = ((x + y) // 2) % 3 == 0
    rgb = np.array(col) * (0.85 + 0.3 * common.noise(n, n, 64, rng)[..., None])
    rgb[twill] = rgb[twill] * 0.55 + 0.45 * np.array([0.82, 0.84, 0.86])
    return rgb * (0.95 + 0.1 * common.noise(n, n, 6, rng)[..., None])


def floral(n, base, petals, centre, rng, count=40, size=0.035):
    """Small five-petal flowers scattered on a cotton ground (tiling)."""
    rgb = weave(n, base, rng, scale=2, depth=0.03)
    r = int(size * n)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    for _ in range(count):
        cy, cx = rng.integers(0, n, 2)
        rot = rng.random() * 2 * math.pi
        col = np.array(petals[rng.integers(0, len(petals))])
        stamp = np.zeros_like(xx, dtype=bool)
        for k in range(5):
            a = rot + k * 2 * math.pi / 5
            px, py = math.cos(a) * r * 0.5, math.sin(a) * r * 0.5
            stamp |= (xx - px) ** 2 + (yy - py) ** 2 < (r * 0.38) ** 2
        mid = xx ** 2 + yy ** 2 < (r * 0.2) ** 2
        rows = (np.arange(-r, r + 1) + cy) % n
        cols = (np.arange(-r, r + 1) + cx) % n
        patch = rgb[np.ix_(rows, cols)]
        patch[stamp] = col
        patch[mid] = centre
        rgb[np.ix_(rows, cols)] = patch
    return rgb


def fabric(name, rgb, rough=0.9, tile_m=0.25):
    """A material whose texture repeats every tile_m metres (UVs are in metres)."""
    img = common.image(name, rgb)
    m = common.material(name, img=img, rough=rough)
    nodes, links = m.node_tree.nodes, m.node_tree.links
    tex = next(n for n in nodes if n.type == "TEX_IMAGE")
    mapping = nodes.new("ShaderNodeMapping")
    coord = nodes.new("ShaderNodeTexCoord")
    mapping.inputs["Scale"].default_value = (1 / tile_m, 1 / tile_m, 1)
    links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    m["tile_m"] = tile_m
    m.use_backface_culling = False
    return m


# --- garments ------------------------------------------------------------------------------------------------------

def z_of(body, joint):
    return float(body.j(joint)[2])


def neck_hole(body, p, part, rx=0.085, ry=0.075, front=0.04, back=0.0):
    """Vertices to leave out for a round neckline: the neck, and the torso inside an ellipse round the neck's base
    (rx sideways, ry front-back), lower by `front` at the front and `back` at the back."""
    base = body.j("neck_01")
    centre = base + np.array([0.0, -0.01, 0.0])
    d = np.sqrt(((p[:, 0] - centre[0]) / rx) ** 2 + ((p[:, 1] - centre[1]) / ry) ** 2)
    drop = np.where(p[:, 1] < centre[1], front, back) * np.clip(1 - np.abs(p[:, 0] - centre[0]) / rx, 0, 1)
    hole = (d < 1.0) & (p[:, 2] > base[2] - 0.03 - drop)
    # The trapezius belongs to the neck bones: the neck's vertices out on the shoulders stay.
    return hole | (part == "head") | ((part == "neck") & (d < 1.5))


def g_abito_nero(body, rng):
    """Old woman's black dress: long sleeves, round neck, buttoned bodice, skirt to mid-calf."""
    waist_z = z_of(body, "spine_02")
    wrist = {s: body.j("hand_" + s) for s in "lr"}

    def keep(i):
        p, part = body.co[i], body.part[i]
        ok = np.isin(part, ["torso", "arm", "forearm"]) & ~neck_hole(body, p, part)
        ok &= p[:, 2] > waist_z - 0.06
        # Sleeves stop 2 cm short of the wrist.
        for s, sgn in (("l", 1), ("r", -1)):
            ax = wrist[s] - body.j("lowerarm_" + s)
            ax /= np.linalg.norm(ax)
            along = (p - wrist[s]) @ ax
            ok &= ~((np.sign(p[:, 0]) == sgn) & (part == "forearm") & (along > -0.02))
        return ok

    # The bodice hangs from the bust and the shoulder blades, loose to the waist.
    armpit_z = z_of(body, "upperarm_l") - 0.04
    top = shell(body, keep, lambda i: np.where(body.part[i] == "torso", 0.016, 0.016), name="Corpetto",
                drapes=[("torso", waist_z - 0.06, armpit_z)])
    cylinder_uv(top, body)
    skirt = loft(body, ["torso", "thigh", "calf"], waist_z + 0.02, z_of(body, "calf_l") * 0.55,
                 lambda z, a: 0.012 + max(0.0, (waist_z - 0.1 - z)) * 0.12, name="Gonna")
    cloth = fabric("Lana_nera", weave(TEX, (0.035, 0.033, 0.035), rng, scale=3), rough=0.95, tile_m=0.12)
    for ob in (top, skirt):
        ob.data.materials.append(cloth)
    return [top, skirt]


def g_fazzoletto(body, rng):
    """Black veil (the old women's 'fazzoletto'): loose over the head, framing the face, closed under the chin round
    the neck and falling over the shoulders, lower at the back than at the front."""
    head = body.j("head")
    neck = body.j("neck_01")
    hd = body.co[body.part == "head"]
    top_z = float(hd[:, 2].max())
    chin_z = float(hd[np.abs(hd[:, 0]) < 0.02][:, 2].min())
    hairline = top_z - 0.06
    front_hem, back_hem = neck[2] - 0.11, neck[2] - 0.2
    shoulder = neck[2] - 0.03

    def ease(z, a):
        # Close on the crown, loose round the neck, wide over the shoulders.
        return float(np.interp(z, [back_hem, shoulder, chin_z, head[2], top_z], [0.045, 0.04, 0.032, 0.02, 0.014]))

    ob = loft(body, ["head", "neck", "torso"], top_z - 0.012, back_hem, ease, n=56, dz=0.012, name="Velo",
              centre_xy=(head[0], head[1] + 0.005))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    front = -math.pi / 2

    def angle(c):
        return math.atan2(c.y - head[1], c.x - head[0])

    gone = []
    for f in bm.faces:
        c = f.calc_center_median()
        da = abs((angle(c) - front + math.pi) % (2 * math.pi) - math.pi)
        # The face: an oval from the chin to the hairline, about 110 degrees wide at the cheeks.
        t = (c.z - chin_z) / (hairline - chin_z)
        if 0.0 < t < 1.0 and da < math.radians(58) * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 4)) + math.radians(8):
            gone.append(f)
            continue
        # The hem: front_hem at the front, back_hem at the back.
        if c.z < front_hem + (back_hem - front_hem) * (da / math.pi):
            gone.append(f)
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    straighten_borders(bm, 14)
    # The crown closed with a dome (rings shrinking up to a top 1.6 cm over the head) - a flat fan cut the skull.
    ring = [v for v in bm.verts if abs(v.co.z - (top_z - 0.012)) < 1e-4]
    if len(ring) > 2:
        ring.sort(key=lambda v: math.atan2(v.co.y - head[1], v.co.x - head[0]))
        cx, cy, z0 = head[0], head[1] + 0.005, top_z - 0.012
        rise = top_z + 0.016 - z0
        rows = [ring]
        for t in (0.35, 0.65, 0.85, 0.96):
            k = math.sqrt(1 - t * t)
            rows.append([bm.verts.new((cx + (v.co.x - cx) * k, cy + (v.co.y - cy) * k, z0 + rise * t)) for v in ring])
        for lo, hi in zip(rows, rows[1:]):
            for i in range(len(ring)):
                j = (i + 1) % len(ring)
                bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
        tip = bm.verts.new((cx, cy, z0 + rise))
        for i in range(len(ring)):
            bm.faces.new([tip, rows[-1][(i + 1) % len(ring)], rows[-1][i]])
    keep_out(bm, body, 0.008)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    mat = fabric("Lana_velo", weave(TEX, (0.045, 0.043, 0.046), rng, scale=2, depth=0.05), rough=0.95, tile_m=0.08)
    ob.data.materials.append(mat)
    return [ob]


def g_scarpe(body, rng, colour=(0.05, 0.035, 0.03), name="Scarpe"):
    """Closed leather shoes: the convex hull of each foot below the ankle, pushed out, with a flat sole."""
    ankle = min(z_of(body, "foot_l"), z_of(body, "foot_r")) + 0.015
    pieces = []
    for sgn in (1, -1):
        sel = np.isin(body.part, ["foot", "calf"]) & (body.co[:, 2] < ankle) & (np.sign(body.co[:, 0]) == sgn)
        bm = bmesh.new()
        for c in body.co[sel]:
            bm.verts.new(c)
        hull = bmesh.ops.convex_hull(bm, input=bm.verts[:])
        for g in hull["geom_interior"] + hull["geom_unused"]:
            if isinstance(g, bmesh.types.BMVert) and g.is_valid:
                bm.verts.remove(g)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.004)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
        bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.normal_update()
        for v in bm.verts:
            v.co += v.normal * 0.007
            v.co.z = max(v.co.z, 0.0)
        # Open at the top, where the ankle goes in.
        top = [f for f in bm.faces if f.calc_center_median().z > ankle - 0.004 and f.normal.z > 0.6]
        bmesh.ops.delete(bm, geom=top, context="FACES")
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.cube_project(cube_size=0.3)
        bpy.ops.object.mode_set(mode="OBJECT")
        ob.select_set(False)
        pieces.append(ob)
    mat = fabric("Cuoio_" + name, common.leather(TEX, colour, rng), rough=0.45, tile_m=1.0)   # cube UVs: one tile = 30 cm
    for ob in pieces:
        ob.data.materials.append(mat)
    return pieces


def g_pantaloni(body, rng, colour=(0.09, 0.085, 0.08), name="Pantaloni"):
    """Trousers: waist to ankle, straight legs (the ease grows down the leg)."""
    waist_z = z_of(body, "spine_01") + 0.02
    knee = z_of(body, "calf_l")

    def keep(i):
        p, part = body.co[i], body.part[i]
        ok = np.isin(part, ["torso", "thigh", "calf"]) & (p[:, 2] < waist_z)
        ok &= p[:, 2] > z_of(body, "foot_l") - 0.01
        return ok

    def ease(i):
        z = body.co[i][:, 2]
        return 0.01 + np.clip((knee + 0.1 - z) / knee, 0, 1) * 0.03

    ob = shell(body, keep, ease, smooth=16, name=name)
    cylinder_uv(ob, body)
    ob.data.materials.append(fabric("Lana_" + name, weave(TEX, colour, rng, scale=3), rough=0.9, tile_m=0.12))
    return [ob]


def g_camicia(body, rng, colour=(0.85, 0.84, 0.8), sleeves="long", name="Camicia"):
    hip_z = z_of(body, "spine_01") - 0.03
    elbow = {s: body.j("lowerarm_" + s) for s in "lr"}
    wrist = {s: body.j("hand_" + s) for s in "lr"}

    def keep(i):
        p, part = body.co[i], body.part[i]
        # Buttoned up: the collar closes round the neck's base.
        ok = np.isin(part, ["torso", "arm", "forearm", "neck"]) & (p[:, 2] > hip_z)
        ok &= ~neck_hole(body, p, part, rx=0.065, ry=0.065, front=0.0)
        for s, sgn in (("l", 1), ("r", -1)):
            mine = np.sign(p[:, 0]) == sgn
            if sleeves == "short":
                ax = elbow[s] - body.j("upperarm_" + s)
                ax /= np.linalg.norm(ax)
                ok &= ~(mine & (part == "forearm"))
                ok &= ~(mine & (part == "arm") & ((p - elbow[s]) @ ax > -0.1))
            else:
                ax = wrist[s] - elbow[s]
                ax /= np.linalg.norm(ax)
                ok &= ~(mine & (part == "forearm") & ((p - wrist[s]) @ ax > -0.015))
        return ok

    ob = shell(body, keep, lambda i: np.where(body.part[i] == "torso", 0.014, 0.018), name=name,
               drapes=[("torso", hip_z, z_of(body, "upperarm_l") - 0.04)])
    cylinder_uv(ob, body)
    if sleeves == "long":
        neck_j = body.j("neck_01")
        lapels(ob, neck_j[2] - 0.07, neck_j, width=0.03, lift=0.003)
        jacket_collar(ob, neck_j, height=0.026)
    ob.data.materials.append(fabric("Cotone_" + name, weave(TEX, colour, rng, scale=2, depth=0.04), rough=0.8,
                                    tile_m=0.06))
    return [ob]


def g_gilet(body, rng, colour=(0.12, 0.11, 0.1)):
    """Waistcoat: no sleeves, V neck, over the shirt."""
    neck = body.j("neck_01")
    hip_z = z_of(body, "spine_01") - 0.05
    chest_z = z_of(body, "spine_04")

    def keep(i):
        p, part = body.co[i], body.part[i]
        ok = (part == "torso") & (p[:, 2] < neck[2] - 0.02) & (p[:, 2] > hip_z)
        # V neck at the front, down to the chest.
        vee = (p[:, 1] < neck[1]) & (np.abs(p[:, 0]) < (p[:, 2] - chest_z - 0.09) * 0.55)
        ok &= ~vee
        return ok

    ob = shell(body, keep, lambda i: np.full(len(i), 0.022), name="Gilet",
               drapes=[("torso", hip_z, z_of(body, "upperarm_l") - 0.04)])
    cylinder_uv(ob, body)
    ob.data.materials.append(fabric("Lana_gilet", common.tweed(TEX, [colour, (0.2, 0.18, 0.15), (0.05, 0.05, 0.05)],
                                                                rng), rough=0.95, tile_m=0.15))
    return [ob]


def walk(verts):
    """Border vertices in order along their border edges, from the lowest end (sorted by height if they don't make
    a single open chain)."""
    group = set(verts)
    nb = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary and e.other_vert(v) in group] for v in verts}
    ends = [v for v in verts if len(nb[v]) == 1]
    if len(ends) != 2 or any(len(n) > 2 for n in nb.values()):
        return sorted(verts, key=lambda v: v.co.z)
    path, prev = [min(ends, key=lambda v: v.co.z)], None
    while True:
        nxt = [v for v in nb[path[-1]] if v is not prev]
        if not nxt:
            break
        prev = path[-1]
        path.append(nxt[0])
    return path if len(path) == len(verts) else sorted(verts, key=lambda v: v.co.z)


def lapels(ob, chest_z, neck, width=0.06, lift=0.006):
    """Lapels along the jacket's V opening: a flap folded back over the chest from each border of the V, widest at
    the notch (three quarters up), narrowing to the button at the bottom and to the collar at the top."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.verify()
    lo, hi = chest_z - 0.01, neck[2] - 0.005
    for sgn in (1, -1):
        border = [v for v in bm.verts if v.is_boundary and lo < v.co.z < hi and v.co.y < neck[1] - 0.01
                  and 0 <= (v.co.x - neck[0]) * sgn < 0.14]
        border = walk(border)
        if len(border) < 3:
            continue
        outer = []
        for v in border:
            t = (v.co.z - lo) / (hi - lo)
            w = width * (min(1.0, t / 0.72) if t < 0.82 else 0.45 + 0.55 * (1 - t) / 0.18)
            side = Vector((sgn, 0.0, 0.0))
            side -= v.normal * side.dot(v.normal)
            side.normalize()
            outer.append(bm.verts.new(v.co + side * w + v.normal * (lift + 0.1 * w)))
        for i in range(len(border) - 1):
            f = bm.faces.new([border[i], border[i + 1], outer[i + 1], outer[i]])
            for l in f.loops:
                l[uv].uv = (l.vert.co.x, l.vert.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def jacket_collar(ob, neck, height=0.03):
    """A collar standing round the back and sides of the neck: the neckline's border extruded up and out."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    edges = [e for e in bm.edges if e.is_boundary and all(v.co.z > neck[2] - 0.07 and v.co.y > neck[1] - 0.035
                                                          for v in e.verts)]
    if edges:
        new = bmesh.ops.extrude_edge_only(bm, edges=edges)["geom"]
        for v in [g for g in new if isinstance(g, bmesh.types.BMVert)]:
            out = Vector((v.co.x - neck[0], v.co.y - neck[1], 0)).normalized()
            v.co += Vector((0, 0, height)) + out * 0.006
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def v_lapels(ob, neck, z_lo, z_hi, slope, width=0.06, lift=0.006):
    """Lapels on the ideal line of a V opening (|x| = (z - z_lo) * slope from the button at z_lo up to z_hi): flaps
    laid on the garment from just inside that line outwards, hiding the opening's stepped edge; widest at the
    notch (three quarters up), narrowing to the button and to the collar."""
    me = ob.data
    tree = BVHTree.FromPolygons([v.co[:] for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()

    def front_y(x, z):
        loc, _, _, _ = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        return loc.y if loc is not None else None

    for sgn in (1, -1):
        rows = []
        for t in np.linspace(0.0, 1.0, 18):
            z = z_lo + (z_hi - z_lo) * float(t)
            x_in = float(neck[0]) + sgn * ((z - z_lo) * slope - 0.006)
            w = width * (min(1.0, t / 0.72) if t < 0.82 else 0.45 + 0.55 * (1 - t) / 0.18) + 0.004
            y_in = front_y(x_in + sgn * 0.012, z)
            y_out = front_y(x_in + sgn * w, z)
            if y_in is None or y_out is None:
                continue
            rows.append((bm.verts.new((x_in, y_in - lift, z)), bm.verts.new((x_in + sgn * w, y_out - lift - 0.1 * w, z))))
        for a, b in zip(rows, rows[1:]):
            f = bm.faces.new([a[0], b[0], b[1], a[1]])
            for l in f.loops:
                l[uv].uv = (l.vert.co.x, l.vert.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()


def extend_hem(ob, body, above, level, flare=0.012):
    """The garment's bottom border (the torso's border edges below `above`) carried straight down to a level hem at
    `level`, a little wider (flare) so what is worn under it stays under it."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    src = ob["src"]
    torso = {i for i, k in enumerate(src) if body.part[k] == "torso"}
    edges = [e for e in bm.edges if e.is_boundary and all(v.co.z < above and v.index in torso for v in e.verts)]
    if edges:
        hem = {v for e in edges for v in e.verts}
        cx = sum(v.co.x for v in hem) / len(hem)
        cy = sum(v.co.y for v in hem) / len(hem)
        for v in hem:
            d = Vector((v.co.x - cx, v.co.y - cy, 0))
            if d.length > 1e-6:
                v.co += d.normalized() * flare
        geom = bmesh.ops.extrude_edge_only(bm, edges=edges)["geom"]
        for v in [g for g in geom if isinstance(g, bmesh.types.BMVert)]:
            v.co.z = level
        # UVs of the new band: round the body (as cylinder_uv's torso), in metres.
        uv = bm.loops.layers.uv.verify()
        faces = [g for g in geom if isinstance(g, bmesh.types.BMFace)]
        cx = sum(v.co.x for v in bm.verts) / len(bm.verts)
        cy = sum(v.co.y for v in bm.verts) / len(bm.verts)
        for f in faces:
            us = [math.atan2(l.vert.co.x - cx, -(l.vert.co.y - cy)) * 0.16 for l in f.loops]
            if max(us) - min(us) > 0.3:
                us = [u + 2 * math.pi * 0.16 if u < 0 else u for u in us]
            for l, u in zip(f.loops, us):
                l[uv].uv = (u, l.vert.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()


def g_giacca(body, rng, colour=(0.1, 0.1, 0.11), cloth="Lana_giacca", with_lapels=True, ease=(0.034, 0.026)):
    """Jacket: long sleeves, open V front with lapels over shirt and waistcoat, buttoned, hanging straight from
    the chest to below the hips."""
    neck = body.j("neck_01")
    hip_z = z_of(body, "spine_01")
    chest_z = z_of(body, "spine_03")
    wrist = {s: body.j("hand_" + s) for s in "lr"}

    def keep(i):
        p, part = body.co[i], body.part[i]
        ok = np.isin(part, ["torso", "neck", "arm", "forearm"]) & ~neck_hole(body, p, part, rx=0.072, ry=0.072,
                                                                               front=0.0)
        ok &= p[:, 2] > hip_z - 0.05
        vee = (p[:, 1] < neck[1]) & (np.abs(p[:, 0]) < (p[:, 2] - chest_z) * 0.33) & (part == "torso")
        ok &= ~vee
        for s, sgn in (("l", 1), ("r", -1)):
            ax = wrist[s] - body.j("lowerarm_" + s)
            ax /= np.linalg.norm(ax)
            ok &= ~((np.sign(p[:, 0]) == sgn) & (part == "forearm") & ((p - wrist[s]) @ ax > -0.03))
        return ok

    top = shell(body, keep, lambda i: np.where(body.part[i] == "torso", ease[0], ease[1]), name="Giacca",
                drapes=[("torso", hip_z - 0.05, z_of(body, "upperarm_l") - 0.04)])
    cylinder_uv(top, body)
    if with_lapels:
        v_lapels(top, neck, chest_z, neck[2] - 0.01, 0.33)
    jacket_collar(top, neck)
    extend_hem(top, body, hip_z + 0.05, hip_z - 0.16)
    cloth = fabric(cloth, weave(TEX, colour, rng, scale=3, depth=0.06), rough=0.9, tile_m=0.1)
    top.data.materials.append(cloth)
    return [top]


def from_front(c, centre):
    """Angle (0..pi) of point c round centre_xy from the front (-Y)."""
    a = math.atan2(c[1] - centre[1], c[0] - centre[0])
    return abs((a + math.pi / 2 + math.pi) % (2 * math.pi) - math.pi)


def trim(ob, centre, gone, borders=10):
    """Deletes the faces of ob whose centre c (Vector) and angle from the front da make gone(c, da) true, then
    straightens the new borders."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    dead = []
    for f in bm.faces:
        c = f.calc_center_median()
        if gone(c, from_front(c, centre)):
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES")
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    straighten_borders(bm, borders)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def near_arms(body, c, radius, start=0.2):
    """Whether c is within radius of either arm's bones (upper arm from `start` of its length, forearm, hand)."""
    p = np.array(c[:])
    for s in "lr":
        pts = [body.j("upperarm_" + s), body.j("lowerarm_" + s), body.j("hand_" + s)]
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            ab = b - a
            t = float(np.clip((p - a) @ ab / (ab @ ab), start if k == 0 else 0.0, 1.0))
            if np.linalg.norm(p - (a + ab * t)) < radius:
                return True
    return False


def fringes(ob, length=0.08, every=0.01, width=0.004):
    """Strands hanging from the hems of ob (the open borders whose cloth ends downwards): thin quads every `every`
    metres, `length` long, with the hem's UVs."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.verify()
    hems = []
    for e in bm.edges:
        if not e.is_boundary or not e.link_faces:
            continue
        f = e.link_faces[0]
        mid = (e.verts[0].co + e.verts[1].co) / 2
        out = mid - f.calc_center_median()
        if out.length > 0 and out.z < -0.5 * out.length:
            loops = {l.vert: l[uv].uv.copy() for l in f.loops}
            hems.append((e.verts[0].co.copy(), e.verts[1].co.copy(), loops[e.verts[0]], loops[e.verts[1]]))
    for a, b, ua, ub in hems:
        span = (b - a).length
        k = max(1, int(span / every))
        side = (b - a).normalized()
        for i in range(k):
            t = (i + 0.5) / k
            top = a + (b - a) * t
            sway = Vector((0, 0, -length))
            q = [bm.verts.new(top - side * width / 2), bm.verts.new(top + side * width / 2),
                 bm.verts.new(top + side * width / 2 + sway), bm.verts.new(top - side * width / 2 + sway)]
            f = bm.faces.new(q)
            u = ua + (ub - ua) * t
            for l, d in zip(f.loops, ((0, 0), (0.004, 0), (0.004, -length), (0, -length))):
                l[uv].uv = (u[0] + d[0], u[1] + d[1])
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def g_scialle(body, rng, colour=(0.06, 0.05, 0.043)):
    """Black wool shawl with fringes: over the shoulders, the two ends hanging down the front to the waist, a point
    at the back; worn over the dress and the veil."""
    neck = body.j("neck_01")
    waist_z = z_of(body, "spine_02")
    armpit_z = z_of(body, "upperarm_l") - 0.04
    centre = (neck[0], neck[1] + 0.01)
    # The arms only at the shoulder caps (further out the shawl would bridge to the A-posed arms).
    caps = np.zeros(len(body.co), bool)
    for side in "lr":
        caps |= np.linalg.norm(body.co - body.j("upperarm_" + side), axis=1) < 0.09
    sel = np.isin(body.part, ["neck", "torso"]) | ((body.part == "arm") & caps)

    def ease(z, a):
        return float(np.interp(z, [waist_z, armpit_z, neck[2] - 0.03], [0.075, 0.07, 0.06]))

    ob = loft(body, None, neck[2] - 0.03, waist_z - 0.05, ease, n=64, dz=0.012, name="Scialle", centre_xy=centre,
              select=sel)

    def gone(c, da):
        t = float(np.clip((neck[2] - c.z) / 0.3, 0, 1))
        if da < 0.42 + 0.25 * t:                       # open at the front
            return True
        # The two ends down the front, rising over the arms, down again to a point at the back.
        hem = float(np.interp(da, [0.42, 1.1, 1.6, 2.0, math.pi],
                              [waist_z + 0.01, waist_z + 0.03, armpit_z - 0.01, armpit_z - 0.02, waist_z - 0.06]))
        return c.z < hem

    trim(ob, centre, gone)
    fringes(ob, length=0.08)
    ob.data.materials.append(fabric("Lana_scialle", knit(TEX, colour, rng), rough=0.95, tile_m=0.1))
    return [ob]


def g_coppola(body, rng, colour=(0.2, 0.17, 0.13)):
    """Coppola: flat wool cap, the crown wider than the head and pulled forward over a short stiff visor."""
    hd = body.co[body.part == "head"]
    head = body.j("head")
    top_z = float(hd[:, 2].max())
    n = 48
    centre = np.array([head[0], head[1]])

    def radii_at(z):
        sl = hd[np.abs(hd[:, 2] - z) < 0.006][:, :2]
        return ring_radii(hull2d(sl), centre, n)

    def band(da):                                      # the headband: on the forehead, lower at the back
        return top_z - 0.072 - 0.053 * da / math.pi

    angles = [2 * math.pi * k / n for k in range(n)]
    das = [from_front((math.cos(a) + centre[0], math.sin(a) + centre[1]), centre) for a in angles]
    base = [radii_at(band(da))[k] + 0.012 for k, da in enumerate(das)]
    # Rings: headband, a little higher, the crown's widest (forward), its top edge; then the top.
    # (height 0..1, bulge, forward shift): on the skull 1.2 cm out, puffing a little near the top, the top panel
    # pulled forward over the visor.
    shape = [(0.0, 0.0, 0.0), (0.5, 0.004, 0.006), (0.85, 0.012, 0.02), (0.97, 0.008, 0.024)]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rows = []
    for t, bulge, fwd in shape:
        row = []
        for k, (a, da) in enumerate(zip(angles, das)):
            crown = top_z + 0.004 - 0.044 * (1 - da / math.pi) ** 1.5   # high at the back, down to the visor
            z = band(da) + (crown - band(da)) * t
            r = (base[k] if t == 0 else radii_at(min(z, top_z - 0.012))[k] + 0.012) + bulge
            row.append(bm.verts.new((centre[0] + r * math.cos(a), centre[1] - fwd + r * math.sin(a), z)))
        rows.append(row)
    for i in range(len(rows) - 1):
        for k in range(n):
            bm.faces.new([rows[i][k], rows[i][(k + 1) % n], rows[i + 1][(k + 1) % n], rows[i + 1][k]])
    tip = bm.verts.new((centre[0], centre[1] - 0.026, top_z + 0.002))
    for k in range(n):
        bm.faces.new([rows[-1][k], rows[-1][(k + 1) % n], tip])
    # Visor: from the headband at the front, 5.5 cm out at the middle, slightly down.
    front = [k for k, da in enumerate(das) if da < math.radians(72)]
    front.sort(key=lambda k: (angles[k] - (-math.pi / 2) + math.pi) % (2 * math.pi))
    inner, outer = [], []
    for k in front:
        v = rows[0][k]
        d = Vector((v.co.x - centre[0], v.co.y - centre[1], 0)).normalized()
        reach = 0.048 * math.sqrt(max(0.0, 1 - (das[k] / math.radians(72)) ** 2)) + 0.004
        inner.append(v)
        outer.append(bm.verts.new(v.co + d * reach + Vector((0, 0, -0.008 * reach / 0.048))))
    for i in range(len(front) - 1):
        bm.faces.new([inner[i], inner[i + 1], outer[i + 1], outer[i]])
    for f in bm.faces:
        for l in f.loops:
            c = l.vert.co
            if c.z < top_z - 0.02:
                l[uv].uv = (math.atan2(c.y - centre[1], c.x - centre[0]) * 0.1, c.z)
            else:
                l[uv].uv = (c.x, c.y)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("Coppola")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Coppola", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(fabric("Lana_coppola", common.tweed(TEX, [colour, (0.12, 0.1, 0.08), (0.28, 0.25, 0.2)],
                                                                  rng), rough=0.95, tile_m=0.06))
    return [ob]


def g_mantello(body, rng, colour=(0.075, 0.062, 0.05)):
    """Shepherd's cloak of coarse wool: standing collar, a cape over the shoulders to the upper arms, the cloak
    belled to mid-calf, slit at the front below the chest, the arms out through slits at the sides."""
    neck = body.j("neck_01")
    armpit_z = z_of(body, "upperarm_l") - 0.04
    chest_z = z_of(body, "spine_04")
    hem_z = z_of(body, "calf_l") * 0.5
    centre = (neck[0], neck[1] + 0.02)
    body_sel = np.isin(body.part, ["neck", "torso", "thigh", "calf"])

    def ease(z, a):
        return float(np.interp(z, [hem_z, chest_z - 0.45, armpit_z, neck[2]], [0.17, 0.09, 0.06, 0.03]))

    cloak = loft(body, None, neck[2] + 0.03, hem_z, ease, n=64, dz=0.02, name="Mantello", centre_xy=centre,
                 select=body_sel)
    trim(cloak, centre, lambda c, da: (c.z < chest_z - 0.15 and da < 0.03 + 0.05 * (chest_z - c.z))
         or near_arms(body, c, 0.09))
    cape_sel = np.isin(body.part, ["neck", "torso", "arm"]) & (body.co[:, 2] > armpit_z - 0.2)

    def cape_ease(z, a):
        return float(np.interp(z, [armpit_z - 0.2, armpit_z, neck[2]], [0.1, 0.085, 0.05]))

    cape = loft(body, None, neck[2] - 0.01, armpit_z - 0.2, cape_ease, n=64, dz=0.012, name="Mantellina",
                centre_xy=centre, select=cape_sel)
    trim(cape, centre, lambda c, da: c.z < armpit_z - 0.06 - 0.08 * da / math.pi or da < 0.04)
    cloth = fabric("Lana_mantello", weave(TEX, colour, rng, scale=4, depth=0.1), rough=0.97, tile_m=0.12)
    for ob in (cloak, cape):
        ob.data.materials.append(cloth)
    return [cloak, cape]


def buttons(ob, x, z_top, z_bottom, every=0.085, name="Bottoni"):
    """Buttons down the front of a garment at x, from z_top to z_bottom, on its own surface."""
    me = ob.data
    tree = BVHTree.FromPolygons([v.co[:] for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    bm = bmesh.new()
    z = z_top
    while z > z_bottom:
        loc, nrm, _, _ = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)))
        if loc is not None:
            if nrm.y > 0:
                nrm = -nrm
            disc = bmesh.new()
            bmesh.ops.create_cone(disc, cap_ends=True, segments=10, radius1=0.0055, radius2=0.0055, depth=0.002)
            rot = Vector((0, 0, 1)).rotation_difference(nrm).to_matrix().to_4x4()
            bmesh.ops.transform(disc, matrix=Matrix.Translation(loc + nrm * 0.002) @ rot, verts=disc.verts[:])
            tmp = bpy.data.meshes.new("tmp")
            disc.to_mesh(tmp)
            disc.free()
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
        z -= every
    me2 = bpy.data.meshes.new(name)
    bm.to_mesh(me2)
    bm.free()
    out = bpy.data.objects.new(name, me2)
    bpy.context.scene.collection.objects.link(out)
    planar_uv(out)
    return out


def g_top(body, rng, mat, sleeves="long", neck="round", hem=None, ease=(0.016, 0.02), drape=True,
          open_front=0.0, name="Top", button=None):
    """Any upper garment as a shell of the body: sleeves long / short / none (a vest with armholes); neck round
    (scooped), crew (high round), collar (a shirt buttoned to the neck: stand and points), open (a shirt open at the
    neck: collar spread on a V) or vest (deep); hem height (default the hips); drape: the cloth hangs from the
    chest instead of following it; open_front: half-width of an opening down the front (cardigans); button: the
    buttons' colour (shirts)."""
    hem_z = z_of(body, "spine_01") - 0.03 if hem is None else hem
    neck_j = body.j("neck_01")
    elbow = {s: body.j("lowerarm_" + s) for s in "lr"}
    wrist = {s: body.j("hand_" + s) for s in "lr"}
    shoulder = {s: body.j("upperarm_" + s) for s in "lr"}

    def keep(i):
        p, part = body.co[i], body.part[i]
        parts = ["torso", "neck"] + (["arm", "forearm"] if sleeves != "none" else [])
        ok = np.isin(part, parts) & (p[:, 2] > hem_z)
        if neck == "open":
            ok &= ~((p[:, 1] < neck_j[1]) & (part == "torso")
                    & (np.abs(p[:, 0] - neck_j[0]) < (p[:, 2] - (neck_j[2] - 0.15)) * 0.42))
        ok &= ~{"round": lambda: neck_hole(body, p, part, front=0.05),
                "open": lambda: neck_hole(body, p, part, rx=0.065, ry=0.065, front=0.0),
                "crew": lambda: neck_hole(body, p, part, rx=0.07, ry=0.07, front=0.015),
                "collar": lambda: neck_hole(body, p, part, rx=0.065, ry=0.065, front=0.0),
                "vest": lambda: neck_hole(body, p, part, rx=0.085, ry=0.085, front=0.11, back=0.03)}[neck]()
        if open_front:
            ok &= ~((p[:, 1] < neck_j[1]) & (np.abs(p[:, 0] - neck_j[0]) < open_front) & (part == "torso"))
        for s, sgn in (("l", 1), ("r", -1)):
            mine = np.sign(p[:, 0]) == sgn
            if sleeves == "none":
                ok &= ~(mine & (np.linalg.norm(p - (shoulder[s] + np.array([0.0, 0.0, -0.05])), axis=1) < 0.095))
            elif sleeves == "short":
                ax = elbow[s] - shoulder[s]
                ax /= np.linalg.norm(ax)
                ok &= ~(mine & (part == "forearm"))
                ok &= ~(mine & (part == "arm") & ((p - elbow[s]) @ ax > -0.1))
            else:
                ax = wrist[s] - elbow[s]
                ax /= np.linalg.norm(ax)
                ok &= ~(mine & (part == "forearm") & ((p - wrist[s]) @ ax > -0.015))
        return ok

    armpit_z = z_of(body, "upperarm_l") - 0.04
    ob = shell(body, keep, lambda i: np.where(body.part[i] == "torso", ease[0], ease[1]), name=name, smooth=24,
               drapes=[("torso", hem_z, armpit_z)] if drape else ())
    cylinder_uv(ob, body)
    if neck == "collar":
        lapels(ob, neck_j[2] - 0.07, neck_j, width=0.03, lift=0.003)     # the points
        jacket_collar(ob, neck_j, height=0.026)
    elif neck == "open":
        v_lapels(ob, neck_j, neck_j[2] - 0.15, neck_j[2] - 0.01, 0.42, width=0.045, lift=0.003)
        jacket_collar(ob, neck_j, height=0.026)
    ob.data.materials.append(mat)
    pieces = [ob]
    if button is not None:
        top_z = neck_j[2] - (0.05 if neck == "collar" else 0.17)
        b = buttons(ob, float(neck_j[0]), top_z, hem_z + 0.04)
        b.data.materials.append(fabric("Seta_bottoni", weave(TEX, button, rng, scale=2, depth=0.02), rough=0.3,
                                       tile_m=0.02))
        pieces.append(b)
    return pieces


def g_trousers(body, rng, mat, ease=(0.02, 0.03), name="Pantaloni", fall=0.12):
    """Trousers in any cloth: waist to ankle, the ease growing down the leg from ease[0] to ease[1]."""
    waist_z = z_of(body, "spine_01") + 0.02
    knee = z_of(body, "calf_l")

    def keep(i):
        p, part = body.co[i], body.part[i]
        return np.isin(part, ["torso", "thigh", "calf"]) & (p[:, 2] < waist_z) & (p[:, 2] > z_of(body, "foot_l") - 0.01)

    def e(i):
        z = body.co[i][:, 2]
        return ease[0] + np.clip((knee + 0.1 - z) / knee, 0, 1) * (ease[1] - ease[0])

    crotch_z = z_of(body, "pelvis") - 0.06
    foot_z = z_of(body, "foot_l")
    legs = [(["thigh", "calf"], foot_z, crotch_z, fall, sd) for sd in (1, -1)]
    ob = shell(body, keep, e, smooth=28, name=name, drapes=legs)      # anatomy smoothed away, legs falling straight
    cylinder_uv(ob, body)
    ob.data.materials.append(mat)
    return [ob]


def g_gonna(body, rng, mat, hem=None, flare=0.12, name="Gonna"):
    """Skirt from the waist, A-line (flare: metres of ease per metre below the hips), to the knee by default."""
    waist_z = z_of(body, "spine_02")
    hem_z = z_of(body, "calf_l") - 0.04 if hem is None else hem
    ob = loft(body, ["torso", "thigh", "calf"], waist_z + 0.02, hem_z,
              lambda z, a: 0.012 + max(0.0, (waist_z - 0.1 - z)) * flare, name=name)
    ob.data.materials.append(mat)
    return [ob]


def side_stripes(ob, body, mat, width=0.02):
    """A band down the outer side of the arms and legs (tracksuits): those faces wear `mat`."""
    ob.data.materials.append(mat)
    slot = len(ob.data.materials) - 1
    part = body.part[np.array(ob["src"])]
    co = np.array([v.co[:] for v in ob.data.vertices])
    axes = {}
    for s in "lr":
        axes[("arm", s)] = (body.j("upperarm_" + s), body.j("lowerarm_" + s))
        axes[("forearm", s)] = (body.j("lowerarm_" + s), body.j("hand_" + s))
        axes[("thigh", s)] = (body.j("thigh_" + s), body.j("calf_" + s))
        axes[("calf", s)] = (body.j("calf_" + s), body.j("foot_" + s))
    for poly in ob.data.polygons:
        vs = list(poly.vertices)
        pt = part[vs[0]]
        c = co[vs].mean(0)
        s = "l" if c[0] >= 0 else "r"
        if (pt, s) not in axes or any(part[v] != pt for v in vs):
            continue
        a, b = axes[(pt, s)]
        ax = (b - a) / np.linalg.norm(b - a)
        d = c - a
        d -= ax * (d @ ax)
        out = np.array([1.0 if s == "l" else -1.0, 0.0, 0.0])
        out -= ax * (out @ ax)
        out /= np.linalg.norm(out)
        if d @ out > 0 and np.linalg.norm(d - out * (d @ out)) < width:
            poly.material_index = slot


def g_tuta(body, rng, colour, part):
    """Tracksuit (1980s acetate): zipped jacket with a collar, or trousers, white bands down the sides."""
    mat = fabric("Seta_tuta", weave(TEX, colour, rng, scale=2, depth=0.03), rough=0.55, tile_m=0.08)
    band = fabric("Seta_banda", weave(TEX, (0.85, 0.85, 0.85), rng, scale=2, depth=0.03), rough=0.55, tile_m=0.08)
    if part == "giacca":
        ob = g_top(body, rng, mat, sleeves="long", neck="collar", ease=(0.028, 0.026), name="TutaGiacca")[0]
    else:
        ob = g_trousers(body, rng, mat, ease=(0.024, 0.04), name="TutaPantaloni", fall=0.2)[0]
    side_stripes(ob, body, band)
    return [ob]


# Adults and the young: cloths.
def m_jeans(rng, name):
    return fabric("Jeans_" + name, denim(TEX, (0.09, 0.14, 0.3), rng), rough=0.85, tile_m=0.05)


def m_quadri(rng):
    return fabric("Cotone_quadri", common.tartan(TEX, (0.62, 0.6, 0.55),
                                                  [(0.0, 0.18, (0.55, 0.1, 0.08), 0.75), (0.5, 0.06, (0.1, 0.12, 0.3), 0.6)],
                                                  rng), rough=0.8, tile_m=0.12)


def m_maglione(rng):
    return fabric("Maglia_maglione", stripes(TEX, [(0.08, 0.1, 0.22), (0.75, 0.7, 0.6), (0.45, 0.08, 0.08),
                                                   (0.75, 0.7, 0.6)], [5, 1, 1, 1], rng), rough=0.95, tile_m=0.16)


def m_fiori(rng):
    return fabric("Cotone_fiori", floral(TEX, (0.14, 0.22, 0.45), [(0.9, 0.88, 0.82), (0.95, 0.75, 0.2)],
                                         (0.95, 0.8, 0.3), rng), rough=0.8, tile_m=0.2)


def planar_uv(ob):
    """UVs in metres from the front (x, z) - for small pieces."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers[0].data
    for l in me.loops:
        c = me.vertices[l.vertex_index].co
        uv[l.index].uv = (c.x + c.y, c.z)


def strip(name, pts, sides, widths, closed=False):
    """A ribbon through points pts, `widths` across along the `sides` directions; closed: a loop."""
    bm = bmesh.new()
    rows = [(bm.verts.new(p - sd * w / 2), bm.verts.new(p + sd * w / 2)) for p, sd, w in zip(pts, sides, widths)]
    count = len(rows) if closed else len(rows) - 1
    for i in range(count):
        a, b = rows[i], rows[(i + 1) % len(rows)]
        bm.faces.new([a[0], b[0], b[1], a[1]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    planar_uv(ob)
    return ob


def ring_round(body, centre, axis, offset, n=24, reach=0.09):
    """Points round a limb on the plane through centre across axis: rays from inside out to the body's surface
    (capped at `reach`, where the limb joins the torso), `offset` out."""
    axis = Vector(axis).normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        d = u * math.cos(a) + v * math.sin(a)
        loc, nrm, _, dist = body.bvh.ray_cast(Vector(centre), d, reach)
        pts.append(loc + d * offset if loc is not None else Vector(centre) + d * (reach * 0.8))
    return pts, axis


def g_cravatta(body, rng, colour=(0.3, 0.07, 0.06), name="Cravatta"):
    """Tie: down the middle of the shirt front from the collar to the belt, a knot at the top, pointed."""
    neck = body.j("neck_01")
    zs = np.linspace(neck[2] - 0.025, z_of(body, "spine_01") + 0.02, 30)
    pts, sides, widths = [], [], []
    hang = None                      # the shirt falls from the chest: the tie's y never comes back towards the body
    for i, z in enumerate(zs):
        loc, nrm, _, _ = body.bvh.ray_cast(Vector((neck[0], -1.0, float(z))), Vector((0, 1, 0)))
        if loc is None:
            continue
        t = i / (len(zs) - 1)
        knot = t < 0.07
        q = loc + nrm * (0.03 if knot else 0.026)
        if hang is not None and not knot:
            q.y = min(q.y, hang + 0.35 * (zs[i - 1] - z))
        hang = q.y
        pts.append(q)
        sides.append(Vector((1, 0, 0)))
        widths.append(0.034 if knot else 0.028 + 0.06 * t)
    ob = strip(name, pts, sides, widths)
    # The point.
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    a, b = bm.verts[-2], bm.verts[-1]
    tip = bm.verts.new((a.co + b.co) / 2 + Vector((0, 0, -0.035)))
    bm.faces.new([a, b, tip])
    bm.to_mesh(ob.data)
    bm.free()
    planar_uv(ob)
    ob.data.materials.append(fabric("Seta_" + name, weave(TEX, colour, rng, scale=2, depth=0.1), rough=0.5,
                                    tile_m=0.04))
    return [ob]


def surface_path(body, pts, offset, closed=False, per_segment=8):
    """A path through pts laid on the body's surface (each point moved to the nearest surface, `offset` out):
    points, and the directions across it (for strip())."""
    pts = [Vector(p) for p in pts]
    dense = []
    count = len(pts) if closed else len(pts) - 1
    for i in range(count):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        for k in range(per_segment):
            dense.append(a.lerp(b, k / per_segment))
    if not closed:
        dense.append(pts[-1])
    out, normals = [], []
    for q in dense:
        loc, nrm, _, _ = body.bvh.find_nearest(q)
        out.append(loc + nrm * offset)
        normals.append(nrm)
    sides = []
    for i, (q, n) in enumerate(zip(out, normals)):
        nxt = out[(i + 1) % len(out)] if closed or i + 1 < len(out) else q
        prv = out[i - 1] if closed or i > 0 else q
        tangent = (nxt - prv).normalized()
        sides.append(n.cross(tangent).normalized())
    return out, sides


def g_fondina(body, rng, colour=(0.3, 0.17, 0.08)):
    """Shoulder holster in brown leather: a strap round each shoulder, one across the back, the holster under the
    left arm."""
    pieces = []
    # A loop round each shoulder: over the front of the shoulder, the top, the shoulder blade, under the armpit.
    loop = [(-0.04, -0.09, 0.02), (-0.03, 0.0, 0.08), (-0.04, 0.09, 0.02), (-0.02, 0.08, -0.1), (0.0, 0.0, -0.13),
            (-0.02, -0.08, -0.1)]
    for side, sgn in (("l", 1), ("r", -1)):
        joint = Vector(body.j("upperarm_" + side))
        pts, sides = surface_path(body, [joint + Vector((dx * sgn, dy, dz)) for dx, dy, dz in loop], 0.014,
                                  closed=True)
        pieces.append(strip("Spallaccio", pts, sides, [0.026] * len(pts), closed=True))
    z = z_of(body, "upperarm_l") + 0.0
    xs = np.linspace(body.j("upperarm_r")[0] + 0.03, body.j("upperarm_l")[0] - 0.03, 14)
    pts = []
    for x in xs:
        loc, nrm, _, _ = body.bvh.ray_cast(Vector((float(x), 1.0, z)), Vector((0, -1, 0)))
        if loc is not None:
            pts.append(loc + nrm * 0.014)
    pieces.append(strip("Schiena", pts, [Vector((0, 0, 1))] * len(pts), [0.026] * len(pts)))
    # The holster: a block on the left side under the arm, its muzzle tilted back.
    armpit_z = z_of(body, "upperarm_l") - 0.04
    side_y = float(body.j("spine_04")[1])
    loc, nrm, _, _ = body.bvh.ray_cast(Vector((1.0, side_y, armpit_z - 0.08)), Vector((-1, 0, 0)))
    if loc is not None:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        mat = (Matrix.Translation(loc + nrm * 0.027) @ Matrix.Rotation(math.radians(-25), 4, "X")
               @ Matrix.Diagonal((0.025, 0.055, 0.14, 1)))
        bmesh.ops.transform(bm, matrix=mat, verts=bm.verts[:])
        me = bpy.data.meshes.new("Fondina")
        bm.to_mesh(me)
        bm.free()
        hol = bpy.data.objects.new("Fondina", me)
        bpy.context.scene.collection.objects.link(hol)
        planar_uv(hol)
        pieces.append(hol)
    mat = fabric("Cuoio_fondina", common.leather(TEX, colour, rng), rough=0.5, tile_m=0.3)
    for ob in pieces:
        ob.data.materials.append(mat)
    return pieces


def g_orologio(body, rng):
    """Gold wristwatch on the left wrist: a band and a round face on the back of the wrist."""
    hand, elbow = body.j("hand_l"), body.j("lowerarm_l")
    axis = (hand - elbow) / np.linalg.norm(hand - elbow)
    pts, ax = ring_round(body, hand - axis * 0.035, axis, 0.004, n=20, reach=0.06)
    band = strip("Cinturino", pts, [ax] * len(pts), [0.018] * len(pts), closed=True)
    # The face: where the band is furthest up and out.
    up_out = Vector((0.6, 0.0, 0.8)).normalized()
    c = max(pts, key=lambda q: (q - Vector(hand - axis * 0.035)).normalized().dot(up_out))
    nrm = (c - Vector(hand - axis * 0.035)).normalized()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.016, radius2=0.016, depth=0.006)
    rot = Vector((0, 0, 1)).rotation_difference(nrm).to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(c + nrm * 0.003) @ rot, verts=bm.verts[:])
    me = bpy.data.meshes.new("Quadrante")
    bm.to_mesh(me)
    bm.free()
    face = bpy.data.objects.new("Quadrante", me)
    bpy.context.scene.collection.objects.link(face)
    planar_uv(face)
    gold = fabric("Oro_orologio", common.leather(TEX, (0.78, 0.58, 0.2), rng), rough=0.3, tile_m=0.1)
    for ob in (band, face):
        ob.data.materials.append(gold)
    return [band, face]


def m_cloth(rng, name, colour, scale=3, depth=0.06, tile_m=0.1):
    return fabric(name, weave(TEX, colour, rng, scale=scale, depth=depth), tile_m=tile_m)


# Garment: (source body, builder). Keys are the outfit pieces; the crowd script combines them into outfits.
GARMENTS = {
    "AbitoNero": ("Anziana1", g_abito_nero),
    "Fazzoletto": ("Anziana1", g_fazzoletto),
    "ScarpeDonna": ("Anziana1", g_scarpe),
    "PantaloniVecchio": ("Anziano1", g_pantaloni),
    "CamiciaVecchio": ("Anziano1", g_camicia),
    "GiletVecchio": ("Anziano1", g_gilet),
    "GiaccaVecchio": ("Anziano1", g_giacca),
    "ScarpeVecchio": ("Anziano1", g_scarpe),
    "Scialle": ("Anziana1", g_scialle),
    "Coppola": ("Anziano1", g_coppola),
    "Mantello": ("Anziano1", g_mantello),
    # Men and boys (Uomo2's body, resized to the others).
    "CamiciaQuadri": ("Uomo2", lambda b, r: g_top(b, r, m_quadri(r), neck="collar", ease=(0.018, 0.022),
                                                  name="CamiciaQuadri", button=(0.85, 0.82, 0.75))),
    "Maglione": ("Uomo2", lambda b, r: g_top(b, r, m_maglione(r), neck="crew", ease=(0.024, 0.024), name="Maglione")),
    "Canottiera": ("Uomo2", lambda b, r: g_top(b, r, fabric("Maglia_canottiera", knit(TEX, (0.86, 0.85, 0.82), r,
                                                                                         rib=True), tile_m=0.05),
                                               sleeves="none", neck="vest", ease=(0.008, 0.008), name="Canottiera")),
    "Jeans": ("Uomo2", lambda b, r: g_trousers(b, r, m_jeans(r, "uomo"), ease=(0.018, 0.026), name="Jeans")),
    "PantaloniChiari": ("Uomo2", lambda b, r: g_trousers(b, r, fabric("Cotone_chiari", weave(TEX, (0.55, 0.5, 0.4), r,
                                                                                             scale=2), tile_m=0.08),
                                                         ease=(0.022, 0.035), name="PantaloniChiari")),
    "TutaGiacca": ("Uomo2", lambda b, r: g_tuta(b, r, (0.08, 0.12, 0.4), "giacca")),
    "TutaPantaloni": ("Uomo2", lambda b, r: g_tuta(b, r, (0.08, 0.12, 0.4), "pantaloni")),
    "ScarpeGinnastica": ("Uomo2", lambda b, r: g_scarpe(b, r, colour=(0.86, 0.86, 0.84), name="Ginnastica")),
    "Mocassini": ("Uomo2", lambda b, r: g_scarpe(b, r, colour=(0.2, 0.11, 0.05), name="Mocassini")),
    # Women and girls (Donna1's body).
    "Camicetta": ("Donna1", lambda b, r: g_top(b, r, fabric("Cotone_camicetta", weave(TEX, (0.88, 0.78, 0.78), r,
                                                                                         scale=2, depth=0.03),
                                                           tile_m=0.06),
                                               sleeves="short", ease=(0.01, 0.016), drape=True, name="Camicetta")),
    "Gonna": ("Donna1", lambda b, r: g_gonna(b, r, fabric("Lana_gonna", weave(TEX, (0.13, 0.11, 0.18), r, scale=3),
                                                          tile_m=0.1))),
    "Cardigan": ("Donna1", lambda b, r: g_top(b, r, fabric("Maglia_cardigan", knit(TEX, (0.5, 0.13, 0.12), r),
                                                           tile_m=0.08),
                                              neck="round", ease=(0.024, 0.024), drape=True, open_front=0.05,
                                              name="Cardigan")),
    "AbitoFiori": ("Donna1", lambda b, r: (lambda m: g_top(b, r, m, sleeves="short", hem=z_of(b, "spine_02") - 0.02,
                                                           drape=True, ease=(0.012, 0.016), name="Corpetto")
                                           + g_gonna(b, r, m, hem=z_of(b, "calf_l") - 0.08, flare=0.18))(m_fiori(r))),
    "JeansDonna": ("Donna1", lambda b, r: g_trousers(b, r, m_jeans(r, "donna"), ease=(0.01, 0.026), name="JeansDonna")),
    "ScarpeBasse": ("Donna1", lambda b, r: g_scarpe(b, r, colour=(0.32, 0.06, 0.05), name="Basse")),
    # Sandro: everyday (light blue shirt, tie, grey-blue jacket, grey trousers) and the white suit (pink silk shirt
    # open at the neck, shoulder holster, gold watch).
    "CamiciaSandro": ("Sandro", lambda b, r: g_top(b, r, m_cloth(r, "Cotone_camiciaSandro", (0.6, 0.7, 0.85), 2, 0.04,
                                                                 0.06), neck="collar", ease=(0.018, 0.022),
                                                 name="CamiciaSandro", button=(0.9, 0.9, 0.88))),
    "CravattaSandro": ("Sandro", lambda b, r: g_cravatta(b, r, (0.32, 0.08, 0.07), name="CravattaSandro")),
    "GiaccaSandro": ("Sandro", lambda b, r: g_giacca(b, r, (0.2, 0.23, 0.29), cloth="Lana_giaccaSandro")),
    "PantaloniSandro": ("Sandro", lambda b, r: g_trousers(b, r, m_cloth(r, "Lana_pantaloniSandro", (0.24, 0.24, 0.25)),
                                                          ease=(0.022, 0.035), name="PantaloniSandro")),
    "ScarpeSandro": ("Sandro", lambda b, r: g_scarpe(b, r, colour=(0.12, 0.07, 0.04), name="Sandro")),
    "CamiciaRosa": ("Sandro", lambda b, r: g_top(b, r, m_cloth(r, "Seta_camiciaRosa", (0.92, 0.6, 0.66), 2, 0.03, 0.05),
                                                 neck="open", ease=(0.022, 0.026), name="CamiciaRosa",
                                                 button=(0.95, 0.92, 0.9))),
    "GiaccaBianca": ("Sandro", lambda b, r: g_giacca(b, r, (0.86, 0.85, 0.8), cloth="Cotone_giaccaBianca",
                                                   ease=(0.05, 0.03))),
    "PantaloniBianchi": ("Sandro", lambda b, r: g_trousers(b, r, m_cloth(r, "Cotone_pantaloniBianchi", (0.86, 0.85, 0.8)),
                                                           ease=(0.022, 0.036), name="PantaloniBianchi")),
    "ScarpeChiare": ("Sandro", lambda b, r: g_scarpe(b, r, colour=(0.72, 0.66, 0.56), name="Chiare")),
    "Fondina": ("Sandro", g_fondina),
    "Orologio": ("Sandro", g_orologio),
}


# --- output --------------------------------------------------------------------------------------------------------

def preview(body, pieces, path_base):
    sc = bpy.context.scene
    lo, hi = body.co.min(0), body.co.max(0)
    centre = Vector(((lo + hi) / 2).tolist())
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.5
    sc.collection.objects.link(sun)
    sc.camera = cam
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 500, 800
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.6, 0.6, 0.62)
    cam.data.lens = 60
    for label, sgn in (("fronte", -1), ("retro", 1)):
        cam.location = centre + Vector((0.6 * -sgn * 0.3, 4.2 * sgn, 0.15))
        cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
        sun.rotation_euler = (math.radians(55), 0, math.radians(20 if sgn < 0 else 200))
        sc.render.filepath = path_base + label + ".png"
        bpy.ops.render.render(write_still=True)


def build(key, src, fn):
    body = Body(src)
    rng = np.random.default_rng(abs(hash(key)) % (2 ** 32))
    pieces = fn(body, rng)
    for ob in pieces:
        decimate(ob, LODS[0])
        for poly in ob.data.polygons:
            poly.use_smooth = True
    out = os.path.join(OUT, key)
    os.makedirs(out, exist_ok=True)
    preview(body, pieces, os.path.join(out, "anteprima_"))
    bpy.data.objects.remove(body.ob)
    # One mesh, triangulated, origin untouched (the garment sits where the body is).
    bpy.ops.object.select_all(action="DESELECT")
    for ob in pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    if len(pieces) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = "SM_M80_" + key
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    # The fabric's repeat goes into the UVs (Unreal reads the texture straight off them).
    uv = ob.data.uv_layers[0].data
    for poly in ob.data.polygons:
        tile = ob.data.materials[poly.material_index].get("tile_m", 1.0)
        for li in poly.loop_indices:
            uv[li].uv = (uv[li].uv[0] / tile, uv[li].uv[1] / tile)
    common.OUT = OUT
    info = common.export(ob, key, {"body": src, "lods": LODS})
    # Lower LODs for the crowd, next to LOD0.
    for n, tris in enumerate(LODS[1:], start=1):
        lod = ob.copy()
        lod.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(lod)
        decimate(lod, tris)
        lod.name = lod.data.name = "SM_M80_%s_LOD%d" % (key, n)
        bpy.ops.object.select_all(action="DESELECT")
        lod.select_set(True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(out, lod.name + ".fbx"), use_selection=True, apply_unit_scale=True,
                                 apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                                 object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True,
                                 path_mode="COPY", embed_textures=False)
        info["lod%d_triangles" % n] = sum(len(p.vertices) - 2 for p in lod.data.polygons)
    with open(os.path.join(out, key + ".json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    print("VESTITO", json.dumps(info))


# Whole outfits on their source body, for a look before Unreal (blender ... -- insieme).
OUTFITS = {
    "VecchiaNero": ["AbitoNero", "Fazzoletto", "ScarpeDonna"],
    "VecchioGiacca": ["PantaloniVecchio", "CamiciaVecchio", "GiletVecchio", "GiaccaVecchio", "ScarpeVecchio"],
    "VecchiaScialle": ["AbitoNero", "Fazzoletto", "Scialle", "ScarpeDonna"],
    "VecchioCoppola": ["PantaloniVecchio", "CamiciaVecchio", "GiletVecchio", "GiaccaVecchio", "Coppola",
                       "ScarpeVecchio"],
    "UomoQuadri": ["CamiciaQuadri", "Jeans", "ScarpeGinnastica"],
    "UomoMaglione": ["Maglione", "PantaloniChiari", "Mocassini"],
    "UomoCanottiera": ["Canottiera", "Jeans", "Mocassini"],
    "Tuta": ["TutaGiacca", "TutaPantaloni", "ScarpeGinnastica"],
    "DonnaGonna": ["Camicetta", "Gonna", "Cardigan", "ScarpeBasse"],
    "DonnaFiori": ["AbitoFiori", "ScarpeBasse"],
    "DonnaJeans": ["Camicetta", "JeansDonna", "ScarpeBasse"],
    "SandroClassico": ["CamiciaSandro", "CravattaSandro", "GiaccaSandro", "PantaloniSandro", "ScarpeSandro"],
    "SandroBianco": ["CamiciaRosa", "Fondina", "GiaccaBianca", "PantaloniBianchi", "ScarpeChiare", "Orologio"],
    "SandroFondina": ["CamiciaRosa", "Fondina", "PantaloniBianchi", "ScarpeChiare", "Orologio"],
    "Pastore": ["PantaloniVecchio", "CamiciaVecchio", "GiaccaVecchio", "Mantello", "Coppola", "ScarpeVecchio"],
}


def preview_outfits(only=()):
    for name, keys in OUTFITS.items():
        if only and name not in only:
            continue
        body = Body(GARMENTS[keys[0]][0])
        rng = np.random.default_rng(1)
        for key in keys:
            for ob in GARMENTS[key][1](body, rng):
                for poly in ob.data.polygons:
                    poly.use_smooth = True
        preview(body, [], os.path.join(OUT, "Insieme_%s_" % name))


def main():
    if ONLY[:1] == ["insieme"]:
        preview_outfits(ONLY[1:])
        return
    for key, (src, fn) in GARMENTS.items():
        if ONLY and key not in ONLY:
            continue
        build(key, src, fn)


if __name__ == "__main__":
    main()
