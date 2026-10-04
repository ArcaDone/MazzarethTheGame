"""Curate a portable Blender 4.3 asset library from existing Mazzarino work.

Run: blender --background --factory-startup --python build_reuse_kit_v1.py
Original files in D:\Blender are read-only inputs.
"""
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = Path(r"D:\Blender\AssetsMazzarethTheGame")
DIORAMA = Path(r"D:\Blender\DioramaAssets")
OUT = Path(__file__).resolve().parent / "output" / "mazzarino_reuse_kit_v1"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "B80": (SOURCE / "balcony_80s.blend", [
        ("Ground.000", "facade_ground", "old_stone"),
        ("Ground.001", "facade_ground", "old_stone"),
        ("Ground.002", "facade_ground", "old_stone"),
        ("Ground.003", "facade_ground", "old_stone"),
        ("Ground.005", "facade_ground", "old_stone"),
        ("Ground.006", "facade_ground", "old_stone"),
        ("Ground.007", "facade_ground", "old_stone"),
        ("Ground.008", "facade_ground", "old_stone"),
        ("Ground.009", "facade_ground", "old_stone"),
        ("Ground.010", "facade_ground", "old_stone"),
        ("Ground.011", "facade_ground", "old_stone"),
        ("Ground.012", "facade_ground", "old_stone"),
        ("Ground.013", "facade_ground", "old_stone"),
        ("Ground.015", "facade_ground", "old_stone"),
        ("wall_000.001", "facade_upper", "old_stone"),
        ("wall_000.002", "facade_upper", "old_stone"),
        ("wall_001", "facade_upper", "old_stone"),
        ("wall_003", "facade_upper", "old_stone"),
        ("wall_007", "facade_upper", "old_stone"),
        ("ground_floor_pillar", "corner", "old_stone"),
        ("middle_floor_pillar", "corner", "old_stone"),
        ("Porta4", "door", "old_stone"),
        ("Porta6", "door", "old_stone"),
        ("Tetto", "roof", "old_stone"),
        ("tegole", "roof", "old_stone"),
        ("trimm", "roof_trim", "old_stone"),
        ("lampione2", "detail", "shared"),
        ("small_chimney_round", "chimney", "shared"),
        ("small_chimney_pointy", "chimney", "shared"),
        ("antenna", "roof_detail", "style03"),
    ]),
    "CS": (SOURCE / "CaseSoluzione.blend", [
        ("wall_001", "facade_upper_candidate", "old_stone"),
        ("wall_002", "facade_upper_candidate", "old_stone"),
        ("wall_003", "facade_upper_candidate", "old_stone"),
        ("wall_004", "facade_upper_candidate", "old_stone"),
        ("wall_005", "facade_upper_candidate", "old_stone"),
        ("wall_006", "facade_upper_candidate", "old_stone"),
        ("wall_007", "facade_upper_candidate", "old_stone"),
        ("wall_010", "facade_upper_candidate", "old_stone"),
        ("wall_011", "facade_upper_candidate", "old_stone"),
        ("wall_012", "facade_upper_candidate", "old_stone"),
        ("wall_013", "facade_upper_candidate", "old_stone"),
    ]),
    "EVY": (SOURCE / "case_evy.blend", [
        ("Ivy_Instance_1_old", "ivy_cluster", "shared"),
        ("Ivy_Instance_2_old", "ivy_cluster", "shared"),
    ]),
    "PILOT": (PROJECT / "Pipeline/Blender/output/style03_reference_v4/Mazzarino_STYLE_03_Reference_Gate_v4.blend", [
        ("KIT_Balcony_StoneAndIron_350", "balcony", "shared"),
    ]),
    "FENCE": (DIORAMA / "assets/models/cast_iron_fence_45f70b96-c031-4860-8109-500ed9a48870/cast_iron_fence_2614fda1-c7bf-406b-a3b1-61a8c278d33f.blend", [
        ("Cast Iron Fence 09", "gate_candidate", "shared"),
    ]),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1800
scene.render.resolution_y = 1300
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"

collections = {}
for key, label in [
    ("facade_ground", "01_Facade_Ground_3m"),
    ("facade_upper", "02_Facade_Upper_3m"),
    ("facade_upper_candidate", "03_CaseSoluzione_Upper_ScaleCandidates"),
    ("door", "04_Doors"), ("balcony", "05_Balconies"),
    ("door_scan_candidate", "04b_Historic_Door_Candidate"),
    ("roof", "06_Roofs"), ("roof_trim", "07_Roof_Trims"),
    ("corner", "08_Corners"), ("chimney", "09_Chimneys"),
    ("ivy_cluster", "10_Ivy_Lightweight"),
    ("ivy_wall", "10b_Ivy_Wall_Variants"), ("detail", "11_Details"),
    ("roof_detail", "12_Roof_Details"),
    ("gate_candidate", "13_Gate_Candidates"),
    ("potted_plant", "14_Potted_Plants"),
]:
    col = bpy.data.collections.new(label)
    scene.collection.children.link(col)
    collections[key] = col

manifest = []
missing_source_objects = []

def repair_image_nodes(obj):
    """Disable missing roughness maps; never leave a pink/broken file texture."""
    repaired = []
    for mat in obj.data.materials:
        if not mat or not mat.use_nodes:
            continue
        for node in list(mat.node_tree.nodes):
            if node.type != "TEX_IMAGE" or not node.image:
                continue
            image = node.image
            path = bpy.path.abspath(image.filepath, library=image.library)
            if image.packed_file or os.path.isfile(path):
                continue
            if not any(output.links for output in node.outputs):
                # Legacy source files carry unconnected placeholder image nodes.
                mat.node_tree.nodes.remove(node)
                repaired.append("removed_unused:" + image.name)
                continue
            # A few source materials reference a lost pillar roughness JPEG.
            # The module already has texture detail in its base/normal channels.
            # Use a conservative matte roughness until the UE master material exists.
            if image.name.lower().startswith("pillar_000_r"):
                value = mat.node_tree.nodes.new("ShaderNodeValue")
                value.name = "M80_Missing_Roughness_Matte_Fallback"
                value.outputs[0].default_value = 0.86
                for link in list(node.outputs["Color"].links):
                    mat.node_tree.links.new(value.outputs[0], link.to_socket)
                repaired.append(image.name)
            else:
                repaired.append("UNRESOLVED:" + image.name)
    return sorted(set(repaired))

def evaluated_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    try:
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True,
                                              depsgraph=depsgraph)
    except Exception:
        mesh = obj.data.copy()
    if not mesh or not mesh.vertices:
        return None
    mesh.transform(obj.matrix_world.to_3x3().to_4x4())
    return mesh

for prefix, (path, requests) in SOURCES.items():
    names = [name for name, _role, _family in requests]
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [name for name in names if name in src.objects]
    loaded = {obj.name: obj for obj in dst.objects if obj}
    for source_name, role, family in requests:
        source_obj = loaded.get(source_name)
        if not source_obj or source_obj.type != "MESH":
            missing_source_objects.append(prefix + ":" + source_name)
            continue
        # Appended objects have a stale identity matrix_world until linked to a
        # scene. This matters for rotated CaseSoluzione tiles and roof geometry.
        scene.collection.objects.link(source_obj)
        bpy.context.view_layer.update()
        mesh = evaluated_mesh(source_obj)
        if not mesh:
            missing_source_objects.append(prefix + ":" + source_name + ":empty")
            continue
        verts = mesh.vertices
        lo = Vector(tuple(min(v.co[i] for v in verts) for i in range(3)))
        hi = Vector(tuple(max(v.co[i] for v in verts) for i in range(3)))
        source_size = hi - lo
        # CaseSoluzione source tiles are 1m units, unlike the 3m balcony_80s
        # variant. Keep this as a flagged candidate until visual scale QA.
        # The earlier pilot script used centimetres as raw Blender units.
        # Convert that balcony once into this metre-scale reusable library.
        factor = 3.0 if prefix == "CS" else (0.01 if prefix == "PILOT" else 1.0)
        center_x = (lo.x + hi.x) * 0.5
        rear_y = hi.y
        bottom_z = lo.z
        for v in verts:
            v.co = (v.co - Vector((center_x, rear_y, bottom_z))) * factor
        mesh.update()
        obj = bpy.data.objects.new(prefix + "__" + source_name, mesh)
        collections[role].objects.link(obj)
        obj["pcg_role"] = role
        obj["style_family"] = family
        obj["source_file"] = str(path)
        obj["source_object"] = source_name
        obj["front_axis"] = "-Y"
        obj["pivot_rule"] = "bottom-center at rear wall plane"
        obj["source_scale_factor"] = factor
        obj["pcg_status"] = "scale_candidate" if prefix == "CS" else "curated"
        obj["attach_socket"] = "wall" if role in {"balcony", "ivy_cluster", "door"} else "lot"
        fixes = repair_image_nodes(obj)
        obj["material_fixes"] = ", ".join(fixes)
        # Place the assets as a browseable contact sheet in the .blend file.
        if role == "facade_ground":
            index = sum(x["role"] == role for x in manifest)
            obj.location = ((index % 7) * 3.6, 0.0, -(index // 7) * 3.7)
        elif role in {"facade_upper", "facade_upper_candidate"}:
            index = sum(x["role"] in {"facade_upper", "facade_upper_candidate"} for x in manifest)
            obj.location = ((index % 7) * 3.6, 0.0, 8.0 - (index // 7) * 3.7)
        else:
            index = sum(x["role"] not in {"facade_ground", "facade_upper", "facade_upper_candidate"} for x in manifest)
            obj.location = ((index % 7) * 4.0, 7.0, -7.5 - (index // 7) * 4.0)
        manifest.append({
            "name": obj.name, "source": str(path), "source_object": source_name,
            "role": role, "style_family": family, "faces": len(mesh.polygons),
            "dimensions_m": [round(x * factor, 4) for x in source_size],
            "material_names": [m.name if m else None for m in mesh.materials],
            "material_fixes": fixes, "pcg_status": obj["pcg_status"],
            "front_axis": "-Y", "pivot": "bottom-center / rear wall plane",
        })
    # Keep only objects in the curated scene, not unlinked source datablocks.
    for source_obj in loaded.values():
        if source_obj and source_obj.name in bpy.data.objects:
            bpy.data.objects.remove(source_obj, do_unlink=True)

def merge_small_prefab(path, source_names, name, role, family):
    """Combine source objects while preserving their authored relative layout."""
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [item for item in source_names if item in src.objects]
    temporary = []
    for source_obj in dst.objects:
        if not source_obj or source_obj.type != "MESH":
            continue
        scene.collection.objects.link(source_obj)
        bpy.context.view_layer.update()
        mesh = evaluated_mesh(source_obj)
        if not mesh:
            continue
        # The evaluated source vertices include orientation/scale but not the
        # source translation; use it here to retain assembly alignment.
        for vert in mesh.vertices:
            vert.co += source_obj.matrix_world.translation
        part = bpy.data.objects.new("TEMP_" + source_obj.name, mesh)
        scene.collection.objects.link(part)
        temporary.append(part)
    if not temporary:
        return
    bpy.ops.object.select_all(action="DESELECT")
    for part in temporary:
        part.select_set(True)
    bpy.context.view_layer.objects.active = temporary[0]
    bpy.ops.object.join()
    obj = temporary[0]
    obj.name = name
    lo = Vector(tuple(min(v.co[i] for v in obj.data.vertices) for i in range(3)))
    hi = Vector(tuple(max(v.co[i] for v in obj.data.vertices) for i in range(3)))
    for vert in obj.data.vertices:
        vert.co -= Vector(((lo.x + hi.x) * 0.5, hi.y, lo.z))
    obj.data.update()
    scene.collection.objects.unlink(obj)
    collections[role].objects.link(obj)
    for source_obj in dst.objects:
        if source_obj and source_obj.name in bpy.data.objects:
            bpy.data.objects.remove(source_obj, do_unlink=True)
    obj["pcg_role"] = role
    obj["style_family"] = family
    obj["source_file"] = str(path)
    obj["source_object"] = ", ".join(source_names)
    obj["front_axis"] = "-Y"
    obj["pivot_rule"] = "bottom-center at rear plane"
    obj["pcg_status"] = "curated" if role == "potted_plant" else "visual_candidate"
    obj.location = (0.0 if role == "potted_plant" else 10.0, 7.0, -24.0)
    fixes = repair_image_nodes(obj)
    manifest.append({"name": name, "source": str(path),
                     "source_object": list(source_names), "role": role,
                     "style_family": family, "faces": len(obj.data.polygons),
                     "dimensions_m": [round(v, 4) for v in (hi - lo)],
                     "material_names": [m.name if m else None for m in obj.data.materials],
                     "material_fixes": fixes, "pcg_status": obj["pcg_status"],
                     "front_axis": "-Y", "pivot": "bottom-center / rear plane"})

merge_small_prefab(
    DIORAMA / "assets/models/plant_pot_big_b6a53708-55d4-4a1c-961e-deedec48715a/plant_pot_big_b55462e8-62e8-4ae8-b5cc-8faa74de4885.blend",
    ("Pot._big", "Plant_2.002", "Plant_2.003", "Soil_big"),
    "PROP__PottedPlant_Small_01", "potted_plant", "shared")
merge_small_prefab(
    SOURCE / "TestBuildingParts/assets/models/old-italian-fron_f6331acb-c598-4b5e-8a90-816d4dc9187c/old-italian-front-door_2K_3fbca813-2f73-4241-bb27-0c35a116eb01.blend",
    ("Doors", "iron grate", "mounts", "columns", "central stone",
     "door damper", "threshold", "door frame"),
    "DOOR__OldItalian_Front_01", "door_scan_candidate", "old_stone")

# Repair the visibly white roof tiles using the established aged terracotta
# from the prior Blender pilot. This is also the seed for the future UE master.
pilot_path = SOURCES["PILOT"][0]
with bpy.data.libraries.load(str(pilot_path), link=False) as (src, dst):
    dst.materials = [name for name in ("M80_terracotta", "M80_glass")
                     if name in src.materials]
terracotta = bpy.data.materials["M80_terracotta"]
glass_dark = bpy.data.materials["M80_glass"]
# Retain the hand-painted tile texture while muting the uniform orange cast.
roof_nodes = terracotta.node_tree.nodes
roof_links = terracotta.node_tree.links
roof_image = next(node for node in roof_nodes if node.type == "TEX_IMAGE")
roof_group = next(node for node in roof_nodes if node.type == "GROUP")
hue = roof_nodes.new("ShaderNodeHueSaturation")
hue.name = "M80_Aged_Terracotta_Color"
hue.inputs["Saturation"].default_value = 0.78
hue.inputs["Value"].default_value = 0.78
roof_links.new(roof_image.outputs["Color"], hue.inputs["Color"])
roof_links.new(hue.outputs["Color"], roof_group.inputs["Base Color"])

for row in manifest:
    obj = bpy.data.objects[row["name"]]
    changed = False
    for index, material in enumerate(obj.data.materials):
        if material and "glass" in material.name.lower():
            obj.data.materials[index] = glass_dark
            changed = True
    if changed:
        row["material_fixes"].append("dark_window_glass")
        row["material_names"] = [mat.name if mat else None for mat in obj.data.materials]
for row in manifest:
    if row["role"] not in {"roof", "roof_trim"}:
        continue
    obj = bpy.data.objects[row["name"]]
    for index, material in enumerate(obj.data.materials):
        if material and material.name.lower().startswith("tegole"):
            obj.data.materials[index] = terracotta
            row["material_fixes"].append("aged_terracotta_roof")
    row["material_names"] = [mat.name if mat else None for mat in obj.data.materials]

pot = bpy.data.objects.get("PROP__PottedPlant_Small_01")
if pot:
    for index, material in enumerate(pot.data.materials):
        if material and material.name == "Hammered_Metal_Gold":
            pot.data.materials[index] = terracotta
            break
    pot_row = next(item for item in manifest if item["name"] == pot.name)
    pot_row["material_fixes"].append("terracotta_pot")
    pot_row["material_names"] = [m.name if m else None for m in pot.data.materials]

# A gate is useful at low density around a few courtyards. Keep the authored
# original and a decimated comparison for performance review in Unreal.
gate = bpy.data.objects.get("FENCE__Cast Iron Fence 09")
if gate:
    light = bpy.data.objects.new(gate.name + "_LOD1", gate.data.copy())
    collections["gate_candidate"].objects.link(light)
    light.location = gate.location + Vector((4.0, 0.0, 0.0))
    for key in gate.keys():
        light[key] = gate[key]
    light["pcg_status"] = "lod_candidate"
    decimate = light.modifiers.new("M80_Gate_LOD1", "DECIMATE")
    decimate.ratio = 0.20
    bpy.ops.object.select_all(action="DESELECT")
    light.select_set(True)
    bpy.context.view_layer.objects.active = light
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    gate_row = next(item for item in manifest if item["name"] == gate.name)
    manifest.append({**gate_row, "name": light.name, "faces": len(light.data.polygons),
                     "pcg_status": "lod_candidate"})

# The source ivy clusters lie horizontally on roofs. Create proper wall-plane
# variants from the same lightweight geometry, facing -Y for facade sockets.
for row in list(manifest):
    if row["role"] != "ivy_cluster":
        continue
    original = bpy.data.objects[row["name"]]
    mesh = original.data.copy()
    mesh.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    lo = Vector(tuple(min(v.co[i] for v in mesh.vertices) for i in range(3)))
    hi = Vector(tuple(max(v.co[i] for v in mesh.vertices) for i in range(3)))
    offset = Vector(((lo.x + hi.x) * 0.5, hi.y, lo.z))
    for vert in mesh.vertices:
        vert.co -= offset
    mesh.update()
    obj = bpy.data.objects.new(original.name + "_WALL", mesh)
    collections["ivy_wall"].objects.link(obj)
    for key in original.keys():
        obj[key] = original[key]
    obj["pcg_role"] = "ivy_wall"
    obj["front_axis"] = "-Y"
    obj["attach_socket"] = "wall"
    obj["pivot_rule"] = "bottom-center at rear wall plane"
    index = sum(x["role"] == "ivy_wall" for x in manifest)
    obj.location = (index * 1.2, 7.0, -20.0)
    size = hi - lo
    manifest.append({**row, "name": obj.name, "role": "ivy_wall",
                     "dimensions_m": [round(v, 4) for v in size],
                     "pivot": "bottom-center / rear wall plane",
                     "pcg_status": "curated_wall_variant"})

# Pack all images actually used by curated material nodes. Unused missing source
# images may remain in bpy.data but cannot affect the curated kit.
used_images = set()
for row in manifest:
    obj = bpy.data.objects[row["name"]]
    for material in obj.data.materials:
        if not material or not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image and any(out.links for out in node.outputs):
                used_images.add(node.image)
unresolved = []
for image in used_images:
    if image.packed_file:
        continue
    path = bpy.path.abspath(image.filepath, library=image.library)
    if os.path.isfile(path):
        try:
            image.pack()
        except Exception as exc:
            unresolved.append(image.name + ":" + str(exc))
    else:
        # Lost roughness is disconnected by repair_image_nodes; safe to retain
        # as an unused source image datablock, but log it for clean UE mapping.
        unresolved.append(image.name)

scene.render.filepath = str(OUT / "Mazzarino_Reuse_Kit_v1_preview.png")
blend_path = OUT / "Mazzarino_Reuse_Kit_v1.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
summary = {
    "blender": bpy.app.version_string, "source_files": [str(x[0]) for x in SOURCES.values()],
    "blend_file": str(blend_path), "count": len(manifest),
    "faces_total": sum(row["faces"] for row in manifest),
    "missing_source_objects": missing_source_objects,
    "unresolved_image_names": sorted(set(unresolved)),
    "objects": manifest,
}
(OUT / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("M80_KIT_SUMMARY", json.dumps({key: summary[key] for key in
                                    ["count", "faces_total", "missing_source_objects",
                                     "unresolved_image_names"]}))
