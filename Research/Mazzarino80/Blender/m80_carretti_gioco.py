"""Blender 5.2: the four soapbox carts of D:/BlenderTest/carretti for the game, each with the pose of its rider.

Run (one cart at a time, Blender 5.2: the files are too new for 4.3):
  blender -b <carretto_x.blend> --python m80_carretti_gioco.py -- <key> <out_dir> <SKM_UEFN_Mannequin.fbx>
key: Cuscinetti | Triangolo | Cassetta | Persiana

What it writes (the source .blend is never saved):
- <out_dir>/Carretto<Key>.fbx: skeletal mesh in centimetres, front along +X, wheels on the ground. Bones (all pointing
  +Y, as the drivable cars): Root, Steer (the pivoting front axle or tiller, at the bolt), Wheel_FL/FR/RL/RR (Wheel_F
  for the three-wheeler), Sella (where the rider's mesh origin goes), Mano_L/R and Piede_L/R (where the rider's
  wrists and ankles go; under Steer when they hold the steering, so they follow it in the game).
- <out_dir>/Carretto<Key>.json: wheels (centre, radius, width), body box, materials (for m80_import_blender_assets.py).
- <out_dir>/A_M80_Carretto_<Key>.fbx: the rider's pose for the UEFN mannequin (armature only, 2 s loop with a little
  breathing), built from bone directions and two-bone IK onto the cart's grips:
    Cuscinetti: lying on the chest, hands on the wooden bar sticking out at the front (a sled);
    Triangolo, Cassetta: sitting as in a go-kart, heels on the front axle, hands on the rope;
    Persiana: sitting as in a go-kart, arms up on the broomstick's handle (a chopper).
- <out_dir>/Carretto<Key>_*.png: previews of the cart with its rider.
"""
import json
import math
import os
import re
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
KEY, OUT, MANNEQUIN = ARGS[0], ARGS[1], ARGS[2]
NAME = "Carretto" + KEY
os.makedirs(os.path.join(OUT, "Textures"), exist_ok=True)
REPORT = {"key": NAME, "kind": "cart", "steps": []}

# Per cart (Blender metres, front +X, left +Y). "seat": point under the rider (x, y) and the surface it rests on;
# "grip": where the hands hold; "feet": what the feet rest on; "steer_feet": the feet are on the steering.
CARTS = {
    "Cuscinetti": {"pose": "prono", "chest_x": 0.05, "grip": "bar", "feet": None},
    # Rope carts: the fists in front of the rider ("hands": forward of the hips, apart, above the hips); the rope is made
    # again taut from the axle ends to them (the model's rope lies slack on the cart).
    "Triangolo": {"pose": "kart", "pelvis_x": -0.17, "grip": "rope", "hands": (0.40, 0.12, 0.12), "feet": "axle", "foot_y": 0.19},
    "Cassetta": {"pose": "kart", "pelvis_x": -0.27, "grip": "rope", "hands": (0.40, 0.11, 0.14), "feet": "axle", "foot_y": 0.16},
    "Persiana": {"pose": "chopper", "pelvis_x": -0.29, "grip": "handle", "feet": "deck", "foot_y": 0.15},
}
CFG = CARTS[KEY]


def log(*a):
    msg = " ".join(str(x) for x in a)
    REPORT["steps"].append(msg)
    print("M80", msg)


def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def world_verts(o):
    m = o.matrix_world
    return [m @ v.co for v in o.data.vertices]


def bbox(points):
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


# ---------------------------------------------------------------------------------------------
# 1) The cart as meshes, one per bone

def bone_of(o):
    """Wheel_XX for a wheel and its bearing parts, Steer for what turns with the front axle, else Root."""
    p = o
    while p:
        if re.fullmatch(r"Wheel_(FL|FR|RL|RR|F)", p.name):
            return p.name
        if p.name == "Steering_Pivot":
            return "Steer"
        p = p.parent
    return "Root"


def collect():
    # The model leaves the steering turned a little: straight for the game (it turns in code).
    piv = bpy.data.objects["Steering_Pivot"]
    piv.rotation_euler.z = 0.0
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    parts = {}
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or not o.visible_get() or o.hide_render:
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        if not me or not me.polygons:
            continue
        me.transform(o.matrix_world)
        # The originals stay for measuring (grips, rope) but out of the previews.
        o.hide_render = True
        o.hide_set(True)
        if o.name == "Steering_Rope" and CFG["grip"] == "rope":
            continue   # made again, taut to the hands
        n = bpy.data.objects.new("M80_" + o.name, me)
        bpy.context.scene.collection.objects.link(n)
        parts.setdefault(bone_of(o), []).append(n)
    pivot = piv.matrix_world.translation.copy()
    return parts, pivot


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = o.data.name = name
    return o


# ---------------------------------------------------------------------------------------------
# 2) Where the rider holds and sits (from the cart's own parts, steering straight)

def obj_verts(name):
    return world_verts(bpy.data.objects[name])


def grips(pelvis=None):
    """(left, right) hand grip points (for the rope, from the hips)."""
    g = CFG["grip"]
    if g == "bar":
        # The wooden bar across the front: near its two ends, on top.
        vs = obj_verts("Steering_Bar")
        lo, hi = bbox(vs)
        x = (lo.x + hi.x) / 2
        y = hi.y - 0.07
        return Vector((x, y, hi.z)), Vector((x, -y, hi.z))
    if g == "handle":
        vs = obj_verts("Tiller_Handle_Stick")
        lo, hi = bbox(vs)
        out = []
        for side in (1, -1):
            end = [v for v in vs if (v.y - hi.y if side > 0 else lo.y - v.y) > -0.045]
            c = sum(end, Vector()) / len(end)
            out.append(Vector((c.x, c.y - side * 0.02, c.z)))
        return out[0], out[1]
    dx, y, dz = CFG["hands"]
    return pelvis + Vector((dx, y, dz)), pelvis + Vector((dx, -y, dz))


def rope_ends():
    """Where the model's rope is tied to the axle: the foremost point of the rope on each side."""
    vs = obj_verts("Steering_Rope")
    out = []
    for side in (1, -1):
        sv = [v for v in vs if v.y * side > 0.05]
        p = max(sv, key=lambda v: v.x)
        out.append(sum((v for v in sv if (v - p).length < 0.02), Vector()) / len([v for v in sv if (v - p).length < 0.02]))
    return out


def make_rope(hands):
    """The steering rope, taut from each axle end to a fist, slack between the fists (1 cm thick)."""
    a, b = rope_ends()
    hl, hr = hands
    sag = (hl + hr) / 2 - Vector((0.03, 0, 0.07))
    pts = [a, a.lerp(hl, 0.5) - Vector((0, 0, 0.012)), hl, sag, hr, b.lerp(hr, 0.5) - Vector((0, 0, 0.012)), b]
    cu = bpy.data.curves.new("M80Corda", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.005
    cu.bevel_resolution = 2
    cu.resolution_u = 6
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = bpy.data.objects.new("M80Corda", cu)
    bpy.context.scene.collection.objects.link(ob)
    rope_mat = bpy.data.objects["Steering_Rope"].material_slots[0].material
    cu.materials.append(rope_mat)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(ob, do_unlink=True)
    n = bpy.data.objects.new("M80_Corda", me)
    bpy.context.scene.collection.objects.link(n)
    return n


SEAT_MESH = []


def seat_height(x, y):
    """Top of the cart's body under (x, y) (a ray from above; 0 = the ground)."""
    ok, loc, _n, _i = SEAT_MESH[0].ray_cast(Vector((x, y, 0.45)), Vector((0, 0, -1)))
    return loc.z if ok else 0.0


def feet():
    """(left, right) ankle targets, or None."""
    f = CFG["feet"]
    if not f:
        return None
    y = CFG["foot_y"]
    if f == "axle":
        # Heels on top of the front axle, toes up.
        lo, hi = bbox(obj_verts("Steering_Bar"))
        x = (lo.x + hi.x) / 2
        return Vector((x - 0.01, y, hi.z + 0.065)), Vector((x - 0.01, -y, hi.z + 0.065))
    # Flat on the front of the deck.
    lo, hi = bbox(obj_verts("Shutter_Rail_Front"))
    return Vector((hi.x - 0.12, y, hi.z + 0.085)), Vector((hi.x - 0.12, -y, hi.z + 0.085))


# ---------------------------------------------------------------------------------------------
# 3) The rider

class Rider:
    def __init__(self):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=MANNEQUIN, use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False)
        new = [o for o in bpy.data.objects if o not in before]
        self.arm = next(o for o in new if o.type == "ARMATURE")
        self.meshes = [o for o in new if o.type == "MESH"]
        self.rest_matrix = self.arm.matrix_world.copy()
        bpy.context.view_layer.objects.active = self.arm
        bpy.ops.object.mode_set(mode="POSE")
        self.P = self.arm.pose.bones
        self.UP = Vector((0, 0, 1))
        f = self.head("ball_l") - self.head("foot_l")
        f.z = 0
        self.FWD = f.normalized()
        left = self.head("thigh_l") - self.head("thigh_r")
        left.z = 0
        self.LEFT = left.normalized()
        self.sella = Vector((0, 0, 0))
        self.place(self.sella)
        self.palm_sign = {}
        self.reset()
        for s in ("l", "r"):
            self.palm_sign[s] = 1.0
            n = self.palm(s)
            out = self.LEFT if s == "l" else -self.LEFT
            # At rest (A pose) the palms face down and in.
            self.palm_sign[s] = 1.0 if n.dot(-self.UP - out) > 0 else -1.0

    # Cart world (metres) <-> armature space (cm). The mesh origin sits at self.sella, facing the cart's +X.
    def place(self, sella):
        self.sella = sella.copy()
        self.arm.matrix_world = Matrix.Translation(sella) @ Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Scale(0.01, 4)
        bpy.context.view_layer.update()

    def to_arm(self, w):
        return self.arm.matrix_world.inverted() @ w

    def to_world(self, a):
        return self.arm.matrix_world @ a

    def head(self, name):
        bpy.context.view_layer.update()
        return self.P[name].head.copy()

    def reset(self):
        for pb in self.P:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    def rotate(self, name, q):
        bpy.context.view_layer.update()
        pb = self.P[name]
        h = pb.head.copy()
        pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ pb.matrix
        bpy.context.view_layer.update()

    def align(self, bone, child, desired):
        cur = (self.head(child) - self.head(bone)).normalized()
        self.rotate(bone, cur.rotation_difference(desired.normalized()))

    def tilt_back(self, bone, degrees, probe="head", toward=None):
        """Rotates about the left axis so that `probe` moves backwards, or towards `toward` (negative: the other way)."""
        toward = -self.FWD if toward is None else toward
        before = self.head(probe).dot(toward)
        self.rotate(bone, Quaternion(self.LEFT, math.radians(degrees)))
        if (self.head(probe).dot(toward) - before) * degrees < 0:
            self.rotate(bone, Quaternion(self.LEFT, math.radians(-2 * degrees)))

    def length(self, a, b):
        return (self.head(b) - self.head(a)).length

    def two_bone(self, upper, lower, end, target, pole):
        """Upper and lower bone so that `end` reaches target (armature space), the middle joint towards pole."""
        a = self.head(upper)
        l1, l2 = self.length(upper, lower), self.length(lower, end)
        d = target - a
        dist = min(d.length, (l1 + l2) * 0.995)
        axis = d.normalized()
        tgt = a + axis * dist
        cosa = max(min((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), 1.0), -1.0)
        perp = (pole - axis * pole.dot(axis)).normalized()
        mid = a + axis * l1 * cosa + perp * l1 * math.sqrt(max(0.0, 1 - cosa * cosa))
        self.align(upper, lower, mid - a)
        self.align(lower, end, tgt - self.head(lower))
        return (target - tgt).length

    def palm(self, s):
        """Normal of the palm (where the fingers close), from the knuckles."""
        h = self.head("hand_" + s)
        i, p = self.head("index_01_" + s), self.head("pinky_01_" + s)
        n = (i - h).cross(p - h).normalized()
        return n * self.palm_sign.get(s, 1.0)

    def orient_hand(self, s, fingers, palm):
        """Hand pointing `fingers` with the palm facing `palm` (armature space)."""
        mid = "middle_metacarpal_" + s if ("middle_metacarpal_" + s) in self.P else "middle_01_" + s
        self.align("hand_" + s, mid, fingers)
        d = (self.head(mid) - self.head("hand_" + s)).normalized()
        n = self.palm(s)
        want = (palm - d * palm.dot(d)).normalized()
        have = (n - d * n.dot(d)).normalized()
        ang = math.atan2(have.cross(want).dot(d), have.dot(want))
        self.rotate("hand_" + s, Quaternion(d, ang))

    def fist(self, s, amount=1.0):
        """Fingers closed round a bar or a rope."""
        n = self.palm(s)
        for f, angles in (("index", (45, 70, 40)), ("middle", (50, 75, 40)), ("ring", (55, 75, 40)), ("pinky", (60, 75, 40))):
            for k, ang in enumerate(angles):
                b = "%s_%02d_%s" % (f, k + 1, s)
                c = "%s_%02d_%s" % (f, k + 2, s) if k < 2 else None
                if b not in self.P:
                    continue
                if c and c in self.P:
                    d = (self.head(c) - self.head(b)).normalized()
                else:
                    d = (self.P[b].tail - self.P[b].head).normalized()
                axis = d.cross(n).normalized()
                self.rotate(b, Quaternion(axis, math.radians(ang * amount)))
        for k, ang in enumerate((15, 25, 20)):
            b = "thumb_%02d_%s" % (k + 1, s)
            if b in self.P:
                d = (self.P[b].tail - self.P[b].head).normalized()
                self.rotate(b, Quaternion(d.cross(n).normalized(), math.radians(ang * amount)))

    # ---- contact with the cart: the lowest point of a body part, in cart space
    def lowest(self, groups, near=None, radius=0.2):
        dg = bpy.context.evaluated_depsgraph_get()
        best = None
        for o in self.meshes:
            names = {g.index: g.name for g in o.vertex_groups}
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            m = o.matrix_world
            for v, src in zip(me.vertices, o.data.vertices):
                if not src.groups:
                    continue
                g = max(src.groups, key=lambda x: x.weight)
                if names.get(g.group) not in groups:
                    continue
                w = m @ v.co
                if near is not None and (Vector((w.x, w.y)) - Vector((near.x, near.y))).length > radius:
                    continue
                if best is None or w.z < best.z:
                    best = w
            ev.to_mesh_clear()
        return best


def side_out(r, s):
    return r.LEFT if s == "l" else -r.LEFT


def build_pose(r, hands, ankles, breath=0.0):
    """Pose in armature space; hands/ankles in cart space (metres). Returns the IK misses (cm)."""
    pose = CFG["pose"]
    F, U = r.FWD, r.UP
    r.reset()
    if pose == "prono":
        # Flat on the chest: the whole body tips forward about the hips, head and chest up a little.
        r.tilt_back("pelvis", -86)
        # Lying down, "back" is ambiguous: chest, neck and head turn up.
        r.tilt_back("spine_03", 6, toward=U)
        r.tilt_back("spine_05", 8 + breath, toward=U)
        r.tilt_back("neck_01", 38, toward=U)
        r.tilt_back("head", 20, toward=U)
        for s in ("l", "r"):
            o = side_out(r, s)
            # Thighs back and a little apart, knees bent so the feet are up in the air (as kids on a sled).
            r.align("thigh_" + s, "calf_" + s, -F * 0.96 + o * 0.16 + U * 0.04)
            r.align("calf_" + s, "foot_" + s, -F * 0.55 + U * 0.83 + o * 0.05)
            r.align("foot_" + s, "ball_" + s, -F * 0.75 + U * 0.25)
    else:
        lean = CFG.get("lean", 0.0)
        r.tilt_back("pelvis", lean)
        r.tilt_back("spine_05", breath)
        r.tilt_back("neck_01", -lean * 0.8 - 6)
    misses = {}
    if ankles:
        for s, t in zip(("l", "r"), ankles):
            o = side_out(r, s)
            pole = U * 0.9 + o * 0.25 + F * 0.3
            misses["piede_" + s] = r.two_bone("thigh_" + s, "calf_" + s, "foot_" + s, r.to_arm(t), pole)
            if CFG["feet"] == "axle":
                r.align("foot_" + s, "ball_" + s, U * 0.85 + F * 0.5 + o * 0.15)   # heels on the axle, toes up
            else:
                r.align("foot_" + s, "ball_" + s, F * 0.95 - U * 0.2 + o * 0.1)    # flat on the deck
    elif pose != "prono":
        for s in ("l", "r"):
            r.align("thigh_" + s, "calf_" + s, F * 0.97 + side_out(r, s) * 0.14)
    for s, g in zip(("l", "r"), hands):
        o = side_out(r, s)
        if CFG["grip"] == "rope":
            fingers, palm = (F * 0.75 - o * 0.45 - U * 0.3), (-U * 0.6 - F * 0.2 - o * 0.4)
            pole = -U * 0.7 + o * 0.7
        elif CFG["grip"] == "handle":
            fingers, palm = (F * 0.85 - U * 0.3 - o * 0.2), (-U * 0.8 - F * 0.3)
            pole = o * 0.8 - U * 0.5
        else:
            fingers, palm = (F * 0.9 - U * 0.35), (-U)
            pole = o * 0.85 + U * 0.5
        # The wrist sits behind the grip (the fingers wrap round it) and a little above.
        wrist = r.to_arm(g) - fingers.normalized() * 7.0 - palm.normalized() * 3.0
        misses["mano_" + s] = r.two_bone("upperarm_" + s, "lowerarm_" + s, "hand_" + s, wrist, pole)
        r.orient_hand(s, fingers, palm)
        r.fist(s)
    return misses


def wrists_world(r):
    return [r.to_world(r.head("hand_" + s)) for s in ("l", "r")], [r.to_world(r.head("foot_" + s)) for s in ("l", "r")]


def make_rider():
    r = Rider()
    hands = grips() if CFG["grip"] != "rope" else (Vector(), Vector())
    ankles = feet()
    # Place the body: the hips (or the chest) on the cart, then the limbs onto the grips. The forward lean of a
    # sitting rider grows until the hands reach the rope.
    for attempt in range(8):
        r.place(Vector((0, 0, 0)))
        build_pose(r, hands, None)
        if CFG["pose"] == "prono":
            sh = (r.to_world(r.head("upperarm_l")) + r.to_world(r.head("upperarm_r"))) / 2
            want_xy = Vector((CFG["chest_x"], 0.0))
            r.place(Vector((want_xy.x - sh.x, -sh.y, 0)))
            chest = r.to_world(r.head("spine_04"))
            low = r.lowest({"spine_02", "spine_03", "spine_04", "spine_05", "clavicle_l", "clavicle_r"}, chest, 0.18)
            surf = seat_height(low.x, low.y)
        else:
            pel = r.to_world(r.head("pelvis"))
            r.place(Vector((CFG["pelvis_x"] - pel.x, -pel.y, 0)))
            pel = r.to_world(r.head("pelvis"))
            low = r.lowest({"pelvis", "thigh_l", "thigh_r"}, pel, 0.14)
            surf = seat_height(low.x, low.y)
        r.place(r.sella + Vector((0, 0, surf - low.z)))
        if CFG["grip"] == "rope":
            hands = grips(r.to_world(r.head("pelvis")))
        misses = build_pose(r, hands, ankles)
        reach = max(v for k, v in misses.items() if k.startswith("mano"))
        log("attempt", attempt, "lean", CFG.get("lean", 0), "seat z", round(surf, 3), "misses cm", {k: round(v, 1) for k, v in misses.items()})
        if CFG["pose"] == "prono" or reach < 1.0:
            break
        CFG["lean"] = CFG.get("lean", 0.0) - 6.0   # lean forward
    REPORT["grips_m"] = [[round(c, 3) for c in g] for g in hands]
    REPORT["feet_m"] = [[round(c, 3) for c in a] for a in ankles] if ankles else None
    REPORT["rider"] = {"sella_m": [round(c, 4) for c in r.sella], "lean_deg": CFG.get("lean", 0.0), "misses_cm": {k: round(v, 1) for k, v in misses.items()}}
    # Bone targets: where the wrists and ankles actually are (the grips may be out of reach by a little).
    w, a = wrists_world(r)
    return r, hands, ankles, w, (a if ankles else None)


def keyframe_rider(r, hands, ankles):
    for f, breath in ((1, 0.0), (30, 1.2), (60, 0.0)):
        bpy.context.scene.frame_set(f)
        build_pose(r, hands, ankles, breath)
        for pb in r.P:
            pb.keyframe_insert("location", frame=f)
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("scale", frame=f)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 60
    sc.render.fps = 30
    r.arm.animation_data.action.name = "M80_Carretto_" + KEY


def previews(r, cart_objs):
    sc = bpy.context.scene
    sc.frame_set(1)
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = 1100, 750
    world = bpy.data.worlds.new("M80W")
    world.color = (0.55, 0.6, 0.68)
    sc.world = world
    sun = bpy.data.objects.new("M80Sun", bpy.data.lights.new("M80Sun", "SUN"))
    sun.data.energy = 4.0
    sun.rotation_euler = (0.7, 0.25, 0.9)
    sc.collection.objects.link(sun)
    ground = bpy.data.objects.new("M80Ground", bpy.data.meshes.new("M80Ground"))
    ground.data.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    sc.collection.objects.link(ground)
    mat = bpy.data.materials.new("M80Ground")
    mat.diffuse_color = (0.45, 0.33, 0.25, 1)
    ground.data.materials.append(mat)
    cam = bpy.data.objects.new("M80Cam", bpy.data.cameras.new("M80Cam"))
    cam.data.lens = 35
    sc.collection.objects.link(cam)
    sc.camera = cam
    centre = Vector((0.0, 0.0, 0.35))
    hand = r.to_world(r.head("hand_l"))
    for name, eye, at in (("lato", Vector((-0.2, 2.6, 0.7)), centre), ("tre_quarti", Vector((2.0, 1.6, 1.2)), centre),
                          ("alto", Vector((0.4, 0.3, 3.0)), centre), ("davanti", Vector((2.4, -0.3, 0.5)), centre),
                          ("mano", hand + Vector((0.25, 0.35, 0.2)), hand + Vector((0.05, 0, 0)))):
        centre_ = at
        cam.location = eye
        cam.rotation_euler = (centre_ - eye).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (NAME, name))
        bpy.ops.render.render(write_still=True)
    for o in (sun, ground, cam):
        bpy.data.objects.remove(o, do_unlink=True)


def export_rider(r):
    # Back to the armature's own frame (the pose lives in armature space): the FBX root stays as imported.
    r.arm.matrix_world = r.rest_matrix
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    r.arm.select_set(True)
    bpy.context.view_layer.objects.active = r.arm
    path = os.path.join(OUT, "A_M80_Carretto_%s.fbx" % KEY)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE"}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, armature_nodetype="NULL",
                             primary_bone_axis="Y", secondary_bone_axis="X")
    log("rider pose exported", path)
    for o in [r.arm] + r.meshes:
        bpy.data.objects.remove(o, do_unlink=True)


# ---------------------------------------------------------------------------------------------
# 4) Materials (same JSON as m80_prepare_vehicle.py)

SAVED = {}


def clean(name):
    return re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")[:48] or "Mat"


def save_image(im):
    if im is None:
        return None
    base = clean(os.path.splitext(re.sub(r"\.\d{3}$", "", im.name))[0])
    if base in SAVED:
        return SAVED[base]
    path = os.path.join(OUT, "Textures", "T_%s_%s.png" % (NAME, base))
    im.file_format = "PNG"
    im.save(filepath=path)
    SAVED[base] = os.path.basename(path)
    return SAVED[base]


def export_materials(objs):
    mats = {}
    for o in objs:
        for s in o.material_slots:
            m = s.material
            if not m or m.name in mats:
                continue
            p = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
            d = {"slot": clean(m.name), "color": list(m.diffuse_color[:3]), "metallic": 0.0, "roughness": 0.8, "opacity": 1.0,
                 "emissive": [0, 0, 0], "base_tex": None, "normal_tex": None}
            if p:
                bc = p.inputs["Base Color"]
                if bc.is_linked and bc.links[0].from_node.type == "TEX_IMAGE":
                    d["base_tex"] = save_image(bc.links[0].from_node.image)
                    d["color"] = [1.0, 1.0, 1.0]
                else:
                    d["color"] = list(bc.default_value[:3])
                d["metallic"] = float(p.inputs["Metallic"].default_value)
                d["roughness"] = float(p.inputs["Roughness"].default_value)
            d["type"] = "metal" if d["metallic"] > 0.5 else "generic"
            mats[m.name] = d
    return mats


# ---------------------------------------------------------------------------------------------
# 5) Skeleton and export

def make_rig(meshes, bones):
    """bones: name -> (head in metres, parent). Every bone points +Y (identity frame in Unreal)."""
    data = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for name, (head, parent) in bones.items():
        b = data.edit_bones.new(name)
        b.head = head * 100.0
        b.tail = head * 100.0 + Vector((0, 8.0 if name != "Root" else 30.0, 0))
        if parent:
            b.parent = made[parent]
        made[name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    for bone, o in meshes.items():
        vg = o.vertex_groups.new(name=bone)
        vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")
        o.parent = arm
        md = o.modifiers.new("Armature", "ARMATURE")
        md.object = arm
    return arm


def main():
    parts, pivot = collect()
    log("parts", {k: len(v) for k, v in parts.items()}, "pivot", [round(c, 3) for c in pivot])
    meshes = {}
    names = {"Root": "Corpo", "Steer": "Sterzo"}
    for bone, objs in parts.items():
        meshes[bone] = join(objs, names.get(bone, bone.replace("Wheel_", "Ruota_")))
    wheels = {}
    for bone, o in meshes.items():
        if bone.startswith("Wheel_"):
            lo, hi = bbox(world_verts(o))
            c = (lo + hi) / 2
            wheels[bone] = {"centre": c, "radius": max(hi.x - lo.x, hi.z - lo.z) / 2, "width": hi.y - lo.y}
    REPORT["wheels"] = {k[6:]: {"centre_cm": [round(x * 100, 1) for x in v["centre"]], "radius_cm": round(v["radius"] * 100, 2),
                                "width_cm": round(v["width"] * 100, 2)} for k, v in wheels.items()}
    lo, hi = bbox(world_verts(meshes["Root"]))
    REPORT["body_box_cm"] = [round(x * 100, 1) for x in list(lo) + list(hi)]
    REPORT["pivot_cm"] = [round(x * 100, 1) for x in pivot]

    # The rider: seated on the body, hands and feet on the original parts (still there, hidden).
    SEAT_MESH.append(meshes["Root"])
    rider, hands, ankles, wrists, ank = make_rider()
    keyframe_rider(rider, hands, ankles)
    bpy.ops.object.mode_set(mode="OBJECT")
    if CFG["grip"] == "rope":
        meshes["Steer"] = join([meshes["Steer"], make_rope(hands)], "Sterzo")
    previews(rider, list(meshes.values()))
    sella = rider.sella.copy()
    export_rider(rider)

    on_steer = CFG["grip"] in ("rope", "bar", "handle")
    bones = {"Root": (Vector((0, 0, 0)), None), "Steer": (pivot, "Root")}
    for w in sorted(wheels):
        bones[w] = (wheels[w]["centre"], "Root")
    bones["Sella"] = (sella, "Root")
    bones["Mano_L"] = (wrists[0], "Steer" if on_steer else "Root")
    bones["Mano_R"] = (wrists[1], "Steer" if on_steer else "Root")
    if ank:
        bones["Piede_L"] = (ank[0], "Steer" if CFG["feet"] == "axle" else "Root")
        bones["Piede_R"] = (ank[1], "Steer" if CFG["feet"] == "axle" else "Root")
    REPORT["bones_cm"] = {k: [round(c * 100, 1) for c in v[0]] for k, v in bones.items()}
    REPORT["materials"] = export_materials(list(meshes.values()))
    REPORT["triangles"] = {o.name: tri_count(o) for o in meshes.values()}
    for o in meshes.values():
        for p in o.data.polygons:
            p.use_smooth = True
    # Centimetres (scene unit 0.01): otherwise the root bone gets a x100 scale in Unreal and Chaos misplaces the wheels.
    sc100 = Matrix.Scale(100.0, 4)
    for o in meshes.values():
        o.data.transform(sc100 @ o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.01
    arm = make_rig(meshes, bones)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes.values():
        o.select_set(True)
    arm.select_set(True)
    path = os.path.join(OUT, NAME + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"}, axis_forward="-Y", axis_up="Z",
                             apply_unit_scale=True, mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False,
                             use_armature_deform_only=False, primary_bone_axis="Y", secondary_bone_axis="X", path_mode="STRIP")
    log("cart exported", path)
    REPORT["textures"] = sorted(SAVED.values())
    with open(os.path.join(OUT, NAME + ".json"), "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=1)
    log("done")


main()
