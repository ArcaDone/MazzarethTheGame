"""Accessories for the crowd, carried in the hand by AM80Pedone: an old man's walnut walking stick with a crook handle, a
woven shopping bag with bread and celery sticking out, a lady's black handbag. Each has its origin where the hand
grips it and hangs down -Z (the game keeps it upright under the hand). Real size, metres.
Run: blender -b --factory-startup -P m80_accessori_folla.py
Out: Saved/Mazzarino80/Folla/Accessori/SM_M80_{Bastone,BorsaSpesa,Borsetta}.fbx + accessori.json (material colours)
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = "D:/UE5Projects/GameAnimationSample/Saved/Mazzarino80/Folla/Accessori"
MATERIALS = {
    "Legno": {"color": (0.16, 0.08, 0.035), "roughness": 0.45},
    "Gomma": {"color": (0.02, 0.02, 0.02), "roughness": 0.8},
    "Tessuto": {"color": (0.32, 0.08, 0.06), "roughness": 0.9},
    "Manici": {"color": (0.12, 0.06, 0.03), "roughness": 0.6},
    "Pane": {"color": (0.72, 0.45, 0.2), "roughness": 0.85},
    "Verdura": {"color": (0.22, 0.45, 0.12), "roughness": 0.7},
    "Pelle": {"color": (0.025, 0.022, 0.02), "roughness": 0.35},
    "Fermaglio": {"color": (0.8, 0.62, 0.3), "roughness": 0.3, "metallic": 1.0},
}


def material(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*MATERIALS[name]["color"], 1)
    return m


def new_object(name):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def add_part(bm, ob, geom_fn, mat):
    """Adds geometry made by geom_fn(bm) and gives its new faces the material slot mat."""
    if mat not in [m.name for m in ob.data.materials]:
        ob.data.materials.append(material(mat))
    slot = [m.name for m in ob.data.materials].index(mat)
    before = set(bm.faces)
    geom_fn(bm)
    for f in set(bm.faces) - before:
        f.material_index = slot
        f.smooth = True


def tube(points, radius, segments=12):
    """A tube along a polyline (closed ends)."""
    def fn(bm):
        rings = []
        for i, p in enumerate(points):
            d = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
            a = d.orthogonal().normalized()
            b = d.cross(a).normalized()
            rings.append([bm.verts.new(p + radius * (math.cos(t) * a + math.sin(t) * b))
                          for t in (2 * math.pi * k / segments for k in range(segments))])
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(segments):
                bm.faces.new((r0[k], r0[(k + 1) % segments], r1[(k + 1) % segments], r1[k]))
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return fn


def box(center, size, bevel=0.0):
    def fn(bm):
        res = bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(center) @ Matrix.Diagonal((*size, 1)))
        if bevel:
            bmesh.ops.bevel(bm, geom=list({e for v in res["verts"] for e in v.link_edges}), offset=bevel, segments=3,
                            affect="EDGES", profile=0.5)
    return fn


def ellipsoid(center, radii, rotation=Matrix.Identity(3)):
    def fn(bm):
        res = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
        m = Matrix.Translation(center) @ rotation.to_4x4() @ Matrix.Diagonal((*radii, 1))
        bmesh.ops.transform(bm, matrix=m, verts=res["verts"])
    return fn


def arc(center, radius, start, end, plane_x, plane_y, n=14):
    return [center + radius * (math.cos(t) * plane_x + math.sin(t) * plane_y)
            for t in (start + (end - start) * k / n for k in range(n + 1))]


def finish(ob, bm):
    bm.normal_update()
    bm.to_mesh(ob.data)
    bm.free()
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def bastone():
    ob = new_object("SM_M80_Bastone")
    bm = bmesh.new()
    X, Z = Vector((1, 0, 0)), Vector((0, 0, 1))
    # Crook: the hand holds its top; it curls forward and down; the shaft goes down behind the grip.
    crook = arc(Vector((0.05, 0, -0.01)), 0.05, math.pi, -0.35, X, Z, 16)
    shaft = [Vector((0, 0, -0.01)) + Vector((0, 0, -0.86 * k / 10)) for k in range(11)]
    add_part(bm, ob, tube(list(reversed(crook)) + shaft[1:], 0.012), "Legno")
    add_part(bm, ob, tube([Vector((0, 0, -0.86)), Vector((0, 0, -0.895))], 0.0135), "Gomma")
    finish(ob, bm)
    return ob


def borsa_spesa():
    ob = new_object("SM_M80_BorsaSpesa")
    bm = bmesh.new()
    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    top = -0.17
    add_part(bm, ob, box(Vector((0, 0, top - 0.18)), (0.34, 0.15, 0.36), bevel=0.02), "Tessuto")
    for y in (-0.055, 0.055):
        add_part(bm, ob, tube(arc(Vector((0, y, top)), 0.12, 0.0, math.pi, X, Z * 1.4, 16), 0.008, 8), "Manici")
    # A loaf of bread and a head of celery sticking out of the top.
    tilt = Matrix.Rotation(math.radians(25), 3, "Y")
    add_part(bm, ob, ellipsoid(Vector((-0.08, 0.0, top + 0.02)), (0.05, 0.05, 0.13), tilt), "Pane")
    for k, (x, y) in enumerate(((0.07, -0.03), (0.09, 0.02), (0.05, 0.03))):
        stem = [Vector((x, y, top - 0.1)), Vector((x + 0.01 * k, y, top + 0.12 + 0.03 * k))]
        add_part(bm, ob, tube(stem, 0.012, 8), "Verdura")
        add_part(bm, ob, ellipsoid(stem[1] + Vector((0, 0, 0.03)), (0.035, 0.035, 0.05)), "Verdura")
    finish(ob, bm)
    return ob


def borsetta():
    ob = new_object("SM_M80_Borsetta")
    bm = bmesh.new()
    X, Z = Vector((1, 0, 0)), Vector((0, 0, 1))
    top = -0.11
    add_part(bm, ob, box(Vector((0, 0, top - 0.095)), (0.26, 0.09, 0.19), bevel=0.015), "Pelle")
    add_part(bm, ob, tube(arc(Vector((0, 0, top)), 0.07, 0.15, math.pi - 0.15, X, Z * 1.5, 14), 0.009, 8), "Pelle")
    add_part(bm, ob, box(Vector((0, -0.047, top - 0.03)), (0.05, 0.006, 0.02)), "Fermaglio")
    finish(ob, bm)
    return ob


def export(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath="%s/%s.fbx" % (OUT, ob.name), use_selection=True, object_types={"MESH"},
                             mesh_smooth_type="FACE", apply_scale_options="FBX_SCALE_UNITS")


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for make in (bastone, borsa_spesa, borsetta):
        export(make())
    with open(OUT + "/accessori.json", "w", encoding="utf-8") as fh:
        json.dump(MATERIALS, fh, indent=1)
    # A look at them side by side.
    bpy.ops.object.select_all(action="SELECT")
    for i, ob in enumerate(o for o in bpy.data.objects if o.type == "MESH"):
        ob.location.x = i * 0.5
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (0.5, -2.2, -0.3)
    cam.rotation_euler = (math.radians(92), 0, 0)
    bpy.context.scene.camera = cam
    light = bpy.data.objects.new("Sole", bpy.data.lights.new("Sole", "SUN"))
    bpy.context.scene.collection.objects.link(light)
    light.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 900, 700
    sc.render.filepath = OUT + "/anteprima.png"
    bpy.ops.render.render(write_still=True)


main()
