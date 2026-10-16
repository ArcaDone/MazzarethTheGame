"""The crowd's Mixamo animations (D:/animations, skeleton only) made ready for Unreal, where they are retargeted to the UEFN
mannequin (Scripts/m80_folla_animazioni.py). Their skeleton is not the one of the climbing clips (SK_M80_Mixamo: legs
44 cm a bone, these 32 cm): retargeted through that one the hips read as crouched and the feet as lifted. So:
- SK_M80_MixamoFolla.fbx: this skeleton in its rest pose with a dummy mesh (a box per bone), since Unreal needs a
  skeletal mesh to import animations onto and to retarget from;
- A_<name>.fbx: each animation re-exported from the same skeleton (same bone orientations as the mesh), all frames baked.
Run: blender -b --factory-startup -P m80_mixamo_folla.py
Out: Saved/Mazzarino80/Folla/Animazioni/*.fbx + mixamo.json (frames, fps, hips travel per clip)
"""
import glob
import json
import os
import re

import bpy
import bmesh
from mathutils import Vector

SRC = "D:/animations"
OUT = "D:/UE5Projects/GameAnimationSample/Saved/Mazzarino80/Folla/Animazioni"


def clean_name(path):
    base = os.path.splitext(os.path.basename(path))[0]
    return "A_M80_" + re.sub(r"[^A-Za-z0-9]+", "", base.title())


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    return next(o for o in bpy.data.objects if o.type == "ARMATURE")


def dummy_mesh(arm):
    """A thin box along each bone, skinned to it alone: enough for Unreal to make a skeleton and a retarget pose."""
    bm = bmesh.new()
    groups = []
    for b in arm.data.bones:
        head, tail = arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local
        axis = tail - head
        if axis.length < 1e-4:
            continue
        side = axis.orthogonal().normalized() * max(0.004, axis.length * 0.08)
        up = axis.normalized().cross(side).normalized() * side.length
        corners = [head + s * side + u * up for s in (-1, 1) for u in (-1, 1)] + \
                  [tail + s * side + u * up for s in (-1, 1) for u in (-1, 1)]
        vs = [bm.verts.new(c) for c in corners]
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            bm.faces.new([vs[i] for i in f])
        groups.append((b.name, len(bm.verts) - 8))
    me = bpy.data.meshes.new("SK_M80_MixamoFolla")
    bm.to_mesh(me)
    ob = bpy.data.objects.new("SK_M80_MixamoFolla", me)
    bpy.context.scene.collection.objects.link(ob)
    for name, start in groups:
        vg = ob.vertex_groups.new(name=name)
        vg.add(list(range(start, start + 8)), 1.0, "REPLACE")
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return ob


def export(path, objects, anim):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"},
                             add_leaf_bones=False, bake_anim=anim, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                             bake_anim_simplify_factor=0.0, use_armature_deform_only=False)


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(SRC + "/*.fbx"))
    report = {}
    # The skeleton with its dummy mesh, in the rest pose, from the first file (all share the Mixamo rig).
    arm = load(files[0])
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    mesh = dummy_mesh(arm)
    export(OUT + "/SK_M80_MixamoFolla.fbx", [arm, mesh], False)
    for f in files:
        arm = load(f)
        act = arm.animation_data.action
        sc = bpy.context.scene
        start, end = int(act.frame_range[0]), int(act.frame_range[1])
        sc.frame_start, sc.frame_end = start, end
        hips = arm.pose.bones["mixamorig:Hips"]
        pos = []
        for fr in (start, end):
            sc.frame_set(fr)
            pos.append(arm.matrix_world @ hips.head)
        travel = pos[1] - pos[0]
        name = clean_name(f)
        report[name] = {"source": os.path.basename(f), "frames": end - start, "fps": sc.render.fps,
                        "seconds": (end - start) / sc.render.fps,
                        "travel_m": [round(v, 3) for v in travel],
                        "speed_cm_s": round(Vector((travel.x, travel.y)).length * 100 / max(1e-3, (end - start) / sc.render.fps), 1),
                        "hips_end_z": round(pos[1].z, 3)}
        export(OUT + "/%s.fbx" % name, [arm], True)
    with open(OUT + "/mixamo.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)


main()
