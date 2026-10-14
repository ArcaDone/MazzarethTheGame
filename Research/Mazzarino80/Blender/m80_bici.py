"""Blender 5.2: two 1970s-80s Italian kids' bikes for the crowd, modelled from the user's references.

- Saltafoss: the white "chopper" (cantilever frame with a double top tube, long blue banana seat with a tall chrome
  sissy bar, ape-hanger bars with cables, chrome mudguards, whitewall tyres, spoked wheels, chain guard).
- Bimbo: a small orange kid's bike (16", straight frame, padded seat with a short back hoop, high bars, cream
  mudguards and tyres, kickstand).
One static mesh each, metres in Blender -> cm in the FBX, origin on the ground under the bottom bracket, front along -Y
(as the other props). Wheels are separate named parts in the .json (centre, radius) for when they turn.
Run: blender -b --factory-startup --python m80_bici.py -- [Saltafoss,Bimbo]
Out: Saved/Mazzarino80/Folla/Oggetti/<Key>/{SM_M80_<Key>.fbx, <Key>.json, anteprima.png}
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_folla_oggetti as common  # noqa: E402  (finish, export, material, reset)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = [k for k in (ARGS[0].split(",") if ARGS else []) if k]


def tube(points, radius, mat, name="tube", res=8):
    """A round tube along a polyline (bevelled curve converted to mesh)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = max(1, res // 4)
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (co[0], co[1], co[2], 1)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    ob.data.materials.append(mat)
    ob.select_set(False)
    return ob


def arc(centre, radius, a0, a1, n=12, axis="xz"):
    """Points on a circle arc in the XZ plane (angles in degrees, 0 = +X, 90 = up)."""
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((centre[0] + radius * math.cos(a), centre[1], centre[2] + radius * math.sin(a)))
    return pts


def curve_pts(ctrl, n=16):
    """Catmull-Rom through control points: smooth bends for bars and frames."""
    out = []
    pts = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = (Vector(p) for p in pts[i - 1:i + 3])
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(ctrl[-1]))
    return out


def wheel(cx, cz, r, mats, spokes=36, width=0.045, whitewall=True):
    """Tyre, whitewall band, rim, hub and spokes, axle along Y."""
    parts = []
    rot = (math.radians(90), 0, 0)
    bpy.ops.mesh.primitive_torus_add(major_radius=r - width * 0.5, minor_radius=width * 0.5, major_segments=48,
                                     minor_segments=10, location=(cx, 0, cz), rotation=rot)
    tyre = bpy.context.active_object
    tyre.data.materials.append(mats["gomma"])
    parts.append(tyre)
    if whitewall:
        for side in (-1, 1):
            bpy.ops.mesh.primitive_torus_add(major_radius=r - width * 1.05, minor_radius=width * 0.2, major_segments=48,
                                             minor_segments=6, location=(cx, side * width * 0.28, cz), rotation=rot)
            ww = bpy.context.active_object
            ww.data.materials.append(mats["fascia"])
            parts.append(ww)
    bpy.ops.mesh.primitive_torus_add(major_radius=r - width * 1.15, minor_radius=0.008, major_segments=48,
                                     minor_segments=6, location=(cx, 0, cz), rotation=rot)
    rim = bpy.context.active_object
    rim.data.materials.append(mats["cromo"])
    parts.append(rim)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.02, depth=0.1, location=(cx, 0, cz), rotation=rot)
    hub = bpy.context.active_object
    hub.data.materials.append(mats["cromo"])
    parts.append(hub)
    inner = r - width * 1.15
    for i in range(spokes):
        a = 2 * math.pi * i / spokes
        side = 0.035 if i % 2 else -0.035
        parts.append(tube([(cx + 0.02 * math.cos(a + 0.4), side, cz + 0.02 * math.sin(a + 0.4)),
                           (cx + inner * math.cos(a), 0, cz + inner * math.sin(a))], 0.0012, mats["cromo"], res=4))
    return parts


def saltafoss(key="Saltafoss"):
    common.reset()
    m = {
        "telaio": common.material("M80_Saltafoss_Telaio", color=(0.9, 0.9, 0.88), rough=0.25),
        "cromo": common.material("M80_Saltafoss_Cromo", color=(0.85, 0.85, 0.87), rough=0.12, metal=1.0),
        "gomma": common.material("M80_Saltafoss_Gomma", color=(0.03, 0.03, 0.03), rough=0.85),
        "fascia": common.material("M80_Saltafoss_Fascia", color=(0.92, 0.9, 0.85), rough=0.7),
        "sella": common.material("M80_Saltafoss_Sella", color=(0.1, 0.4, 0.62), rough=0.55),
        "manopole": common.material("M80_Saltafoss_Manopole", color=(0.15, 0.15, 0.15), rough=0.6),
    }
    R = 0.31                      # 24" wheels
    rear, front = (-0.52, R), (0.62, R)
    bb = (0.0, 0.29)              # bottom bracket
    head_lo, head_hi = (0.43, 0.62), (0.47, 0.76)
    seat_top = (-0.12, 0.78)
    parts = []
    parts += wheel(rear[0], rear[1], R, m)
    parts += wheel(front[0], front[1], R, m)
    y = 0.0
    # Cantilever frame: double top tube sweeping down to the rear axle, down tube, seat tube, stays.
    for dz, rad in ((0.0, 0.014), (-0.07, 0.012)):
        parts.append(tube(curve_pts([(head_hi[0], y, head_hi[1] + dz), (0.1, y, 0.72 + dz), (-0.25, y, 0.6 + dz * 0.5),
                                     (rear[0] + 0.03, y, rear[1] + 0.02)]), rad, m["telaio"]))
    parts.append(tube([(head_lo[0], y, head_lo[1]), (bb[0], y, bb[1])], 0.016, m["telaio"]))
    parts.append(tube([(bb[0], y, bb[1]), (seat_top[0], y, seat_top[1] - 0.12)], 0.015, m["telaio"]))
    for side in (-0.05, 0.05):
        parts.append(tube([(bb[0], side * 0.6, bb[1]), (rear[0], side, rear[1])], 0.009, m["telaio"]))
    parts.append(tube([(head_lo[0], y, head_lo[1] - 0.02), (head_hi[0], y, head_hi[1] + 0.02)], 0.02, m["telaio"]))
    # Fork (two legs to the front axle) and the springer's front blades.
    for side in (-0.045, 0.045):
        parts.append(tube([(head_lo[0], side * 0.5, head_lo[1]), (front[0] - 0.02, side, front[1] + 0.05), (front[0], side, front[1])],
                          0.011, m["cromo"]))
        parts.append(tube([(head_lo[0] + 0.05, side * 0.8, head_lo[1] + 0.02), (front[0] + 0.03, side, front[1] + 0.03)],
                          0.007, m["cromo"]))
    # Ape-hanger bars with grips and brake cables.
    stem = (head_hi[0] + 0.02, 0.0, head_hi[1] + 0.05)
    for s in (-1, 1):
        bar = curve_pts([stem, (stem[0] - 0.02, s * 0.12, stem[2] + 0.02), (stem[0] - 0.05, s * 0.2, stem[2] + 0.35),
                         (stem[0] - 0.12, s * 0.27, stem[2] + 0.42), (stem[0] - 0.26, s * 0.3, stem[2] + 0.43)], n=10)
        parts.append(tube(bar, 0.011, m["cromo"]))
        g0 = bar[-1]
        parts.append(tube([(g0[0] + 0.04, g0[1], g0[2]), (g0[0] - 0.08, g0[1], g0[2])], 0.016, m["manopole"]))
        parts.append(tube(curve_pts([(g0[0] + 0.02, g0[1] * 0.95, g0[2] - 0.01), (stem[0] + 0.15, s * 0.12, stem[2] + 0.15),
                                     (head_lo[0] + 0.03, s * 0.04, head_lo[1] + 0.05)], n=8), 0.003, m["manopole"]))
    # Banana seat: a long, soft, upturned pad on a chrome post.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0)
    seat = bpy.context.active_object
    for v in seat.data.vertices:
        x, yy, z = v.co
        v.co = Vector((x * 0.33, yy * (0.1 - 0.025 * x), z * 0.05 + 0.07 * max(0.0, -x) ** 2))
    seat.location = (seat_top[0] - 0.2, 0, seat_top[1] - 0.02)   # long, back over the rear wheel, against the sissy bar
    seat.data.materials.append(m["sella"])
    parts.append(seat)
    parts.append(tube([(seat_top[0], 0, seat_top[1] - 0.12), (seat_top[0] - 0.02, 0, seat_top[1])], 0.011, m["cromo"]))
    # Sissy bar: a tall chrome hoop behind the seat, braced to the rear axle.
    hoop = [(rear[0] + 0.05, -0.05, rear[1])] + [(rear[0] - 0.02, -0.05, 0.95)] + \
        [(rear[0] - 0.02 + 0.0, 0.05 * math.cos(math.radians(a)) * -1, 1.15 + 0.05 * math.sin(math.radians(a))) for a in range(0, 181, 20)] + \
        [(rear[0] - 0.02, 0.05, 0.95), (rear[0] + 0.05, 0.05, rear[1])]
    parts.append(tube(hoop, 0.009, m["cromo"]))
    # Mudguards: chrome shells over both wheels.
    for (cx, cz), a0, a1 in ((rear, 0, 165), (front, 30, 175)):

        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=R + 0.03, depth=0.07, location=(cx, 0, cz),
                                            rotation=(math.radians(90), 0, 0), end_fill_type="NOTHING")
        guard = bpy.context.active_object
        bm = bmesh.new()
        bm.from_mesh(guard.data)
        keep = lambda v: a0 <= (math.degrees(math.atan2(v.co.y, v.co.x)) % 360) <= a1  # noqa: E731
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep(v)], context="VERTS")
        bm.to_mesh(guard.data)
        bm.free()
        solid = guard.modifiers.new("s", "SOLIDIFY")
        solid.thickness = 0.003
        bpy.context.view_layer.objects.active = guard
        bpy.ops.object.modifier_apply(modifier="s")
        guard.data.materials.append(m["cromo"])
        parts.append(guard)
    # Drive: chainring, cranks, pedals, chain guard.
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.09, depth=0.006, location=(bb[0], 0.05, bb[1]),
                                        rotation=(math.radians(90), 0, 0))
    ring = bpy.context.active_object
    ring.data.materials.append(m["cromo"])
    parts.append(ring)
    for s, ang in ((1, -60), (-1, 120)):
        a = math.radians(ang)
        end = (bb[0] + 0.16 * math.cos(a), s * 0.075, bb[1] + 0.16 * math.sin(a))
        parts.append(tube([(bb[0], s * 0.06, bb[1]), end], 0.01, m["cromo"]))
        bpy.ops.mesh.primitive_cube_add(size=1, location=(end[0], s * 0.13, end[2]))
        pedal = bpy.context.active_object
        pedal.scale = (0.09, 0.09, 0.025)
        pedal.data.materials.append(m["manopole"])
        parts.append(pedal)
    bpy.ops.mesh.primitive_cube_add(size=1, location=((bb[0] + rear[0]) / 2, 0.07, (bb[1] + rear[1]) / 2 + 0.03))
    guardc = bpy.context.active_object
    guardc.scale = (0.5, 0.004, 0.09)
    guardc.rotation_euler.y = math.atan2(bb[1] - rear[1], bb[0] - rear[0]) * -1
    guardc.data.materials.append(m["cromo"])
    parts.append(guardc)
    ob = common.finish(parts, key)
    ob.data.transform(Matrix.Rotation(math.radians(-90), 4, "Z"))   # front from +X to -Y
    return common.export(ob, key, {"made": "Saltafoss chopper bike", "wheels": {"rear": [rear[0], rear[1], R], "front": [front[0], front[1], R]}})


def bimbo(key="Bimbo"):
    common.reset()
    m = {
        "telaio": common.material("M80_Bimbo_Telaio", color=(0.85, 0.42, 0.08), rough=0.45),
        "cromo": common.material("M80_Bimbo_Cromo", color=(0.6, 0.6, 0.6), rough=0.35, metal=1.0),
        "gomma": common.material("M80_Bimbo_Gomma", color=(0.05, 0.05, 0.04), rough=0.9),
        "fascia": common.material("M80_Bimbo_Fascia", color=(0.85, 0.75, 0.5), rough=0.7),
        "sella": common.material("M80_Bimbo_Sella", color=(0.8, 0.72, 0.52), rough=0.7),
        "manopole": common.material("M80_Bimbo_Manopole", color=(0.65, 0.55, 0.4), rough=0.7),
    }
    R = 0.21                      # 16" wheels
    rear, front = (-0.36, R), (0.42, R)
    bb = (0.0, 0.2)
    parts = []
    parts += wheel(rear[0], rear[1], R, m, spokes=28, width=0.05)
    parts += wheel(front[0], front[1], R, m, spokes=28, width=0.05)
    head_lo, head_hi = (0.3, 0.42), (0.33, 0.55)
    # Step-through frame: one big tube from the head down to the bottom bracket, a seat tube, stays.
    parts.append(tube(curve_pts([(head_hi[0], 0, head_hi[1] - 0.03), (0.15, 0, 0.36), (0.02, 0, bb[1] + 0.03)]), 0.02, m["telaio"]))
    parts.append(tube([(bb[0], 0, bb[1]), (-0.08, 0, 0.55)], 0.016, m["telaio"]))
    for side in (-0.04, 0.04):
        parts.append(tube([(bb[0], side * 0.6, bb[1]), (rear[0], side, rear[1])], 0.01, m["telaio"]))
        parts.append(tube([(-0.07, side * 0.5, 0.5), (rear[0], side, rear[1])], 0.009, m["telaio"]))
        parts.append(tube([(head_lo[0], side * 0.5, head_lo[1]), (front[0], side, front[1])], 0.011, m["telaio"]))
    parts.append(tube([(head_lo[0], 0, head_lo[1] - 0.02), (head_hi[0], 0, head_hi[1] + 0.02)], 0.022, m["telaio"]))
    # High bars and grips.
    stem = (head_hi[0] + 0.01, 0, head_hi[1] + 0.04)
    for s in (-1, 1):
        bar = curve_pts([stem, (stem[0], s * 0.08, stem[2] + 0.02), (stem[0] - 0.03, s * 0.18, stem[2] + 0.17),
                         (stem[0] - 0.12, s * 0.22, stem[2] + 0.2)], n=8)
        parts.append(tube(bar, 0.01, m["cromo"]))
        g0 = bar[-1]
        parts.append(tube([(g0[0] + 0.03, g0[1], g0[2]), (g0[0] - 0.07, g0[1], g0[2])], 0.015, m["manopole"]))
    # Padded seat with a short back hoop.
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.12, 0, 0.6))
    seat = bpy.context.active_object
    seat.scale = (0.24, 0.12, 0.05)
    bev = seat.modifiers.new("b", "BEVEL")
    bev.width, bev.segments = 0.02, 3
    bpy.context.view_layer.objects.active = seat
    bpy.ops.object.modifier_apply(modifier="b")
    seat.data.materials.append(m["sella"])
    parts.append(seat)
    parts.append(tube([(-0.24, -0.05, 0.6)] + [(-0.28, -0.05 * math.cos(math.radians(a)), 0.72 + 0.04 * math.sin(math.radians(a)))
                                              for a in range(0, 181, 30)] + [(-0.24, 0.05, 0.6)], 0.008, m["telaio"]))
    # Mudguards (cream), chain guard (orange), cranks, pedals, kickstand.
    for (cx, cz), a0, a1 in ((rear, 10, 160), (front, 30, 160)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=R + 0.03, depth=0.07, location=(cx, 0, cz),
                                            rotation=(math.radians(90), 0, 0), end_fill_type="NOTHING")
        guard = bpy.context.active_object
        bm = bmesh.new()
        bm.from_mesh(guard.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not a0 <= (math.degrees(math.atan2(v.co.y, v.co.x)) % 360) <= a1],
                         context="VERTS")
        bm.to_mesh(guard.data)
        bm.free()
        solid = guard.modifiers.new("s", "SOLIDIFY")
        solid.thickness = 0.004
        bpy.context.view_layer.objects.active = guard
        bpy.ops.object.modifier_apply(modifier="s")
        guard.data.materials.append(m["fascia"])
        parts.append(guard)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.17, 0.06, 0.23))
    cg = bpy.context.active_object
    cg.scale = (0.42, 0.006, 0.12)
    cg.data.materials.append(m["telaio"])
    parts.append(cg)
    for s, ang in ((1, -60), (-1, 120)):
        a = math.radians(ang)
        end = (bb[0] + 0.12 * math.cos(a), s * 0.07, bb[1] + 0.12 * math.sin(a))
        parts.append(tube([(bb[0], s * 0.05, bb[1]), end], 0.009, m["cromo"]))
        bpy.ops.mesh.primitive_cube_add(size=1, location=(end[0], s * 0.11, end[2]))
        pedal = bpy.context.active_object
        pedal.scale = (0.07, 0.07, 0.02)
        pedal.data.materials.append(m["gomma"])
        parts.append(pedal)
    parts.append(tube([(-0.2, -0.05, 0.2), (-0.12, -0.16, 0.0)], 0.007, m["cromo"]))
    ob = common.finish(parts, key)
    ob.data.transform(Matrix.Rotation(math.radians(-90), 4, "Z"))   # front from +X to -Y
    return common.export(ob, key, {"made": "kid's bike", "wheels": {"rear": [rear[0], rear[1], R], "front": [front[0], front[1], R]}})


report = {}
for key, fn in (("Saltafoss", saltafoss), ("Bimbo", bimbo)):
    if not ONLY or key in ONLY:
        report[key] = fn()
print("BICI", json.dumps(report))
