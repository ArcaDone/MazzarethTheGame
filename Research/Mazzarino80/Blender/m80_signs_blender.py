"""Blender 4.3: road signs on poles and a marble street plaque, exported to FBX (houses V3, step 11).

Run: blender -b --factory-startup --python m80_signs_blender.py
Units are metres (Unreal imports them as cm). Every sign: pole at the origin, plate facing -Y,
material slots "Face" (the printed face, UV 0-1 over the plate) and "Metal" (pole, back, clamps).
The plaque: back on the Y = 0 plane (the wall), face towards -Y, slots "Face" and "Stone".
"""
import math
from pathlib import Path

import bmesh
import bpy

OUT = Path(__file__).resolve().parent / "M80_Signs.fbx"


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def plate(bm, outline, center_z, thick, face_mat, back_mat, uv_layer, u_size, v_size, y=-0.04):
    """Extruded plate from a 2D outline (x, z around the centre). Front faces -Y."""
    front = [bm.verts.new((x, y - thick, center_z + z)) for x, z in outline]
    back = [bm.verts.new((x, y, center_z + z)) for x, z in outline]
    f = bm.faces.new(front)
    f.material_index = face_mat
    f.normal_update()
    if f.normal.y > 0:
        f.normal_flip()
    for loop in f.loops:
        co = loop.vert.co
        loop[uv_layer].uv = (co.x / u_size + 0.5, (co.z - center_z) / v_size + 0.5)
    b = bm.faces.new(list(reversed(back)))
    b.material_index = back_mat
    b.normal_update()
    if b.normal.y < 0:
        b.normal_flip()
    n = len(outline)
    for i in range(n):
        s = bm.faces.new((front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]))
        s.material_index = back_mat
    return f


def cylinder(bm, radius, z0, z1, segments, mat, x=0.0, y=0.0):
    ring0 = [bm.verts.new((x + radius * math.cos(2 * math.pi * k / segments), y + radius * math.sin(2 * math.pi * k / segments), z0)) for k in range(segments)]
    ring1 = [bm.verts.new((x + radius * math.cos(2 * math.pi * k / segments), y + radius * math.sin(2 * math.pi * k / segments), z1)) for k in range(segments)]
    for k in range(segments):
        f = bm.faces.new((ring0[k], ring0[(k + 1) % segments], ring1[(k + 1) % segments], ring1[k]))
        f.material_index = mat
    top = bm.faces.new(ring1)
    top.material_index = mat


def box(bm, center, half, mat):
    cx, cy, cz = center
    hx, hy, hz = half
    v = [bm.verts.new((cx + sx * hx, cy + sy * hy, cz + sz * hz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    for idx in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        f = bm.faces.new([v[i] for i in idx])
        f.material_index = mat


def make_object(name, build, slots):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    build(bm, uv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for s in slots:
        mesh.materials.append(material(s))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def regular(n, r, rot=0.0):
    return [(r * math.cos(rot + 2 * math.pi * k / n), r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def sign(name, outline, size_u, size_v, height=2.25):
    def build(bm, uv):
        cylinder(bm, 0.03, 0.0, height + 0.25, 12, 1)
        plate(bm, outline, height, 0.012, 0, 1, uv, size_u, size_v)
        for dz in (-0.12, 0.12):
            box(bm, (0, -0.02, height + dz), (0.05, 0.025, 0.015), 1)
    return make_object(name, build, ["M_SignFace", "M_SignMetal"])


def main():
    clear()
    r = 0.30
    sign("SM_M80_Sign_Stop", regular(8, r, math.pi / 8), 2 * r, 2 * r)
    tri = [(-0.45, 0.38), (0.45, 0.38), (0.0, -0.40)]  # matches the drawn triangle (UV centre at z = 0)
    sign("SM_M80_Sign_Yield", tri, 0.9, 0.9)
    circle = regular(32, r)
    for n in ("NoParking", "NoEntry", "NoTransit"):
        sign("SM_M80_Sign_" + n, circle, 2 * r, 2 * r)
    sign("SM_M80_Sign_OneWay", [(-0.45, -0.22), (0.45, -0.22), (0.45, 0.22), (-0.45, 0.22)], 0.9, 0.44)

    def plaque(bm, uv):
        # Thin marble slab, back on the wall plane (Y = 0).
        plate(bm, [(-0.30, -0.075), (0.30, -0.075), (0.30, 0.075), (-0.30, 0.075)], 0.0, 0.02, 0, 1, uv, 0.6, 0.15, y=0.0)
    make_object("SM_M80_StreetPlaque", plaque, ["M_PlaqueFace", "M_PlaqueStone"])

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(filepath=str(OUT), use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE", use_mesh_modifiers=True,
                             bake_space_transform=True)
    print("EXPORTED", OUT)


main()
