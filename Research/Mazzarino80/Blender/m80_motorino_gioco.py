"""Blender 5.2: the Piaggio Si moped of D:/Mazzarino80_Sorgenti/Auto/Piaggio_Si for the game, with its rider: the pose on it and
the clips of getting on and off.

Run: blender -b <piaggioCiao.blend> --python m80_motorino_gioco.py -- <out_dir> <SKM_UEFN_Mannequin.fbx> <textures_dir>
piaggioCiao.blend is the Si of piaggio-si-scooter with the tyres of the Bravo (moped_-_vespa_piaggio_bravo.glb) and the fork with
the handlebar as a mesh of its own; textures_dir is piaggio-si-scooter/textures (the Si's own maps, not in the .blend).

What it writes (the source .blend is never saved):
- <out>/PiaggioSi.fbx: skeletal mesh in centimetres, front along +X, wheels on the ground, the middle between the axles at the
  origin, at its real length (1.63 m). Bones (pointing +Y, as the drivable cars): Root, Steer (fork, handlebar, headlight; at
  the steering head, its Z along the raked steering axis, about which it turns in the game), Wheel_F, Wheel_R, Sella (where the
  rider's mesh origin goes), Mano_L/R (the wrists on the grips, under Steer), Piede_L/R (the ankles on the pedals).
  The pedals, left by the model half way round, are turned level (the rider's feet side by side).
- <out>/PiaggioSi.json: wheels, body box, steering axis, where to stand to get on, materials (Scripts/m80_motorino_import.py).
- <out>/Textures/*.png: colour, normal, metal (R) + roughness (G) maps.
- <out>/A_M80_Motorino_Guida.fbx: the rider on it (UEFN mannequin, armature only, 2 s loop with a little breathing).
- <out>/A_M80_Motorino_Sale.fbx, A_M80_Motorino_Scende.fbx: getting on from the left (hands on the grips, the right leg over the
  saddle, astride, sitting down, the feet onto the pedals) and off the same way back; in the moped's space with the mesh
  origin on Sella (the pelvis bone carries the body from beside it onto the saddle), so they play with the rider attached.
- <out>/PiaggioSi_*.png: previews of the pose and of moments of getting on.
"""
import json
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT, MANNEQUIN, TEXDIR = ARGS[0], ARGS[1], ARGS[2]
NAME = "PiaggioSi"
os.makedirs(os.path.join(OUT, "Textures"), exist_ok=True)
REPORT = {"key": NAME, "kind": "bike", "steps": []}

LENGTH = 1.63   # Piaggio Si: 1630 mm long, 16 inch wheels, saddle about 78 cm up
PARTS = {"Piaggio SI": "Root", "Piaggio SI.003": "Steer", "defaultMaterial.033": "Wheel_F", "Piaggio SI.002": "Wheel_R"}
# The Si's own maps (Unity standard: metallic in R, smoothness in A); the Bravo's tyres (Hjul) keep the packed ones.
SI_TEX = {"Piaggio SI": {"base": "Piaggio_SI_Scooter_Piaggio_SI_AlbedoTransp.png", "normal": "Piaggio_SI_Scooter_Piaggio_SI_Normal.png",
                         "metal_smooth": "Piaggio_SI_Scooter_Piaggio_SI_MetallicSmoo.png"},
          "Wheels": {"base": "Piaggio_SI_Scooter_Wheels_AlbedoTransparen.png"}}
FPS = 30
SIDE_Y = 0.45   # where the rider stands to get on: 45 cm left of the middle


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


def r3(v, k=100.0, nd=1):
    return [round(c * k, nd) for c in v]


# ---------------------------------------------------------------------------------------------
# 1) The moped as one mesh per bone, at its real size

def collect():
    dg = bpy.context.evaluated_depsgraph_get()
    raw = {}
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or o.name not in PARTS:
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        n = bpy.data.objects.new("M80_" + PARTS[o.name], me)
        bpy.context.scene.collection.objects.link(n)
        raw[PARTS[o.name]] = n
    for o in list(bpy.context.scene.objects):
        if not o.name.startswith("M80_"):
            o.hide_render = True
            o.hide_set(True)
    allv = [v for o in raw.values() for v in world_verts(o)]
    lo, hi = bbox(allv)
    s = LENGTH / (hi.x - lo.x)
    wf, wr = (bbox(world_verts(raw[k])) for k in ("Wheel_F", "Wheel_R"))
    mid = Vector((((wf[0].x + wf[1].x) / 2 + (wr[0].x + wr[1].x) / 2) / 2, (wf[0].y + wf[1].y + wr[0].y + wr[1].y) / 4, lo.z))
    m = Matrix.Scale(s, 4) @ Matrix.Translation(-mid)
    for o in raw.values():
        o.data.transform(m)
        for p in o.data.polygons:
            p.use_smooth = True
    log("scale", round(s, 4), "parts", {k: tri_count(o) for k, o in raw.items()})
    return raw


def level_pedals(body):
    """Turns the crank arms and the pedals (outside the frame, low) about their axle until the two pedals are level."""
    vs = body.data.vertices
    wide = [v for v in vs if abs(v.co.y) > 0.13 and v.co.z < 0.45]
    pl = [v.co for v in wide if v.co.y > 0]
    pr = [v.co for v in wide if v.co.y < 0]
    if not pl or not pr:
        log("pedals not found")
        return None
    cl, cr = sum(pl, Vector()) / len(pl), sum(pr, Vector()) / len(pr)
    c = (cl + cr) / 2
    arm = Vector((cl.x - c.x, cl.z - c.z))
    radius = arm.length
    # Level, the left pedal in front: the angle that takes the left one to the front (x+) at the axle's height.
    ang = math.atan2(arm.y, arm.x)   # from +x towards +z
    moved = 0
    for v in vs:
        d = Vector((v.co.x - c.x, v.co.z - c.z))
        if abs(v.co.y) > 0.10 and d.length < radius + 0.06 and v.co.z < 0.45:
            ca, sa = math.cos(-ang), math.sin(-ang)
            v.co.x = c.x + d.x * ca - d.y * sa
            v.co.z = c.z + d.x * sa + d.y * ca
            moved += 1
    body.data.update()
    left = Vector((c.x + radius, cl.y, c.z))
    right = Vector((c.x - radius, cr.y, c.z))
    log("pedals levelled: axle", r3(c), "radius cm", round(radius * 100, 1), "turned deg", round(math.degrees(ang), 1), "vertices", moved)
    # The pedals' top: the highest point near each pedal centre.
    tops = []
    for p in (left, right):
        near = [v.co for v in vs if (Vector((v.co.x, v.co.z)) - Vector((p.x, p.z))).length < 0.05 and abs(v.co.y - p.y) < 0.05]
        tops.append(Vector((p.x, p.y, max((q.z for q in near), default=p.z))))
    return tops


def steering_axis(steer, wheel_f):
    """The fork legs (beside the front wheel, above its axle): a line x = a + b z; the pivot on it under the handlebar."""
    lo, hi = bbox(world_verts(wheel_f))
    axle = (lo + hi) / 2
    pts = [v for v in world_verts(steer) if axle.z + 0.06 < v.z < 0.62 and 0.02 < abs(v.y) < 0.09 and v.x > axle.x - 0.3]
    z = np.array([p.z for p in pts])
    x = np.array([p.x for p in pts])
    b, a = np.polyfit(z, x, 1)
    axis = Vector((b, 0.0, 1.0)).normalized()
    zp = 0.72
    pivot = Vector((a + b * zp, 0.0, zp))
    log("steering axis: rake deg", round(math.degrees(math.atan(-b)), 1), "pivot", r3(pivot), "fork points", len(pts))
    return pivot, axis


def grips(steer):
    """Where the hands hold: on the rubber grip 5 cm in from the bar's end. The brake levers reach out as far as the
    grips, a little in front: only the hindmost tube near the end counts."""
    vs = world_verts(steer)
    out = []
    for side in (1, -1):
        ext = max(v.y * side for v in vs)
        end = [v for v in vs if ext - v.y * side < 0.07]
        back = min(v.x for v in end)
        tube = [v for v in end if v.x < back + 0.035]
        c = sum(tube, Vector()) / len(tube)
        out.append(Vector((c.x, side * (ext - 0.05), c.z)))
    log("grips", [r3(g) for g in out])
    return out


SEAT_MESH = []
SEAT_HALF = 0.07   # half the saddle's width
SEAT_RANGE = [-1.0, 1.0]   # its length (x), set from the moped


def seat_height(x, y):
    """Top of the body under (x, y): the highest of a few rays 2 cm apart (the saddle's cover has seams the rays slip through)."""
    best = 0.0
    for dx in (-0.02, 0.0, 0.02):
        for dy in (-0.02, 0.0, 0.02):
            ok, loc, _n, _i = SEAT_MESH[0].ray_cast(Vector((x + dx, y + dy, 2.0)), Vector((0, 0, -1)))
            if ok:
                best = max(best, loc.z)
    return best


# ---------------------------------------------------------------------------------------------
# 2) The rider (UEFN mannequin), as the carts' (Research/Mazzarino80/Blender/m80_carretti_gioco.py)

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
            self.palm_sign[s] = 1.0 if n.dot(-self.UP - out) > 0 else -1.0
        # Standing as imported: heights of the hips and the ankles over the ground, the foot's direction (flat on the ground).
        self.pelvis_h = self.to_world(self.head("pelvis")).z
        self.ankle_h = self.to_world(self.head("foot_l")).z
        self.foot_flat = (self.head("ball_l") - self.head("foot_l")).normalized()

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

    def move(self, name, delta):
        bpy.context.view_layer.update()
        pb = self.P[name]
        pb.matrix = Matrix.Translation(delta) @ pb.matrix
        bpy.context.view_layer.update()

    def align(self, bone, child, desired):
        cur = (self.head(child) - self.head(bone)).normalized()
        self.rotate(bone, cur.rotation_difference(desired.normalized()))

    def tilt_back(self, bone, degrees, probe="head", toward=None):
        toward = -self.FWD if toward is None else toward
        before = self.head(probe).dot(toward)
        self.rotate(bone, Quaternion(self.LEFT, math.radians(degrees)))
        if (self.head(probe).dot(toward) - before) * degrees < 0:
            self.rotate(bone, Quaternion(self.LEFT, math.radians(-2 * degrees)))

    def length(self, a, b):
        return (self.head(b) - self.head(a)).length

    def two_bone(self, upper, lower, end, target, pole):
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
        h = self.head("hand_" + s)
        i, p = self.head("index_01_" + s), self.head("pinky_01_" + s)
        n = (i - h).cross(p - h).normalized()
        return n * self.palm_sign.get(s, 1.0)

    def orient_hand(self, s, fingers, palm):
        mid = "middle_metacarpal_" + s if ("middle_metacarpal_" + s) in self.P else "middle_01_" + s
        self.align("hand_" + s, mid, fingers)
        d = (self.head(mid) - self.head("hand_" + s)).normalized()
        n = self.palm(s)
        want = (palm - d * palm.dot(d)).normalized()
        have = (n - d * n.dot(d)).normalized()
        ang = math.atan2(have.cross(want).dot(d), have.dot(want))
        self.rotate("hand_" + s, Quaternion(d, ang))

    def fist(self, s, amount=1.0):
        """Fingers closed round a grip: every joint bends about the same axis, the line of the knuckles (bending each about
        its own axis splayed them crooked)."""
        n = self.palm(s)
        across = (self.head("pinky_01_" + s) - self.head("index_01_" + s)).normalized()
        for f, angles in (("index", (40, 65, 35)), ("middle", (45, 70, 35)), ("ring", (50, 70, 35)), ("pinky", (55, 70, 35))):
            for k, ang in enumerate(angles):
                b = "%s_%02d_%s" % (f, k + 1, s)
                c = "%s_%02d_%s" % (f, k + 2, s) if k < 2 else None
                if b not in self.P:
                    continue
                if c and c in self.P:
                    d = (self.head(c) - self.head(b)).normalized()
                else:
                    d = (self.P[b].tail - self.P[b].head).normalized()
                # Turning d about the axis moves it towards axis x d: towards the palm's side.
                axis = across if across.cross(d).dot(n) > 0 else -across
                self.rotate(b, Quaternion(axis, math.radians(ang * amount)))
        for k, ang in enumerate((15, 25, 20)):
            b = "thumb_%02d_%s" % (k + 1, s)
            if b in self.P:
                d = (self.P[b].tail - self.P[b].head).normalized()
                self.rotate(b, Quaternion(d.cross(n).normalized(), math.radians(ang * amount)))

    def lowest(self, groups, near=None, radius=0.2, half_width=None):
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
                if half_width is not None and (abs(w.y) > half_width or not SEAT_RANGE[0] < w.x < SEAT_RANGE[1]):
                    continue
                if best is None or w.z < best.z:
                    best = w
            ev.to_mesh_clear()
        return best


def side_out(r, s):
    return r.LEFT if s == "l" else -r.LEFT


ARM_BONES = {s: ["upperarm_" + s, "lowerarm_" + s, "hand_" + s] + ["%s_%02d_%s" % (f, k, s) for f in ("index", "middle", "ring", "pinky", "thumb")
                                                                   for k in (1, 2, 3)] for s in ("l", "r")}


def build(r, K, breath=0.0):
    """One pose from a key (moped space, metres): the hips at K["pelvis"], leaning K["lean"] degrees (negative: forward), the
    ankles on K["feet"] (knees towards K["knees"]), the hands on K["hands"] by K["hold"] (0: hanging down, 1: on the grips)."""
    F, U = r.FWD, r.UP
    r.reset()
    # The imported armature has no root bone (it is the armature object, "root" in Unreal): the hips carry the body.
    r.move("pelvis", r.to_arm(K["pelvis"]) - r.head("pelvis"))
    r.tilt_back("pelvis", K["lean"])
    r.tilt_back("spine_05", breath)
    r.tilt_back("neck_01", -K["lean"] * 0.8 - 6)
    misses = {}
    for i, s in enumerate(("l", "r")):
        o = side_out(r, s)
        t = r.to_arm(K["feet"][i])
        pole = K["knees"][i][0] * F + K["knees"][i][1] * U + K["knees"][i][2] * o
        misses["piede_" + s] = r.two_bone("thigh_" + s, "calf_" + s, "foot_" + s, t, pole)
        # The foot flat as standing (on the ground, on a pedal), turned with the leg's heading.
        fl = r.foot_flat
        r.align("foot_" + s, "ball_" + s, F * fl.dot(F) + U * fl.dot(U) * K.get("toes", [1.0, 1.0])[i] + o * 0.08)
    for i, s in enumerate(("l", "r")):
        o = side_out(r, s)
        # Hanging: the arm down along the body, the forearm a little forward.
        r.align("upperarm_" + s, "lowerarm_" + s, -U * 0.97 + o * 0.16 + F * 0.04)
        r.align("lowerarm_" + s, "hand_" + s, -U * 0.9 + F * 0.3 + o * 0.03)
        mid = "middle_metacarpal_" + s if ("middle_metacarpal_" + s) in r.P else "middle_01_" + s
        r.align("hand_" + s, mid, -U * 0.95 + F * 0.2)
        r.fist(s, 0.25)
        w = K["hold"][i]
        if w <= 0.0:
            continue
        hang = {b: r.P[b].matrix_basis.copy() for b in ARM_BONES[s] if b in r.P}
        for b in hang:
            r.P[b].matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        # Over the grip from behind: the back of the hand up, the palm down and forward on the rubber, the fingers round
        # its front and under it.
        fingers, palm = (F * 0.85 - U * 0.4 - o * 0.1), (-U * 0.8 + F * 0.45)
        pole = o * 0.75 - U * 0.55
        wrist = r.to_arm(K["hands"][i]) - fingers.normalized() * 7.0 + palm.normalized() * 1.5
        misses["mano_" + s] = r.two_bone("upperarm_" + s, "lowerarm_" + s, "hand_" + s, wrist, pole)
        r.orient_hand(s, fingers, palm)
        r.fist(s, 1.3)
        if w < 1.0:
            for b, m in hang.items():
                q = m.to_quaternion().slerp(r.P[b].matrix_basis.to_quaternion(), w)
                r.P[b].matrix_basis = q.to_matrix().to_4x4()
            bpy.context.view_layer.update()
    return misses


# ---------------------------------------------------------------------------------------------
# 3) The pose on the moped and the keys of getting on

def ride_key(r, hands, pedals, pelvis_x, lean):
    return {"pelvis": None, "pelvis_x": pelvis_x, "lean": lean, "feet": [pedals[0] + Vector((-0.10, 0, 0.085)), pedals[1] + Vector((-0.10, 0, 0.085))],
            "knees": [(0.9, 0.35, 0.04), (0.9, 0.35, 0.04)], "hands": hands, "hold": [1.0, 1.0], "toes": [0.6, 0.6]}


def make_rider(hands, pedals, seat_x):
    """Sitting on the saddle (the lowest point of the hips and thighs on it), leaning forward until the hands reach the grips."""
    r = Rider()
    lean = 0.0
    for attempt in range(8):
        K = ride_key(r, hands, pedals, seat_x, lean)
        r.place(Vector((0, 0, 0)))
        r.reset()
        pel = r.to_world(r.head("pelvis"))
        r.place(Vector((seat_x - pel.x, -pel.y, 0)))
        K["pelvis"] = r.to_world(r.head("pelvis"))
        build(r, K)
        pel = r.to_world(r.head("pelvis"))
        # On the saddle (narrow, and not the low frame in front of it): the lowest point of the hips and thighs over it.
        low = r.lowest({"pelvis", "thigh_l", "thigh_r"}, pel, 0.2, SEAT_HALF)
        surf = seat_height(low.x, low.y)
        r.place(r.sella + Vector((0, 0, surf - low.z)))
        r.reset()
        K["pelvis"] = r.to_world(r.head("pelvis"))
        misses = build(r, K)
        reach = max(v for k, v in misses.items() if k.startswith("mano"))
        log("attempt", attempt, "lean", lean, "seat z", round(surf, 3), "misses cm", {k: round(v, 1) for k, v in misses.items()})
        if reach < 1.0:
            break
        lean -= 5.0
    REPORT["rider"] = {"sella_m": [round(c, 4) for c in r.sella], "lean_deg": lean, "misses_cm": {k: round(v, 1) for k, v in misses.items()}}
    return r, K


def mount_keys(r, ride, seat_top):
    """Keys of getting on from the left (frame, key). The left foot stays where it stands until the rider sits."""
    pr = ride["pelvis"]
    hp, ha = r.pelvis_h, r.ankle_h
    xs = pr.x + 0.12
    stand_l = Vector((xs, SIDE_Y + 0.11, ha))
    stand_r = Vector((xs, SIDE_Y - 0.11, ha))
    knee = (0.9, 0.3, 0.2)

    def key(pelvis, lean, feet, hold, knees=(knee, knee), toes=(1.0, 1.0)):
        return {"pelvis": pelvis, "lean": lean, "feet": list(feet), "knees": list(knees), "hands": ride["hands"], "hold": list(hold), "toes": list(toes)}

    k0 = key(Vector((xs, SIDE_Y, hp - 0.01)), 0.0, (stand_l, stand_r), (0.0, 0.0))
    k1 = key(Vector((xs + 0.03, SIDE_Y - 0.06, hp - 0.04)), -10.0, (stand_l, stand_r), (1.0, 1.0))
    # The right leg back and up over the saddle's tail, the knee bent and pointing down.
    k2 = key(Vector((xs - 0.02, SIDE_Y - 0.16, hp - 0.06)), -24.0, (stand_l, Vector((pr.x - 0.50, 0.04, seat_top + 0.16))), (1.0, 1.0),
             knees=(knee, (-0.3, -0.9, 0.3)), toes=(1.0, 0.4))
    k3 = key(Vector((xs - 0.04, SIDE_Y - 0.28, hp - 0.09)), -22.0, (stand_l, Vector((pr.x - 0.16, -0.30, seat_top + 0.06))), (1.0, 1.0),
             knees=(knee, (0.3, -0.5, 0.6)), toes=(1.0, 0.7))
    # Astride, standing over the saddle; then sitting with both feet on the ground; then the feet onto the pedals.
    k4 = key(Vector((pr.x + 0.05, 0.03, hp - 0.07)), -16.0, (Vector((xs - 0.02, 0.32, ha)), Vector((xs - 0.02, -0.32, ha))), (1.0, 1.0),
             knees=((0.9, 0.3, 0.35), (0.9, 0.3, 0.35)))
    k5 = key(pr.copy(), ride["lean"], (Vector((pr.x + 0.14, 0.31, ha)), Vector((pr.x + 0.14, -0.31, ha))), (1.0, 1.0),
             knees=((0.9, 0.35, 0.15), (0.9, 0.35, 0.15)))
    k6 = dict(ride)
    sale = [(1, k0), (16, k1), (30, k2), (40, k3), (50, k4), (63, k5), (76, k6), (82, k6)]
    # Getting off is not getting on backwards: feet down, standing up astride, the right leg back over the saddle with the
    # right hand let go, standing upright beside it with the left hand still holding the handlebar, then letting it go.
    a4 = key(Vector((pr.x + 0.05, 0.03, hp - 0.06)), -8.0, k4["feet"], (1.0, 1.0), knees=k4["knees"])
    a3 = key(Vector((xs - 0.04, 0.16, hp - 0.07)), -14.0, (Vector((xs - 0.02, 0.32, ha)), Vector((pr.x - 0.40, 0.02, seat_top + 0.14))), (1.0, 0.3),
             knees=((0.9, 0.3, 0.3), (-0.3, -0.9, 0.3)), toes=(1.0, 0.4))
    a2 = key(Vector((xs - 0.02, SIDE_Y - 0.12, hp - 0.05)), -6.0, (stand_l, Vector((xs - 0.12, SIDE_Y - 0.20, ha + 0.10))), (1.0, 0.0),
             knees=(knee, (0.4, -0.4, 0.5)), toes=(1.0, 0.8))
    a1 = key(Vector((xs + 0.02, SIDE_Y - 0.03, hp - 0.02)), -3.0, (stand_l, stand_r), (1.0, 0.0))
    scende = [(1, k6), (10, k5), (22, a4), (34, a3), (44, a2), (54, a1), (66, k0), (72, k0)]
    # Picking it up from the ground (beside it, where getting on starts): bending at knees and back down to the handlebar,
    # then standing up as the moped comes up (the hands follow the grips by IK in the game, not in the clip).
    p1 = key(Vector((xs + 0.06, SIDE_Y - 0.04, hp - 0.36)), -48.0, (stand_l, stand_r), (0.0, 0.0),
             knees=((0.9, 0.2, 0.35), (0.9, 0.2, 0.35)))
    p2 = key(k1["pelvis"].copy(), -10.0, (stand_l, stand_r), (0.0, 0.0))
    raccoglie = [(1, k0), (20, p1), (30, p1), (52, p2), (56, p2)]
    return sale, scende, raccoglie


def mix(a, b, t):
    e = t * t * (3 - 2 * t)
    out = {}
    for k in ("pelvis",):
        out[k] = a[k].lerp(b[k], e)
    out["lean"] = a["lean"] + (b["lean"] - a["lean"]) * e
    out["feet"] = [a["feet"][i].lerp(b["feet"][i], e) for i in range(2)]
    out["knees"] = [tuple(a["knees"][i][j] + (b["knees"][i][j] - a["knees"][i][j]) * e for j in range(3)) for i in range(2)]
    out["toes"] = [a["toes"][i] + (b["toes"][i] - a["toes"][i]) * e for i in range(2)]
    out["hands"] = a["hands"]
    out["hold"] = [a["hold"][i] + (b["hold"][i] - a["hold"][i]) * e for i in range(2)]
    return out


def at(keys, f):
    for (f0, k0), (f1, k1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            return mix(k0, k1, (f - f0) / max(1, f1 - f0))
    return keys[-1][1]


def key_all(r, f):
    for pb in r.P:
        pb.keyframe_insert("location", frame=f)
        pb.keyframe_insert("rotation_quaternion", frame=f)
        pb.keyframe_insert("scale", frame=f)


def new_action(r, name):
    if r.arm.animation_data and r.arm.animation_data.action:
        old = r.arm.animation_data.action
        r.arm.animation_data.action = None
        bpy.data.actions.remove(old)
    r.arm.animation_data_create()
    act = bpy.data.actions.new(name)
    r.arm.animation_data.action = act
    return act


def export_clip(r, name, first, last):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = first, last
    sc.render.fps = FPS
    mw = r.arm.matrix_world.copy()
    r.arm.matrix_world = r.rest_matrix
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    r.arm.select_set(True)
    bpy.context.view_layer.objects.active = r.arm
    path = os.path.join(OUT, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE"}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, armature_nodetype="NULL",
                             primary_bone_axis="Y", secondary_bone_axis="X")
    r.arm.matrix_world = mw
    bpy.context.view_layer.objects.active = r.arm
    bpy.ops.object.mode_set(mode="POSE")
    log("clip exported", path, "frames", first, last)


def clips(r, ride, seat_top):
    sale, scende, raccoglie = mount_keys(r, ride, seat_top)
    # The skinned meshes are not needed while solving: hidden, the scene updates much faster.
    for o in r.meshes:
        o.hide_viewport = True
    new_action(r, "M80_Motorino_Guida")
    for f, breath in ((1, 0.0), (30, 1.2), (60, 0.0)):
        bpy.context.scene.frame_set(f)
        build(r, ride, breath)
        key_all(r, f)
    export_clip(r, "A_M80_Motorino_Guida", 1, 60)
    misses = {}
    for name, keys in (("A_M80_Motorino_Sale", sale), ("A_M80_Motorino_Scende", scende)):
        new_action(r, name)
        last = keys[-1][0]
        worst = {}
        for f in range(1, last + 1):
            bpy.context.scene.frame_set(f)
            m = build(r, at(keys, f))
            for k, v in m.items():
                if v > worst.get(k, (0.0, 0))[0]:
                    worst[k] = (round(v, 1), f)
            key_all(r, f)
        misses[name] = worst
        export_clip(r, name, 1, last)
    # Picking it up: played standing on the road (the mesh origin where getting on starts, not on the saddle), as the
    # moped lies there.
    sella = r.sella.copy()
    origin = Vector((sale[0][1]["pelvis"].x, SIDE_Y, 0.0))
    r.place(origin)
    new_action(r, "A_M80_Motorino_Raccoglie")
    for f in range(1, raccoglie[-1][0] + 1):
        bpy.context.scene.frame_set(f)
        build(r, at(raccoglie, f))
        key_all(r, f)
    export_clip(r, "A_M80_Motorino_Raccoglie", 1, raccoglie[-1][0])
    r.place(sella)
    REPORT["pickup_origin_cm"] = [round(origin.x * 100, 1), round(-origin.y * 100, 1), 0.0]
    REPORT["clip_worst_miss_cm"] = misses
    # Without the action: the previews show the poses built for them, not the clip's frame.
    r.arm.animation_data.action = None
    for o in r.meshes:
        o.hide_viewport = False
    return sale, scende


# ---------------------------------------------------------------------------------------------
# 4) Previews

def previews(r, ride, sale, scende):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    sc.render.resolution_x, sc.render.resolution_y = 1000, 750
    world = bpy.data.worlds.new("M80W")
    try:
        world.use_nodes = False
    except AttributeError:
        pass
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
    centre = Vector((0.0, 0.0, 0.75))

    def shot(name, eye, at_=centre):
        cam.location = eye
        cam.rotation_euler = (at_ - eye).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (NAME, name))
        bpy.ops.render.render(write_still=True)

    build(r, ride)
    hand = r.to_world(r.head("hand_l"))
    shot("mano_sinistra", hand + Vector((0.18, 0.28, 0.12)), hand + Vector((0.04, -0.02, -0.03)))
    shot("mano_sinistra_sopra", hand + Vector((0.02, 0.05, 0.35)), hand + Vector((0.04, -0.02, -0.03)))
    shot("guida_lato", Vector((-0.1, 3.2, 0.9)))
    shot("guida_tre_quarti", Vector((2.3, 1.9, 1.5)))
    shot("guida_davanti", Vector((3.0, -0.4, 1.0)))
    shot("guida_alto", Vector((0.3, 0.2, 3.4)))
    for f in (1, 16, 30, 40, 50, 63):
        build(r, at(sale, f))
        shot("sale_%02d" % f, Vector((1.6, 3.0, 1.4)))
    shot("sale_63_dietro", Vector((-2.8, 1.2, 1.5)))
    for f in (22, 34, 44, 54):
        build(r, at(scende, f))
        shot("scende_%02d" % f, Vector((1.6, 3.0, 1.4)))
    for o in (sun, ground, cam):
        bpy.data.objects.remove(o, do_unlink=True)


# ---------------------------------------------------------------------------------------------
# 5) Materials and textures

SAVED = {}


def clean(name):
    return re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")[:48] or "Mat"


def save_pixels(im, base, px=None):
    """PNG at most 2048 px; px (h*w*4 floats) replaces the image's own pixels."""
    if base in SAVED:
        return SAVED[base]
    w, h = im.size
    out = bpy.data.images.new("M80_" + base, w, h, alpha=True, float_buffer=False)
    out.pixels.foreach_set(px if px is not None else np.array(im.pixels[:], dtype=np.float32))
    if max(w, h) > 2048:
        out.scale(min(w, 2048), min(h, 2048))
    path = os.path.join(OUT, "Textures", "T_%s_%s.png" % (NAME, base))
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    SAVED[base] = os.path.basename(path)
    return SAVED[base]


def metal_rough(im, metal_ch, rough_ch, rough_from_smooth):
    """Metal in R and roughness in G (B 0, A 1) from a map holding them in other channels."""
    a = np.array(im.pixels[:], dtype=np.float32).reshape(-1, 4)
    out = np.zeros_like(a)
    out[:, 0] = a[:, metal_ch]
    out[:, 1] = 1.0 - a[:, rough_ch] if rough_from_smooth else a[:, rough_ch]
    out[:, 3] = 1.0
    return out.reshape(-1), float(out[:, 0].mean()), float(out[:, 1].mean())


def export_materials(objs):
    mats = {}
    for o in objs:
        for s in o.material_slots:
            m = s.material
            if not m or m.name in mats:
                continue
            d = {"slot": clean(m.name), "color": [1.0, 1.0, 1.0], "metallic": 1.0, "roughness": 1.0, "base_tex": None, "normal_tex": None,
                 "metal_rough_tex": None}
            if m.name in SI_TEX:
                t = SI_TEX[m.name]
                im = bpy.data.images.load(os.path.join(TEXDIR, t["base"]))
                d["base_tex"] = save_pixels(im, clean(m.name) + "_Colore")
                if "normal" in t:
                    im = bpy.data.images.load(os.path.join(TEXDIR, t["normal"]))
                    im.colorspace_settings.name = "Non-Color"
                    d["normal_tex"] = save_pixels(im, clean(m.name) + "_Normale")
                if "metal_smooth" in t:
                    im = bpy.data.images.load(os.path.join(TEXDIR, t["metal_smooth"]))
                    im.colorspace_settings.name = "Non-Color"
                    px, mm, rr = metal_rough(im, 0, 3, True)
                    d["metal_rough_tex"] = save_pixels(im, clean(m.name) + "_MetalloRuvidita", px)
                    d["mean_metal_rough"] = [round(mm, 3), round(rr, 3)]
                else:
                    d["metallic"], d["roughness"] = 0.0, 0.6
            else:
                nodes = m.node_tree.nodes
                p = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
                bc = p.inputs["Base Color"]
                if bc.is_linked and bc.links[0].from_node.type == "TEX_IMAGE":
                    d["base_tex"] = save_pixels(bc.links[0].from_node.image, clean(m.name) + "_Colore")
                nm = next((n for n in nodes if n.type == "NORMAL_MAP"), None)
                if nm and nm.inputs["Color"].is_linked:
                    d["normal_tex"] = save_pixels(nm.inputs["Color"].links[0].from_node.image, clean(m.name) + "_Normale")
                # glTF: roughness in G, metal in B (through a Separate Color).
                rl = p.inputs["Roughness"]
                if rl.is_linked and rl.links[0].from_node.type in ("SEPARATE_COLOR", "SEPRGB"):
                    sep = rl.links[0].from_node
                    im = sep.inputs[0].links[0].from_node.image
                    px, mm, rr = metal_rough(im, 2, 1, False)
                    d["metal_rough_tex"] = save_pixels(im, clean(m.name) + "_MetalloRuvidita", px)
                    d["mean_metal_rough"] = [round(mm, 3), round(rr, 3)]
            mats[m.name] = d
    return mats


# ---------------------------------------------------------------------------------------------
# 6) Skeleton and export

def make_rig(meshes, bones, steer_axis):
    """bones: name -> (head in metres, parent). Every bone points +Y (identity frame in Unreal); Steer is rolled so that its Z
    runs along the steering axis."""
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
        if name == "Steer":
            b.align_roll(steer_axis)
        if parent:
            b.parent = made[parent]
        made[name] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    REPORT["steer_bone_z"] = [round(c, 3) for c in arm.data.bones["Steer"].matrix_local.to_3x3().col[2]]
    for bone, o in meshes.items():
        vg = o.vertex_groups.new(name=bone)
        vg.add(range(len(o.data.vertices)), 1.0, "REPLACE")
        o.parent = arm
        md = o.modifiers.new("Armature", "ARMATURE")
        md.object = arm
    return arm


def main():
    meshes = collect()
    pedals = level_pedals(meshes["Root"])
    wheels = {}
    for bone in ("Wheel_F", "Wheel_R"):
        lo, hi = bbox(world_verts(meshes[bone]))
        wheels[bone] = {"centre": (lo + hi) / 2, "radius": max(hi.x - lo.x, hi.z - lo.z) / 2, "width": hi.y - lo.y}
    REPORT["wheels"] = {k[6:]: {"centre_cm": r3(v["centre"]), "radius_cm": round(v["radius"] * 100, 2), "width_cm": round(v["width"] * 100, 2)}
                        for k, v in wheels.items()}
    lo, hi = bbox(world_verts(meshes["Root"]))
    REPORT["body_box_cm"] = r3(lo) + r3(hi)
    pivot, axis = steering_axis(meshes["Steer"], meshes["Wheel_F"])
    REPORT["steer_pivot_cm"], REPORT["steer_axis"] = r3(pivot), [round(c, 3) for c in axis]
    hands = grips(meshes["Steer"])
    REPORT["grips_cm"] = [r3(h) for h in hands]
    SEAT_MESH.append(meshes["Root"])
    # The saddle: its highest stretch along the middle; the rider sits on its front half.
    xs = [x / 100 for x in range(int(lo.x * 100) + 5, int(hi.x * 100) - 5, 2)]
    tops = [(x, seat_height(x, 0.0)) for x in xs]
    seat_top = max(z for _x, z in tops)
    seat = [x for x, z in tops if z > seat_top - 0.03]
    seat_x = min(seat) + (max(seat) - min(seat)) * 0.62
    SEAT_RANGE[:] = [min(seat), max(seat)]
    REPORT["seat"] = {"top_cm": round(seat_top * 100, 1), "from_x_cm": round(min(seat) * 100, 1), "to_x_cm": round(max(seat) * 100, 1),
                      "rider_x_cm": round(seat_x * 100, 1)}
    log("seat", REPORT["seat"])
    if not pedals:
        pedals = [Vector((seat_x + 0.15, 0.18, 0.25)), Vector((seat_x + 0.15, -0.18, 0.25))]
    REPORT["pedals_cm"] = [r3(p) for p in pedals]

    rider, ride = make_rider(hands, pedals, seat_x)
    sella = rider.sella.copy()
    # Where the wrists and ankles are in the pose (the grips may be out of reach by a little): the bones for the game.
    build(rider, ride)
    wrists = [rider.to_world(rider.head("hand_" + s)) for s in ("l", "r")]
    ankles = [rider.to_world(rider.head("foot_" + s)) for s in ("l", "r")]
    sale, scende = clips(rider, ride, seat_top)
    previews(rider, ride, sale, scende)
    stand = at(sale, 1)["pelvis"]
    # Unreal: y the other way (left is -Y).
    REPORT["mount_from_cm"] = [round(stand.x * 100, 1), round(-stand.y * 100, 1), 60.0]
    REPORT["pelvis_ride_cm"] = r3(ride["pelvis"])
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in [rider.arm] + rider.meshes:
        bpy.data.objects.remove(o, do_unlink=True)

    bones = {"Root": (Vector((0, 0, 0)), None), "Steer": (pivot, "Root")}
    for w in ("Wheel_F", "Wheel_R"):
        bones[w] = (wheels[w]["centre"], "Root")
    bones["Sella"] = (sella, "Root")
    bones["Mano_L"] = (wrists[0], "Steer")
    bones["Mano_R"] = (wrists[1], "Steer")
    bones["Piede_L"] = (ankles[0], "Root")
    bones["Piede_R"] = (ankles[1], "Root")
    REPORT["bones_cm"] = {k: r3(v[0]) for k, v in bones.items()}
    REPORT["materials"] = export_materials(list(meshes.values()))
    REPORT["triangles"] = {o.name: tri_count(o) for o in meshes.values()}
    sc100 = Matrix.Scale(100.0, 4)
    for o in meshes.values():
        o.data.transform(sc100 @ o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.01
    named = {"Root": "Telaio", "Steer": "Sterzo", "Wheel_F": "Ruota_F", "Wheel_R": "Ruota_R"}
    for b, o in meshes.items():
        o.name = o.data.name = named[b]
    arm = make_rig(meshes, bones, axis)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes.values():
        o.select_set(True)
    arm.select_set(True)
    path = os.path.join(OUT, NAME + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE", "MESH"}, axis_forward="-Y", axis_up="Z",
                             apply_unit_scale=True, mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False,
                             use_armature_deform_only=False, primary_bone_axis="Y", secondary_bone_axis="X", path_mode="STRIP")
    log("moped exported", path)
    REPORT["textures"] = sorted(SAVED.values())
    with open(os.path.join(OUT, NAME + ".json"), "w", encoding="utf-8") as f:
        json.dump(REPORT, f, indent=1)
    log("done")


main()
