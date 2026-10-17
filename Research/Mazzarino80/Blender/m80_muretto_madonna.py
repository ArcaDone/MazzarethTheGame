"""Blender 4.3: the Madonna's railing (object MurettoMadonna in D:/Mazzarino80_Sorgenti/Edifici/Madonna/Madonna.blend: a stone
post with a vase-shaped cap and three iron rails with a middle bar, 3.5 m, made to stand on top of a wall) as two
pieces the walls of AM80Stairs repeat along their spline (fence kind "Ringhiera della Madonna"):
- MurettoMadonna_Pilastrino: the stone post (material MainMaterial), pivot at its plan centre, bottom.
- MurettoMadonna_Ringhiera: the rails (Metal.001), pivot at the post's plan centre and bottom, so one bay of rails runs
  along +X from a post to the next one, SPAN cm further (stretched in X for other spacings).
Two stray vertices 3 m under the railing (z 1.5) are dropped. Export in cm, X along the railing, Y across.
Run: blender -b Madonna.blend --factory-startup --python m80_muretto_madonna.py -- <out_dir>
Out: <out_dir>/MurettoMadonna_Pilastrino.fbx, MurettoMadonna_Ringhiera.fbx, MurettoMadonna.json
"""
import json
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
src = bpy.data.objects["MurettoMadonna"]
for o in list(bpy.data.objects):
    if o is not src:
        bpy.data.objects.remove(o, do_unlink=True)

# World-space copy without the stray vertices.
me = src.data.copy()
me.transform(src.matrix_world)
bm = bmesh.new()
bm.from_mesh(me)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < 4.0], context="VERTS")
bm.to_mesh(me)
bm.free()
mats = [s.material for s in src.material_slots]
stone = next(i for i, m in enumerate(mats) if m and m.name == "MainMaterial")


def part(name, keep_index):
    m = me.copy()
    bm = bmesh.new()
    bm.from_mesh(m)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if (f.material_index == stone) != keep_index], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(m)
    bm.free()
    o = bpy.data.objects.new(name, m)
    bpy.context.scene.collection.objects.link(o)
    return o


post = part("MurettoMadonna_Pilastrino", True)
rails = part("MurettoMadonna_Ringhiera", False)


def box(o):
    pts = [v.co for v in o.data.vertices]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


plo, phi = box(post)
rlo, rhi = box(rails)
centre = Vector(((plo.x + phi.x) / 2, (plo.y + phi.y) / 2, plo.z))
post_w = phi.x - plo.x
# The rails end against the next post's face: posts SPAN apart centre to centre.
span = (rhi.x - centre.x) + post_w / 2
for o in (post, rails):
    o.data.transform(Matrix.Translation(-centre))
    o.data.transform(Matrix.Scale(100.0, 4))
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 0.01
for o in (post, rails):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, o.name + ".fbx"), use_selection=True, object_types={"MESH"},
                             axis_forward="-Y", axis_up="Z", apply_unit_scale=True, mesh_smooth_type="FACE", bake_anim=False,
                             path_mode="STRIP")
info = {"span_cm": round(span * 100, 1), "post_width_cm": round(post_w * 100, 1), "post_depth_cm": round((phi.y - plo.y) * 100, 1),
        "post_height_cm": round((phi.z - plo.z) * 100, 1), "rails_top_cm": round((rhi.z - centre.z) * 100, 1),
        "rails_bottom_cm": round((rlo.z - centre.z) * 100, 1),
        "triangles": {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in (post, rails)},
        "materials": {o.name: sorted({o.data.materials[p.material_index].name for p in o.data.polygons}) for o in (post, rails)}}
with open(os.path.join(OUT, "MurettoMadonna.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, indent=1)
print("M80", json.dumps(info))
