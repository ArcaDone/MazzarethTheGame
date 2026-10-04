"""Check the saved Blender visual pilot without exporting it to Unreal."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

out=Path(__file__).resolve().parent / "output/style03_reference_v4"
bpy.ops.wm.open_mainfile(filepath=str(out/"Mazzarino_STYLE_03_Reference_Gate_v4.blend"))
visible=[obj for obj in bpy.data.objects if obj.type in {"MESH","CURVE"}
         and obj.get("module_type") not in {"scale_mannequin_180cm","scale_ruler"}]
unmaterialed=[obj.name for obj in visible if not obj.data.materials or not obj.data.materials[0]]
materials={mat for obj in visible for mat in obj.data.materials if mat}
unpacked=[]
for mat in materials:
    if not mat.use_nodes:
        continue
    for node in mat.node_tree.nodes:
        if node.type=="TEX_IMAGE" and node.image and not node.image.packed_file:
            unpacked.append((mat.name,node.image.name,node.image.filepath))
balcony=next(obj for obj in visible if obj.get("module_type")=="balcony_stone_iron_350")
bounds=[balcony.matrix_world @ Vector(corner) for corner in balcony.bound_box]
report={
    "blender":bpy.app.version_string,
    "house_width_cm":620,"floor_height_cm":315,"mannequin_cm":180,
    "visible_parts":len(visible),"materials_used":len(materials),
    "missing_materials":unmaterialed,"unpacked_used_images":unpacked,
    "shared_master_present":"NG_M80_Architectural_Master" in bpy.data.node_groups,
    "balcony":{"name":balcony.name,"faces":len(balcony.data.polygons),
               "material_names":[mat.name for mat in balcony.data.materials],
               "material_face_counts":{
                   str(index):sum(poly.material_index==index for poly in balcony.data.polygons)
                   for index in range(len(balcony.data.materials))},
               "bounds_cm":{"x":[min(p.x for p in bounds),max(p.x for p in bounds)],
                            "y":[min(p.y for p in bounds),max(p.y for p in bounds)],
                            "z":[min(p.z for p in bounds),max(p.z for p in bounds)]},
               "wall_attachment_y_cm":balcony.get("wall_attachment_y_cm"),
               "street_facing_axis":balcony.get("street_facing_axis")}}
(out/"audit.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("M80_AUDIT",json.dumps(report))
