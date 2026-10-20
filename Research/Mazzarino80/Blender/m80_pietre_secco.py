"""Blender 4.3: the stones of the dry-stone walls ("Pietra a secco" of "Scalinata (Mazzarino)"), exported to
D:/Mazzarino80_Sorgenti/Muretti/M80_PietreSecco.fbx for Scripts/m80_muretti_prova.py.

Run: blender -b --factory-startup --python m80_pietre_secco.py
SM_M80_PietraSecco_0..7: field stones of pale limestone, each its own shape: a box of real size (about
20-45 cm long, 14-26 cm tall, 20-30 cm deep) rounded by subdivision, then knocked about by large lumps, flat
split faces, chipped edges and a fine pitted grain. X runs along the wall, -Y is the face seen from outside the
wall, Z is up; the pivot is the centre of the bounding box. The actor scales them only a little to fill a course.
UVs: cube projection, 1 unit per metre (the material tiles a scanned rock surface on them).
Material slot "Pietra".
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, noise

OUT_DIR = Path("D:/Mazzarino80_Sorgenti/Muretti")
OUT = OUT_DIR / "M80_PietreSecco.fbx"
COUNT = 8


def stone(index):
    rnd = random.Random(100 + index)
    size = Vector((rnd.uniform(0.22, 0.45), rnd.uniform(0.2, 0.3), rnd.uniform(0.14, 0.26)))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    # A little taper and skew: field stones are never boxes.
    for v in bm.verts:
        v.co.x *= 1.0 + rnd.uniform(-0.12, 0.12) * (v.co.z / size.z)
        v.co.z += rnd.uniform(-0.15, 0.15) * size.z * (v.co.x / size.x)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    mesh = bpy.data.meshes.new("SM_M80_PietraSecco_%d" % index)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    sub = obj.modifiers.new("round", "SUBSURF")
    sub.levels = sub.render_levels = 4
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="round")
    seed = Vector((index * 7.3, index * 3.1, index * 5.7))
    # Split faces: a few planes cut flat facets into the rounded block.
    planes = []
    for _ in range(rnd.randint(3, 6)):
        n = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.6))).normalized()
        planes.append((n, max(abs(n.x) * size.x, abs(n.y) * size.y, abs(n.z) * size.z) * 0.5 * rnd.uniform(0.82, 0.95)))
    for v in mesh.vertices:
        p = v.co.copy()
        for n, d in planes:
            over = p.dot(n) - d
            if over > 0:
                p -= n * over
        # Lumps, chips (sharp ridged noise) and grain, along the normal.
        q = p * 6.0 + seed
        lump = noise.fractal(q, 0.5, 2.0, 3) * 0.008
        chip = -max(0.0, noise.ridged_multi_fractal(p * 14.0 + seed, 0.8, 2.0, 3, 1.0, 2.0) - 1.1) * 0.012
        grain = noise.noise(p * 90.0 + seed) * 0.0015 + noise.noise(p * 35.0 + seed) * 0.003
        v.co = p + v.normal * (lump + chip + grain)
    # Centre the bounding box on the pivot.
    lo = Vector([min(v.co[i] for v in mesh.vertices) for i in range(3)])
    hi = Vector([max(v.co[i] for v in mesh.vertices) for i in range(3)])
    mid = (lo + hi) * 0.5
    for v in mesh.vertices:
        v.co -= mid
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(MATERIAL[0])
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=1.0, scale_to_bounds=False, correct_aspect=False)
    bpy.ops.mesh.quads_convert_to_tris()
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    return obj, hi - lo


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATERIAL.append(bpy.data.materials.new("Pietra"))
    objs = []
    for i in range(COUNT):
        obj, dims = stone(i)
        objs.append(obj)
        print("M80 stone", obj.name, [round(d * 100, 1) for d in dims], len(obj.data.polygons), "tris")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT), use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True)
    print("M80 dry stones exported:", OUT)


MATERIAL = []
main()
