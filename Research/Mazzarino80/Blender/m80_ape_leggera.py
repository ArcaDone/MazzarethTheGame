"""Blender 5.2: the user's lighter Ape (D:/PerGioco/ApeDrivable_low.blend) exported for Unreal, to replace the heavy
skeletal mesh /Game/Drive/ApeCar/ApeDrivable (1.7 M vertices) with the same bones.

Run: blender -b "D:/PerGioco/ApeDrivable_low.blend" --python m80_ape_leggera.py -- <out.fbx>
The file keeps the reduced parts in the collection ApeCompleted (same names as the old ones) and the old ones in
"M80 Originali" (not exported). The skeleton in Unreal is the object hierarchy of the old FBX: ApeCar (the body,
root bone) and its twelve children, one bone each (the wheels Circle, Circle_001, Circle_002 are the Chaos wheels).
ApeCar.001 and ApeCar.003 hang from no parent: joined into ApeCar when M80_UNISCI=1 (else left out), so no new bone
appears. Units and axes as the old import: centimetres (the scene unit is 0.01), -Y forward, Z up.
"""
import json
import os
import sys

import bpy
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
BONES = "D:/UE5Projects/GameAnimationSample/Saved/Mazzarino80/Vehicles/ape_ispeziona.json"
JOIN = os.environ.get("M80_UNISCI") == "1"


def main():
    keep = set(bpy.data.collections["ApeCompleted"].objects)
    # the old FBX named this bone with dashes
    box = bpy.data.objects.get("Medieval box 5")
    if box:
        box.name = "Medieval-box-5"
    # a bone stands where its object's origin is: the reduction moved some origins (2-3 m off for Circle.003,
    # Cylinder.002, Sphere.001), so they go back on the old bones (Scripts/m80_ape_ispeziona.py, Unreal component
    # space in cm = this file's units with y turned), the geometry staying where it is
    bones = json.load(open(BONES, encoding="utf-8"))["ossa_cm"]
    for o in keep:
        b = bones.get(o.name.replace(".", "_"))
        if o.type != "MESH" or not b:
            continue
        target = Vector((b[0], -b[1], b[2]))
        if (o.matrix_world.translation - target).length > 1.0:
            m = o.matrix_world.copy()
            m.translation = target
            o.data.transform(m.inverted() @ o.matrix_world)
            kids = [(c, c.matrix_world.copy()) for c in o.children]
            o.matrix_world = m
            for c, mw in kids:
                c.matrix_world = mw
            print("M80 origine rimessa", o.name, round((o.matrix_world.translation - target).length, 2))
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    root = bpy.data.objects["ApeCar"]
    loose = [bpy.data.objects[n] for n in ("ApeCar.001", "ApeCar.003") if n in bpy.data.objects]
    if JOIN and loose:
        bpy.ops.object.select_all(action="DESELECT")
        for o in loose:
            o.select_set(True)
        root.select_set(True)
        bpy.context.view_layer.objects.active = root
        bpy.ops.object.join()
    else:
        for o in loose:
            bpy.data.objects.remove(o, do_unlink=True)
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
    print("M80 oggetti", len(objs), "triangoli", tris, "uniti" if JOIN else "senza ApeCar.001/.003")
    for o in objs:
        print("M80   ", o.name, "padre", o.parent.name if o.parent else None)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=OUT, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_NONE", axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE",
                             add_leaf_bones=False, bake_anim=False)
    print("M80 esportato", OUT)


main()
