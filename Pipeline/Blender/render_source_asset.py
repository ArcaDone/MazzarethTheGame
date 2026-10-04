"""Render a read-only preview of an existing Blender asset in 4.3."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

source=Path(sys.argv[sys.argv.index("--")+1])
target_file=Path(sys.argv[sys.argv.index("--")+2])
selected_name=(sys.argv[sys.argv.index("--")+3]
               if len(sys.argv)>sys.argv.index("--")+3 else None)
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene
for o in list(bpy.data.objects):
    if o.type in {"CAMERA","LIGHT"} or (selected_name and o.name!=selected_name):
        bpy.data.objects.remove(o,do_unlink=True)
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
bpy.context.view_layer.update()
points=[o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
mid=(lo+hi)/2
span=max((hi-lo))
cam_data=bpy.data.cameras.new("InventoryPreview")
cam_data.type="ORTHO"
cam_data.ortho_scale=span*1.5
cam_data.clip_end=span*30
cam=bpy.data.objects.new("InventoryPreview",cam_data)
scene.collection.objects.link(cam)
cam.location=mid+Vector((span*.95,-span*1.8,span*.6))
cam.rotation_euler=(mid-cam.location).to_track_quat("-Z","Y").to_euler()
scene.camera=cam
light=bpy.data.lights.new("InventorySun","SUN")
light.energy=3
ob=bpy.data.objects.new("InventorySun",light)
scene.collection.objects.link(ob)
ob.rotation_euler=(.4,-.3,-.3)
if scene.world is None:
    scene.world=bpy.data.worlds.new("InventoryWorld")
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.8
scene.render.engine="CYCLES"
scene.cycles.samples=32
scene.render.resolution_x=800
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(target_file)
bpy.ops.render.render(write_still=True)
print("M80_SOURCE_PREVIEW",str(target_file),"bounds",list(hi-lo))
