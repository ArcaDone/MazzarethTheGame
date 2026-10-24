"""Blender 5.2: Sant'Ignazio's game mesh (SantIgnazio_gioco.blend, already turned outward by m80_normali_fuori.py) made
closer to the photos of the Collegio's street front (Via Collegio), the details placed on the package's own named parts:
- the end wall the front wing of the Collegio was missing towards Via Carcere (the cloister could be seen through it);
- rusticated pilasters (lesene) on the Collegio front: plinth, alternating ashlars, cap; only where the wall is solid
  over their whole width and height (no window or door behind them);
- double "eared" stone frames around the ground-floor windows;
- the diamond iron grilles of those windows rebuilt with real bars (square, crossing at 45 degrees, in a frame), the
  old thin ones removed;
- the portal's balcony: a thicker slab with a moulded front on five volute corbels (instead of the round knobs);
- the portal's fluted columns on tall pedestals, with an impost block from the capital up to the balcony.
Game coordinates (m): x out of the street front (its face at x = 0), y along it, z up. The package's high-poly parts
("HP • ...") are in centimetres and mirrored in y (y_game = -y / 100).
New faces take the slot of their material, UVs in metres like m80_chiese_gioco.py (UVMap) and the dirt UVs of the
nearest old face (Sporco).

Run: blender -b <SantIgnazio_gioco.blend> --python m80_santignazio_dettagli.py -- <out_dir>
Out: out_dir/SantIgnazio_gioco.blend, SM_M80_SantIgnazio.fbx and SM_M80_SantIgnazio_Dettagli.fbx (the settings of
     m80_chiese_gioco.py),
     dettagli.json (what was added where), prima_/dopo_ views of the front and close-ups.
"""
import json
import math
import os
import re
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(ARGS[0])
MAIN, DET = "SM_M80_SantIgnazio", "SM_M80_SantIgnazio_Dettagli"
FRONT_X = 0.0
# the end wall of the Collegio's front wing (measured with rays: the courtyard wall's outer face at x = -8.7, the
# east wing's street face at y = 24.98, the roof at z = 10.6)
END_WALL = {"x": (-8.75, -0.1), "y": (24.38, 24.98), "z": (-0.2, 10.62)}
PILASTER_Y = (-7.0, 1.05, 5.4, 14.6, 19.6)
PILASTER_HALF = 0.5
PILASTER_TOP = 10.05      # under the upper string course (Cornice Collegio.001, z 10.15)
REPORT = {"aggiunte": [], "tolte": {}}


# ---------------------------------------------------------------------------------------------
# where things are

def hp_boxes(prefix):
    """Game-space boxes (lo, hi) of the package's high-poly parts whose name starts with prefix."""
    out = []
    for o in bpy.data.objects:
        name = re.sub(r"^HP\W+", "", o.name)
        if o.type != "MESH" or not o.name.startswith("HP") or not name.startswith(prefix):
            continue
        pts = [o.matrix_world @ Vector(v) for v in o.bound_box]
        g = [Vector((p.x / 100, -p.y / 100, p.z / 100)) for p in pts]
        out.append((Vector((min(p.x for p in g), min(p.y for p in g), min(p.z for p in g))),
                    Vector((max(p.x for p in g), max(p.y for p in g), max(p.z for p in g)))))
    return out


def clusters(boxes, gap=0.4):
    """Boxes grouped when they touch (within gap): one group per window."""
    groups = []
    for lo, hi in boxes:
        for g in groups:
            if lo.y <= g[1].y + gap and hi.y >= g[0].y - gap and lo.z <= g[1].z + gap and hi.z >= g[0].z - gap:
                g[0] = Vector((min(g[0].x, lo.x), min(g[0].y, lo.y), min(g[0].z, lo.z)))
                g[1] = Vector((max(g[1].x, hi.x), max(g[1].y, hi.y), max(g[1].z, hi.z)))
                break
        else:
            groups.append([lo.copy(), hi.copy()])
    return groups


def world_tree(objs):
    bm = bmesh.new()
    for o in objs:
        tmp = o.data.copy()
        tmp.transform(o.matrix_world)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    return BVHTree.FromBMesh(bm), bm


def solid_front(tree, y0, y1, z0, z1):
    """The street front is a plain wall over this whole patch: rays from the street hit it at the front's face."""
    for k in range(7):
        y = y0 + (y1 - y0) * k / 6
        for j in range(9):
            z = z0 + (z1 - z0) * j / 8
            hit = tree.ray_cast(Vector((FRONT_X + 3, y, z)), Vector((-1, 0, 0)), 6)
            # an opening lets the ray in deeper than the front; mouldings standing out of it are fine
            if hit[0] is None or hit[0].x < FRONT_X - 0.15:
                return False
    return True


# ---------------------------------------------------------------------------------------------
# geometry

class Part:
    """New faces for one object and one material slot."""

    def __init__(self, obj, slot):
        self.obj, self.slot = obj, slot
        self.verts, self.faces = [], []

    def quad_strip(self, pts, faces):
        base = len(self.verts)
        self.verts.extend(pts)
        self.faces.extend([tuple(base + i for i in f) for f in faces])

    def box(self, lo, hi):
        lo, hi = Vector(lo), Vector(hi)
        p = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        # index = 4 * ix + 2 * iy + iz
        self.quad_strip(p, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])

    def bar(self, a, b, t, depth_x):
        """A square bar from a to b in the front's plane (y, z), t thick, depth_x = (x0, x1)."""
        a, b = Vector(a), Vector(b)
        d = (b - a).normalized()
        n = Vector((0, -d.z, d.y)) * (t / 2)
        x0, x1 = depth_x
        p = []
        for x in (x0, x1):
            for q in (a - n, a + n, b + n, b - n):
                p.append(Vector((x, q.y, q.z)))
        self.quad_strip(p, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def prism_y(self, profile, y0, y1):
        """A shape drawn in (x, z) (counter-clockwise seen from +y) extruded along y."""
        n = len(profile)
        p = [Vector((x, y0, z)) for x, z in profile] + [Vector((x, y1, z)) for x, z in profile]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.quad_strip(p, faces)

    def cylinder_y(self, cx, cz, r, y0, y1, seg=12):
        prof = [(cx + r * math.cos(2 * math.pi * k / seg), cz + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
        self.prism_y(prof, y0, y1)


def slot_of(obj, key):
    for i, m in enumerate(obj.data.materials):
        if m and m.name.endswith("_" + key):
            return i
    raise KeyError(key)


def material_at(tree, bm_world, point, direction, objs):
    """Material slot name of the face a ray hits (to give a new wall the same stone as its neighbour)."""
    hit = tree.ray_cast(Vector(point), Vector(direction), 10)
    if hit[2] is None:
        return None
    # the world bmesh was built object after object: find which object the face index falls in
    idx = hit[2]
    for o in objs:
        n = len(o.data.polygons)
        if idx < n:
            return o.data.materials[o.data.polygons[idx].material_index].name.rsplit("_", 1)[-1]
        idx -= n
    return None


def append(part, near_tree, near_uv):
    """The part's faces into its object, with metric UVs and the nearest old face's dirt UVs."""
    if not part.faces:
        return 0
    me = part.obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv0 = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    uv1 = bm.loops.layers.uv.get("Sporco")
    to_local = part.obj.matrix_world.inverted()
    vs = [bm.verts.new(to_local @ v) for v in part.verts]
    new_faces = []
    for f in part.faces:
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            continue
        face.material_index = part.slot
        new_faces.append(face)
    # every piece is closed: its normals outward
    bmesh.ops.recalc_face_normals(bm, faces=new_faces)
    made = 0
    for face in new_faces:
        face.normal_update()
        n = face.normal
        if abs(n.z) > 0.92:
            U, V = Vector((1, 0, 0)), Vector((0, 1, 0))
        else:
            U = Vector((-n.y, n.x, 0)).normalized()
            V = n.cross(U).normalized()
        c = face.calc_center_median()
        dirt = None
        if uv1 is not None:
            loc, _, idx, _ = near_tree.find_nearest(c)
            dirt = near_uv[idx] if idx is not None else (0.5, 0.5)
        for lp in face.loops:
            lp[uv0].uv = (lp.vert.co.dot(U), lp.vert.co.dot(V))
            if uv1 is not None:
                lp[uv1].uv = dirt
        made += 1
    bm.to_mesh(me)
    bm.free()
    me.update()
    return made


def remove_ring(obj, windows, inner, outer):
    """Removes the old mouldings standing out of the front in a ring around each window (inner..outer m from the
    opening): the corner brackets the eared frames replace. The old frame (closer) and the wall stay."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = []
    for f in bm.faces:
        c = obj.matrix_world @ f.calc_center_median()
        if not (FRONT_X + 0.004 < c.x < FRONT_X + 0.3):
            continue
        for lo, hi in windows:
            in_outer = lo.y - outer <= c.y <= hi.y + outer and lo.z - outer <= c.z <= hi.z + outer
            in_inner = lo.y - inner < c.y < hi.y + inner and lo.z - inner < c.z < hi.z + inner
            if in_outer and not in_inner:
                doomed.append(f)
                break
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(doomed)


def remove_column_bases(obj, shafts):
    """The old bulging column bases stood out of the new pedestals: their curved faces under the pedestal's top go
    (flat step treads and risers nearby stay)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = []
    for f in bm.faces:
        c = obj.matrix_world @ f.calc_center_median()
        n = f.normal
        if c.z > 0.9 or abs(n.z) > 0.9 or abs(n.x) > 0.97 or abs(n.y) > 0.97:
            continue
        for lo, hi in shafts:
            if math.hypot(c.x - (lo.x + hi.x) / 2, c.y - (lo.y + hi.y) / 2) < 0.62:
                doomed.append(f)
                break
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(doomed)


def delete_inside(obj, boxes, slot=None, min_x=None):
    """Removes the object's faces whose centre is inside one of the boxes (game space)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = []
    for f in bm.faces:
        if slot is not None and f.material_index != slot:
            continue
        c = obj.matrix_world @ f.calc_center_median()
        if min_x is not None and c.x < min_x:
            continue
        if any(lo.x <= c.x <= hi.x and lo.y <= c.y <= hi.y and lo.z <= c.z <= hi.z for lo, hi in boxes):
            doomed.append(f)
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return len(doomed)


# ---------------------------------------------------------------------------------------------
# the details

def end_wall(stone, slot_name):
    w = END_WALL
    stone.box((w["x"][0], w["y"][0], w["z"][0]), (w["x"][1], w["y"][1], w["z"][1]))
    REPORT["aggiunte"].append({"muro_testata": w, "materiale": slot_name})


def pilaster(stone, y):
    """A rusticated pilaster on the street front centred at y."""
    h = PILASTER_HALF
    stone.box((FRONT_X - 0.05, y - h - 0.05, -0.2), (FRONT_X + 0.26, y + h + 0.05, 1.05))          # plinth
    stone.box((FRONT_X - 0.05, y - h - 0.09, 1.05), (FRONT_X + 0.31, y + h + 0.09, 1.17))          # its cap
    stone.box((FRONT_X - 0.05, y - h + 0.12, 1.17), (FRONT_X + 0.10, y + h - 0.12, PILASTER_TOP))  # bed behind the ashlars
    z, k = 1.19, 0
    while z + 0.40 < PILASTER_TOP - 0.32:
        half = h - 0.04 if k % 2 == 0 else h - 0.12
        stone.box((FRONT_X + 0.05, y - half, z), (FRONT_X + 0.15, y + half, z + 0.40))
        z += 0.425
        k += 1
    stone.box((FRONT_X - 0.05, y - h, PILASTER_TOP - 0.32), (FRONT_X + 0.19, y + h, PILASTER_TOP - 0.12))
    stone.box((FRONT_X - 0.05, y - h - 0.06, PILASTER_TOP - 0.12), (FRONT_X + 0.24, y + h + 0.06, PILASTER_TOP))


def eared_frame(stone, y0, y1, z0, z1):
    """Two stone frames around a window opening (y0..y1, z0..z1): an inner band and an outer one stepping out at the
    top and bottom corners ("orecchie"), like the Collegio's ground floor."""
    def ring(off, width, relief, ear=0.0, ear_h=0.0):
        a0, a1, b0, b1 = y0 - off - width, y1 + off + width, z0 - off - width, z1 + off + width
        x0, x1 = FRONT_X - 0.03, FRONT_X + relief
        stone.box((x0, a0, b0), (x1, a0 + width, b1))            # left
        stone.box((x0, a1 - width, b0), (x1, a1, b1))            # right
        stone.box((x0, a0 + width, b1 - width), (x1, a1 - width, b1))   # top
        stone.box((x0, a0 + width, b0), (x1, a1 - width, b0 + width))   # bottom
        if ear:
            for zz0, zz1 in ((b1 - ear_h, b1), (b0, b0 + ear_h)):
                stone.box((x0, a0 - ear, zz0), (x1, a0, zz1))
                stone.box((x0, a1, zz0), (x1, a1 + ear, zz1))
    ring(0.20, 0.10, 0.10)
    ring(0.36, 0.13, 0.06, ear=0.16, ear_h=0.40)


def diamond_grille(iron, y0, y1, z0, z1, x):
    """Square bars crossing at 45 degrees inside a frame of flat bars, x = the grille's plane."""
    t, step = 0.028, 0.23
    iron.box((x - 0.02, y0, z0), (x + 0.02, y0 + 0.04, z1))
    iron.box((x - 0.02, y1 - 0.04, z0), (x + 0.02, y1, z1))
    iron.box((x - 0.02, y0, z0), (x + 0.02, y1, z0 + 0.04))
    iron.box((x - 0.02, y0, z1 - 0.04), (x + 0.02, y1, z1))
    a0, a1 = y0 + 0.04, y1 - 0.04
    b0, b1 = z0 + 0.04, z1 - 0.04
    bars = 0
    for sign, depth in ((1, (x - 0.014, x + 0.014)), (-1, (x + 0.006, x + 0.034))):
        # lines y - sign * z = c, c spaced so the bars are `step` apart
        cs = [a0 - sign * b0, a1 - sign * b1, a0 - sign * b1, a1 - sign * b0]
        c = min(cs) + step * math.sqrt(2) / 2
        while c < max(cs):
            pts = []
            for zz in (b0, b1):
                yy = c + sign * zz
                if a0 - 1e-6 <= yy <= a1 + 1e-6:
                    pts.append((yy, zz))
            for yy in (a0, a1):
                zz = (yy - c) * sign
                if b0 - 1e-6 <= zz <= b1 + 1e-6:
                    pts.append((yy, zz))
            pts = sorted(set((round(p[0], 5), round(p[1], 5)) for p in pts))
            if len(pts) >= 2 and (Vector(pts[0]) - Vector(pts[-1])).length > 0.05:
                p0, p1 = pts[0], pts[-1]
                iron.bar((0, p0[0], p0[1]), (0, p1[0], p1[1]), t, depth)
                bars += 1
            c += step * math.sqrt(2)
    return bars


def volute_corbel(stone, y, x_out, z_top, height):
    """A stone corbel under the balcony: a block against the wall turning into an S-shaped scroll."""
    prof = [(FRONT_X - 0.05, z_top), (x_out, z_top), (x_out, z_top - 0.16)]
    # the underside: an S from the front down to the wall
    for k in range(1, 12):
        s = k / 12
        xx = x_out - (x_out - FRONT_X - 0.10) * s
        zz = z_top - 0.16 - (height - 0.16) * (0.5 - 0.5 * math.cos(math.pi * s)) - 0.06 * math.sin(2 * math.pi * s)
        prof.append((xx, zz))
    prof.append((FRONT_X - 0.05, z_top - height))
    stone.prism_y(prof, y - 0.13, y + 0.13)
    stone.cylinder_y(FRONT_X + 0.17, z_top - height + 0.12, 0.12, y - 0.15, y + 0.15)      # the scroll's eye
    stone.cylinder_y(x_out - 0.08, z_top - 0.24, 0.09, y - 0.15, y + 0.15)                  # the front curl


def portal(stone):
    shafts = hp_boxes("Fusto colonna portale")
    corbels = hp_boxes("Corpo mensola scolpita")
    slab = hp_boxes("Baldacchino ingresso")
    rep = {"colonne": len(shafts), "mensole": len(corbels)}
    REPORT["tolte"]["basi_colonne"] = remove_column_bases(bpy.data.objects[MAIN], shafts)
    for lo, hi in shafts:
        cy = (lo.y + hi.y) / 2
        stone.box((FRONT_X + 0.04, cy - 0.40, -0.2), (FRONT_X + 0.88, cy + 0.40, 0.80))     # pedestal
        stone.box((FRONT_X + 0.02, cy - 0.44, 0.80), (FRONT_X + 0.92, cy + 0.44, 0.90))     # its cornice
        stone.box((FRONT_X + 0.06, cy - 0.40, 4.19), (FRONT_X + 0.86, cy + 0.40, 4.80))     # impost block
        stone.box((FRONT_X + 0.03, cy - 0.44, 4.80), (FRONT_X + 0.90, cy + 0.44, 4.92))
    if slab:
        lo = Vector((min(b[0].x for b in slab), min(b[0].y for b in slab), min(b[0].z for b in slab)))
        hi = Vector((max(b[1].x for b in slab), max(b[1].y for b in slab), max(b[1].z for b in slab)))
        rep["balcone"] = [list(lo), list(hi)]
        stone.box((FRONT_X - 0.05, lo.y - 0.05, lo.z - 0.10), (hi.x, hi.y + 0.05, lo.z))          # thicker slab
        stone.box((hi.x - 0.02, lo.y - 0.12, lo.z - 0.14), (hi.x + 0.10, hi.y + 0.12, lo.z + 0.06))  # moulded front
        stone.box((hi.x + 0.06, lo.y - 0.14, hi.z - 0.04), (hi.x + 0.13, hi.y + 0.14, hi.z + 0.02))
        z_top = lo.z - 0.10
        x_out = hi.x - 0.12
    else:
        z_top, x_out = 5.43, 1.0
    if corbels:
        REPORT["tolte"]["mensole"] = delete_inside(
            bpy.data.objects[MAIN],
            [(lo - Vector((0.02, 0.02, 0.02)), hi + Vector((0.02, 0.02, 0.02))) for lo, hi in corbels], min_x=0.05)
    for lo, hi in corbels:
        volute_corbel(stone, (lo.y + hi.y) / 2, x_out, z_top, 0.78)
    REPORT["aggiunte"].append({"portale": rep})


# ---------------------------------------------------------------------------------------------
# views

def views(tag, objs):
    sc = bpy.context.scene
    for o in sc.objects:
        o.hide_render = o not in objs
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.show_cavity = True
    sc.display.shading.show_backface_culling = True
    cam = bpy.data.objects.new("M80_Cam", bpy.data.cameras.new("M80_Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    shots = {"collegio": ((30, 11.5, 6.5), (0, 11.5, 6.5), 31, 2400, 1100, "ORTHO"),
             "portale": ((30, 10.0, 4.0), (0, 10.0, 4.0), 9, 1600, 1500, "ORTHO"),
             "portale_3q": ((9, 4.5, 2.0), (0, 10.0, 4.0), 0, 1600, 1100, "PERSP"),
             "finestra": ((30, 3.0, 3.0), (0, 3.0, 3.0), 5, 1500, 1500, "ORTHO"),
             "testata": ((14, 40, 7), (-4, 24.9, 5), 0, 1600, 1100, "PERSP")}
    for name, (loc, look, ortho, w, h, kind) in shots.items():
        cam.data.type = kind
        if kind == "ORTHO":
            cam.data.ortho_scale = ortho
        else:
            cam.data.lens = 30
        sc.render.resolution_x, sc.render.resolution_y = w, h
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (tag, name))
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def main():
    os.makedirs(OUT, exist_ok=True)
    main_ob, det_ob = bpy.data.objects[MAIN], bpy.data.objects[DET]
    objs = [main_ob, det_ob]
    views("prima", objs)
    tree, bm_world = world_tree(objs)
    # dirt UVs of the old faces, to give each new face the nearest one's
    near_bm = bmesh.new()
    near_bm.from_mesh(main_ob.data)
    sp = near_bm.loops.layers.uv.get("Sporco")
    near_uv = [tuple(sum((lp[sp].uv for lp in f.loops), Vector((0, 0))) / len(f.loops)) if sp else (0.5, 0.5)
               for f in near_bm.faces]
    near_tree = BVHTree.FromBMesh(near_bm)

    stone = Part(main_ob, slot_of(main_ob, "Pietra"))
    wall_name = material_at(tree, bm_world, (-12, 30, 6), (0, -1, 0), objs) or "Pietrame"
    wall = Part(main_ob, slot_of(main_ob, wall_name))
    iron = Part(det_ob, slot_of(det_ob, "Ferro"))

    end_wall(wall, wall_name)
    windows = [g for g in clusters(hp_boxes("Grata a rombi")) if g[1].y - g[0].y > 0.5]
    placed = []
    for y in PILASTER_Y:
        # clear of the windows' new eared frames (0.65 m out from the opening) and on solid wall
        w = PILASTER_HALF + 0.1
        free = all(y + w < lo.y - 0.68 or y - w > hi.y + 0.68 for lo, hi in windows)
        if free and solid_front(tree, y - w, y + w, 0.4, PILASTER_TOP - 0.3):
            pilaster(stone, y)
            placed.append(y)
    REPORT["aggiunte"].append({"lesene_y": placed, "scartate_y": [y for y in PILASTER_Y if y not in placed]})

    old = [(g[0] - Vector((0.2, 0.03, 0.03)), g[1] + Vector((0.2, 0.03, 0.03))) for g in windows]
    REPORT["tolte"]["grate_vecchie"] = delete_inside(det_ob, old, slot=slot_of(det_ob, "Ferro"))
    main_ob_ = bpy.data.objects[MAIN]
    REPORT["tolte"]["squadrette_finestre"] = remove_ring(main_ob_, windows, 0.24, 0.72)
    bars = 0
    for lo, hi in windows:
        eared_frame(stone, lo.y, hi.y, lo.z, hi.z)
        bars += diamond_grille(iron, lo.y, hi.y, lo.z, hi.z, (lo.x + hi.x) / 2)
    REPORT["aggiunte"].append({"finestre": [[round(v, 2) for v in (lo.y, hi.y, lo.z, hi.z)] for lo, hi in windows],
                               "barre_grate": bars})
    portal(stone)

    for part in (wall, stone):
        REPORT.setdefault("facce", {})[part.obj.name + ":" + part.obj.data.materials[part.slot].name] = append(part, near_tree, near_uv)
    REPORT["facce"][det_ob.name + ":Ferro"] = append(iron, near_tree, near_uv)
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(o.data)
        bm.free()
        REPORT.setdefault("triangoli", {})[o.name] = len(o.data.polygons)
    views("dopo", objs)
    with open(os.path.join(OUT, "dettagli.json"), "w", encoding="utf-8") as fh:
        json.dump(REPORT, fh, indent=1, default=lambda v: [round(c, 3) for c in v])
    print("M80", json.dumps(REPORT, default=lambda v: [round(c, 3) for c in v])[:3000])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, os.path.basename(bpy.data.filepath)))
    # one file per mesh: Unreal's importer then can't merge them or name them otherwise
    for o in objs:
        bpy.ops.object.select_all(action="DESELECT")
        o.hide_set(False)
        o.hide_render = False
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, o.name + ".fbx"), use_selection=True, apply_unit_scale=True,
                                 apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                                 object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True)


main()
