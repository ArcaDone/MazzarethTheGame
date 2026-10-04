"""Blender 4.3: renders all the Sicilian props in a row with the atlas, to check them before Unreal.

Run: blender -b --factory-startup --python m80_sicilia_preview.py -- <output.png>
"""
import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0]]  # m80_sicilia_blender exports on import; reuse its builders
exec(compile((HERE / "m80_sicilia_blender.py").read_text(encoding="utf-8").replace("\nmain()\n", "\n"), "m80_sicilia_blender", "exec"))

out = sys.orig_argv[sys.orig_argv.index("--") + 1] if "--" in sys.orig_argv else str(HERE / "preview.png")
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = [testa_di_moro(), pigna(), grasta("G1", True), grasta("G2", False), quartara(), bummulo(), edicola(), stemma(),  # noqa: F821
        lanterna(), doccione(), batacchio(), strattu(), peperoncini(), civico(1), panaru(),  # noqa: F821
        panni("P1", [("lenzuolo", "whitewash"), ("asciugamano", "glaze_blue"), ("maglia", "geranium")], 1),  # noqa: F821
        panni("P2", [("maglia", "whitewash"), ("pantaloni", "glaze_blue"), ("asciugamano", "lemon"), ("maglia", "leaf")], 2)]  # noqa: F821
img = bpy.data.images.load(str(HERE / "Textures/T_M80_SiciliaAtlas.png"))
for name, rough in (("M_Glazed", 0.15), ("M_Matte", 0.8), ("M_Iron", 0.5)):
    m = bpy.data.materials.get(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
x = 0.0
for o in objs:
    w = max(o.dimensions.x, 0.2)
    o.location = (x + w / 2, 0, 0 if o.name != "SM_M80_Panaru" else 3.6)
    if o.name in ("P1", "P2"):
        o.location.z = 1.8
    if o.name in ("SM_M80_Edicola", "SM_M80_Stemma", "SM_M80_Lanterna", "SM_M80_Batacchio", "SM_M80_Civico_2", "SM_M80_Doccione", "SM_M80_Peperoncini"):
        o.location.z = 0.9
    x += w + 0.15
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.collection.objects.link(cam)
cam.location = (x / 2 - 0.3, -10.5, 1.5)
cam.rotation_euler = (math.radians(82), 0, 0)
cam.data.lens = 34
bpy.context.scene.camera = cam
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(30))
sun.data.energy = 4
bpy.context.collection.objects.link(sun)
world = bpy.data.worlds.new("W")
world.color = (0.6, 0.65, 0.7)
bpy.context.scene.world = world
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 1800, 700
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("RENDERED", out)
