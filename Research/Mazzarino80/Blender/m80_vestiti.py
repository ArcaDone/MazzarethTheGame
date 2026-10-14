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


def drape(bm, src, body, part, z_lo, z_hi, fall=0.35, band=0.012):
    """Cloth over the hollows of `part` between z_lo and z_hi: per height band its vertices go out to the band's convex
    hull (no cleavage, no hollow at the small of the back), and from the top down each band is at least as wide as
    the one above less `fall` per metre of drop (the cloth hangs from the bust instead of following under it)."""
    verts = [v for v in bm.verts if body.part[v[src]] == part and z_lo <= v.co.z <= z_hi and not v.is_boundary]
    if not verts:
        return
    n = 72
    xy = np.array([(v.co.x, v.co.y) for v in verts])
    centre = xy.mean(axis=0)
    zs = np.array([v.co.z for v in verts])
    prev, prev_z = None, None
    for top in np.arange(z_hi, z_lo - band, -band):
        idx = np.nonzero((zs <= top) & (zs > top - band))[0]
        if len(idx) < 3:
            continue
        radii = ring_radii(hull2d(xy[idx]), centre, n)
        if prev is not None:
            radii = np.maximum(radii, prev - fall * (prev_z - top))
        prev, prev_z = radii, top
        for i in idx:
            d = xy[i] - centre
            r = float(np.linalg.norm(d))
            if r < 1e-6:
                continue
            a = math.atan2(d[1], d[0]) % (2 * math.pi) / (2 * math.pi) * n
            k = int(a) % n
            target = radii[k] + (radii[(k + 1) % n] - radii[k]) * (a - int(a))
            if target > r:
                verts[i].co.x, verts[i].co.y = centre + d / r * target


def shell(body, keep, ease, smooth=12, name="Shell", drapes=()):
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


def loft(body, parts, z_top, z_hem, ease, n=40, dz=0.02, name="Loft", centre_xy=None, close_top=False):
    """Rings around the body's cross sections of `parts` (convex hull per height), from z_top down to z_hem.
    ease(z, angle) -> metres added to the radius. Below the lowest body slice the last ring is carried down."""
    mask = np.isin(body.part, parts)
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
    # Smooth radii along the height and around.
    rr = np.array([r for _, _, r in rings])
    for _ in range(12):
        rr[1:-1] = (rr[:-2] + 2 * rr[1:-1] + rr[2:]) / 4
    for _ in range(3):
        rr = (np.roll(rr, 1, 1) + 2 * rr + np.roll(rr, -1, 1)) / 4
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
    # The crown closed with a fan.
    ring = [v for v in bm.verts if abs(v.co.z - (top_z - 0.012)) < 1e-4]
    if len(ring) > 2:
        tip = bm.verts.new((head[0], head[1] + 0.005, top_z + 0.002))
        ring.sort(key=lambda v: math.atan2(v.co.y - head[1], v.co.x - head[0]))
        for v0, v1 in zip(ring, ring[1:] + ring[:1]):
            try:
                bm.faces.new([tip, v1, v0])
            except ValueError:
                pass
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

    ob = shell(body, keep, lambda i: np.where(body.part[i] == "torso", 0.01, 0.014), name=name)
    cylinder_uv(ob, body)
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
        vee = (p[:, 1] < neck[1]) & (np.abs(p[:, 0]) < (p[:, 2] - chest_z) * 0.45)
        ok &= ~vee
        return ok

    ob = shell(body, keep, lambda i: np.full(len(i), 0.016), name="Gilet")
    cylinder_uv(ob, body)
    ob.data.materials.append(fabric("Lana_gilet", common.tweed(TEX, [colour, (0.2, 0.18, 0.15), (0.05, 0.05, 0.05)],
                                                                rng), rough=0.95, tile_m=0.15))
    return [ob]


def g_giacca(body, rng, colour=(0.1, 0.1, 0.11)):
    """Jacket: long sleeves, open V front over shirt and waistcoat, tails to below the hips."""
    neck = body.j("neck_01")
    hip_z = z_of(body, "spine_01")
    chest_z = z_of(body, "spine_03")
    wrist = {s: body.j("hand_" + s) for s in "lr"}

    def keep(i):
        p, part = body.co[i], body.part[i]
        ok = np.isin(part, ["torso", "arm", "forearm"]) & ~neck_hole(body, p, part, rx=0.08, ry=0.08, front=0.0)
        ok &= p[:, 2] > hip_z - 0.02
        vee = (p[:, 1] < neck[1]) & (np.abs(p[:, 0]) < (p[:, 2] - chest_z) * 0.33) & (part == "torso")
        ok &= ~vee
        for s, sgn in (("l", 1), ("r", -1)):
            ax = wrist[s] - body.j("lowerarm_" + s)
            ax /= np.linalg.norm(ax)
            ok &= ~((np.sign(p[:, 0]) == sgn) & (part == "forearm") & ((p - wrist[s]) @ ax > -0.03))
        return ok

    top = shell(body, keep, lambda i: np.where(body.part[i] == "torso", 0.026, 0.02), name="Giacca")
    cylinder_uv(top, body)
    tails = loft(body, ["torso", "thigh"], hip_z + 0.02, hip_z - 0.15, lambda z, a: 0.02, name="Falde")
    cloth = fabric("Lana_giacca", weave(TEX, colour, rng, scale=3, depth=0.06), rough=0.9, tile_m=0.1)
    for ob in (top, tails):
        ob.data.materials.append(cloth)
    return [top, tails]


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
}


def preview_outfits():
    for name, keys in OUTFITS.items():
        body = Body(GARMENTS[keys[0]][0])
        rng = np.random.default_rng(1)
        for key in keys:
            for ob in GARMENTS[key][1](body, rng):
                for poly in ob.data.polygons:
                    poly.use_smooth = True
        preview(body, [], os.path.join(OUT, "Insieme_%s_" % name))


def main():
    if ONLY == ["insieme"]:
        preview_outfits()
        return
    for key, (src, fn) in GARMENTS.items():
        if ONLY and key not in ONLY:
            continue
        build(key, src, fn)


if __name__ == "__main__":
    main()
