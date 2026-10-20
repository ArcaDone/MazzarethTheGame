"""Blender 4.3: the 1970s-80s steel road lamp ("palo a frusta") of the outskirts, exported to
D:/Mazzarino80_Sorgenti/Lampioni/M80_LampioneFrusta.fbx for Scripts/m80_lampione_frusta_setup.py.

Run: blender -b --factory-startup --python m80_lampione_frusta.py
Two meshes, so the actor "Lampione (Mazzarino)" (kind "A frusta") can choose the height:
- SM_M80_Frusta_Palo: the straight tapered pole, 1 m tall (the actor stretches it in Z; a cone stretched along
  its axis keeps its radii). Pivot at the base centre.
- SM_M80_Frusta_Testa: the top of the pole bending over into the arm along +X, with a slip-on collar at the
  joint and the luminaire at the end: an aluminium shell over a glass bowl, tilted 10 degrees up like the
  real ones. Pivot at the joint with the pole (its top, radius 4.5 cm).
Material slots: "Palo" (painted steel), "Armatura" (aluminium shell), "Vetro" (bowl, lit at night).
Units are metres. The bowl centre (the light) is written to M80_LampioneFrusta.json.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT_DIR = Path("D:/Mazzarino80_Sorgenti/Lampioni")
OUT = OUT_DIR / "M80_LampioneFrusta.fbx"
INFO = OUT_DIR / "M80_LampioneFrusta.json"
POLE, SHELL, GLASS = 0, 1, 2
NAMES = ("Palo", "Armatura", "Vetro")

POLE_R0, POLE_R1 = 0.075, 0.045      # base and top radius of the straight pole
RISE = 0.5                           # straight piece of the head before the bend
BEND_R, BEND_DEG = 1.5, 80.0         # radius and angle of the bend (the arm ends 10 degrees above level)
ARM_END = 0.4                        # straight end of the arm (into the shell)
ARM_R1 = 0.035                       # arm radius at the luminaire
SHELL_A, SHELL_B, SHELL_C = 0.36, 0.16, 0.09   # half length, half width, height of the shell
BOWL_C = 0.06                        # depth of the glass bowl
SIDES = 16


def frames(path):
    """Tangent and a normal carried along the path (rotation-minimising enough for a planar bend)."""
    out = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        n = Vector((0, 1, 0)).cross(t).normalized()
        out.append((t, n, t.cross(n).normalized()))
    return out


def tube(bm, path, radii, sides=SIDES, cap_start=True, cap_end=True):
    rings = []
    for p, r, (t, n, b) in zip(path, radii, frames(path)):
        ring = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            ring.append(bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * r))
        rings.append(ring)
    faces = []
    for ra, rb in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append(bm.faces.new((ra[i], ra[j], rb[j], rb[i])))
    if cap_start:
        faces.append(bm.faces.new(list(reversed(rings[0]))))
    if cap_end:
        faces.append(bm.faces.new(rings[-1]))
    return faces


def to_object(bm, name):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    for m in MATERIALS:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def set_material(faces, index):
    for f in faces:
        f.material_index = index


def pole():
    bm = bmesh.new()
    path = [Vector((0, 0, z / 8)) for z in range(9)]
    set_material(tube(bm, path, [POLE_R0 + (POLE_R1 - POLE_R0) * p.z for p in path], cap_start=False, cap_end=False), POLE)
    return to_object(bm, "SM_M80_Frusta_Palo")


def head():
    bm = bmesh.new()
    # The arm: up, round the bend, then straight into the shell.
    path = [Vector((0, 0, z * RISE / 4)) for z in range(5)]
    centre = Vector((BEND_R, 0, RISE))
    for k in range(1, 25):
        a = math.radians(180.0 - BEND_DEG * k / 24)
        path.append(centre + Vector((math.cos(a), 0, math.sin(a))) * BEND_R)
    a = math.radians(180.0 - BEND_DEG)
    tangent = Vector((math.sin(a), 0, -math.cos(a)))
    arc_end = path[-1].copy()
    for k in range(1, 5):
        path.append(arc_end + tangent * ARM_END * k / 4)
    run = [0.0]
    for p, q in zip(path, path[1:]):
        run.append(run[-1] + (q - p).length)
    set_material(tube(bm, path, [POLE_R1 + (ARM_R1 - POLE_R1) * s / run[-1] for s in run], cap_start=False), POLE)
    # Slip-on collar over the joint with the pole.
    set_material(tube(bm, [Vector((0, 0, -0.06)), Vector((0, 0, 0.07))], [POLE_R1 + 0.012] * 2), POLE)
    # Luminaire: a shell (upper half of an ellipsoid) over a flatter glass bowl, along the arm's last direction.
    pitch = math.radians(90.0 - BEND_DEG)
    lum = arc_end + tangent * (ARM_END + SHELL_A - 0.25)
    turn = Matrix.Translation(lum) @ Matrix.Rotation(-pitch, 4, "Y")
    sphere = bmesh.new()
    bmesh.ops.create_uvsphere(sphere, u_segments=24, v_segments=12, radius=1.0)
    for v in sphere.verts:
        x, y, z = v.co
        v.co = Vector((x * SHELL_A, y * SHELL_B, z * (SHELL_C if z >= 0 else BOWL_C)))
    lower = [f for f in sphere.faces if f.calc_center_median().z < 0]
    for f in sphere.faces:
        f.material_index = GLASS if f in lower else SHELL
    sphere.transform(turn)
    mesh = bpy.data.meshes.new("tmp")
    sphere.to_mesh(mesh)
    sphere.free()
    bm.from_mesh(mesh)
    bpy.data.meshes.remove(mesh)
    # A thin rim where the bowl meets the shell.
    rim = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        rim.append(turn @ Vector((math.cos(a) * SHELL_A * 1.01, math.sin(a) * SHELL_B * 1.01, 0)))
    set_material(tube(bm, rim, [0.008] * len(rim), sides=6, cap_start=False, cap_end=False), SHELL)
    light = turn @ Vector((0, 0, -BOWL_C * 0.5))
    return to_object(bm, "SM_M80_Frusta_Testa"), light


def make_materials():
    out = []
    for name, rgb in zip(NAMES, ((0.55, 0.56, 0.55), (0.6, 0.6, 0.58), (0.9, 0.85, 0.7))):
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*rgb, 1)
        out.append(m)
    return out


def unwrap(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATERIALS[:] = make_materials()
    p = pole()
    h, light = head()
    for obj in (p, h):
        unwrap(obj)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    INFO.write_text(json.dumps({"light_cm": [round(c * 100, 1) for c in light],
                                "head_bounds_cm": [[round(min(v.co[i] for v in h.data.vertices) * 100, 1) for i in range(3)],
                                                   [round(max(v.co[i] for v in h.data.vertices) * 100, 1) for i in range(3)]]},
                               indent=1), encoding="utf-8")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (p, h):
        obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT), use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True)
    print("M80 lampione a frusta exported:", OUT, INFO.read_text())


MATERIALS = []
main()
