"""List reusable mesh candidates from a Blender library without editing it."""
import json
from pathlib import Path
import sys
import bpy

args = sys.argv[sys.argv.index("--") + 1:]
source = Path(args[0])
output = Path(args[1])
with bpy.data.libraries.load(str(source), link=False) as (src, dst):
    names = list(src.objects)
    dst.objects = names
records = []
for name in names:
    obj = name if isinstance(name, bpy.types.Object) else bpy.data.objects.get(name)
    if obj and obj.type == "MESH":
        records.append({"name": obj.name, "dimensions_m": [round(x, 3) for x in obj.dimensions],
                        "faces": len(obj.data.polygons), "materials":
                        [m.name if m else None for m in obj.data.materials]})
output.write_text(json.dumps({"source": str(source), "meshes": records}, indent=2),
                  encoding="utf-8")
print("BLEND_LIBRARY", source, len(records), output)
