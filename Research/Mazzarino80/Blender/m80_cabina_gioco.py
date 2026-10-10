"""The phone booth of the Da importare package (parte4/Cabina_Telefonica) made lighter for the game: its base mesh and
four condition variants have 91k triangles each (36 MB per skeletal mesh in Unreal). Each .blend of the package is
opened as it is (nothing saved back), a planar dissolve and a collapse are put before the rig in the modifier stack,
down to TARGET triangles, and the mesh is exported with the package's own FBX settings and rest pose, so the
skeleton and the four clips of the package still fit. Every part is a separate island bound rigidly to one bone, so
the collapse never mixes weights; checked before export.
Run: blender -b --factory-startup --python m80_cabina_gioco.py
Out: Saved/Mazzarino80/Cabina/exports/SK_Cabina_*.fbx (read by Scripts/m80_cabina_import.py)
"""
import json
import math
import os

import bpy

PKG = "D:/BlenderTest/Da importare/parte4/Cabina_Telefonica"
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(ROOT, "Saved", "Mazzarino80", "Cabina", "exports")
TARGET = 25000
BLENDS = {"SK_Cabina_Telefonica": "Cabina_Telefonica.blend",
          "SK_Cabina_01_Usurata": "variants/Cabina_01_Usurata.blend",
          "SK_Cabina_02_Rovinata": "variants/Cabina_02_Rovinata.blend",
          "SK_Cabina_03_Vetri_Spaccati": "variants/Cabina_03_Vetri_Spaccati.blend",
          "SK_Cabina_04_Fuori_Servizio": "variants/Cabina_04_Fuori_Servizio.blend"}


def triangles(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    rigid = sum(1 for v in me.vertices if len(v.groups) == 1 and abs(v.groups[0].weight - 1) < 1e-4) == len(me.vertices)
    ob.evaluated_get(dg).to_mesh_clear()
    return n, rigid


def build(name, blend):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(PKG, blend))
    ob = bpy.data.objects[name]
    arm = ob.parent
    rig = next(m for m in ob.modifiers if m.type == "ARMATURE")
    rig.show_viewport = False
    before, _ = triangles(ob)
    # Flat parts first (coplanar faces merged inside one material and UV island), then a collapse to the target.
    flat = ob.modifiers.new("Piani", "DECIMATE")
    flat.decimate_type = "DISSOLVE"
    flat.angle_limit = math.radians(2.0)
    flat.delimit = {"MATERIAL", "SEAM", "UV"}
    after_flat, _ = triangles(ob)
    if after_flat > TARGET:
        col = ob.modifiers.new("Riduzione", "DECIMATE")
        col.ratio = TARGET / float(after_flat)
        col.use_collapse_triangulate = True
    tri = ob.modifiers.new("Triangoli", "TRIANGULATE")
    tri.keep_custom_normals = True
    after, rigid = triangles(ob)
    if not rigid:
        raise RuntimeError("%s: weights no longer rigid" % name)
    # The rig back to the bottom of the stack and on, in the rest pose the package exports with.
    ob.modifiers.move(list(ob.modifiers).index(rig), len(ob.modifiers) - 1)
    rig.show_viewport = True
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    arm.pose.bones["indicator_green"].scale = (.001, .001, .001)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = ob
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), use_selection=True,
                             object_types={"MESH", "ARMATURE"}, global_scale=1, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_NONE", axis_forward="Y", axis_up="Z",
                             bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type="FACE",
                             add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
                             use_armature_deform_only=False, bake_anim=False, path_mode="AUTO", embed_textures=False)
    print("M80 cabina %s: %d -> %d (planar %d) triangles" % (name, before, after, after_flat))
    return {"before": before, "planar": after_flat, "after": after}


if __name__ == "__main__":
    report = {name: build(name, blend) for name, blend in BLENDS.items()}
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
