"""Blender 4.3 STYLE_03 reference gate with source balcony stone and iron.

Only this one house is developed here. Nothing in this script exports to Unreal
or changes the existing PCG. The source scene keeps the parts editable.
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_stylized_pilots as k
import build_style_showroom as s

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Pipeline/Blender/output/style03_reference_v4"
OUT.mkdir(parents=True, exist_ok=True)
LOT = "STYLE_03"
FRONT = -260
WIDTH = 620
DEPTH = 520
FLOOR_H = 315
HEIGHT = FLOOR_H * 2
BALCONY_WIDTH = 350
USE_SCANNED_PINK_PLASTER = False  # rejected in reference comparison


def box(name, part, at, size, mat, bevel=0):
    return s.b(LOT, "Details", part, name, at, size, mat, bevel)


def remove_named(prefix):
    for obj in list(bpy.data.objects):
        if obj.name.startswith(prefix) and obj.get("module_type"):
            for items in k.OBJECTS.values():
                if obj in items:
                    items.remove(obj)
            bpy.data.objects.remove(obj, do_unlink=True)


def tube(name, part, pts, radius, material, cyclic=False, resolution=8):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 14
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    spline = curve.splines.new("POLY")
    spline.points.add(len(pts)-1)
    for point, xyz in zip(spline.points, pts):
        point.co = (*xyz, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    obj.data.materials.append(k.MATERIALS[material])
    k.OBJECTS[(LOT, "Details")].append(obj)
    s.mark(obj, part)
    return obj


def prism(name, part, profile_yz, x0, x1, material):
    n = len(profile_yz)
    verts = [(x, y, z) for x in (x0, x1) for y, z in profile_yz]
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, 2*n))]
    for i in range(n):
        j = (i+1) % n
        faces.append((i,j,n+j,n+i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(k.MATERIALS[material])
    uv = mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        for idx in face.loop_indices:
            v = mesh.vertices[mesh.loops[idx].vertex_index].co
            uv.data[idx].uv = (v.y / 210, v.z / 210)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    k.OBJECTS[(LOT, "Details")].append(obj)
    s.mark(obj, part)
    bevel = obj.modifiers.new("hand-cut worn edge", "BEVEL")
    bevel.width = 2.2
    bevel.segments = 2
    obj.modifiers.new("weighted face normals", "WEIGHTED_NORMAL")
    return obj


def broken_plaster_patch(name, part, x, z, w, h, y, material, seed):
    rng = random.Random(seed)
    # A stepped, chipped contour sits directly over the masonry plane.
    outline = []
    for edge in range(4):
        for j in range(12):
            t = j / 12
            perturb = rng.uniform(-.075, .075)
            if edge == 0:
                outline.append((x-w/2+t*w, y, z-h/2+perturb*h))
            elif edge == 1:
                outline.append((x+w/2+perturb*w, y, z-h/2+t*h))
            elif edge == 2:
                outline.append((x+w/2-t*w, y, z+h/2+perturb*h))
            else:
                outline.append((x-w/2+perturb*w, y, z+h/2-t*h))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(outline, [], [tuple(range(len(outline)))])
    mesh.materials.append(k.MATERIALS[material])
    uv = mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        for idx in face.loop_indices:
            p = mesh.vertices[mesh.loops[idx].vertex_index].co
            uv.data[idx].uv = ((p.x + WIDTH/2) / WIDTH,
                               p.z / HEIGHT)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    k.OBJECTS[(LOT, "Facades")].append(obj)
    s.mark(obj, part)
    return obj


def broken_side_patch(name, y, z, w, h, seed):
    """Irregular exposed masonry on the visible side facade."""
    rng=random.Random(seed)
    x=WIDTH/2+21.6
    points=[]
    for edge in range(4):
        for j in range(11):
            t=j/11
            perturb=rng.uniform(-.07,.07)
            if edge==0:
                points.append((x,y-w/2+t*w,z-h/2+perturb*h))
            elif edge==1:
                points.append((x,y+w/2+perturb*w,z-h/2+t*h))
            elif edge==2:
                points.append((x,y+w/2-t*w,z+h/2+perturb*h))
            else:
                points.append((x,y-w/2+perturb*w,z+h/2-t*h))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(points,[],[tuple(range(len(points)))])
    mesh.materials.append(k.MATERIALS["stone_wall"])
    uv=mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        for idx in face.loop_indices:
            p=mesh.vertices[mesh.loops[idx].vertex_index].co
            uv.data[idx].uv=((p.y+DEPTH/2)/DEPTH,p.z/HEIGHT)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    k.OBJECTS[(LOT,"Facades")].append(obj)
    s.mark(obj,"stratified_side_wear")
    return obj


def fit_materials():
    for name, (lo, hi, rough) in k.PALETTE.items():
        if name == "stone":
            lo, hi, rough = (.56,.48,.36), (.78,.69,.53), .93
        elif name == "stone_formal":
            lo, hi, rough = (.61,.54,.43), (.84,.76,.63), .91
        elif name == "glass":
            lo, hi, rough = (.08,.12,.14), (.20,.28,.31), .28
        k.make_material(name, lo, hi, rough)
    k.make_material("stone_wall", *k.PALETTE["stone"])
    k.make_material("copper_old", (.29,.14,.075), (.47,.27,.14), .78)
    k.make_material("plaster_dark", (.28,.20,.13), (.44,.34,.23), .94)
    k.make_material("cement_aged", (.43,.38,.28), (.59,.53,.40), .94)
    k.make_material("shutter_steel", (.24,.27,.27), (.43,.44,.42), .91)
    for name, filename in (("plaster", "T_M80_Plaster_Warm_Generated_v1.png"),
                           ("stone_wall", "T_M80_Limestone_Generated_v1.png")):
        source = ROOT / "Pipeline/Blender/output/style_showroom_v1" / filename
        if source.exists():
            tex = next(n for n in k.MATERIALS[name].node_tree.nodes if n.type == "TEX_IMAGE")
            tex.image = bpy.data.images.load(str(source), check_existing=True)
            tex.image.pack()
            tex.extension = "EXTEND"
    source=Path(r"D:\Blender\AssetsMazzarethTheGame\TestBuildingParts\assets\materials\peach-plaster-te_b2515d87-b77f-4973-8495-34e56a3d8461\peach-plaster-texture_2K_04ec210a-768e-41d0-a15f-12716115a424.blend")
    if USE_SCANNED_PINK_PLASTER and source.exists():
        with bpy.data.libraries.load(str(source), link=False) as (library, loaded):
            loaded.materials=["Peach Plaster Texture"]
        source_mat=loaded.materials[0]
        images={image.name.lower():image for image in bpy.data.images
                if image.name.lower().startswith("peachplastertexture-")}
        mat=k.MATERIALS["plaster"]
        tree=mat.node_tree
        master=next(n for n in tree.nodes if n.type=="GROUP" and n.node_tree==k.ARCHITECTURAL_MASTER)
        color=next(n for n in tree.nodes if n.type=="TEX_IMAGE")
        color.image=next(i for key,i in images.items() if "-jpg" in key)
        color.extension="REPEAT"
        rough=tree.nodes.new("ShaderNodeTexImage")
        rough.image=next(i for key,i in images.items() if "roughness" in key)
        rough.image.colorspace_settings.name="Non-Color"
        rough_range=tree.nodes.new("ShaderNodeMapRange")
        rough_range.inputs["To Min"].default_value=.78
        rough_range.inputs["To Max"].default_value=.96
        tree.links.new(rough.outputs["Color"],rough_range.inputs["Value"])
        tree.links.new(rough_range.outputs["Result"],master.inputs["Roughness"])
        normal_tex=tree.nodes.new("ShaderNodeTexImage")
        normal_tex.image=next(i for key,i in images.items() if "normal" in key)
        normal_tex.image.colorspace_settings.name="Non-Color"
        normal=tree.nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value=.4
        tree.links.new(normal_tex.outputs["Color"],normal.inputs["Color"])
        tree.links.new(normal.outputs["Normal"],master.inputs["Normal"])
        # Keep the source material only as an image carrier; every visible wall
        # uses the common master group, including this scanned PBR variant.
        bpy.data.materials.remove(source_mat)


def detailed_balcony():
    # Replace block corbels with a stepped and curved cast-stone silhouette.
    remove_named("cantilever_corbel")
    for name in ("rail_lower", "rail_upper", "forged_baluster",
                 "balcony_side_rail", "balcony_side_baluster"):
        remove_named(name)
    for x in (WIDTH*.25-101, WIDTH*.25, WIDTH*.25+101):
        profile = [(FRONT-125, 319), (FRONT-125, 304),
                   (FRONT-105, 299), (FRONT-87, 280),
                   (FRONT-75, 259), (FRONT-69, 247),
                   (FRONT-49, 248), (FRONT-37, 280),
                   (FRONT-9, 299), (FRONT-9, 319)]
        prism("sculpted_stone_corbel", "balcony_cast_stone_corbel",
              profile, x-13, x+13, "stone")
    # Two independent ornamental bands read clearly from street height.
    x0 = WIDTH*.25-BALCONY_WIDTH/2+8
    x1 = WIDTH*.25+BALCONY_WIDTH/2-8
    rail_y = FRONT-137
    for z in (302, 332, 376, 394):
        tube("forged_rail_band", "balcony_wrought_iron",
             [(x0,rail_y,z),(x1,rail_y,z)], 1.6 if z != 394 else 2.4, "iron")
    spacing = 18
    for i in range(int((x1-x0)/spacing)+1):
        x = x0 + i*(x1-x0)/int((x1-x0)/spacing)
        tube("forged_vertical", "balcony_wrought_iron",
             [(x,rail_y,300),(x,rail_y,394)], 1.5, "iron")
        if i % 2 == 0:
            circle = [(x + 7*math.cos(a*math.tau/24), rail_y-1.3,
                       345 + 7*math.sin(a*math.tau/24)) for a in range(24)]
            tube("forged_circle", "balcony_wrought_iron", circle, 1.1, "iron", True)
            pts = [(x+8*math.sin(t*math.tau/30),rail_y-1.4,
                    358+13*math.cos(t*math.tau/30)) for t in range(31)]
            tube("forged_scroll", "balcony_wrought_iron", pts, .9, "iron")
    for x in (x0,x1):
        k.cyl("turned_iron_finial", (x,rail_y,402), 5.2, 12, "iron", LOT, "Details", 16)
        for side_z in (301,394):
            tube("balcony_return_rail", "balcony_wrought_iron",
                 [(x,rail_y,side_z),(x,FRONT-39,side_z)],2.0,"iron")
        for j in range(7):
            yy=rail_y+j*(98/6)
            tube("balcony_return_upright", "balcony_wrought_iron",
                 [(x,yy,301),(x,yy,394)],1.5,"iron")
    for z,thick,overhang in ((307,4,8),(320,4,10)):
        box("balcony_carved_front_edge", "balcony_cast_stone_moulding",
            (WIDTH*.25, FRONT-138-overhang*.2,z),
            (BALCONY_WIDTH-3, thick, thick),"stone",.7)
    # Saucers are created with their matching pots, at the same x/y anchor.


def ornate_iron_with_cut_stone():
    """Reuse the detailed source ironwork without its opaque stone parapet."""
    detailed_balcony()
    for prefix in ("forged_rail_band", "forged_vertical", "forged_circle",
                   "forged_scroll", "turned_iron_finial", "balcony_return_rail",
                   "balcony_return_upright"):
        remove_named(prefix)
    source=Path(r"D:\Blender\AssetsMazzarethTheGame\balcony_80s.blend")
    if not source.exists():
        return
    with bpy.data.libraries.load(str(source),link=False) as (library,loaded):
        loaded.objects=["Balcony2"]
    original=loaded.objects[0]
    if original is None:
        return
    original_points=[]
    faces=[]
    mapping={}
    # Library-loading the object alone resets its world matrix to identity.
    # The authored source stands upright only after its -90° X rotation.
    source_orientation=Matrix.Rotation(-math.pi/2,4,"X")
    for face in original.data.polygons:
        if face.material_index!=0:
            continue
        ring=[]
        for vi in face.vertices:
            vi=int(vi)
            if vi not in mapping:
                mapping[vi]=len(original_points)
                original_points.append(source_orientation @ original.data.vertices[vi].co)
            ring.append(mapping[vi])
        faces.append(tuple(ring))
    if not original_points:
        return
    low=Vector(tuple(min(p[i] for p in original_points) for i in range(3)))
    high=Vector(tuple(max(p[i] for p in original_points) for i in range(3)))
    center=(low+high)/2
    size=high-low
    # Keep the street edge fixed and extend both return rails to the facade.
    # The module pivot is on that actual attachment plane, not out in space.
    target_size=Vector((BALCONY_WIDTH-3,131,105))
    target_center=Vector((WIDTH*.25,FRONT-65.5,373.5))
    attachment=Vector((WIDTH*.25,FRONT,FLOOR_H))
    target_points=[]
    for p in original_points:
        world=Vector((target_center[0]+(p[0]-center[0])*target_size[0]/size[0],
                      target_center[1]+(p[1]-center[1])*target_size[1]/size[1],
                      target_center[2]+(p[2]-center[2])*target_size[2]/size[2]))
        target_points.append(world-attachment)
    mesh=bpy.data.meshes.new("KIT_Balcony_OrnateIron_347")
    mesh.from_pydata(target_points,[],faces)
    mesh.materials.append(k.MATERIALS["iron"])
    obj=bpy.data.objects.new("KIT_Balcony_OrnateIron_347",mesh)
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    obj.location=attachment
    obj["module_type"]="balcony_ornate_iron_347"
    obj["nominal_width_cm"]=BALCONY_WIDTH-3
    obj["wall_attachment_z_cm"]=FLOOR_H
    obj["street_facing_axis"]="-Y"
    obj["wall_attachment_y_cm"]=FRONT
    obj["source_blend"]=str(source)
    k.OBJECTS[(LOT,"Details")].append(obj)
    s.PARTS["balcony_ornate_iron_347"].append(obj)


def source_balcony_complete():
    """One reusable balcony with sculpted source stone and wrought iron."""
    source=Path(r"D:\Blender\AssetsMazzarethTheGame\balcony_80s.blend")
    if not source.exists():
        ornate_iron_with_cut_stone()
        return
    for name in ("balcony_slab","cantilever_corbel","rail_lower","rail_upper",
                 "forged_baluster","balcony_side_rail","balcony_side_baluster",
                 "decorated_ring"):
        remove_named(name)
    with bpy.data.libraries.load(str(source),link=False) as (library,loaded):
        loaded.objects=["Balcony2"]
    original=loaded.objects[0]
    if original is None:
        ornate_iron_with_cut_stone()
        return
    # Rebuild the mesh so that imported custom normals from the old file do
    # not leave the stone slab unnaturally dark after the rotation and resize.
    source_orientation=Matrix.Rotation(-math.pi/2,4,"X")
    points=[source_orientation @ vertex.co for vertex in original.data.vertices]
    low=Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    high=Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    size=high-low
    attachment=Vector((WIDTH*.25,FRONT,FLOOR_H))
    target_points=[]
    for point in points:
        world=Vector((WIDTH*.25+(point.x-(low.x+high.x)*.5)*BALCONY_WIDTH/size.x,
                      FRONT-118+(point.y-low.y)*120/size.y,
                      245+(point.z-low.z)*183/size.z))
        target_points.append(world-attachment)
    mesh=bpy.data.meshes.new("KIT_Balcony_StoneAndIron_350")
    mesh.from_pydata(target_points,[],
                     [tuple(face.vertices) for face in original.data.polygons])
    mesh.materials.append(k.MATERIALS["iron"])
    mesh.materials.append(k.MATERIALS["stone"])
    for face,source_face in zip(mesh.polygons,original.data.polygons):
        face.material_index=source_face.material_index
        face.use_smooth=source_face.use_smooth
    uv=mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        for loop_index in face.loop_indices:
            p=mesh.vertices[mesh.loops[loop_index].vertex_index].co+attachment
            if abs(face.normal.y)>.5:
                uv.data[loop_index].uv=(p.x/190,p.z/190)
            elif abs(face.normal.x)>.5:
                uv.data[loop_index].uv=(p.y/190,p.z/190)
            else:
                uv.data[loop_index].uv=(p.x/190,p.y/190)
    obj=bpy.data.objects.new("KIT_Balcony_StoneAndIron_350",mesh)
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    obj.location=attachment
    obj["module_type"]="balcony_stone_iron_350"
    obj["nominal_width_cm"]=BALCONY_WIDTH
    obj["wall_attachment_y_cm"]=FRONT
    obj["wall_attachment_z_cm"]=FLOOR_H
    obj["street_facing_axis"]="-Y"
    obj["source_blend"]=str(source)
    k.OBJECTS[(LOT,"Details")].append(obj)
    s.PARTS["balcony_stone_iron_350"].append(obj)


def drains_and_cables():
    remove_named("aged_downpipe")
    remove_named("downpipe_collar")
    remove_named("downpipe_outlet")
    remove_named("meter_box")
    remove_named("period_cable")
    remove_named("cable_clip")
    for x in (-WIDTH/2+31, WIDTH/2-31):
        y = FRONT-32
        tube("copper_downpipe", "aged_copper_drain",
             [(x,y,620),(x,y,160),(x,y,23),(x,y-17,16),(x,y-34,16)],
             4.3, "copper_old", resolution=6)
        for z in (70,235,455,595):
            k.cyl("copper_pipe_collars", (x,y,z), 5.9, 5,
                  "copper_old", LOT, "Details", 18)
        tube("gutter_heel", "aged_copper_drain",
             [(x,y,608),(x,y+7,617),(x,y+11,628)], 5.5, "copper_old")
    for z,dy in ((577,-42),(585,-48)):
        tube("period_electric_cable", "period_cables",
             [(-WIDTH/2+44,FRONT+dy,z),
              (-65,FRONT+dy-3,z-5), (WIDTH/2-40,FRONT+dy,z-1)],
             1.1, "iron")
    for x in (-WIDTH/2+45, -60, WIDTH/2-45):
        box("cable_wall_clip", "period_cables", (x,FRONT-57,585),
            (7,7,10), "copper_old", 1)


def textured_garage_and_door():
    # The authored shutter uses one weathered metal material and shallow,
    # regularly spaced lamellae. Remove alternating dark bands and pasted-on
    # rectangular rust tabs from the first proxy.
    remove_named("aged_roller_slat")
    remove_named("surface_rust")
    # Narrow mechanical joints, side runners, rolled bottom and handle.
    gx = -WIDTH*.25
    gwidth = 240
    for j in range(25):
        z=9+j*7.75
        s.front(LOT,"Openings","garage_weathered_steel","formed_steel_lamella",
                gx,FRONT-8,z,gwidth-22,4.5,7.2,"shutter_steel",.45)
    for z in (37,76,115,154,193):
        tube("roller_worn_seam", "garage_fittings",
             [(gx-gwidth*.46,FRONT-13,z), (gx+gwidth*.46,FRONT-13,z)],
             .35, "iron")
    for x in (gx-gwidth*.48,gx+gwidth*.48):
        box("roller_side_guide", "garage_fittings", (x,FRONT-17,110),
            (5,10,217), "iron", 1)
    box("shutter_pull", "garage_fittings", (gx,FRONT-17,21),
        (35,9,5), "iron", 1)
    dx=WIDTH*.25
    # Separate iron transom and fan curl over the front timber door.
    for x in (dx-40, dx-20, dx, dx+20, dx+40):
        tube("transom_iron_scroll", "door_ironwork",
             [(x-9,FRONT-32,229),(x,FRONT-33,238),(x+9,FRONT-32,229)],
             1.1, "iron")


def scanned_timber_door():
    source=Path(r"D:\Blender\AssetsMazzarethTheGame\TestBuildingParts\assets\models\old-door_eba007af-ccdf-4f82-8556-c47d773d2c55\old-door_ad2627d7-8bb7-4043-b1b5-ecdda5d5bea4.blend")
    if not source.exists():
        return
    for name in ("timber_door", "recessed_panel", "door_knocker"):
        remove_named(name)
    with bpy.data.libraries.load(str(source), link=False) as (library, loaded):
        loaded.objects=[name for name in library.objects if name=="Old Door"]
    obj=loaded.objects[0]
    if obj is None:
        return
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    obj.name="old_sicilian_timber_door_scanned"
    obj.scale=(100,100,100)
    obj.rotation_euler=(0,0,0)
    bpy.context.view_layer.update()
    bounds=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    middle=Vector(tuple((min(p[i] for p in bounds)+max(p[i] for p in bounds))/2
                        for i in range(3)))
    obj.location+=Vector((WIDTH*.25,FRONT-16,112))-middle
    obj["source_blend"]=str(source)
    obj["module_type"]="front_door_scanned"
    s.PARTS["front_door_scanned"].append(obj)
    k.OBJECTS[(LOT,"Openings")].append(obj)
    if obj.data.materials:
        original=obj.data.materials[0]
        images={}
        for node in original.node_tree.nodes if original and original.use_nodes else []:
            if node.type=="TEX_IMAGE" and node.image:
                image=node.image
                if not image.packed_file:
                    image.pack()
                lower=image.name.lower()
                if "basecolor" in lower:
                    images["base"]=image
                elif "normal" in lower:
                    images["normal"]=image
                elif "orm" in lower:
                    images["orm"]=image
        material=bpy.data.materials.new("M80_scanned_timber_door")
        material.use_nodes=True
        nodes=material.node_tree.nodes
        nodes.clear()
        output=nodes.new("ShaderNodeOutputMaterial")
        master=nodes.new("ShaderNodeGroup")
        master.node_tree=k.ARCHITECTURAL_MASTER
        master.inputs["Roughness"].default_value=.86
        master.inputs["Wear Color"].default_value=(.09,.05,.03,1)
        tex=nodes.new("ShaderNodeTexImage")
        tex.image=images.get("base")
        warm=nodes.new("ShaderNodeMixRGB")
        warm.blend_type="MULTIPLY"
        warm.inputs[0].default_value=.40
        warm.inputs[2].default_value=(.55,.36,.25,1)
        material.node_tree.links.new(tex.outputs["Color"],warm.inputs[1])
        material.node_tree.links.new(warm.outputs["Color"],master.inputs["Base Color"])
        if "normal" in images:
            norm_tex=nodes.new("ShaderNodeTexImage")
            norm_tex.image=images["normal"]
            norm_tex.image.colorspace_settings.name="Non-Color"
            normal=nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value=.65
            material.node_tree.links.new(norm_tex.outputs["Color"],normal.inputs["Color"])
            material.node_tree.links.new(normal.outputs["Normal"],master.inputs["Normal"])
        if "orm" in images:
            orm=nodes.new("ShaderNodeTexImage")
            orm.image=images["orm"]
            orm.image.colorspace_settings.name="Non-Color"
            split=nodes.new("ShaderNodeSeparateColor")
            material.node_tree.links.new(orm.outputs["Color"],split.inputs["Color"])
            rough_range=nodes.new("ShaderNodeMapRange")
            rough_range.inputs["To Min"].default_value=.68
            rough_range.inputs["To Max"].default_value=.95
            material.node_tree.links.new(split.outputs["Green"],rough_range.inputs["Value"])
            material.node_tree.links.new(rough_range.outputs["Result"],master.inputs["Roughness"])
        material.node_tree.links.new(master.outputs["Surface"],output.inputs["Surface"])
        obj.data.materials.clear()
        obj.data.materials.append(material)


def side_stair_rebuild():
    remove_named("stair_side_wall")
    # The parapet follows the treads and is continuous into the upper landing.
    profile=[(-DEPTH/2+12,0),(DEPTH/2-14,0),(DEPTH/2-14,378),
             (DEPTH/2-69,378),(-DEPTH/2+12,57)]
    prism("continuous_stair_parapet", "integrated_side_stair",
          profile, WIDTH/2+143, WIDTH/2+165, "plaster")
    for j in range(13):
        y = -DEPTH/2+25+j*(DEPTH-100)/13
        z = 62+j*310/13
        cap=box("terracotta_stair_coping", "integrated_side_stair",
                (WIDTH/2+154,y,z),(28,31,9),"terracotta",1)
        cap.rotation_euler.x=math.atan2(310,DEPTH-100)
    # First tread starts at pavement elevation; tread front nosings overhang.
    for obj in bpy.data.objects:
        if obj.name.startswith("worn_stair_tread"):
            obj.location.z -= 10
            box("chipped_stair_nosing", "integrated_side_stair",
                (obj.location.x,obj.location.y-11,obj.location.z+8),
                (151,13,7),"stone",1)
    box("landing_threshold", "integrated_side_stair",
        (WIDTH/2+85,DEPTH/2-35,321),(180,72,14),"stone",2)


def surface_age_and_detail():
    remove_named("localized_wear")
    remove_named("stone_basecourse")
    # Keep the base course out of the garage and entrance openings.
    for x,w in ((-294,32),(33,132),(260,98)):
        box("segmented_stone_plinth","base_course_clear_of_openings",
            (x,FRONT-27,14),(w,23,28),"stone",1)
    # Localized stone areas vary in width and placement, with exposed patches
    # around the base, corner, balcony and service installations.
    for i,(x,z,w,h) in enumerate((
        (-294,68,30,105),(-27,55,48,60),
        (239,75,70,113),(284,182,35,70),
        (10,293,72,31),(-76,442,42,47),
    )):
        broken_plaster_patch(f"exposed_stone_{i}","stratified_plaster_wear",
                             x,z,w,h,FRONT-23.3,"stone_wall",392+i*17)
    broken_side_patch("side_exposed_stone_large",-117,465,105,118,1774)
    broken_side_patch("side_exposed_stone_high",72,566,64,53,1902)
    # The wall is not divided into flat horizontal strips: thin limestone
    # courses and a stepped parapet supply an architectural rhythm.
    for z,thick,projection in ((42,9,10),(309,7,13),(605,7,18),
                               (619,8,24),(632,7,18)):
        box("worn_limestone_course", "architectural_stone_courses",
            (0,FRONT-projection,z),(WIDTH+projection*2,19,thick),"stone",2)
    for z in (610,623):
        box("parapet_side_course", "architectural_stone_courses",
            (WIDTH/2+11,0,z),(23,DEPTH+10,8),"stone",2)
    # Copper brackets give the roof line the finer rhythm of the reference.
    for x in range(-275,276,70):
        box("cornice_bracket", "roofline_detail", (x,FRONT-30,602),
            (12,24,18),"stone",1)
    # A small electricity meter with separate insulated leads.
    box("old_service_box", "facade_services", (WIDTH/2+31,FRONT+125,510),
        (18,31,45),"cement_aged",2)
    tube("service_drop", "facade_services",
         [(WIDTH/2+43,FRONT+125,488),
          (WIDTH/2+43,FRONT+125,472),
          (WIDTH/2+43,FRONT+112,458)],2.3,"iron")


def terracotta_planter(x,y,z,scale,seed):
    rng=random.Random(seed)
    saucer=s.mark(k.cyl("hand_thrown_pot_saucer",(x,y,z+3*scale),
                          19*scale,4*scale,"terracotta",LOT,"Details",24),
                   "potted_plant")
    profile=((0,5),(11,5),(12,7),(15,32),(17,36),(17,40),
             (14,40),(13,36),(12,30),(9,9),(0,9))
    radial=24
    verts=[]
    for radius,height in profile:
        for a in range(radial):
            angle=a*math.tau/radial
            verts.append((x+radius*math.cos(angle)*scale,
                          y+radius*math.sin(angle)*scale,
                          z+height*scale))
    faces=[]
    for ring in range(len(profile)-1):
        for a in range(radial):
            b=(a+1)%radial
            faces.append((ring*radial+a,ring*radial+b,
                          (ring+1)*radial+b,(ring+1)*radial+a))
    mesh=bpy.data.meshes.new("hand_thrown_terracotta_pot")
    mesh.from_pydata(verts,[],faces)
    mesh.materials.append(k.MATERIALS["terracotta"])
    obj=bpy.data.objects.new("hand_thrown_terracotta_pot",mesh)
    bpy.context.scene.collection.children[LOT].objects.link(obj)
    obj["module_type"]="potted_plant"
    k.OBJECTS[(LOT,"Details")].append(obj)
    s.PARTS["potted_plant"].append(obj)
    soil=s.mark(k.cyl("pot_soil",(x,y,z+36*scale),13*scale,3*scale,
                      "plaster_dark",LOT,"Details",20),"potted_plant")
    leaf_verts=[]
    leaf_faces=[]
    leaf_z=z+37*scale
    for stem in range(31):
        theta=rng.random()*math.tau
        height=rng.uniform(17,47)*scale
        spread=rng.uniform(8,24)*scale
        start=(x+rng.uniform(-5,5)*scale,y+rng.uniform(-5,5)*scale,leaf_z)
        bend=(x+math.cos(theta)*spread*.45,
              y+math.sin(theta)*spread*.45,leaf_z+height*.55)
        tip=(x+math.cos(theta)*spread,y+math.sin(theta)*spread,
             leaf_z+height)
        tube("realistic_plant_stem","potted_plant",[start,bend,tip],
             .65*scale,"moss",resolution=2)
        for t in (.43,.67,.87):
            px=start[0]*(1-t)+tip[0]*t
            py=start[1]*(1-t)+tip[1]*t
            pz=start[2]*(1-t)+tip[2]*t
            leaf_w=rng.uniform(3,6)*scale
            leaf_l=rng.uniform(7,12)*scale
            dx=math.cos(theta+math.pi/2)*leaf_w
            dy=math.sin(theta+math.pi/2)*leaf_w
            forward_x=math.cos(theta)*leaf_l
            forward_y=math.sin(theta)*leaf_l
            idx=len(leaf_verts)
            leaf_verts.extend(((px-dx,py-dy,pz),
                               (px+dx,py+dy,pz),
                               (px+forward_x,py+forward_y,pz+leaf_l*.38)))
            leaf_faces.append((idx,idx+1,idx+2))
    leaves=bpy.data.meshes.new("individual_plant_leaves")
    leaves.from_pydata(leaf_verts,[],leaf_faces)
    leaves.materials.append(k.MATERIALS["moss"])
    leaf_obj=bpy.data.objects.new("individual_plant_leaves",leaves)
    bpy.context.scene.collection.children[LOT].objects.link(leaf_obj)
    leaf_obj["module_type"]="potted_plant"
    k.OBJECTS[(LOT,"Details")].append(leaf_obj)
    s.PARTS["potted_plant"].append(leaf_obj)


def potted_vegetation():
    for prefix in ("terracotta_pot", "dark_pot_soil", "plant_stem", "leaf_cluster"):
        remove_named(prefix)
    for j,x in enumerate((WIDTH*.08,WIDTH*.25,WIDTH*.42)):
        terracotta_planter(x,FRONT-80,326,1 if j==0 else .75,1300+j)
    for j,(x,scale) in enumerate(((-WIDTH*.42,1.05),(WIDTH*.43,.82))):
        terracotta_planter(x,FRONT-76,-1,scale,1430+j)


def scale_dummy():
    # An editable 180 cm figure at street grade, excluded from beauty render.
    x,y=WIDTH/2+260, FRONT-70
    parts=(("head",(x,y,167),(24,20,25)),
           ("torso",(x,y,119),(47,23,68)),
           ("left_leg",(x-12,y,42),(17,19,84)),
           ("right_leg",(x+12,y,42),(17,19,84)),
           ("left_arm",(x-30,y,120),(11,13,70)),
           ("right_arm",(x+30,y,120),(11,13,70)))
    for name,at,size in parts:
        obj=box("scale_mannequin_"+name,"scale_mannequin_180cm",at,size,"concrete",5)
        obj.hide_render=True
        obj["reference_height_cm"]=180


def render():
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=80
    scene.render.resolution_x=1400
    scene.render.resolution_y=1550
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.90,.91,.94,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.55
    sun=bpy.data.lights.new("SouthernAfternoon","SUN")
    sun.energy=3.0
    sun.angle=math.radians(3.5)
    sun_obj=bpy.data.objects.new("SouthernAfternoon",sun)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler=(math.radians(33),math.radians(-20),math.radians(-24))
    camera_data=bpy.data.cameras.new("ReferenceAngle")
    camera_data.type="ORTHO"
    camera_data.ortho_scale=1200
    camera_data.clip_end=100000
    camera=bpy.data.objects.new("ReferenceAngle",camera_data)
    scene.collection.objects.link(camera)
    target=Vector((0,0,335))
    camera.location=target+Vector((760,-1790,120))
    camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.camera=camera
    scene.render.filepath=str(OUT/"STYLE_03_reference_gate_v4.png")
    bpy.ops.render.render(write_still=True)


def render_scale_audit(filename="STYLE_03_scale_audit_42mm_v2.png"):
    """Eye-height, 42 mm perspective audit with the 180 cm dummy visible."""
    scene=bpy.context.scene
    beauty_camera=scene.camera
    audit_data=bpy.data.cameras.new("ScaleAudit_42mm_EyeHeight170cm")
    audit_data.type="PERSP"
    audit_data.lens=42
    audit_data.clip_end=100000
    audit=bpy.data.objects.new("ScaleAudit_42mm_EyeHeight170cm",audit_data)
    scene.collection.objects.link(audit)
    audit.location=(310,FRONT-1950,170)
    target=Vector((15,0,345))
    audit.rotation_euler=(target-audit.location).to_track_quat("-Z","Y").to_euler()
    scene.camera=audit
    for obj in bpy.data.objects:
        if obj.get("module_type")=="scale_mannequin_180cm":
            obj.hide_render=False
        if obj.get("module_type")=="scale_ruler":
            obj.hide_render=True
    scene.cycles.samples=48
    scene.render.resolution_x=1600
    scene.render.resolution_y=1000
    scene.render.filepath=str(OUT/filename)
    bpy.ops.render.render(write_still=True)
    for obj in bpy.data.objects:
        if obj.get("module_type")=="scale_mannequin_180cm":
            obj.hide_render=True
    scene.camera=beauty_camera


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    k.MATERIALS.clear()
    k.OBJECTS.clear()
    k.ARCHITECTURAL_MASTER=None
    fit_materials()
    bpy.context.scene.unit_settings.system="METRIC"
    bpy.context.scene.unit_settings.scale_length=.01
    s.house(LOT,WIDTH,DEPTH,2,FLOOR_H)
    # Keep openings and doors at human dimensions. The new 315 cm floors add
    # believable wall above them rather than stretching the assets vertically.
    for obj in bpy.data.objects:
        if obj.name.startswith("balcony_slab") and obj.get("module_type"):
            obj.dimensions.x=BALCONY_WIDTH
            for modifier in obj.modifiers:
                if modifier.type=="BEVEL":
                    modifier.width=1.6
        elif obj.name.startswith("worn_cornice") and obj.get("module_type"):
            obj.dimensions.y=52
            obj.dimensions.z=15
            for modifier in obj.modifiers:
                if modifier.type=="BEVEL":
                    modifier.width=1.5
        elif obj.name.startswith("aged_floor_course") and obj.get("module_type"):
            obj.dimensions.y=43
            obj.dimensions.z=8
            for modifier in obj.modifiers:
                if modifier.type=="BEVEL":
                    modifier.width=1.2
        elif obj.name.startswith("weathered_terrace") and obj.get("module_type"):
            obj.data.materials.clear()
            obj.data.materials.append(k.MATERIALS["cement_aged"])
    bpy.context.view_layer.update()
    s.map_facade_across_house(LOT,WIDTH,DEPTH,HEIGHT)
    scanned_timber_door()
    source_balcony_complete()
    drains_and_cables()
    textured_garage_and_door()
    side_stair_rebuild()
    surface_age_and_detail()
    potted_vegetation()
    scale_dummy()
    render()
    render_scale_audit("STYLE_03_scale_audit_42mm_v4.png")
    blend=OUT/"Mazzarino_STYLE_03_Reference_Gate_v4.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    manifest={"blender":bpy.app.version_string,
              "source_reference":"C:/Users/12700K RTX3070Ti/Downloads/house_ex.png",
              "state":"reference comparison pending; not approved for Unreal/PCG",
              "master_shader":"NG_M80_Architectural_Master",
              "width_cm":WIDTH,"floor_height_cm":FLOOR_H,
              "height_cm":HEIGHT,"mannequin_cm":180,
              "material_instances":sorted(k.MATERIALS),
              "objects":len([o for o in bpy.data.objects if o.type in {"MESH","CURVE"}]),
              "blend_file":str(blend)}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("M80_STYLE03_GATE",json.dumps(manifest))


if __name__=="__main__":
    main()
