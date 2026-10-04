"""Read datablock names without loading large historical Blender scenes."""
import json
from pathlib import Path
import bpy

root=Path(r"D:\Blender\AssetsMazzarethTheGame")
files=("balcony_80s.blend","balconyAndRoof.blend","building_01.blend",
       "building_house_3.blend","building_house2.blend","CaseSoluzione.blend")
summary=[]
for filename in files:
    path=root/filename
    with bpy.data.libraries.load(str(path),link=False) as (source,unused):
        names=source.objects
        collections=source.collections
        materials=source.materials
        meshes=source.meshes
    filter_terms=("balcon","rail","roof","door","shutter","window","stair",
                  "coppi","tetto","ringh","porta","scala","cornic","facciat",
                  "wall","house","plant","vaso","gronda")
    relevant=[name for name in names if any(term in name.lower() for term in filter_terms)]
    summary.append({"file":filename,"objects":len(names),"meshes":len(meshes),
                    "materials":len(materials),"collections":collections[:24],
                    "matching_objects":relevant[:80]})
print("M80_LARGE_BLENDS",json.dumps(summary))
