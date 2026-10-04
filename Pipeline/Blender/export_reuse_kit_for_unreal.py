"""Export metre-scale reusable kit meshes and four assembled QA pilots.

The source .blend remains authoritative. Pilot exports are for street-scale
inspection only; PCG consumes the independent modules exported beside them.
"""
from pathlib import Path
import json
import re

import bpy
import bmesh
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export"
MODULES = OUT / "modules"
PILOTS = OUT / "pilots"
STAGES = OUT / "pilot_stages"
for directory in (MODULES, PILOTS, STAGES):
    directory.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
source_records = []
pilot_records = []
stage_records = []
cleaned_triangles = {}


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")


def export_objects(objects, destination, x_shift=0.0, keep_transform=True):
    copies = []
    for original in objects:
        duplicate = bpy.data.objects.new(original.name, original.data.copy())
        scene.collection.objects.link(duplicate)
        duplicate.matrix_world = original.matrix_world.copy() if keep_transform else Matrix.Identity(4)
        if keep_transform:
            duplicate.location.x -= x_shift
        duplicate.hide_render = False
        duplicate.hide_set(False)
        duplicate.data.calc_loop_triangles()
        bad = sum(1 for tri in duplicate.data.loop_triangles
                  if tri.area < 1e-10)
        if bad:
            bm = bmesh.new()
            bm.from_mesh(duplicate.data)
            bmesh.ops.triangulate(bm, faces=list(bm.faces))
            zero_faces = [face for face in bm.faces if face.calc_area() < 1e-10]
            bmesh.ops.delete(bm, geom=zero_faces, context="FACES")
            bm.to_mesh(duplicate.data)
            bm.free()
            duplicate.data.validate(clean_customdata=False)
            duplicate.data.update()
            cleaned_triangles[original.name] = len(zero_faces)
        copies.append(duplicate)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in copies:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.export_scene.fbx(
        filepath=str(destination), use_selection=True, object_types={"MESH"},
        apply_unit_scale=True, global_scale=1.0, axis_forward="-Y", axis_up="Z",
        use_mesh_modifiers=True, add_leaf_bones=False, path_mode="ABSOLUTE",
        embed_textures=False, bake_anim=False,
    )
    for duplicate in copies:
        bpy.data.objects.remove(duplicate, do_unlink=True)


for original in sorted(bpy.data.objects, key=lambda obj: obj.name):
    if original.type != "MESH" or "pcg_role" not in original:
        continue
    if original.name.startswith("STYLE_") or original.name.startswith("SOCKET_"):
        continue
    if any(col.name.startswith("QA_STYLE_") for col in original.users_collection):
        continue
    destination = MODULES / ("SM_M80_" + safe_name(original.name) + ".fbx")
    export_objects([original], destination, keep_transform=False)
    source_records.append({
        "name": original.name,
        "role": original.get("pcg_role"),
        "front_axis": original.get("front_axis", "-Y"),
        "file": str(destination),
        "dimensions_m": [round(v, 4) for v in original.dimensions],
        "materials": [material.name if material else None for material in original.data.materials],
    })

for index, (style, lot) in enumerate((
    ("STYLE_01", "1249069204"), ("STYLE_02", "1249068307"),
    ("STYLE_03", "1249069200"), ("STYLE_04", "1249069228"),
)):
    collection = bpy.data.collections[f"QA_{style}_{lot}"]
    objects = [obj for obj in collection.objects
               if obj.type == "MESH" and obj.name.startswith(style + "_") and not obj.hide_render]
    if not objects:
        raise RuntimeError("Pilot is empty: " + style)
    destination = PILOTS / f"SM_M80_QA_{style}_{lot}.fbx"
    export_objects(objects, destination, x_shift=index * 13.0)
    pilot_records.append({"style": style, "lot": lot, "file": str(destination),
                          "object_count": len(objects), "qa_only": True})

    def stage_for(obj):
        role = obj.get("pcg_role", "")
        if role in {"structure", "courtyard_wall", "courtyard_floor"}:
            return "Structure"
        if role.startswith("facade") or role in {"wall_wear", "pilaster"}:
            return "Facades"
        if role in {"opening", "opening_repair", "garage_roller_shutter"}:
            return "Openings"
        if role.startswith("roof"):
            return "Roofs"
        return "Details"

    for stage in ("Structure", "Facades", "Openings", "Roofs", "Details"):
        members = [obj for obj in objects if stage_for(obj) == stage]
        if not members:
            continue
        stage_file = STAGES / f"SM_M80_QA_{style}_{lot}_{stage}.fbx"
        export_objects(members, stage_file, x_shift=index * 13.0)
        stage_records.append({"style": style, "lot": lot, "stage": stage,
                              "file": str(stage_file), "object_count": len(members),
                              "qa_only": True})

manifest = {"source_blend": str(SOURCE), "metres_to_centimetres": 100,
            "degenerate_triangles_removed_on_export": cleaned_triangles,
            "modules": source_records, "pilots": pilot_records,
            "pilot_stages": stage_records}
(OUT / "export_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("M80_UNREAL_EXPORT", len(source_records), "modules", len(pilot_records),
      "pilots", len(stage_records), "stages", OUT)
