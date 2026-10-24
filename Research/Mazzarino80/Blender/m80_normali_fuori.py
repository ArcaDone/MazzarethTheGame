"""Blender 5.2: turns outward the faces of a game mesh that look inward (Unreal culls back faces: a wall facing the
wrong way is seen through from the street). For the churches made by m80_chiese_gioco.py (<Key>_gioco.blend).

Run: blender -b <Key>_gioco.blend --python m80_normali_fuori.py -- <out_dir> <object> [<object>...]
Every loose part of the objects is looked at on its own:
- a closed part (no open edge: a block, a column, a closed cornice) gets its normals recalculated outward;
- an open part (a wall sheet, a roof skin) is turned over when, from its biggest faces, rays shot behind them reach
  the sky or the street much more often than rays shot in front of them (the front looks into the building).
  Parts open on both sides (a parapet, a sheet in the middle of a courtyard) are left as they are.
Before and after: views from four sides and from above with back faces hidden as Unreal does (prima_*/dopo_*.png).
Saves out_dir/<blend name> and exports out_dir/<first object>.fbx with the settings of m80_chiese_gioco.py; the
report normali.json lists the parts turned over (where, how big).
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(ARGS[0])
NAMES = ARGS[1:]
SAMPLE_FACES = 12
RAYS = 6
REACH_M = 300.0
MARGIN = 0.35          # escape share behind minus in front needed to turn a part over
random.seed(80)


def parts(bm):
    todo = set(bm.faces)
    while todo:
        seed = todo.pop()
        part, stack = [seed], [seed]
        while stack:
            f = stack.pop()
            for e in f.edges:
                for g in e.link_faces:
                    if g in todo:
                        todo.discard(g)
                        part.append(g)
                        stack.append(g)
        yield part


def escape_share(tree, origin, normal):
    free = 0
    for _ in range(RAYS):
        jitter = Vector((random.gauss(0, 1), random.gauss(0, 1), random.gauss(0, 1))).normalized() * 0.8
        d = (normal + jitter).normalized()
        if d.dot(normal) <= 0.05:
            d = normal
        hit = tree.ray_cast(origin + d * 0.004, d, REACH_M)
        if hit[0] is None:
            free += 1
    return free / RAYS


def fix(objs):
    # one tree of everything, in world space: a wall is judged against the whole building
    world = bmesh.new()
    for o in objs:
        tmp = o.data.copy()
        tmp.transform(o.matrix_world)
        world.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    tree = BVHTree.FromBMesh(world)
    world.free()
    rep = {}
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        mw = o.matrix_world
        closed_fixed = open_flipped = 0
        turned = []
        for part in parts(bm):
            edges = {e for f in part for e in f.edges}
            if all(len(e.link_faces) == 2 for e in edges):
                before = [f.normal.copy() for f in part]
                bmesh.ops.recalc_face_normals(bm, faces=part)
                changed = sum(1 for f, n in zip(part, before) if f.normal.dot(n) < 0)
                closed_fixed += changed
                continue
            big = sorted(part, key=lambda f: f.calc_area(), reverse=True)[:SAMPLE_FACES]
            area = sum(f.calc_area() for f in big)
            if area <= 0:
                continue
            front = back = 0.0
            for f in big:
                c = mw @ f.calc_center_median()
                n = (mw.to_3x3() @ f.normal).normalized()
                w = f.calc_area() / area
                front += w * escape_share(tree, c, n)
                back += w * escape_share(tree, c, -n)
            if back - front > MARGIN:
                bmesh.ops.reverse_faces(bm, faces=part)
                open_flipped += len(part)
                c = mw @ big[0].calc_center_median()
                turned.append({"facce": len(part), "area_m2": round(sum(f.calc_area() for f in part), 2),
                               "centro_m": [round(c.x, 2), round(c.y, 2), round(c.z, 2)],
                               "fuga_davanti_dietro": [round(front, 2), round(back, 2)]})
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
        rep[o.name] = {"chiuse_corrette": closed_fixed, "aperte_girate": open_flipped,
                       "parti_girate": sorted(turned, key=lambda t: -t["area_m2"])}
        print("M80 %s: facce di parti chiuse rigirate %d, facce di parti aperte girate %d (%d parti)"
              % (o.name, closed_fixed, open_flipped, len(turned)))
    return rep


def views(objs, tag):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_backface_culling = True
    sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.world = sc.world or bpy.data.worlds.new("W")
    sc.world.color = (0.55, 0.65, 0.8)
    for o in sc.objects:
        o.hide_render = o not in objs
    cam = bpy.data.objects.new("M80_Cam", bpy.data.cameras.new("M80_Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    pts = [o.matrix_world @ Vector(v) for o in objs for v in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    r = max(hi.x - lo.x, hi.y - lo.y)
    shots = {"fronte_x": Vector((1, 0, 0)), "retro_x": Vector((-1, 0, 0)), "lato_y": Vector((0, 1, 0)),
             "lato_meno_y": Vector((0, -1, 0))}
    for name, d in shots.items():
        cam.location = c + d * r * 1.1 + Vector((0, 0, (hi.z - lo.z) * 0.3))
        cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 28
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (tag, name))
        bpy.ops.render.render(write_still=True)
    cam.location = c + Vector((r * 0.5, -r * 0.5, r * 1.2))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, "%s_alto.png" % tag)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)


def main():
    os.makedirs(OUT, exist_ok=True)
    objs = [bpy.data.objects[n] for n in NAMES]
    views(objs, "prima")
    rep = fix(objs)
    views(objs, "dopo")
    with open(os.path.join(OUT, "normali.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, os.path.basename(bpy.data.filepath)))
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, objs[0].name + ".fbx"), use_selection=True, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z", object_types={"MESH"},
                             mesh_smooth_type="FACE", bake_space_transform=True)


main()
