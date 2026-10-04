"""Blender 4.3: 80s black sunglasses (wayfarer-like) for the player -> M80_Occhiali.fbx.

Run: blender -b --factory-startup --python m80_sunglasses.py -- <out.fbx>
Two materials: frame (slot 0) and lenses (slot 1). Lenses face -Y in Blender (+Y in Unreal), centre of
the bridge at the origin, 14.4 cm wide.
"""
import math
import sys

import bmesh
import bpy

OUT = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)


def lens_outline(cx, w, h, n=28):
    """Trapezoid with rounded corners, wider at the top (wayfarer)."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, z = math.cos(a), math.sin(a)
        # superellipse for the squarish look, top a bit wider than the bottom
        px = math.copysign(abs(x) ** 0.6, x) * (w / 2) * (1.0 if z > 0 else 0.86)
        pz = math.copysign(abs(z) ** 0.6, z) * (h / 2)
        pts.append((cx + px + (0.004 if z > 0 else 0.0) * math.copysign(1, cx), pz))
    return pts


def ring(bm, outline, depth, grow, y0):
    """Frame rim: an outline extruded in depth, grown outward."""
    cx = sum(p[0] for p in outline) / len(outline)
    outer = [(cx + (x - cx) * (1 + grow), z * (1 + grow * 1.25)) for x, z in outline]
    vs = []
    for (xi, zi), (xo, zo) in zip(outline, outer):
        vs.append([bm.verts.new((xi, y0, zi)), bm.verts.new((xo, y0, zo)), bm.verts.new((xo, y0 + depth, zo)), bm.verts.new((xi, y0 + depth, zi))])
    n = len(vs)
    for i in range(n):
        a, b = vs[i], vs[(i + 1) % n]
        for k in range(4):
            bm.faces.new((a[k], b[k], b[(k + 1) % 4], a[(k + 1) % 4]))


def make():
    mesh = bpy.data.meshes.new("M80_Occhiali")
    obj = bpy.data.objects.new("SM_M80_Occhiali", mesh)
    bpy.context.collection.objects.link(obj)
    frame = bpy.data.materials.new("M_Montatura")
    lens = bpy.data.materials.new("M_Lenti")
    mesh.materials.append(frame)
    mesh.materials.append(lens)
    bm = bmesh.new()
    lw, lh, gap = 0.052, 0.040, 0.018
    for side in (-1, 1):
        cx = side * (gap / 2 + lw / 2)
        out = lens_outline(cx, lw, lh)
        ring(bm, out, 0.006, 0.16, -0.003)
        # lens: a slightly curved disc set into the frame
        centre = bm.verts.new((cx, 0.0005, 0.0))
        rim = [bm.verts.new((x, 0.0, z)) for x, z in out]
        for i in range(len(rim)):
            f = bm.faces.new((centre, rim[i], rim[(i + 1) % len(rim)]))
            f.material_index = 1
        # temple (arm) going back from the outer top corner
        x0 = cx + side * (lw / 2 + 0.006)
        bmesh.ops.create_cube(bm, size=1.0, matrix=__import__("mathutils").Matrix.LocRotScale(
            (x0, 0.06, 0.012), None, (0.004, 0.125, 0.009)))
    # bridge
    bmesh.ops.create_cube(bm, size=1.0, matrix=__import__("mathutils").Matrix.LocRotScale((0, 0.0, 0.014), None, (gap + 0.01, 0.006, 0.007)))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    return obj


make()
bpy.ops.export_scene.fbx(filepath=OUT, object_types={"MESH"}, axis_forward="-Y", axis_up="Z", apply_unit_scale=True, mesh_smooth_type="FACE")
print("M80 written", OUT)
