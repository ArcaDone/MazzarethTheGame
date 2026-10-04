"""Blender 4.3: driving pose for the UEFN mannequin (skeleton of the player animations).

Run: blender -b --factory-startup --python m80_sit_pose.py -- <SKM_UEFN_Mannequin.fbx> <out_anim.fbx> <preview.png>
The pose is built from bone directions in armature space (no hand-tuned local axes): thighs forward,
knees bent, feet on the pedals, back slightly reclined, hands on a steering wheel at "ten to two".
A 2 s loop with a little breathing is exported as an FBX animation (armature only).
"""
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index("--") + 1:]
SRC, DST, PREVIEW = args[0], args[1], args[2]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC, use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
P = arm.pose.bones


def head(name):
    bpy.context.view_layer.update()
    return P[name].head.copy()


UP = Vector((0, 0, 1))
FWD = (head("ball_l") - head("foot_l"))
FWD.z = 0
FWD.normalize()
LEFT = (head("thigh_l") - head("thigh_r"))
LEFT.z = 0
LEFT.normalize()


def rotate(pb, q):
    bpy.context.view_layer.update()
    h = pb.head.copy()
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def align(bone, child, desired):
    cur = (head(child) - head(bone)).normalized()
    rotate(P[bone], cur.rotation_difference(desired.normalized()))


def tilt_back(bone, degrees):
    """Rotate about the left axis so the bone's children move backwards (sign found by test)."""
    probe = "head"
    before = head(probe).dot(FWD)
    q = Quaternion(LEFT, math.radians(degrees))
    rotate(P[bone], q)
    if head(probe).dot(FWD) > before:  # went forward: undo twice
        rotate(P[bone], Quaternion(LEFT, math.radians(-2 * degrees)))


def build_pose():
    for pb in P:
        pb.matrix_basis = Matrix.Identity(4)
    tilt_back("pelvis", 5)
    tilt_back("spine_03", -6)  # back straightens a little over the wheel
    for side, out in (("l", LEFT), ("r", -LEFT)):
        align("thigh_" + side, "calf_" + side, FWD * 0.97 - UP * 0.12 + out * 0.14)
        align("calf_" + side, "foot_" + side, -UP * 0.9 + FWD * 0.42)
        align("foot_" + side, "ball_" + side, FWD * 0.8 - UP * 0.45)
    sh_l, sh_r = head("upperarm_l"), head("upperarm_r")
    upper = (head("lowerarm_l") - sh_l).length
    lower = (head("hand_l") - head("lowerarm_l")).length
    mid = (sh_l + sh_r) / 2
    wheel = mid + FWD * (upper + lower) * 0.8 - UP * (upper + lower) * 0.2
    for side, out in (("l", LEFT), ("r", -LEFT)):
        grip = wheel + out * (upper + lower) * 0.36 + UP * (upper + lower) * 0.06
        sh = head("upperarm_" + side)
        # Elbow: on the circle of possible elbows, the one lowest and a bit outward.
        d = (grip - sh).length
        a = max(min((upper * upper + d * d - lower * lower) / (2 * upper * d), 1.0), -1.0)
        axis_dir = (grip - sh).normalized()
        perp = (-UP * 0.85 + out * 0.5)
        perp = (perp - axis_dir * perp.dot(axis_dir)).normalized()
        elbow = sh + axis_dir * upper * a + perp * upper * math.sqrt(max(0.0, 1 - a * a))
        align("upperarm_" + side, "lowerarm_" + side, elbow - sh)
        align("lowerarm_" + side, "hand_" + side, grip - head("lowerarm_" + side))
        hand_child = "middle_metacarpal_" + side if ("middle_metacarpal_" + side) in P else "middle_01_" + side
        if hand_child in P:
            align("hand_" + side, hand_child, FWD * 0.5 + UP * 0.35 - out * 0.6)
    # Head level and looking ahead.
    tilt_back("neck_01", -8)


build_pose()
frames = {1: 0.0, 30: 1.0, 60: 0.0}
for f, breath in frames.items():
    bpy.context.scene.frame_set(f)
    build_pose()
    if breath:
        tilt_back("spine_05", 1.2)
    for pb in P:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
        pb.keyframe_insert("scale", frame=f)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, 60
scene.render.fps = 30
bpy.ops.object.mode_set(mode="OBJECT")
arm.animation_data.action.name = "M80_Seduto_Guida"

# Preview: side and front.
scene.frame_set(1)
mins = Vector((1e9, 1e9, 1e9))
maxs = -mins
for o in bpy.data.objects:
    if o.type == "MESH":
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mins = Vector(map(min, mins, w))
            maxs = Vector(map(max, maxs, w))
center = (mins + maxs) / 2
size = (maxs - mins).length
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = 4
sun.rotation_euler = (0.8, 0.2, 0.6)
scene.collection.objects.link(sun)
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x, scene.render.resolution_y = 700, 700
world = bpy.data.worlds.new("W")
world.color = (0.5, 0.55, 0.6)
scene.world = world
side_dir = LEFT
for name, d in (("side", side_dir), ("front", FWD)):
    cam.location = center + d * size * 1.4 + UP * size * 0.1
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = PREVIEW.replace(".png", "_" + name + ".png")
    bpy.ops.render.render(write_still=True)

for o in list(bpy.data.objects):
    if o.type == "MESH":
        bpy.data.objects.remove(o)
bpy.ops.export_scene.fbx(filepath=DST, object_types={"ARMATURE"}, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_bones=True,
                         bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True,
                         bake_anim_simplify_factor=0.0, armature_nodetype="NULL", primary_bone_axis="Y", secondary_bone_axis="X")
print("M80 sit pose written", DST, "fwd", tuple(round(v, 2) for v in FWD), "left", tuple(round(v, 2) for v in LEFT))
