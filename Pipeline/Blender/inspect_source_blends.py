"""Inventory existing user-owned Blender assets for potential kit reuse."""
import json
import sys
from pathlib import Path

import bpy

root = Path(r"D:\Blender\AssetsMazzarethTheGame\TestBuildingParts\assets\models")
need = ("old-building_", "old-italian-fron_", "old-door_",
        "vintage-victoria_", "wrought-iron-out_", "old-wall-mounted_",
        "street-lamp-01_", "2floor-whitehous_")
inventory = []
for directory in root.iterdir():
    if not directory.name.startswith(need):
        continue
    files = list(directory.rglob("*.blend"))
    if not files:
        continue
    path = files[0]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        inventory.append({
            "path": str(path),
            "mesh_count": len(meshes),
            "polygon_count": sum(len(o.data.polygons) for o in meshes),
            "material_count": len(bpy.data.materials),
            "image_count": len(bpy.data.images),
            "object_names": [o.name for o in meshes[:12]],
        })
    except Exception as error:
        inventory.append({"path":str(path), "error":str(error)})
print("M80_SOURCE_INVENTORY", json.dumps(inventory))
