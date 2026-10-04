"""Build four metre-scale, modular visual gates from the curated Blender kit.

These are review assemblies. They are deliberately kept out of Unreal until
the four exterior styles pass a street-level comparison with the art reference.
"""
from pathlib import Path
import json
import math
import random

import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "Pipeline/Blender/output/mazzarino_reuse_kit_v1/Mazzarino_Reuse_Kit_v1.blend"
STYLE = ROOT / "Pipeline/Blender/output/style_showroom_v1/Mazzarino_4_Stili_Showroom.blend"
HOUSE3 = Path(r"D:\Blender\AssetsMazzarethTheGame\building_house_3.blend")
CLOTHES = ROOT / "Pipeline/Unreal/comune_geometry_review"
OUT = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(KIT), load_ui=False)
scene = bpy.context.scene
for obj in bpy.data.objects:
    if "pcg_role" in obj:
        obj.hide_render = True

with bpy.data.libraries.load(str(STYLE), link=False) as (src, dst):
    dst.materials = [name for name in
                     ("M80_stone_wall", "M80_stone_formal", "M80_plaster", "M80_wood", "M80_iron")
                     if name in src.materials]

stone = bpy.data.materials["M80_stone_wall"]
formal = bpy.data.materials["M80_stone_formal"]
plaster = bpy.data.materials["M80_plaster"]
iron = bpy.data.materials["M80_iron"]
wood = bpy.data.materials["M80_wood"]
glass = bpy.data.materials["M80_glass"]
pipe_metal = bpy.data.materials.new("M80_Pipe_Rust_Dark_Shared")
pipe_metal.diffuse_color = (.22, .15, .11, 1)
pipe_metal.use_nodes = True
pipe_bsdf = pipe_metal.node_tree.nodes.get("Principled BSDF")
pipe_bsdf.inputs["Base Color"].default_value = (.22, .15, .11, 1)
pipe_bsdf.inputs["Metallic"].default_value = .25
pipe_bsdf.inputs["Roughness"].default_value = .83

paving_mat = bpy.data.materials.new("M80_Court_Paving_Stone_Shared")
paving_mat.use_nodes = True
paving_nodes = paving_mat.node_tree.nodes
paving_links = paving_mat.node_tree.links
paving_bsdf = paving_nodes.get("Principled BSDF")
paving_bsdf.inputs["Metallic"].default_value = 0
paving_bsdf.inputs["Roughness"].default_value = .93
paving_noise = paving_nodes.new("ShaderNodeTexNoise")
paving_noise.inputs["Scale"].default_value = 5.2
paving_noise.inputs["Detail"].default_value = 3.0
paving_noise.inputs["Roughness"].default_value = .72
paving_ramp = paving_nodes.new("ShaderNodeValToRGB")
paving_ramp.color_ramp.elements[0].position = .25
paving_ramp.color_ramp.elements[0].color = (.26, .225, .17, 1)
paving_ramp.color_ramp.elements[1].position = .78
paving_ramp.color_ramp.elements[1].color = (.58, .50, .38, 1)
paving_links.new(paving_noise.outputs["Fac"], paving_ramp.inputs["Fac"])
paving_links.new(paving_ramp.outputs["Color"], paving_bsdf.inputs["Base Color"])
paving_bump = paving_nodes.new("ShaderNodeBump")
paving_bump.inputs["Strength"].default_value = .11
paving_bump.inputs["Distance"].default_value = .018
paving_links.new(paving_noise.outputs["Fac"], paving_bump.inputs["Height"])
paving_links.new(paving_bump.outputs["Normal"], paving_bsdf.inputs["Normal"])

shutter_mat = bpy.data.materials.new("M80_Roller_Shutter_70s_Shared")
shutter_mat.use_nodes = True
shutter_bsdf = shutter_mat.node_tree.nodes.get("Principled BSDF")
shutter_bsdf.inputs["Base Color"].default_value = (.22, .21, .19, 1)
shutter_bsdf.inputs["Metallic"].default_value = .38
shutter_bsdf.inputs["Roughness"].default_value = .88
shutter_noise = shutter_mat.node_tree.nodes.new("ShaderNodeTexNoise")
shutter_noise.inputs["Scale"].default_value = 6.5
shutter_noise.inputs["Detail"].default_value = 2.0
shutter_ramp = shutter_mat.node_tree.nodes.new("ShaderNodeValToRGB")
shutter_ramp.color_ramp.elements[0].color = (.12, .12, .11, 1)
shutter_ramp.color_ramp.elements[1].color = (.30, .25, .20, 1)
shutter_mat.node_tree.links.new(shutter_noise.outputs["Fac"], shutter_ramp.inputs["Fac"])
shutter_mat.node_tree.links.new(shutter_ramp.outputs["Color"], shutter_bsdf.inputs["Base Color"])

def cloth_material(name, dark, light):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Metallic"].default_value = 0
    bsdf.inputs["Roughness"].default_value = .94
    noise = mat.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 4.2
    noise.inputs["Detail"].default_value = 2.0
    ramp = mat.node_tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    mat.node_tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    mat.node_tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat

cloth_blue = cloth_material("M80_Cloth_Faded_Blue_Shared", (.085, .15, .19), (.22, .32, .36))
cloth_ochre = cloth_material("M80_Cloth_Faded_Ochre_Shared", (.27, .15, .09), (.51, .33, .20))

def load_cloth_fbx(filename, lod_name, module_name, material):
    existing = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(CLOTHES / filename))
    imported = [obj for obj in bpy.data.objects if obj not in existing]
    source = next(obj for obj in imported if obj.name == lod_name)
    mesh = source.data.copy()
    mesh.transform(source.matrix_world)
    mins = [min(v.co[i] for v in mesh.vertices) for i in range(3)]
    maxs = [max(v.co[i] for v in mesh.vertices) for i in range(3)]
    mesh.transform(Matrix.Translation((-(mins[0]+maxs[0])/2,
                                       -(mins[1]+maxs[1])/2, -maxs[2])))
    mesh.materials.clear()
    mesh.materials.append(material)
    module = bpy.data.objects.new(module_name, mesh)
    scene.collection.objects.link(module)
    module.hide_render = True
    module["pcg_role"] = "laundry_garment"
    module["source_fbx"] = filename
    module["front_axis"] = "-Y"
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    return module

load_cloth_fbx("clothes_favela__SM_Clothes_01.fbx", "SM_Clothes_01_LOD1",
               "CLOTH__Favela_01_LOD1", cloth_ochre)
load_cloth_fbx("clothes_middleeast__SM_clothes_B_02.fbx", "SM_clothes_B_02",
               "CLOTH__MiddleEast_DrapedSheet_02", cloth_blue)

# This modernised 1970s window is a genuinely different reusable 3 m bay from
# the user's building_house_3 library. Its source transform is baked into an
# independent mesh; the library file remains untouched.
with bpy.data.libraries.load(str(HOUSE3), link=False) as (src, dst):
    dst.objects = ["middle_floor_wall_03"]
modern_source = dst.objects[0]
modern_mesh = modern_source.data.copy()
modern_mesh.transform(modern_source.matrix_world)
min_corner = [min(v.co[i] for v in modern_mesh.vertices) for i in range(3)]
max_corner = [max(v.co[i] for v in modern_mesh.vertices) for i in range(3)]
modern_mesh.transform(Matrix.Translation((-(min_corner[0] + max_corner[0]) / 2,
                                          -max_corner[1], -min_corner[2])))
modern_module = bpy.data.objects.new("SRC03__ModernisedWindow_300", modern_mesh)
scene.collection.objects.link(modern_module)
modern_module.hide_render = True
modern_module["pcg_role"] = "facade_upper_candidate"
modern_module["front_axis"] = "-Y"
bpy.data.objects.remove(modern_source, do_unlink=True)
for wall_finish in (stone, formal, plaster):
    for node in wall_finish.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.extension = "REPEAT"

# Rebuild the wall UVs on the actual mesh. A shader-only box projection would
# look correct in Blender but would not survive FBX/Unreal import. Face-normal
# projection also maps the narrow returns and top caps without stretching.
def project_surface_uv(mesh, material_indices, tile_m=3.0):
    uv_layer = next((layer for layer in mesh.uv_layers if layer.active_render), None)
    if uv_layer is None:
        uv_layer = mesh.uv_layers.active or mesh.uv_layers.new(name="M80_Wall_UV")
    mesh.uv_layers.active_index = list(mesh.uv_layers).index(uv_layer)
    mins = [min(v.co[i] for v in mesh.vertices) for i in range(3)]
    for face in mesh.polygons:
        if face.material_index not in material_indices:
            continue
        n = face.normal
        face_coords = [mesh.vertices[index].co for index in face.vertices]
        face_span_x = max(co.x for co in face_coords) - min(co.x for co in face_coords)
        face_span_y = max(co.y for co in face_coords) - min(co.y for co in face_coords)
        # Choose the broad horizontal direction of this face. Whole-object
        # bounds stretch narrow wall returns and gable end faces into stripes.
        horizontal = 0 if face_span_x >= face_span_y else 1
        for loop_index in face.loop_indices:
            co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            if abs(n.z) > .75:
                u, v = co.x - mins[0], co.y - mins[1]
            else:
                u, v = co[horizontal] - mins[horizontal], co.z - mins[2]
            uv_layer.data[loop_index].uv = (u / tile_m, v / tile_m)
    mesh.update()


def repair_collapsed_uv(mesh, tile_m=1.0):
    """Give only zero-area textured islands a planar UV in mesh coordinates."""
    uv_layer = next((layer for layer in mesh.uv_layers if layer.active_render), None)
    if uv_layer is None:
        return
    mins = [min(v.co[i] for v in mesh.vertices) for i in range(3)]
    textured = {i for i, mat in enumerate(mesh.materials)
                if mat and mat.use_nodes and any(n.type == "TEX_IMAGE" for n in mat.node_tree.nodes)}
    for face in mesh.polygons:
        if face.material_index not in textured or face.area < .001:
            continue
        coords = [uv_layer.data[i].uv for i in face.loop_indices]
        area = abs(sum(coords[i].x * coords[(i + 1) % len(coords)].y -
                       coords[(i + 1) % len(coords)].x * coords[i].y
                       for i in range(len(coords)))) * .5
        if area >= 1e-8:
            continue
        vertices = [mesh.vertices[i].co for i in face.vertices]
        def projection_area(a, b):
            return abs(sum(vertices[i][a] * vertices[(i + 1) % len(vertices)][b] -
                           vertices[(i + 1) % len(vertices)][a] * vertices[i][b]
                           for i in range(len(vertices)))) * .5
        axes = max(((0, 1), (0, 2), (1, 2)), key=lambda pair: projection_area(*pair))
        for loop_index in face.loop_indices:
            co = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            uv_layer.data[loop_index].uv = ((co[axes[0]] - mins[axes[0]]) / tile_m,
                                            (co[axes[1]] - mins[axes[1]]) / tile_m)
    mesh.update()

STYLES = [
    ("STYLE_01", "1249069204", 2, stone, "gable"),
    ("STYLE_02", "1249068307", 2, formal, "terrace"),
    ("STYLE_03", "1249069200", 2, plaster, "terrace"),
    ("STYLE_04", "1249069228", 2, stone, "damaged_gable"),
]
LOT_FLOOR_HEIGHT_CM = {"1249069204": 294, "1249068307": 306,
                       "1249069200": 270, "1249069228": 294}

collections = {}
records = []


def clone(source, name, col, xyz, angle=0.0, wall_mat=None, scale=(1, 1, 1), role=None):
    original = bpy.data.objects[source]
    # Mesh copy only where a style changes the wall finish. Remaining geometry
    # shares its mesh and PBR slots across the four examples.
    mesh = original.data.copy() if wall_mat else original.data
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.location = xyz
    obj.rotation_euler[2] = math.radians(angle)
    obj.scale = scale
    obj["source_module"] = source
    obj["pcg_role"] = role or original.get("pcg_role", "detail")
    obj["front_axis"] = "-Y"
    if wall_mat:
        replaced_indices = set()
        for i, mat in enumerate(mesh.materials):
            if mat and (mat.name.lower().startswith("house_wall") or
                        mat.name.lower().startswith("mailhousewall") or
                        mat.name.lower().startswith("proxy_mat_yellow")):
                mesh.materials[i] = wall_mat
                replaced_indices.add(i)
            elif mat and mat.name.lower().startswith("proxy_mat_grey"):
                mesh.materials[i] = wood
            elif mat and mat.name.lower().startswith("proxy_mat_general_reflective"):
                mesh.materials[i] = glass
            elif mat and (mat.name.lower().startswith("marble") or
                          mat.name.lower().startswith("marciapiede")):
                if source.startswith("CS__"):
                    mesh.materials[i] = formal
                replaced_indices.add(i)
        project_surface_uv(mesh, replaced_indices)
        repair_collapsed_uv(mesh)
    return obj


def block(name, col, xyz, dims, material, role="structure"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    obj.data.materials.append(material)
    project_surface_uv(obj.data, {0})
    obj["pcg_role"] = role
    return obj


def moulding(name, col, x0, x1, y, z, profile, material, role="facade_trim"):
    """A reusable length of carved stone trim, with actual stepped silhouette."""
    vertices = [(x, y + py, z + pz) for x in (x0, x1) for py, pz in profile]
    n = len(profile)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    mesh.update()
    project_surface_uv(mesh, {0}, tile_m=2.4)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj["pcg_role"] = role
    obj["front_axis"] = "-Y"
    return obj


def weathered_patch(name, col, x, y, z, width, height, material, seed):
    """A shallow, irregular surviving plaster or exposed-stone island."""
    points = []
    count = 18
    for i in range(count):
        angle = 2 * math.pi * i / count
        wobble = 0.79 + .14 * math.sin(i * 4.31 + seed) + .06 * math.sin(i * 7.07 + seed * 2)
        points.append((x + math.cos(angle) * width * .5 * wobble,
                       y - .025,
                       z + math.sin(angle) * height * .5 * wobble))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(points, [], [tuple(range(count))])
    mesh.materials.append(material)
    mesh.update()
    project_surface_uv(mesh, {0}, tile_m=1.4)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj["pcg_role"] = "wall_wear"
    obj["front_axis"] = "-Y"
    return obj


def remove_missing_roof_tiles(obj):
    """Expose small worn roof patches while retaining the source underlay."""
    mesh = obj.data.copy()
    obj.data = mesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    selected = []
    for face in bm.faces:
        if face.material_index != 1:
            continue
        c = face.calc_center_median()
        in_rear_patch = (1.13 < c.x < 2.15 and -1.16 < c.y < -.46 and
                         math.sin(c.x * 11 + c.y * 8) > -.3)
        in_front_patch = (-2.35 < c.x < -1.65 and -3.30 < c.y < -2.72 and
                          math.sin(c.x * 9 - c.y * 13) > .05)
        if in_rear_patch or in_front_patch:
            selected.append(face)
    bmesh.ops.delete(bm, geom=selected, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj["damaged_tile_faces_removed"] = len(selected)


def roof_surface_z(mesh, x, y):
    nearby = [vertex.co.z for vertex in mesh.vertices
              if abs(vertex.co.x - x) < .19 and abs(vertex.co.y - y) < .19]
    if not nearby:
        raise ValueError(f"roof has no surface near {x}, {y}")
    return max(nearby)


def drainpipe(name, col, points, material):
    curve = bpy.data.curves.new(name + "_path", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = .042
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    col.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.data.materials.append(material)
    obj["pcg_role"] = "drainpipe"
    obj["front_axis"] = "-Y"
    return obj


def court_paving(name, col, center_x, back_y=-.20, front_y=-3.36):
    rng = random.Random(9228)
    vertices, faces = [], []
    rows, columns = 9, 8
    width, depth = 5.62, back_y - front_y
    gap = .018
    for row in range(rows):
        y0 = front_y + row * depth / rows + gap
        y1 = front_y + (row + 1) * depth / rows - gap
        stagger = .14 if row % 2 else -.06
        for column in range(columns):
            x0 = center_x - width / 2 + column * width / columns + gap + stagger
            x1 = center_x - width / 2 + (column + 1) * width / columns - gap + stagger
            x0 = max(x0, center_x - width / 2 + gap)
            x1 = min(x1, center_x + width / 2 - gap)
            if x1 - x0 < .2:
                continue
            jitter = [(rng.random() - .5) * .035 for _ in range(8)]
            corners = [(x0+jitter[0], y0+jitter[1]),
                       (x1+jitter[2], y0+jitter[3]),
                       (x1+jitter[4], y1+jitter[5]),
                       (x0+jitter[6], y1+jitter[7])]
            midx = (x0 + x1) / 2
            midy = (y0 + y1) / 2
            start = len(vertices)
            for x, y in corners:
                vertices.append((x, y, .005))
            for x, y in corners:
                vertices.append((midx + (x-midx)*.965, midy + (y-midy)*.94,
                                 .037 + (rng.random() - .5)*.008))
            faces.append(tuple(start+i for i in (4,5,6,7)))
            for i in range(4):
                j = (i+1) % 4
                faces.append((start+i, start+j, start+4+j, start+4+i))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(paving_mat)
    mesh.update()
    project_surface_uv(mesh, {0}, tile_m=1.15)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj["pcg_role"] = "courtyard_floor"
    obj["front_axis"] = "-Y"
    return obj


def roller_shutter(name, col, x, y, z, width=2.52, height=2.42):
    """Single reusable 1970s corrugated metal closure with real slat relief."""
    verts, faces = [], []
    def cuboid(x0, x1, y0, y1, z0, z1):
        start = len(verts)
        verts.extend(((x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
                      (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)))
        faces.extend(tuple(start+j for j in face) for face in
                     ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)))
    count = 35
    cuboid(x-width/2-.11, x+width/2+.11, y+.07, y+.09,
           z-.08, z+height+.20)
    for i in range(count):
        lo = z + i * height / count
        hi = z + (i + 1) * height / count - .004
        relief = .016 if i % 2 == 0 else .004
        cuboid(x-width/2, x+width/2, y-.025-relief, y+.025,
               lo, hi)
    for side in (-1, 1):
        px = x + side * (width/2 + .025)
        cuboid(px-.032, px+.032, y-.075, y+.065, z-.035, z+height+.08)
    cuboid(x-width/2-.06, x+width/2+.06, y-.11, y+.06,
           z+height+.02, z+height+.18)
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(shutter_mat)
    mesh.update()
    project_surface_uv(mesh, {0}, tile_m=1.7)
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj["pcg_role"] = "garage_roller_shutter"
    obj["front_axis"] = "-Y"
    return obj


def laundry_line(name, col, points):
    curve = bpy.data.curves.new(name + "_path", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = .006
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    col.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.data.materials.append(iron)
    obj["pcg_role"] = "laundry_line"
    obj["front_axis"] = "-Y"
    return obj


def socket(name, col, xyz, kind, parent=None):
    obj = bpy.data.objects.new(name, None)
    col.objects.link(obj)
    obj.location = xyz
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = .06
    obj.hide_render = True
    obj["pcg_role"] = "attachment_socket"
    obj["socket_type"] = kind
    if parent:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


for index, (style, lot, floors, wall_mat, roof_kind) in enumerate(STYLES):
    col = bpy.data.collections.new(f"QA_{style}_{lot}")
    scene.collection.children.link(col)
    collections[style] = col
    xoff = index * 13.0
    floor_h = LOT_FLOOR_HEIGHT_CM[lot] / 100.0
    floor_scale = floor_h / 3.0
    height = floors * floor_h
    depth = 4.0 if roof_kind in ("gable", "damaged_gable") else 6.0
    front_ground = ["B80__Ground.002", "CS__wall_006"]
    front_upper = {
        "STYLE_01": ["CS__wall_004", "CS__wall_010"],
        "STYLE_02": ["CS__wall_004", "CS__wall_004"],
        "STYLE_03": ["CS__wall_004", "SRC03__ModernisedWindow_300"],
        "STYLE_04": ["CS__wall_012", "CS__wall_004"],
    }[style]
    if style == "STYLE_02":
        front_ground = ["CS__wall_006", "B80__Ground.001"]
    if style == "STYLE_03":
        front_ground = ["B80__Ground.013", "B80__Ground.002"]
    if style == "STYLE_04":
        front_ground = ["B80__Ground.002", "CS__wall_007"]

    for bay, source in enumerate(front_ground):
        clone(source, f"{style}_Ground_{bay}", col,
              (xoff + (-1.5 if bay == 0 else 1.5), 0, 0), wall_mat=wall_mat,
              scale=(1, 1, floor_scale),
              role="facade_ground")
    door_bay = 1 if style == "STYLE_02" else 0 if style != "STYLE_03" else 1
    clone("B80__Porta6" if style != "STYLE_04" else "B80__Porta4",
          f"{style}_Door", col, (xoff + (-1.5 if door_bay == 0 else 1.5), -.01, 0),
          scale=(1, 1, floor_scale), role="opening")

    for floor in range(1, floors):
        for bay, source in enumerate(front_upper):
            clone(source, f"{style}_Upper_{floor}_{bay}", col,
                  (xoff + (-1.5 if bay == 0 else 1.5), 0, floor * floor_h),
                  wall_mat=wall_mat, scale=(1, 1, floor_scale), role="facade_upper")

    # Gabled houses use the source roof's true four-metre span. Their rear metre
    # is a separate infill module rather than stretching tiles by 54 percent.
    for floor in range(floors):
        z = floor * floor_h
        for side, x, facing in (("left", -2.63, -90), ("right", 2.63, 90)):
            for section, y in enumerate((1.5,) if depth == 4.0 else (1.5, 4.5)):
                side_window = side == "right" and floor >= 1 and section == (1 if style == "STYLE_02" else 0)
                side_source = ({"STYLE_01": "CS__wall_010", "STYLE_02": "CS__wall_004",
                                "STYLE_03": "CS__wall_010", "STYLE_04": "CS__wall_012"}[style]
                               if side_window else "B80__wall_000.001")
                side_depth = {"CS__wall_010": 1.0158, "CS__wall_004": 1.0158,
                              "CS__wall_012": .5329}.get(side_source, .3697)
                side_x = (-3.0 + side_depth if side == "left" else 3.0 - side_depth)
                clone(side_source, f"{style}_{side}_{floor}_{section}", col,
                      (xoff + side_x, y, z), angle=facing, wall_mat=wall_mat,
                      scale=(1, 1, floor_scale), role="wall_side")
            if depth == 4.0:
                block(f"{style}_{side}_{floor}_rear_infill", col,
                      (xoff + (-2.815 if side == "left" else 2.815), 3.5, z + floor_h / 2),
                      (.37, 1.0, floor_h), wall_mat, "wall_side")
        for bay, x in enumerate((-1.5, 1.5)):
            clone("B80__wall_000.001", f"{style}_Rear_{floor}_{bay}", col,
                  (xoff + x, depth, z), angle=180, wall_mat=wall_mat,
                  scale=(1, 1, floor_scale), role="wall_rear")

    if roof_kind == "terrace":
        block(f"{style}_TerraceSlab", col, (xoff, 3, height + .07),
              (6.25, 6.25, .18), wall_mat, "roof")
        for side, xyz, dims in (
            ("front", (xoff, -.05, height + .37), (6.5, .32, .6)),
            ("rear", (xoff, 6.05, height + .37), (6.5, .32, .6)),
            ("left", (xoff - 3.05, 3, height + .37), (.32, 6.1, .6)),
            ("right", (xoff + 3.05, 3, height + .37), (.32, 6.1, .6)),
        ):
            block(f"{style}_Parapet_{side}", col, xyz, dims, wall_mat, "roof_trim")
    else:
        roof = clone("B80__Tetto", f"{style}_Roof", col,
                     (xoff, depth, height), wall_mat=wall_mat,
                     role="roof")
        if style == "STYLE_04":
            remove_missing_roof_tiles(roof)
        chimney_x, chimney_y = 2.40, -.80
        chimney_z = height + roof_surface_z(roof.data, chimney_x, chimney_y) - .05
        clone("B80__small_chimney_round", f"{style}_Chimney", col,
              (xoff + chimney_x, depth + chimney_y, chimney_z), role="roof_detail")

    if style == "STYLE_02":
        # A formal palazzo needs a legible stone cornice, a floor course and
        # corner pilasters. Each remains a separate reusable architectural part.
        for label, z, profile in (
            ("FloorCourse", floor_h - .17,
             ((0, 0), (-.10, 0), (-.12, .05), (-.13, .09), (-.07, .14), (0, .14))),
            ("Crown", height - .27,
             ((0, 0), (-.10, 0), (-.15, .05), (-.21, .11), (-.21, .18),
              (-.14, .24), (-.08, .28), (0, .28))),
        ):
            moulding(f"{style}_{label}", col, xoff - 3.23, xoff + 3.23,
                     -.54, z, profile, formal)
        for side, px in (("L", -2.73), ("R", 2.73)):
            for floor in range(floors):
                clone("B80__middle_floor_pillar", f"{style}_Pilaster_{side}_{floor}", col,
                      (xoff + px, -.55, floor * floor_h),
                      wall_mat=formal, scale=(1, 1, floor_scale), role="pilaster")

    if style == "STYLE_03":
        roller_shutter(f"{style}_GarageRoller_01", col,
                       xoff - 1.5, -.68, .02)
        line_z = floor_h + 1.68
        laundry_line(f"{style}_LaundryLine_01", col,
                     ((xoff - 2.72, -.78, line_z + .025),
                      (xoff - 1.48, -1.25, line_z - .04),
                      (xoff - .27, -.78, line_z + .025)))
        clone("CLOTH__Favela_01_LOD1", f"{style}_Garment_01", col,
              (xoff - 2.25, -1.21, line_z - .02), scale=(.56,.56,.56),
              role="laundry_garment")
        clone("CLOTH__MiddleEast_DrapedSheet_02", f"{style}_DrapedSheet_02", col,
              (xoff - 1.05, -1.21, line_z - .02), angle=90,
              scale=(.80,.80,.80), role="laundry_garment")
        for n, px in enumerate((-2.36, -2.13, -1.42, -.70)):
            block(f"{style}_LaundryPin_{n}", col,
                  (xoff + px, -1.21, line_z - .02),
                  (.024, .025, .052), wood, "laundry_pin")
        socket(f"SOCKET_{style}_LaundryAnchorLeft", col,
               (xoff - 2.72, -.78, line_z + .025), "laundry_anchor")
        socket(f"SOCKET_{style}_LaundryAnchorRight", col,
               (xoff - .27, -.78, line_z + .025), "laundry_anchor")
        # Localized stone showing through the 1970s plaster: worn, not a
        # rectangular decal masquerading as broken wall geometry.
        weathered_patch(f"{style}_ExposedStone_Left", col,
                        xoff - 2.68, -.54, 1.17, .52, 1.35, stone, 2)
        weathered_patch(f"{style}_ExposedStone_Right", col,
                        xoff + 2.76, -.54, floor_h + 1.92, .32, .65, stone, 7)

    if style == "STYLE_04":
        for n, (px, pz, w, h) in enumerate((
            (-2.63, .96, .55, 1.22), (2.65, 1.58, .45, .94),
            (-2.65, floor_h + 1.95, .42, .84), (2.66, floor_h + .57, .48, .71),
        )):
            weathered_patch(f"{style}_PlasterRemnant_{n}", col,
                            xoff + px, -.54, pz, w, h, plaster, n + 11)

    pipe_x = xoff + 2.83
    drainpipe(f"{style}_Drainpipe_Right", col,
              ((pipe_x, .12, height + .07), (pipe_x, -.25, height + .07),
               (pipe_x, -.61, height - .18), (pipe_x, -.61, .20),
               (pipe_x, -.78, .07)), pipe_metal)
    for floor in range(floors):
        block(f"{style}_PipeBracket_{floor}", col,
              (pipe_x, -.51, floor * floor_h + 1.08),
              (.11, .18, .04), pipe_metal, "drainpipe_bracket")
    socket(f"SOCKET_{style}_DrainpipeTop", col,
           (pipe_x, .12, height + .07), "roof_gutter")

    if style == "STYLE_02":
        bays = (0, 1)
        for floor in range(1, floors):
            for bay in bays:
                bx = xoff + (-1.5 if bay == 0 else 1.5)
                clone("PILOT__KIT_Balcony_StoneAndIron_350",
                      f"{style}_Balcony_{floor}_{bay}", col,
                      (bx, -.48, floor * floor_h - .68), scale=(.86, 1, 1), role="balcony")
                socket(f"SOCKET_{style}_Pot_{floor}_{bay}", col,
                       (bx - .95, -1.28, floor * floor_h + .15), "balcony_pot")
                clone("PROP__PottedPlant_Small_01", f"{style}_Pot_{floor}_{bay}", col,
                      (bx - .95, -1.28, floor * floor_h + .15), role="balcony_pot")

    if style in ("STYLE_01", "STYLE_04"):
        for n, (dx, z) in enumerate(((2.42, floor_h + .2), (2.75, floor_h + 1.65))):
            clone("EVY__Ivy_Instance_1_old_WALL", f"{style}_Ivy_{n}", col,
                  (xoff + dx, -.40, z), role="ivy_wall")
    if style in ("STYLE_01", "STYLE_02"):
        for n, px in enumerate((-2.65, 2.55) if style == "STYLE_02" else (2.55,)):
            clone("PROP__PottedPlant_Small_01", f"{style}_GroundPot_{n}", col,
                  (xoff + px, -.70, .015), scale=(1.42,1.42,1.42),
                  role="ground_pot")
            socket(f"SOCKET_{style}_GroundPot_{n}", col,
                   (xoff + px, -.70, .015), "ground_pot")
    if style == "STYLE_03":
        clone("B80__antenna", f"{style}_Antenna", col,
              (xoff + 1.8, 4.8, height + .15), role="roof_detail")
    if style == "STYLE_04":
        court_paving(f"{style}_CourtPaving", col, xoff)
        for n, (px, py) in enumerate(((-2.39, -1.05), (2.32, -1.50))):
            clone("PROP__PottedPlant_Small_01", f"{style}_CourtPot_{n}", col,
                  (xoff + px, py, .015), scale=(1.55,1.55,1.55),
                  role="courtyard_pot")
            socket(f"SOCKET_{style}_CourtPot_{n}", col,
                   (xoff + px, py, .015), "courtyard_pot")
        for n, z in enumerate((floor_h + .9, floor_h + 1.36, floor_h + 1.82)):
            plank = block(f"{style}_BoardedWindow_{n}", col,
                          (xoff + 1.5, -.60, z), (1.62, .07, .15), wood,
                          "opening_repair")
            plank.rotation_euler[1] = math.radians((-6, 4, -3)[n])
        # Courtyard is legible at street level, with gate base resting on grade.
        block(f"{style}_CourtWall_Left", col, (xoff - 2.14, -3.25, 1.1),
              (1.72, .4, 2.2), stone, "courtyard_wall")
        block(f"{style}_CourtWall_Right", col, (xoff + 2.14, -3.25, 1.1),
              (1.72, .4, 2.2), stone, "courtyard_wall")
        block(f"{style}_CourtWall_ReturnLeft", col, (xoff - 3.0, -1.6, 1.1),
              (.4, 3.3, 2.2), stone, "courtyard_wall")
        block(f"{style}_CourtWall_ReturnRight", col, (xoff + 3.0, -1.6, 1.1),
              (.4, 3.3, 2.2), stone, "courtyard_wall")
        # Use actual wall foliage here. A solid green polygon reads as paint,
        # not moss, and fails the close-up visual gate.
        for n, (px, pz, size) in enumerate(((2.40, .30, .70),
                                             (-2.48, .22, .60))):
            clone("EVY__Ivy_Instance_1_old_WALL", f"{style}_CourtIvy_{n}", col,
                  (xoff + px, -3.49, pz), scale=(size, size, size),
                  role="ivy_wall")
        clone("FENCE__Cast Iron Fence 09_LOD1", f"{style}_Gate_Candidate", col,
              (xoff, -3.25, 0), role="courtyard_gate_candidate")
        for n, z in enumerate((.42, 1.25)):
            block(f"{style}_Gate_Hinge_{n}", col, (xoff - 1.28, -3.25, z),
                  (.1, .15, .13), iron, "gate_hinge")
        block(f"{style}_Gate_Latch", col, (xoff + 1.24, -3.33, .92),
              (.18, .06, .045), iron, "gate_latch")
        socket(f"SOCKET_{style}_GateHinge", col,
               (xoff - 1.28, -3.25, 0), "courtyard_gate_hinge")
        socket(f"SOCKET_{style}_GateLatch", col,
               (xoff + 1.28, -3.25, .92), "courtyard_gate_latch")

    records.append({"style": style, "lot": lot, "floors": floors,
                    "floor_height_m": floor_h, "footprint_m": [6.0, depth],
                    "lot_floor_height_cm": LOT_FLOOR_HEIGHT_CM[lot],
                    "floor_height_delta_cm": 0,
                    "status": "visual_review_only", "roof": roof_kind,
                    "objects": [o.name for o in col.objects],
                    "unique_meshes": len({o.data.name for o in col.objects if o.type == "MESH"})})

# A scale figure exists in the same saved Blender scene as the four samples.
person_mat = bpy.data.materials.new("QA_Mannequin_180cm_Neutral")
person_mat.diffuse_color = (.22, .24, .25, 1)
for style_index, (style, *_unused) in enumerate(STYLES):
    col = collections[style]
    x = style_index * 13.0 - 3.5
    for label, xyz, dims in (("torso", (x, -2.8, 1.2), (.46, .24, .75)),
                             ("head", (x, -2.8, 1.68), (.27, .27, .24)),
                             ("leg_L", (x - .12, -2.8, .43), (.18, .22, .86)),
                             ("leg_R", (x + .12, -2.8, .43), (.18, .22, .86))):
        block(f"QA_180cm_{style}_{label}", col, xyz, dims, person_mat, "scale_reference")

ground = bpy.data.materials.new("QA_Ground_Dust")
ground.diffuse_color = (.40, .36, .31, 1)
for index, (style, *_unused) in enumerate(STYLES):
    block(f"QA_Ground_{style}", collections[style], (index * 13.0, 0, -.09),
          (11.5, 13.5, .15), ground, "qa_ground")

if scene.world is None:
    scene.world = bpy.data.worlds.new("QA_World")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (.58, .66, .76, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .75
sun = bpy.data.lights.new("QA_SicilianSun", "SUN")
sun.energy = 2.0
sun.angle = math.radians(5)
sun_obj = bpy.data.objects.new("QA_SicilianSun", sun)
scene.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(27), math.radians(-25), math.radians(-18))

cam_data = bpy.data.cameras.new("QA_Street_50mm")
cam_data.type = "PERSP"
cam_data.lens = 50
cam = bpy.data.objects.new("QA_Street_50mm", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 1280
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"

blend = OUT / "Mazzarino_4_Stili_Reuse_Gates_v2.blend"
scene.render.filepath = str(OUT / "preview.png")
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
(OUT / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

for index, (style, lot, floors, _mat, _roof) in enumerate(STYLES):
    x = index * 13.0
    cam.location = (x + 9.5, -16.5, 7.0 if floors == 2 else 9.0)
    target = Vector((x, 1.8, floors * 1.5))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    for other_style, col in collections.items():
        col.hide_render = other_style != style
    scene.render.filepath = str(OUT / f"{lot}_{style}.png")
    bpy.ops.render.render(write_still=True)
    print("M80_STYLE_GATE", style, lot, scene.render.filepath)

print("M80_STYLE_GATES_DONE", blend)
