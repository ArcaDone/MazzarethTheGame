"""Build the four exterior art-direction pilots with Blender 4.3.

The source of truth for scale and lot geometry is Buildings_Test18.json.  This
script never reads the baked PCG meshes.  It writes a .blend, stage FBXs, PBR
base-colour maps, previews, and a machine-readable placement manifest.
"""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Pipeline" / "Blender" / "output" / "stylized_pilots_v1"
FBX = OUT / "fbx"
TEX = OUT / "textures"
PREVIEW = OUT / "previews"
for folder in (OUT, FBX, TEX, PREVIEW):
    folder.mkdir(parents=True, exist_ok=True)

CATALOG = json.loads((ROOT / "Research/Mazzarino80/PCG/Buildings_Test18.json").read_text(encoding="utf-8"))
LOTS = {"1249069204": "STYLE_01", "1249068307": "STYLE_02",
        "1249069200": "STYLE_03", "1249069228": "STYLE_04"}
STAGES = ("Structure", "Facades", "Openings", "Roofs", "Details")
PALETTE = {
    "stone": ((0.56, 0.39, 0.23), (0.76, 0.59, 0.38), 0.87),
    "stone_formal": ((0.65, 0.49, 0.31), (0.82, 0.69, 0.48), 0.83),
    "plaster": ((0.65, 0.54, 0.38), (0.83, 0.72, 0.53), 0.91),
    "plaster_pale": ((0.70, 0.63, 0.47), (0.88, 0.80, 0.61), 0.88),
    "brick": ((0.50, 0.24, 0.15), (0.72, 0.38, 0.24), 0.88),
    "terracotta": ((0.49, 0.20, 0.12), (0.76, 0.38, 0.22), 0.83),
    "wood": ((0.19, 0.10, 0.055), (0.39, 0.22, 0.11), 0.84),
    "green_wood": ((0.10, 0.17, 0.105), (0.24, 0.33, 0.18), 0.84),
    "iron": ((0.065, 0.055, 0.045), (0.18, 0.15, 0.11), 0.77),
    "concrete": ((0.40, 0.38, 0.32), (0.65, 0.62, 0.51), 0.92),
    "glass": ((0.045, 0.075, 0.075), (0.11, 0.16, 0.16), 0.40),
    "moss": ((0.08, 0.12, 0.045), (0.21, 0.25, 0.08), 0.95),
}
MATERIALS = {}
ARCHITECTURAL_MASTER = None
OBJECTS = defaultdict(list)
REPORT = {"blender_version": bpy.app.version_string, "units": "centimetres",
          "pilot_lots": {}, "assets": {}, "warnings": []}


def image_for_material(name, low, high):
    """A quiet, broad colour variation. Geometry and localized wear carry detail."""
    size = 512
    rng = np.random.default_rng(sum(map(ord, name)) * 1980)
    y, x = np.mgrid[:size, :size].astype(np.float32)
    def noise(cells):
        grid=rng.random((cells+1,cells+1),dtype=np.float32)
        qx=x*cells/size
        qy=y*cells/size
        ix=np.floor(qx).astype(np.int32)
        iy=np.floor(qy).astype(np.int32)
        tx=qx-ix
        ty=qy-iy
        tx=tx*tx*(3-2*tx)
        ty=ty*ty*(3-2*ty)
        a=grid[iy,ix]*(1-tx)+grid[iy,ix+1]*tx
        b=grid[iy+1,ix]*(1-tx)+grid[iy+1,ix+1]*tx
        return a*(1-ty)+b*ty
    macro=noise(3)
    medium=noise(11)
    small=noise(31)
    fine=rng.random((size,size),dtype=np.float32)
    mix=np.clip(.14+.45*macro+.30*medium+.08*small+.03*fine,0,1)
    if name in {"brick", "terracotta"}:
        unit_x=50
        unit_y=31
        warp=(medium-.5)*8
        row=np.floor((y+warp)/unit_y).astype(np.int32)
        offset=np.sin(row*12.989)*unit_x*.42
        joints=((x+offset+warp)%unit_x<2.2) | ((y+warp)%unit_y<2.0)
        mix=np.where(joints,mix*.41,mix)
        mix=np.clip(mix+(small-.5)*.17,0,1)
    if name in {"stone", "stone_formal"}:
        # Cut trim is one weathered stone, never a miniature masonry pattern.
        mix=np.clip(.38*macro+.44*medium+.18*small,0,1)
    if name in {"wood", "green_wood"}:
        grain=(np.sin(x/5.4+medium*5)+1)*.5
        mix=np.clip(mix*.66+grain*.34,0,1)
    rgb = np.asarray(low)[None, None, :] * (1 - mix[:, :, None]) + np.asarray(high)[None, None, :] * mix[:, :, None]
    if name in {"plaster","plaster_pale"}:
        cracks=(medium*.52+small*.48)<.27
        freckles=(small<.32)&(macro<.48)
        exposed=np.asarray((.46,.36,.26) if name=="plaster" else (.55,.43,.31))
        mask=cracks|freckles
        rgb=np.where(mask[:,:,None],rgb*.38+exposed[None,None,:]*.62,rgb)
    rgba = np.concatenate((rgb, np.ones((size, size, 1), dtype=np.float32)), axis=2)
    img = bpy.data.images.new("T_M80_" + name, width=size, height=size)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw = str(TEX / ("T_M80_" + name + ".png"))
    img.file_format = "PNG"
    img.save()
    img.pack()
    return img


def make_material(name, low, high, roughness):
    global ARCHITECTURAL_MASTER
    if ARCHITECTURAL_MASTER is None:
        group = bpy.data.node_groups.new("NG_M80_Architectural_Master", "ShaderNodeTree")
        for socket_name, socket_type in (("Base Color", "NodeSocketColor"),
                                         ("Wear Color", "NodeSocketColor"),
                                         ("Wear Mask", "NodeSocketFloat"),
                                         ("Roughness", "NodeSocketFloat"),
                                         ("Metallic", "NodeSocketFloat"),
                                         ("Normal", "NodeSocketVector")):
            group.interface.new_socket(name=socket_name, in_out="INPUT", socket_type=socket_type)
        group.interface.new_socket(name="Surface", in_out="OUTPUT", socket_type="NodeSocketShader")
        inp = group.nodes.new("NodeGroupInput")
        inp.location = (-500, 0)
        mix = group.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MIX"
        mix.location = (-250, 150)
        pbr = group.nodes.new("ShaderNodeBsdfPrincipled")
        pbr.location = (0, 100)
        out = group.nodes.new("NodeGroupOutput")
        out.location = (300, 100)
        for source, target in (("Wear Mask", "Fac"), ("Base Color", "Color1"),
                               ("Wear Color", "Color2")):
            group.links.new(inp.outputs[source], mix.inputs[target])
        group.links.new(mix.outputs["Color"], pbr.inputs["Base Color"])
        for source, target in (("Roughness", "Roughness"), ("Metallic", "Metallic"),
                               ("Normal", "Normal")):
            group.links.new(inp.outputs[source], pbr.inputs[target])
        group.links.new(pbr.outputs["BSDF"], out.inputs["Surface"])
        ARCHITECTURAL_MASTER = group
    mat = bpy.data.materials.new("M80_" + name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    pbr = nodes.new("ShaderNodeGroup")
    pbr.node_tree = ARCHITECTURAL_MASTER
    pbr.inputs["Roughness"].default_value = roughness
    pbr.inputs["Metallic"].default_value = .18 if name == "iron" else 0
    pbr.inputs["Wear Color"].default_value = (*(np.asarray(low) * .43), 1)
    pbr.inputs["Wear Mask"].default_value = 0
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image_for_material(name, low, high)
    mat.node_tree.links.new(tex.outputs["Color"], pbr.inputs["Base Color"])
    # One shared shader graph; the small set of surface instances only supplies
    # textures and physically meaningful parameters. Keep wall roughness high.
    if name in {"plaster", "plaster_pale", "stone", "stone_formal", "stone_wall"}:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 2.5
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = .22
        ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        ramp.color_ramp.elements[1].position = .84
        ramp.color_ramp.elements[1].color = (.11, .11, .11, 1)
        mat.node_tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        mat.node_tree.links.new(ramp.outputs["Color"], pbr.inputs["Wear Mask"])
    if name in {"stone","stone_formal","plaster","plaster_pale","brick","terracotta"}:
        bump=nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=.13
        bump.inputs["Distance"].default_value=.09
        mat.node_tree.links.new(tex.outputs["Color"],bump.inputs["Height"])
        mat.node_tree.links.new(bump.outputs["Normal"],pbr.inputs["Normal"])
    mat.node_tree.links.new(pbr.outputs["Surface"], out.inputs["Surface"])
    mat.diffuse_color = (*(np.asarray(low) * .4 + np.asarray(high) * .6), 1)
    MATERIALS[name] = mat


def new_collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def box(name, center, size, material, lot, stage, yaw=0, bevel=0):
    sx, sy, sz = size
    if min(size) <= .01:
        return None
    # Local box dimensions are in centimetres. UVs tile about every 1.7 m.
    verts = [(x * sx / 2, y * sy / 2, z * sz / 2)
             for x, y, z in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                             (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(MATERIALS[material])
    uv = mesh.uv_layers.new(name="UVMap")
    tile_cm={"plaster":520,"plaster_pale":520,"stone":360,"stone_formal":350,
             "brick":250,"terracotta":270,"wood":180,"green_wood":180}.get(material,340)
    for poly in mesh.polygons:
        coords = [Vector(verts[mesh.loops[k].vertex_index]) for k in poly.loop_indices]
        normal = poly.normal
        axes = (0,1) if abs(normal.z) > .5 else ((0,2) if abs(normal.y) > .5 else (1,2))
        for loop_i, co in zip(poly.loop_indices, coords):
            uv.data[loop_i].uv = ((co[axes[0]]+center[axes[0]])/tile_cm,
                                  (co[axes[1]]+center[axes[1]])/tile_cm)
    obj = bpy.data.objects.new(name, mesh)
    OBJECTS[(lot,stage)].append(obj)
    bpy.context.scene.collection.children[lot].objects.link(obj)
    obj.location = center
    obj.rotation_euler[2] = yaw
    if bevel:
        modifier = obj.modifiers.new("soft worn edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 1
        modifier.affect = "EDGES"
        modifier.profile = .5
        modifier.loop_slide = True
        obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    return obj


def cyl(name, center, radius, depth, material, lot, stage, vertices=8, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=center)
    obj = bpy.context.object
    obj.name = name
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    bpy.context.scene.collection.children[lot].objects.link(obj)
    obj.data.materials.append(MATERIALS[material])
    if rotation:
        obj.rotation_euler = rotation
    OBJECTS[(lot,stage)].append(obj)
    return obj


def poly_mesh(name, pts, z, material, lot, stage, thickness=10):
    loop = [Vector((p[0],p[1],z)) for p in pts]
    tris = tessellate_polygon([loop])
    verts = [(p[0],p[1],z) for p in pts] + [(p[0],p[1],z-thickness) for p in pts]
    faces = []
    for tri in tris:
        inds = [int(v) if isinstance(v, int) else min(range(len(loop)), key=lambda k:(loop[k]-v).length_squared) for v in tri]
        faces.append(tuple(inds))
        faces.append(tuple(k+len(loop) for k in reversed(inds)))
    for i in range(len(pts)):
        j=(i+1)%len(pts)
        faces.append((i,j,j+len(loop),i+len(loop)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.materials.append(MATERIALS[material])
    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for k in poly.loop_indices:
            p=mesh.vertices[mesh.loops[k].vertex_index].co
            uv.data[k].uv=(p.x/170,p.y/170)
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.scene.collection.children[lot].objects.link(obj)
    OBJECTS[(lot,stage)].append(obj)
    return obj


def edge_box(name,a,ux,uy,out,u,offset,z,width,depth,height,mat,lot,stage,bevel=0):
    x=a[0]+ux*u+out[0]*offset
    y=a[1]+uy*u+out[1]*offset
    return box(name,(x,y,z),(width,depth,height),mat,lot,stage,math.atan2(uy,ux),bevel)


def window(a,ux,uy,out,u,z,width,height,lot,style,balcony=False,damaged=False):
    trim = "stone_formal" if style=="STYLE_02" else ("concrete" if style=="STYLE_03" else "stone")
    leaf = "green_wood" if style in {"STYLE_01","STYLE_02"} else "wood"
    edge_box("window_recess",a,ux,uy,out,u,-12,z,width-8,4,height-8,"iron",lot,"Openings")
    edge_box("glass_recess",a,ux,uy,out,u,-8,z,width-17,3,height-17,"glass",lot,"Openings")
    for sign in (-1,1):
        edge_box("stone_jamb",a,ux,uy,out,u+sign*(width/2+5),7,z,13,20,height+18,trim,lot,"Openings",1)
    edge_box("window_lintel",a,ux,uy,out,u,7,z+height/2+6,width+32,24,13,trim,lot,"Openings",1)
    edge_box("window_sill",a,ux,uy,out,u,16,z-height/2-7,width+38,34,12,trim,lot,"Openings",1)
    edge_box("window_mullion",a,ux,uy,out,u,0,z,5,8,height-15,leaf,lot,"Openings")
    edge_box("window_transom",a,ux,uy,out,u,0,z+height*.16,width-16,8,5,leaf,lot,"Openings")
    if damaged:
        for sign in (-1,1):
            edge_box("boarded_shutter",a,ux,uy,out,u+sign*(width*.27),20,z,
                     width*.22,8,height*.9,"wood",lot,"Openings",1)
    elif style=="STYLE_03":
        edge_box("aged_roller_box",a,ux,uy,out,u,19,z+height/2-10,width-6,14,18,"concrete",lot,"Openings")
        for sign in (-1,1):
            edge_box("roller_rail",a,ux,uy,out,u+sign*width*.43,17,z,5,11,height-20,"iron",lot,"Openings")
    else:
        for sign in (-1,1):
            edge_box("shutter_leaf",a,ux,uy,out,u+sign*(width*.74),19,z,width*.38,7,height*.9,leaf,lot,"Openings",1)
            for d in (-.28,-.06,.16,.38):
                edge_box("shutter_louvre",a,ux,uy,out,u+sign*(width*.74),24,z+d*height,
                         width*.36,3,3,"wood",lot,"Details")
    if balcony:
        bw=width+85
        by=z-height/2-13
        edge_box("balcony_stone_slab",a,ux,uy,out,u,59,by,bw,118,18,
                 "concrete" if style=="STYLE_03" else trim,lot,"Details",2)
        for d in (-.35,.35):
            edge_box("balcony_bracket",a,ux,uy,out,u+d*bw,39,by-39,17,70,65,trim,lot,"Details",2)
        edge_box("balcony_front_rail",a,ux,uy,out,u,118,by+56,bw-9,5,108,"iron",lot,"Details")
        # The open bars give a readable silhouette at street height.
        for j in range(max(5,int(bw/18))):
            x=u-bw*.45+j*bw*.9/max(1,int(bw/18)-1)
            edge_box("balcony_iron_bar",a,ux,uy,out,x,119,by+51,4,6,98,"iron",lot,"Details")
        if style=="STYLE_02":
            for d in (-.32,0,.32):
                edge_box("ornate_rail_diamond",a,ux,uy,out,u+d*bw,122,by+63,11,10,14,"stone_formal",lot,"Details",1)


def door(a,ux,uy,out,u,z,width,height,lot,style,gate=False):
    trim="stone_formal" if style=="STYLE_02" else ("concrete" if style=="STYLE_03" else "stone")
    leaf="iron" if gate else "wood"
    edge_box("door_recess",a,ux,uy,out,u,-13,z,width-7,5,height-8,"iron",lot,"Openings")
    edge_box("worn_entrance",a,ux,uy,out,u,-7,z,width-18,8,height-15,leaf,lot,"Openings",2)
    for s in (-1,1):
        edge_box("entrance_jamb",a,ux,uy,out,u+s*(width/2+5),6,z,15,20,height+15,trim,lot,"Openings",1)
        edge_box("door_panel",a,ux,uy,out,u+s*width*.24,2,z,width*.39,4,height*.75,"wood",lot,"Openings",1)
    edge_box("entrance_lintel",a,ux,uy,out,u,6,z+height/2+7,width+43,25,18,trim,lot,"Openings",2)
    if style=="STYLE_02":
        # A segmented arch gives the palazzo its formal main entrance.
        for j in range(11):
            ang=math.pi*j/10
            xx=u+math.cos(ang)*width*.51
            zz=z+height/2+math.sin(ang)*width*.25
            edge_box("entrance_arch_voussoir",a,ux,uy,out,xx,14,zz,18,27,20,trim,lot,"Details",1)
    for j in range(3):
        edge_box("entrance_step",a,ux,uy,out,u,28+j*31,z-height/2-35+j*12,
                 width+65,34,22,trim,lot,"Details",2)


def build_house(record,style):
    lot=record["building_id"]
    new_collection(lot)
    raw=[p[:2] for p in record["footprint_world_cm"]]
    center=(sum(p[0] for p in raw)/len(raw),sum(p[1] for p in raw)/len(raw))
    poly=[(p[0]-center[0],p[1]-center[1]) for p in raw]
    signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))
    floors=int(record["primary_floors"])
    floor_h=float(record["floor_height_cm"])
    height=floors*floor_h
    front=int(record["front_edge"])
    party=set(json.loads(record["party_wall_edges"]))
    rng=random.Random(int(record["variation_seed"]))
    wall="stone_formal" if style=="STYLE_02" else ("plaster" if style=="STYLE_03" else "stone")
    report={"style":style,"center_world_cm":[center[0],center[1],min(p[2] for p in record["footprint_world_cm"])],
            "floors":floors,"floor_height_cm":floor_h,"front_edge":front,"edge_count":len(poly),"stages":{}}
    for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        if length<35:
            continue
        ux,uy=dx/length,dy/length
        out=(uy,-ux) if signed>0 else (-uy,ux)
        exterior=i not in party
        for floor in range(floors):
            z0=floor*floor_h
            z1=z0+floor_h
            mat="brick" if style=="STYLE_03" and floor==floors-1 else wall
            # Only the ground floor can contain a door; the rest are real openings.
            spans=[]
            if exterior and (i==front or length>600) and length>290:
                count=max(1,min(5,round(length/(280 if i==front else 440))))
                for j in range(count):
                    u=length*(j+.5)/count
                    is_door=(i==front and floor==0 and j==(count-1)//2)
                    if floor==0 and i!=front and j%2==0:
                        continue
                    ow=min(120 if is_door else (84 if style=="STYLE_01" else 100),length/count*.48)
                    oh=225 if is_door else (135 if style=="STYLE_02" else 120)
                    bottom=z0 if is_door else z0+(92 if floor else 112)
                    top=min(z1-34,bottom+oh)
                    if top-bottom<100:
                        continue
                    spans.append((u-ow/2,u+ow/2,bottom,top,is_door,u,ow))
                    anchor_z=(bottom+top)/2
                    if is_door:
                        door(a,ux,uy,out,u,anchor_z,ow,top-bottom,lot,style,style=="STYLE_04")
                    else:
                        balcony=(floor>0 and i==front and (style=="STYLE_02" or (j%2==0 and style!="STYLE_04")))
                        window(a,ux,uy,out,u,anchor_z,ow,top-bottom,lot,style,balcony,
                               style=="STYLE_04" and j%2==0)
            cuts=sorted({0.0,length,*(v for s in spans for v in s[:2])})
            for left,right in zip(cuts,cuts[1:]):
                w=right-left
                if w<2:
                    continue
                u=(left+right)/2
                op=next((s for s in spans if s[0]<u<s[1]),None)
                levels=[(z0,z1)] if op is None else [(z0,op[2]),(op[3],z1)]
                for lo,hi in levels:
                    if hi-lo>3:
                        edge_box("wall_masonry",a,ux,uy,out,u,0,(lo+hi)/2,w,42,hi-lo,
                                 mat,lot,"Structure")
            if exterior and style in {"STYLE_02","STYLE_03"} and floor<floors-1:
                edge_box("stone_floor_course",a,ux,uy,out,length/2,10,z1-6,length,54,12,
                         "stone_formal" if style=="STYLE_02" else "concrete",lot,"Facades",1)
        if exterior:
            edge_box("stone_plinth",a,ux,uy,out,length/2,18,20,length,52,40,
                     "stone" if style!="STYLE_03" else "concrete",lot,"Facades",1)
            edge_box("worn_cornice",a,ux,uy,out,length/2,16,height-8,length,60,18,
                     "stone_formal" if style=="STYLE_02" else "stone",lot,"Facades",2)
            if style=="STYLE_02" and length>250:
                for u in (22,length-22):
                    edge_box("formal_corner_pilaster",a,ux,uy,out,u,15,height/2,28,65,height,
                             "stone_formal",lot,"Facades",1)
            if style=="STYLE_04" and i==front:
                for u in (length*.12,length*.84):
                    edge_box("masonry_repair",a,ux,uy,out,u,24,105,68,4,152,
                             "plaster",lot,"Facades",1)
            if style=="STYLE_03" and i==front:
                edge_box("old_plaster_patch",a,ux,uy,out,length*.19,23,height*.42,
                         min(138,length*.18),4,111,"plaster_pale",lot,"Facades",1)
        if i==front:
            # The rainwater pipe is deliberately attached to the facade.
            edge_box("wall_downpipe",a,ux,uy,out,max(42,length-45),33,height/2,9,10,height,
                     "iron",lot,"Details")
            if style=="STYLE_04":
                # Courtyard entrance wall ends flush at the building, with no floating ends.
                gate_width=min(230,length*.28)
                gate_u=length*.76
                for j in range(8):
                    edge_box("courtyard_gate_bar",a,ux,uy,out,gate_u-gate_width/2+j*gate_width/7,
                             67,105,5,5,210,"iron",lot,"Details")
                for zz in (22,188):
                    edge_box("courtyard_gate_rail",a,ux,uy,out,gate_u,67,zz,gate_width,8,9,"iron",lot,"Details")
                # Bathroom cantilevers from the wall at first-floor height.
                bath_z=floor_h+55
                bath_u=length*.18
                edge_box("bath_floor",a,ux,uy,out,bath_u,92,bath_z,150,170,16,"stone",lot,"Details",2)
                edge_box("bath_front",a,ux,uy,out,bath_u,169,bath_z+100,150,16,195,"plaster",lot,"Details")
                for j in (-1,1):
                    edge_box("bath_side",a,ux,uy,out,bath_u+j*75,88,bath_z+100,15,165,195,"plaster",lot,"Details")
                    edge_box("bath_bracket",a,ux,uy,out,bath_u+j*55,56,bath_z-43,14,95,75,"stone",lot,"Details")
                edge_box("bath_roof",a,ux,uy,out,bath_u,91,bath_z+203,168,185,14,"terracotta",lot,"Details",2)
                # Sparse vine stems stay on the wall plane and rise from the ground.
                for j in range(3):
                    u=length*(.07+.04*j)
                    edge_box("climbing_vine",a,ux,uy,out,u,29,65+j*22,3,4,130+j*43,"moss",lot,"Details")

    roof="concrete" if style=="STYLE_02" else "terracotta"
    poly_mesh("roof_slab",poly,height+18,roof,lot,"Roofs",18)
    if style=="STYLE_02":
        for i,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dy)
            if length<100 or i in party:
                continue
            ux,uy=dx/length,dy/length
            out=(uy,-ux) if signed>0 else (-uy,ux)
            edge_box("terrace_parapet",a,ux,uy,out,length/2,5,height+45,length,35,55,
                     "stone_formal",lot,"Roofs",2)
    else:
        # A pitched tiled crown with a recognizable terracotta edge. Roof coverage
        # follows the exact lot polygon; these courses provide the street silhouette.
        a=poly[front]
        b=poly[(front+1)%len(poly)]
        dx,dy=b[0]-a[0],b[1]-a[1]
        length=math.hypot(dx,dy)
        ux,uy=dx/length,dy/length
        out=(uy,-ux) if signed>0 else (-uy,ux)
        for j in range(max(1,int(length/31))):
            u=(j+.5)*length/max(1,int(length/31))
            edge_box("coppo_eave",a,ux,uy,out,u,31,height+24,27,24,15,
                     "terracotta",lot,"Roofs",2)
    REPORT["pilot_lots"][lot]=report


def export_stage(lot,style,stage):
    items=OBJECTS[(lot,stage)]
    if not items:
        REPORT["warnings"].append(f"Empty stage {lot} {stage}")
        return
    bpy.ops.object.select_all(action="DESELECT")
    for obj in items:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=items[0]
    name=f"SM_M80_{lot}_{stage}"
    file=FBX/(name+".fbx")
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,apply_unit_scale=True,
                             global_scale=1.0,axis_forward="-Y",axis_up="Z",
                             use_mesh_modifiers=True,add_leaf_bones=False,path_mode="COPY",
                             embed_textures=False)
    REPORT["assets"][name]={"lot":lot,"style":style,"stage":stage,
                            "fbx":str(file.relative_to(ROOT)).replace("\\","/"),
                            "object_count":len(items),
                            "materials":sorted({m.name for o in items for m in o.data.materials})}
    REPORT["pilot_lots"][lot]["stages"][stage]=name


def render_pilot(lot,style):
    scene=bpy.context.scene
    for (other,_stage),items in OBJECTS.items():
        for obj in items:
            obj.hide_render=other!=lot
    pts=[o for (other,_stage),items in OBJECTS.items() if other==lot for o in items]
    bpy.context.view_layer.update()
    bounds=[o.matrix_world @ Vector(corner) for o in pts for corner in o.bound_box]
    mins=Vector(tuple(min(v[i] for v in bounds) for i in range(3)))
    maxs=Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
    size=max((maxs-mins).x,(maxs-mins).y,(maxs-mins).z,700)
    camera_data=bpy.data.cameras.new("PilotCamera_"+lot)
    camera=bpy.data.objects.new("PilotCamera_"+lot,camera_data)
    scene.collection.objects.link(camera)
    center=(mins+maxs)/2
    camera.location=center+Vector((size*.85,-size*1.4,size*.72))
    camera.rotation_euler=(center-camera.location).to_track_quat("-Z","Y").to_euler()
    camera_data.type="ORTHO"
    camera_data.ortho_scale=size*1.65
    camera_data.clip_end=100000
    scene.camera=camera
    scene.render.filepath=str(PREVIEW/(lot+"_"+style+".png"))
    bpy.ops.render.render(write_still=True)
    camera.hide_render=True
    REPORT["pilot_lots"][lot]["preview"]=str(Path(scene.render.filepath).relative_to(ROOT)).replace("\\","/")


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system="METRIC"
    bpy.context.scene.unit_settings.scale_length=.01
    for name,(low,high,roughness) in PALETTE.items():
        make_material(name,low,high,roughness)
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=20
    scene.render.resolution_x=1000
    scene.render.resolution_y=760
    scene.render.resolution_percentage=100
    scene.world.color=(.48,.58,.68)
    light_data=bpy.data.lights.new("MediterraneanSun","SUN")
    light=bpy.data.objects.new("MediterraneanSun",light_data)
    scene.collection.objects.link(light)
    light.rotation_euler=(math.radians(26),math.radians(-17),math.radians(32))
    light_data.energy=2.0
    light_data.angle=math.radians(4)
    records={r["building_id"]:r for r in CATALOG["buildings"]}
    for lot,style in LOTS.items():
        build_house(records[lot],style)
        for stage in STAGES:
            export_stage(lot,style,stage)
        render_pilot(lot,style)
    for items in OBJECTS.values():
        for obj in items:
            obj.hide_render=False
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Mazzarino_Stylized_Pilots_v1.blend"))
    (OUT/"manifest.json").write_text(json.dumps(REPORT,indent=2),encoding="utf-8")
    print("M80_STYLIZED_PILOTS",json.dumps({"assets":len(REPORT["assets"]),"lots":len(REPORT["pilot_lots"]),"warnings":REPORT["warnings"]}))


if __name__=="__main__":
    main()
