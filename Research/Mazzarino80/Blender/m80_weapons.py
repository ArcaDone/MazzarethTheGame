"""Blender 4.3: period weapons for the GTA-like game -> one FBX each in <out_dir>.

Run: blender -b --factory-startup --python m80_weapons.py -- <out_dir>
Revolver, Beretta 92, lupara (sawed-off side-by-side shotgun), switchblade, baseball bat.
Each mesh: origin at the grip (where the right hand closes), barrel / blade along +X, top along +Z
(Unreal axes after export). Materials: slot 0 metal, slot 1 grip (wood or plastic). An empty named
SOCKET_Muzzle (the muzzle or the tip) becomes a static mesh socket in Unreal.
"""
import math
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = sys.argv[sys.argv.index("--") + 1]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box(bm, centre, size, mat=0, rot=None):
    m = Matrix.LocRotScale(centre, rot, size)
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat
    return r


def cyl(bm, start, end, radius, mat=0, segs=16, radius2=None):
    """Cylinder (or cone) from start to end."""
    a, b = Vector(start), Vector(end)
    d = b - a
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation((a + b) / 2) @ rot
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=radius, radius2=radius if radius2 is None else radius2,
                              depth=d.length, matrix=m)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat
    return r


def finish(name, bm, muzzle, mats):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new("SM_M80_" + name, mesh)
    bpy.context.collection.objects.link(obj)
    for n in mats:
        mesh.materials.append(bpy.data.materials.new(n))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = False
    # Auto smooth by angle (Blender 4.1+: shade_smooth_by_angle).
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    except Exception:  # noqa: BLE001
        pass
    sock = bpy.data.objects.new("SOCKET_Muzzle", None)
    sock.location = muzzle
    sock.parent = obj
    bpy.context.collection.objects.link(sock)
    path = "%s/M80_%s.fbx" % (OUT, name)
    bpy.ops.export_scene.fbx(filepath=path, object_types={"MESH", "EMPTY"}, axis_forward="-Y", axis_up="Z",
                             apply_unit_scale=True, mesh_smooth_type="FACE", use_selection=False)
    print("M80 written", path)


def revolver():
    reset()
    bm = bmesh.new()
    # Grip (wood), slanted back.
    tilt = Matrix.Rotation(math.radians(-18), 4, "Y").to_3x3().to_quaternion()
    box(bm, (-0.012, 0, -0.035), (0.032, 0.03, 0.085), 1, tilt)
    # Frame, cylinder, barrel, top strap, trigger guard, hammer.
    box(bm, (0.02, 0, 0.022), (0.07, 0.024, 0.04), 0)
    cyl(bm, (0.0, 0, 0.026), (0.042, 0, 0.026), 0.019, 0, 18)
    cyl(bm, (0.042, 0, 0.034), (0.17, 0, 0.034), 0.0085, 0, 14)
    box(bm, (0.1, 0, 0.044), (0.13, 0.008, 0.006), 0)
    box(bm, (0.165, 0, 0.046), (0.006, 0.004, 0.008), 0)  # front sight
    cyl(bm, (0.045, 0, 0.0235), (0.15, 0, 0.0235), 0.006, 0, 10)  # ejector rod housing
    box(bm, (0.018, 0, -0.008), (0.03, 0.006, 0.004), 0)
    box(bm, (0.003, 0, -0.002), (0.004, 0.006, 0.02), 0)
    box(bm, (0.033, 0, 0.002), (0.004, 0.006, 0.022), 0)
    box(bm, (-0.012, 0, 0.046), (0.012, 0.008, 0.016), 0)
    finish("Revolver", bm, (0.172, 0, 0.034), ["Metallo", "Impugnatura"])


def beretta():
    reset()
    bm = bmesh.new()
    tilt = Matrix.Rotation(math.radians(-14), 4, "Y").to_3x3().to_quaternion()
    box(bm, (-0.006, 0, -0.04), (0.034, 0.03, 0.095), 1, tilt)        # grip panels
    box(bm, (0.065, 0, 0.03), (0.2, 0.028, 0.03), 0)                  # slide
    cyl(bm, (0.16, 0, 0.032), (0.172, 0, 0.032), 0.007, 0, 12)        # barrel tip
    box(bm, (0.075, 0, 0.008), (0.16, 0.026, 0.014), 0)                # frame
    box(bm, (0.03, 0, -0.012), (0.045, 0.006, 0.004), 0)               # trigger guard
    box(bm, (0.052, 0, -0.004), (0.004, 0.006, 0.02), 0)
    box(bm, (0.018, 0, -0.002), (0.004, 0.006, 0.016), 0)              # trigger
    box(bm, (-0.025, 0, 0.032), (0.012, 0.012, 0.014), 0)              # hammer
    box(bm, (0.155, 0, 0.047), (0.006, 0.004, 0.006), 0)
    finish("Beretta", bm, (0.174, 0, 0.032), ["Metallo", "Impugnatura"])


def lupara():
    reset()
    bm = bmesh.new()
    # Sawed-off stock as a pistol grip (wood), action, two barrels side by side, fore-end.
    tilt = Matrix.Rotation(math.radians(-22), 4, "Y").to_3x3().to_quaternion()
    box(bm, (-0.07, 0, -0.03), (0.16, 0.04, 0.05), 1, tilt)
    box(bm, (0.035, 0, 0.0), (0.09, 0.044, 0.05), 0)
    for side in (-0.0115, 0.0115):
        cyl(bm, (0.08, side, 0.012), (0.42, side, 0.012), 0.0115, 0, 16)
    box(bm, (0.2, 0, -0.008), (0.16, 0.036, 0.022), 1)                 # fore-end
    box(bm, (0.25, 0, 0.025), (0.34, 0.008, 0.004), 0)                 # rib
    box(bm, (0.02, 0, -0.032), (0.05, 0.006, 0.004), 0)                # trigger guard
    box(bm, (0.012, 0, -0.022), (0.004, 0.006, 0.02), 0)
    box(bm, (0.0, 0, 0.03), (0.02, 0.03, 0.008), 0)                    # top lever
    finish("Lupara", bm, (0.425, 0, 0.012), ["Metallo", "Impugnatura"])


def coltello():
    reset()
    bm = bmesh.new()
    box(bm, (0.0, 0, 0.0), (0.11, 0.016, 0.022), 1)                    # handle
    box(bm, (0.056, 0, 0.0), (0.008, 0.017, 0.024), 0)                 # bolster
    # Blade: tapered, pointed.
    bm2 = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.LocRotScale((0.11, 0, 0.002), None, (0.1, 0.003, 0.02)))
    for v in bm2["verts"]:
        t = (v.co.x - 0.06) / 0.1
        if v.co.x > 0.12:
            v.co.z = 0.002 + (v.co.z - 0.002) * 0.15 + 0.004
        for f in v.link_faces:
            f.material_index = 0
    finish("Coltello", bm, (0.16, 0, 0.006), ["Metallo", "Impugnatura"])


def mazza():
    reset()
    bm = bmesh.new()
    # Hand at the handle end: knob, handle, then thicker barrel up to the end.
    cyl(bm, (-0.07, 0, 0), (-0.06, 0, 0), 0.022, 1, 16)
    cyl(bm, (-0.06, 0, 0), (0.25, 0, 0), 0.0135, 1, 16, 0.016)
    cyl(bm, (0.25, 0, 0), (0.55, 0, 0), 0.016, 1, 16, 0.033)
    cyl(bm, (0.55, 0, 0), (0.76, 0, 0), 0.033, 1, 16, 0.034)
    cyl(bm, (0.76, 0, 0), (0.775, 0, 0), 0.034, 1, 16, 0.028)
    finish("Mazza", bm, (0.7, 0, 0), ["Metallo", "Impugnatura"])


for make in (revolver, beretta, lupara, coltello, mazza):
    make()
