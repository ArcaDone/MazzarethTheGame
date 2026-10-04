from pathlib import Path
import math, json
import bpy
from mathutils import Matrix

source=Path(r"D:\Blender\AssetsMazzarethTheGame\balcony_80s.blend")
with bpy.data.libraries.load(str(source),link=False) as (library,loaded):
    loaded.objects=["Balcony2"]
obj=loaded.objects[0]
print("BALCONY_MATERIALS",[material.name if material else None for material in obj.data.materials])
transform=Matrix.Rotation(-math.pi/2,4,"X")
for material_index in sorted({face.material_index for face in obj.data.polygons}):
    indices={int(vi) for face in obj.data.polygons if face.material_index==material_index
             for vi in face.vertices}
    points=[transform @ obj.data.vertices[i].co for i in indices]
    low=[min(p[k] for p in points) for k in range(3)]
    high=[max(p[k] for p in points) for k in range(3)]
    print("BALCONY_REGION",json.dumps({"index":material_index,"vertices":len(indices),
          "faces":sum(face.material_index==material_index for face in obj.data.polygons),
          "low":low,"high":high,"size":[high[k]-low[k] for k in range(3)]}))
