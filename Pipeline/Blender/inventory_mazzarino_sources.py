"""Read-only audit of the four user-authored Mazzarino Blender source files."""
import json
import os
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(r"D:\Blender\AssetsMazzarethTheGame")
OUT=Path(__file__).resolve().parent/"output/mazzarino_source_inventory"
OUT.mkdir(parents=True,exist_ok=True)
NAMES=("CaseSoluzione","case_evy","balconyAndRoof","balcony_80s")

def dimensions(obj):
    if obj.type not in {"MESH","CURVE","FONT","SURFACE"}:
        return None
    points=[obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
        "min":[round(min(p[axis] for p in points),4) for axis in range(3)],
        "max":[round(max(p[axis] for p in points),4) for axis in range(3)],
        "size":[round(max(p[axis] for p in points)-min(p[axis] for p in points),4)
                for axis in range(3)],
    }

for name in NAMES:
    path=ROOT/(name+".blend")
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False)
    image_issues=[]
    images=[]
    for image in bpy.data.images:
        if image.source not in {"FILE","TILED"}:
            continue
        resolved=bpy.path.abspath(image.filepath,library=image.library)
        packed=bool(image.packed_file)
        exists=os.path.isfile(resolved)
        info={"name":image.name,"source":image.source,
              "filepath":image.filepath,"resolved":resolved,
              "packed":packed,"exists":exists}
        images.append(info)
        if not packed and not exists:
            image_issues.append(info)
    objects=[]
    for obj in bpy.data.objects:
        if obj.type not in {"MESH","CURVE","EMPTY"}:
            continue
        mesh=obj.data if obj.type=="MESH" else None
        objects.append({
            "name":obj.name,"type":obj.type,
            "collections":[col.name for col in obj.users_collection],
            "parent":obj.parent.name if obj.parent else None,
            "hide_viewport":bool(obj.hide_viewport),
            "hide_render":bool(obj.hide_render),
            "location":[round(v,4) for v in obj.location],
            "rotation_deg":[round(v*180/3.141592653589793,2) for v in obj.rotation_euler],
            "scale":[round(v,4) for v in obj.scale],
            "bounds":dimensions(obj),
            "faces":len(mesh.polygons) if mesh else 0,
            "triangles":len(mesh.loop_triangles) if mesh else 0,
            "uv_layers":[layer.name for layer in mesh.uv_layers] if mesh else [],
            "materials":[mat.name if mat else None for mat in obj.data.materials]
                if obj.type in {"MESH","CURVE"} else [],
            "modifiers":[mod.type for mod in obj.modifiers],
        })
    report={
        "source":str(path),"blender":bpy.app.version_string,
        "unit_system":bpy.context.scene.unit_settings.system,
        "unit_scale":bpy.context.scene.unit_settings.scale_length,
        "objects":objects,"images":images,
        "collections":[{"name":col.name,"parent":col.name_full.rsplit('/',1)[0]
                        if '/' in col.name_full else None,
                        "objects":len(col.objects)} for col in bpy.data.collections],
        "summary":{"objects":len(objects),
                   "mesh_objects":sum(o["type"]=="MESH" for o in objects),
                   "faces":sum(o["faces"] for o in objects),
                   "materials":len(bpy.data.materials),
                   "images":len(images),
                   "missing_unpacked_images":len(image_issues),
                   "collection_names":[col.name for col in bpy.data.collections],
                   "object_name_prefixes":Counter(o["name"].split('.')[0].split('_')[0]
                                                  for o in objects).most_common(15)}}
    (OUT/(name+".json")).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("M80_INVENTORY",name,json.dumps(report["summary"]))
