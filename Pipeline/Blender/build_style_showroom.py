"""Blender 4.3 style showroom: four human-scale houses assembled from editable parts.

This is the visual-quality gate before UE import or PCG replacement.  The
footprint pilots produced by build_stylized_pilots.py are only scale tests.
"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_stylized_pilots as k

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Pipeline/Blender/output/style_showroom_v1"
OUT.mkdir(parents=True, exist_ok=True)
STYLES = ("STYLE_01", "STYLE_02", "STYLE_03", "STYLE_04")
PARTS = defaultdict(list)
CURRENT_PART = None


def mark(obj, part):
    if obj:
        obj["module_type"] = part
        PARTS[part].append(obj)
    return obj


def b(lot,stage,part,name,pos,size,mat,bevel=0):
    return mark(k.box(name,pos,size,mat,lot,stage,bevel=bevel),part)


def front(lot,stage,part,name,x,y,z,w,d,h,mat,bevel=0):
    return b(lot,stage,part,name,(x,y,z),(w,d,h),mat,bevel)


def wall_with_opening(lot,part,cx,y,z0,w,h,ow,oh,bottom,mat):
    left=(w-ow)/2
    for sign in (-1,1):
        front(lot,"Structure",part,"masonry_pier",cx+sign*(ow/2+left/2),y,z0+h/2,left,42,h,mat)
    if bottom>0:
        front(lot,"Structure",part,"masonry_sill",cx,y,z0+bottom/2,ow,42,bottom,mat)
    top=h-bottom-oh
    if top>0:
        front(lot,"Structure",part,"masonry_lintel",cx,y,z0+bottom+oh+top/2,ow,42,top,mat)


def facade_panel(lot,part,x,y,z0,w,h,mat):
    front(lot,"Structure",part,"masonry_full",x,y,z0+h/2,w,42,h,mat)


def frame_window(lot,part,x,y,z0,w,h,style,shutter="green_wood"):
    stone="stone_formal" if style=="STYLE_02" else ("concrete" if style=="STYLE_03" else "stone")
    front(lot,"Openings",part,"deep_reveal",x,y+16,z0+h/2,w+4,7,h+4,"iron")
    front(lot,"Openings",part,"aged_glass",x,y+12,z0+h/2,w-14,4,h-14,"glass")
    for sign in (-1,1):
        front(lot,"Openings",part,"frame_jamb",x+sign*(w/2+8),y-13,z0+h/2,16,30,h+28,stone,2)
        front(lot,"Openings",part,"sash_stile",x+sign*(w/2-8),y+5,z0+h/2,8,9,h-12,"wood")
    front(lot,"Openings",part,"frame_header",x,y-13,z0+h+8,w+32,31,18,stone,2)
    front(lot,"Openings",part,"deep_sill",x,y-20,z0-8,w+43,38,17,stone,2)
    front(lot,"Openings",part,"center_mullion",x,y+3,z0+h/2,8,11,h-15,"wood")
    front(lot,"Openings",part,"horizontal_transom",x,y+3,z0+h*.62,w-12,11,7,"wood")
    if style=="STYLE_03" and shutter=="roller":
        front(lot,"Openings",part,"roller_housing",x,y-26,z0+h-9,w+16,22,22,"concrete",2)
        for sign in (-1,1):
            front(lot,"Openings",part,"roller_guide",x+sign*(w/2-2),y-23,z0+h/2,6,12,h-19,"iron")
    elif shutter=="boarded":
        for sign in (-1,1):
            front(lot,"Openings",part,"weathered_board",x+sign*w*.22,y-28,z0+h/2,w*.39,9,h-15,"wood",2)
        front(lot,"Openings",part,"board_crossbar",x,y-37,z0+h*.45,w-11,8,9,"wood")
    else:
        for sign in (-1,1):
            sx=x+sign*(w*.72)
            leaf_w=w*.41
            leaf_h=h*.91
            for side in (-1,1):
                front(lot,"Openings",part,"shutter_frame_stile",sx+side*leaf_w*.46,y-29,
                      z0+h/2,7,9,leaf_h,shutter,1)
            for zz in (z0+h/2-leaf_h*.47,z0+h/2+leaf_h*.47):
                front(lot,"Openings",part,"shutter_frame_rail",sx,y-29,zz,
                      leaf_w,9,8,shutter,1)
            for j in range(12):
                front(lot,"Openings",part,"aged_wood_louvre",sx,y-32,
                      z0+h/2-leaf_h*.43+j*leaf_h*.86/11,
                      leaf_w-11,7,4,shutter,1)


def entrance(lot,part,x,y,z0,w,h,style):
    trim="stone_formal" if style=="STYLE_02" else "stone"
    front(lot,"Openings",part,"door_shadow",x,y+15,z0+h/2,w-10,4,h-9,"iron")
    front(lot,"Openings",part,"timber_door",x,y+7,z0+h/2,w-18,8,h-18,"wood",3)
    for s in (-1,1):
        front(lot,"Openings",part,"door_jamb",x+s*(w/2+10),y-15,z0+h/2,18,30,h+18,trim,2)
        front(lot,"Openings",part,"recessed_panel",x+s*w*.23,y-5,z0+h*.55,w*.37,6,h*.56,"wood",2)
    front(lot,"Openings",part,"door_lintel",x,y-15,z0+h+10,w+42,35,20,trim,2)
    front(lot,"Details",part,"threshold",x,y-38,z0+4,w+50,60,8,trim,2)
    front(lot,"Details",part,"door_knocker",x+w*.16,y-15,z0+h*.54,9,8,12,"iron",2)
    if style=="STYLE_02":
        for j in range(9):
            theta=math.pi*j/8
            front(lot,"Openings",part,"cut_stone_arch",
                  x+math.cos(theta)*(w*.58),y-25,z0+h+math.sin(theta)*w*.26,
                  18,29,16,"stone_formal",2)


def balcony_door(lot,part,x,y,z0,w,h):
    """Two glazed timber leaves and deeply recessed green louvred shutters."""
    front(lot,"Openings",part,"door_reveal",x,y+18,z0+h/2,w-12,8,h-10,"iron")
    front(lot,"Openings",part,"two_leaf_glazing",x,y+10,z0+h*.61,w-29,5,h*.70,"glass")
    for side in (-1,1):
        front(lot,"Openings",part,"aged_stone_jamb",x+side*(w/2+12),y-19,z0+h/2,22,39,h+27,"stone",2)
        leaf_x=x+side*w*.225
        front(lot,"Openings",part,"lower_timber_panel",leaf_x,y+4,z0+h*.15,w*.42,8,h*.30,"wood",2)
        for local_x in (-1,1):
            front(lot,"Openings",part,"sash_stile",leaf_x+local_x*w*.205,y-3,z0+h*.64,
                  7,10,h*.69,"wood",1)
        front(lot,"Openings",part,"sash_transom",leaf_x,y-3,z0+h*.88,w*.42,10,7,"wood",1)
        shutter_x=x+side*w*.73
        shutter_w=w*.43
        for local_x in (-1,1):
            front(lot,"Openings",part,"shutter_stile",shutter_x+local_x*shutter_w*.46,
                  y-33,z0+h/2,7,11,h*.94,"green_wood",1)
        for j in range(17):
            zz=z0+h*.055+j*h*.89/16
            slat=front(lot,"Openings",part,"angled_louvre",shutter_x,y-37,zz,
                       shutter_w-9,6,3.8,"green_wood",.4)
            slat.rotation_euler.x=math.radians(-20)
        for zz in (z0+h*.07,z0+h*.93):
            front(lot,"Openings",part,"shutter_crossrail",shutter_x,y-36,zz,
                  shutter_w,10,7,"green_wood",1)
    front(lot,"Openings",part,"cut_stone_lintel",x,y-21,z0+h+13,w+54,43,23,"stone",3)
    front(lot,"Openings",part,"worn_sill",x,y-32,z0-10,w+60,57,18,"stone",2)


def garage(lot,part,x,y,z0,w,h):
    front(lot,"Openings",part,"garage_dark",x,y+13,z0+h/2,w-13,5,h-13,"iron")
    for j in range(18):
        z=z0+12+j*(h-24)/18
        front(lot,"Openings",part,"aged_roller_slat",x,y-7,z,w-22,5,(h-24)/18-1,
              "concrete" if j%4 else "iron",.5)
    for s in (-1,1):
        front(lot,"Openings",part,"garage_jamb",x+s*(w/2+13),y-17,z0+h/2,23,39,h+27,"stone",2)
    front(lot,"Openings",part,"garage_header",x,y-17,z0+h+11,w+54,40,22,"stone",2)
    for j,xx in enumerate((-w*.31,-w*.12,w*.09,w*.34)):
        front(lot,"Details",part,"surface_rust",x+xx,y-11,z0+24+j*37,
              21,2,9,"terracotta")


def balcony(lot,part,x,y,z0,w,formal=False,concrete=False):
    slab="concrete" if concrete else ("stone_formal" if formal else "stone")
    front(lot,"Details",part,"balcony_slab",x,y-64,z0-11,w,147,19,slab,4)
    for d in (-.33,0,.33):
        front(lot,"Details",part,"cantilever_corbel",x+w*d,y-42,z0-48,20,83,72,slab,3)
    for s in (-1,1):
        sx=x+s*(w/2-5)
        for zz in (z0+12,z0+98):
            front(lot,"Details",part,"balcony_side_rail",sx,y-76,zz,7,107,7,"iron")
        for j in range(5):
            front(lot,"Details",part,"balcony_side_baluster",sx,y-121+j*23,z0+54,
                  6,5,87,"iron")
    front(lot,"Details",part,"rail_lower",x,y-131,z0+11,w,8,7,"iron")
    front(lot,"Details",part,"rail_upper",x,y-131,z0+99,w,8,9,"iron")
    for j in range(max(7,int(w/17))):
        xx=x-w*.47+j*w*.94/max(1,int(w/17)-1)
        front(lot,"Details",part,"forged_baluster",xx,y-132,z0+54,4,8,87,"iron")
        if formal and j%2==0:
            mark(k.cyl("decorated_ring",(xx,y-136,z0+55),9,3,"iron",lot,"Details",12,
                       (math.pi/2,0,0)),part)


def drain(lot,part,x,y,z0,height):
    front(lot,"Details",part,"aged_downpipe",x,y-31,z0+height/2,10,10,height,"iron")
    for j in (55,height*.5,height-50):
        front(lot,"Details",part,"downpipe_collar",x,y-34,z0+j,15,15,7,"terracotta",1)
    front(lot,"Details",part,"downpipe_outlet",x,y-59,z0+16,10,52,9,"iron")


def cables(lot,part,width,y,z):
    for i in range(3):
        front(lot,"Details",part,"period_cable",0,y-27-i*5,z+i*8,width-45,3,3,"iron")
    front(lot,"Details",part,"meter_box",width*.35,y-32,z-85,41,20,62,"concrete",2)
    for x in (-width*.35,width*.3):
        front(lot,"Details",part,"cable_clip",x,y-31,z,9,13,15,"iron")


def pot(lot,part,x,y,z,scale=1):
    mark(k.cyl("terracotta_pot",(x,y,z+21*scale),15*scale,42*scale,"terracotta",lot,"Details",12),part)
    mark(k.cyl("dark_pot_soil",(x,y,z+43*scale),13*scale,4*scale,"moss",lot,"Details",10),part)
    rng=random.Random(int(x+y+z))
    for j in range(8):
        dx=rng.uniform(-18,18)*scale
        dy=rng.uniform(-18,18)*scale
        front(lot,"Details",part,"plant_stem",x+dx*.6,y+dy*.6,z+65*scale,
              2*scale,2*scale,55*scale,"moss")
        mark(k.cyl("leaf_cluster",(x+dx,y+dy,z+rng.uniform(65,106)*scale),
                   rng.uniform(10,16)*scale,4*scale,"moss",lot,"Details",7,
                   (rng.uniform(-.4,.4),rng.uniform(-.4,.4),rng.uniform(-3,3))),part)


def cracked_patch(lot,part,x,y,z,w,h,mat):
    # A broken seven-sided island, close to the facade, not a white rectangular decal.
    rng=random.Random(int(abs(x)*31+z*17))
    verts=[]
    for j in range(13):
        angle=math.tau*j/13
        radius=rng.uniform(.65,1.07)
        verts.append((x+math.cos(angle)*w*.5*radius,y,
                      z+math.sin(angle)*h*.5*radius))
    mesh=bpy.data.meshes.new("irregular_plaster_loss")
    mesh.from_pydata(verts,[],[tuple(range(len(verts)))])
    mesh.materials.append(k.MATERIALS[mat])
    uv=mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for idx in poly.loop_indices:
            p=mesh.vertices[mesh.loops[idx].vertex_index].co
            uv.data[idx].uv=(p.x/320,p.z/320)
    obj=bpy.data.objects.new("localized_wear",mesh)
    bpy.context.scene.collection.children[lot].objects.link(obj)
    k.OBJECTS[(lot,"Facades")].append(obj)
    mark(obj,part)


def roof(lot,style,width,depth,height):
    y=0
    if style in {"STYLE_02","STYLE_03"}:
        b(lot,"Roofs","roof_flat","weathered_terrace",(0,0,height+9),(width+34,depth+34,18),
          "concrete" if style=="STYLE_03" else "stone_formal",2)
        for x in (-width/2,width/2):
            b(lot,"Roofs","parapet","side_parapet",(x,0,height+37),(33,depth+36,55),
              "plaster" if style=="STYLE_03" else "stone_formal",2)
        for y in (-depth/2,depth/2):
            b(lot,"Roofs","parapet","roof_parapet",(0,y,height+37),(width+40,28,55),
              "plaster" if style=="STYLE_03" else "stone_formal",2)
            front(lot,"Roofs","parapet","terrace_cap",0,y,height+69,width+60,40,12,
                  "stone_formal",3)
            if style=="STYLE_03":
                for j in range(8):
                    xx=-width*.46+j*width*.92/7
                    front(lot,"Roofs","roof_iron_rail","terrace_baluster",xx,y,height+101,
                          4,4,68,"iron")
                front(lot,"Roofs","roof_iron_rail","terrace_hand_rail",0,y,height+137,
                      width*.96,5,6,"iron")
        for x in (-width/2+17,width/2-17):
            for y in (-depth/2+17,depth/2-17):
                b(lot,"Roofs","parapet","roof_corner_finial",(x,y,height+82),(45,45,43),
                  "stone_formal",3)
    else:
        # Two pitch wedges as real planar geometry, with tiled material and fascia.
        coords=[(-width/2-25,-depth/2-27,height+8),(width/2+25,-depth/2-27,height+8),
                (width/2+25,0,height+118),(-width/2-25,0,height+118),
                (-width/2-25,depth/2+27,height+8),(width/2+25,depth/2+27,height+8)]
        faces=[(0,1,2,3),(3,2,5,4)]
        mesh=bpy.data.meshes.new("pitched_coppi")
        mesh.from_pydata(coords,[],faces)
        mesh.materials.append(k.MATERIALS["terracotta"])
        uv=mesh.uv_layers.new(name="UVMap")
        for poly in mesh.polygons:
            for idx in poly.loop_indices:
                v=mesh.vertices[mesh.loops[idx].vertex_index].co
                uv.data[idx].uv=(v.x/180,v.y/180)
        obj=bpy.data.objects.new("pitched_roof_surface",mesh)
        bpy.context.scene.collection.children[lot].objects.link(obj)
        k.OBJECTS[(lot,"Roofs")].append(obj)
        mark(obj,"roof_pitched")
        for y in (-depth/2-27,depth/2+27):
            front(lot,"Roofs","roof_pitched","tile_eave",0,y,height+9,width+55,25,18,"terracotta",2)
        b(lot,"Roofs","roof_pitched","ridge_coppi",(0,0,height+122),(width+55,28,20),"terracotta",2)
        if style=="STYLE_04":
            slope=math.atan2(110,depth/2+27)
            for x0,y0,w0,h0 in [(-width*.24,-depth*.16,68,75),
                                (width*.24,-depth*.30,56,46),
                                (width*.10,-depth*.04,43,59)]:
                z0=height+8+(y0+depth/2+27)/(depth/2+27)*110+2
                patch=b(lot,"Roofs","roof_missing_tiles","dark_missing_coppi",
                        (x0,y0,z0),(w0,h0,3),"wood")
                patch.rotation_euler.x=slope


def stairs(lot,width,depth,h):
    x=width/2+85
    for j in range(17):
        y=-depth/2+33+j*(depth-70)/17
        z=11+j*h/17
        b(lot,"Details","exterior_stair","worn_stair_tread",(x,y,z),(148,depth/17+3,20),"stone",3)
    b(lot,"Details","exterior_stair","stair_side_wall",(x+66,0,h*.46),(18,depth-35,h*.92),"plaster",2)
    b(lot,"Details","exterior_stair","stair_landing",(x,depth/2-5,h+2),(190,100,19),"stone",3)


def house(style,width,depth,floors,floor_h):
    lot=style
    k.new_collection(lot)
    h=floors*floor_h
    y=-depth/2
    wall="stone_formal" if style=="STYLE_02" else ("stone_wall" if style in {"STYLE_01","STYLE_04"} else "plaster")
    for floor in range(floors):
        z=floor*floor_h
        if style=="STYLE_03" and floor==0:
            slots=[(-width*.25,width*.50,"garage"),(width*.25,width*.50,"door")]
        elif style=="STYLE_03":
            slots=[(-width*.25,width*.5,"window"),(width*.25,width*.5,"balcony_door")]
        elif style=="STYLE_02":
            slots=[(-width/3,width/3,"window"),(0,width/3,"door" if floor==0 else "window"),
                   (width/3,width/3,"window")]
        else:
            slots=[(-width*.25,width*.5,"window" if floor>0 else "door"),
                   (width*.25,width*.5,"window")]
        for j,(cx,bay,kind) in enumerate(slots):
            mat=wall
            if kind=="garage":
                ow=min(240,bay-35); oh=210; bot=0
            elif kind=="balcony_door":
                ow=145; oh=218; bot=7
            elif kind=="door":
                ow=108 if style!="STYLE_02" else 130; oh=222; bot=0
            else:
                ow=95 if style=="STYLE_02" else 86; oh=133; bot=88
            part=f"wall_{style}_{floor}_{j}"
            wall_with_opening(lot,part,cx,y,z,bay,floor_h,ow,oh,bot,mat)
            if kind=="garage": garage(lot,"garage_aged",cx,y,z,ow,oh)
            elif kind=="door": entrance(lot,"entrance_wood",cx,y,z,ow,oh,style)
            elif kind=="balcony_door":
                balcony_door(lot,"balcony_door_green",cx,y,z+bot,ow,oh)
                balcony(lot,"balcony_ornate",cx,y,z+bot,bay-13,False,False)
            else:
                shutter="boarded" if style=="STYLE_04" and j==0 else ("roller" if style=="STYLE_03" and j==0 else "green_wood")
                frame_window(lot,"window_"+shutter,cx,y,z+bot,ow,oh,style,shutter)
                has_balcony=(style=="STYLE_02" and ((floor==1 and j==1) or (floor==2 and j!=1))) or (style in {"STYLE_01","STYLE_04"} and j==0)
                if floor>0 and has_balcony:
                    balcony(lot,"balcony_ornate" if style=="STYLE_02" else "balcony_simple",
                            cx,y,z+bot,min(bay-8,ow+(190 if style=="STYLE_03" else 130)),
                            style=="STYLE_02",style=="STYLE_03")
        if floor<floors-1:
            front(lot,"Facades","floor_course","aged_floor_course",0,y-15,z+floor_h,
                  width+20,62,12,"stone_formal" if style=="STYLE_02" else "stone",2)
    for side in (-1,1):
        x=side*width/2
        if side==-1:
            b(lot,"Structure","side_wall","side_masonry",(x,0,h/2),(42,depth,h),wall)
        else:
            for floor in range(floors):
                side_door=style=="STYLE_03" and floor==1
                cy=depth/2-76 if side_door else depth*.1
                ow=92 if side_door else 86
                oh=205 if side_door else 120
                bottom=0 if side_door else 80
                for a0,a1 in ((-depth/2,cy-ow/2),(cy+ow/2,depth/2)):
                    if a1-a0>1:
                        b(lot,"Structure","side_wall","side_masonry",(x,(a0+a1)/2,
                          floor*floor_h+floor_h/2),(42,a1-a0,floor_h),wall)
                if bottom:
                    b(lot,"Structure","side_wall","side_sill_masonry",(x,cy,
                      floor*floor_h+bottom/2),(42,ow,bottom),wall)
                top=floor_h-bottom-oh
                if top>0:
                    b(lot,"Structure","side_wall","side_header_masonry",(x,cy,
                      floor*floor_h+bottom+oh+top/2),(42,ow,top),wall)
                z=floor*floor_h+bottom
                b(lot,"Openings","side_door" if side_door else "side_window",
                  "side_recess",(x+side*10,cy,z+oh/2),(5,ow-10,oh-10),
                  "wood" if side_door else "glass")
                for dy in (-ow/2-8,ow/2+8):
                    b(lot,"Openings","side_door" if side_door else "side_window",
                      "side_window_jamb",(x+side*29,cy+dy,z+oh/2),
                      (17,15,oh+19),"stone",2)
                b(lot,"Openings","side_door" if side_door else "side_window",
                  "side_window_sill",(x+side*33,cy,z-6),(24,ow+38,13),"stone",2)
                b(lot,"Openings","side_door" if side_door else "side_window",
                  "side_window_header",(x+side*33,cy,z+oh+7),(24,ow+35,14),"stone",2)
    b(lot,"Structure","back_wall","back_masonry",(0,depth/2,h/2),(width,42,h),wall)
    front(lot,"Facades","plinth","stone_basecourse",0,y-24,35,width+22,26,70,"stone",2)
    front(lot,"Facades","cornice","worn_cornice",0,y-18,h-12,width+38,71,23,
          "stone_formal" if style=="STYLE_02" else "stone",3)
    if style=="STYLE_02":
        for x in (-width/2+20,width/2-20):
            front(lot,"Facades","formal_pilaster","stone_pilaster",x,y-26,h/2,41,76,h,
                  "stone_formal",2)
    roof(lot,style,width,depth,h)
    drain(lot,"drainpipe_old",-width/2+33,y,0,h)
    drain(lot,"drainpipe_old",width/2-33,y,0,h)
    cables(lot,"cables_and_meter",width,y,h-72)
    if style=="STYLE_03":
        stairs(lot,width,depth,floor_h)
    if style in {"STYLE_03","STYLE_04"}:
        for x,z,w,hh in [(-width*.48,67,42,74),(-width*.07,36,53,48),
                          (width*.47,77,40,81),(width*.07,h*.72,44,43),
                          (width*.45,h*.77,49,52)]:
            cracked_patch(lot,"localized_plaster_loss",x,y-24,z,w,hh,"stone")
    if style=="STYLE_03":
        cracked_patch(lot,"exposed_old_brick",-width*.05,y-25,h*.65,43,38,"brick")
    if style=="STYLE_04":
        for x,z,w,hh in [(width*.43,185,47,58),(-width*.43,h*.55,42,55)]:
            cracked_patch(lot,"old_repair",x,y-27,z,w,hh,"plaster")
    pot_xs=(width*.08,width*.25,width*.42) if style=="STYLE_03" else (-width*.34,-width*.18,width*.25)
    for j,x in enumerate(pot_xs):
        if style=="STYLE_04" and j==2:
            continue
        pot(lot,"terracotta_pot",x,y-92 if style=="STYLE_03" else y-117,
            floor_h+8 if style=="STYLE_03" else floor_h+94,.72 if j else 1)
    if style in {"STYLE_01","STYLE_03"}:
        # Small street-level belongings anchor the facade at pedestrian scale.
        pot(lot,"terracotta_pot_ground",-width*.42,y-76,0,1.2)
        pot(lot,"terracotta_pot_ground",width*.43,y-75,0,.82)
    front(lot,"Details","wall_lamp","lamp_wall_bracket",width*.25,y-37,floor_h-37,
          12,51,8,"iron")
    mark(k.cyl("warm_bulb",(width*.25,y-74,floor_h-52),13,18,
               "concrete",lot,"Details",12),"wall_lamp")
    if style=="STYLE_04":
        for j in range(5):
            front(lot,"Details","ivy_on_wall","climbing_vine",width*.41+j*7,y-28,60+j*36,
                  4,5,127+j*19,"moss")
            for q in range(4):
                mark(k.cyl("ivy_leaves",(width*.39+j*8,y-34,105+j*34+q*42),
                           9+q*2,3,"moss",lot,"Details",7,
                           (math.pi/2,0,j*.4)),"ivy_on_wall")
    # A true 180 cm scale check beside every house.
    ref=b(lot,"Details","scale_ruler","scale_180cm",(width/2+185,y-80,90),(8,8,180),"iron")
    ref["reference_height_cm"]=180


def render_style(style):
    scene=bpy.context.scene
    for (lot,_),items in k.OBJECTS.items():
        for obj in items:
            obj.hide_render=lot!=style or obj.get("module_type")=="scale_ruler"
    bpy.context.view_layer.update()
    pts=[o for (lot,_),items in k.OBJECTS.items() if lot==style for o in items]
    bounds=[o.matrix_world @ Vector(c) for o in pts for c in o.bound_box]
    mins=Vector(tuple(min(p[i] for p in bounds) for i in range(3)))
    maxs=Vector(tuple(max(p[i] for p in bounds) for i in range(3)))
    target=(mins+maxs)/2
    target.z=maxs.z*.46
    span=max((maxs-mins).x,(maxs-mins).y,(maxs-mins).z)
    camera=scene.camera
    camera.location=target+Vector((span*1.02,-span*1.67,span*.72))
    camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.ortho_scale=span*1.53
    scene.render.filepath=str(OUT/(style+"_assembled.png"))
    bpy.ops.render.render(write_still=True)


def map_facade_across_house(style,width,depth,height):
    """Facade-scale UVs avoid repeating one patch on every wall bay."""
    bpy.context.view_layer.update()
    for (lot,_stage),items in k.OBJECTS.items():
        if lot!=style:
            continue
        for obj in items:
            if obj.type!="MESH" or not any(mat and mat.name in {"M80_plaster","M80_stone_wall"} for mat in obj.data.materials):
                continue
            uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name="UVMap")
            for face in obj.data.polygons:
                normal=obj.matrix_world.to_3x3() @ face.normal
                for idx in face.loop_indices:
                    p=obj.matrix_world @ obj.data.vertices[obj.data.loops[idx].vertex_index].co
                    if abs(normal.y)>.5:
                        u=(p.x+width/2)/width
                        v=p.z/(height+155)
                    elif abs(normal.x)>.5:
                        u=(p.y+depth/2)/depth
                        v=p.z/(height+155)
                    else:
                        u=(p.x+width/2)/width
                        v=(p.y+depth/2)/depth
                    uv.data[idx].uv=(u,v)


def export_module(part,objects):
    if part.startswith("wall_STYLE"):
        return
    source=objects
    if not source:
        return
    lot=next((key[0] for key,items in k.OBJECTS.items() if source[0] in items),None)
    # An editable Blender file preserves every finished piece as its own mesh.
    # FBX stage export remains a technical bridge until the visual gate passes.


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    k.OBJECTS.clear()
    k.MATERIALS.clear()
    for name,(lo,hi,r) in k.PALETTE.items():
        k.make_material(name,lo,hi,r)
    k.make_material("stone_wall",*k.PALETTE["stone"])
    generated=OUT/"T_M80_Plaster_Warm_Generated_v1.png"
    if generated.exists():
        tex_node=next(n for n in k.MATERIALS["plaster"].node_tree.nodes if n.type=="TEX_IMAGE")
        tex_node.image=bpy.data.images.load(str(generated),check_existing=True)
        tex_node.image.pack()
        tex_node.extension="EXTEND"
    limestone=OUT/"T_M80_Limestone_Generated_v1.png"
    if limestone.exists():
        tex_node=next(n for n in k.MATERIALS["stone_wall"].node_tree.nodes if n.type=="TEX_IMAGE")
        tex_node.image=bpy.data.images.load(str(limestone),check_existing=True)
        tex_node.image.pack()
        tex_node.extension="EXTEND"
    scene=bpy.context.scene
    scene.unit_settings.system="METRIC"
    scene.unit_settings.scale_length=.01
    scene.render.engine="CYCLES"
    scene.cycles.samples=48
    scene.render.resolution_x=1000
    scene.render.resolution_y=1200
    scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.84,.87,.91,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.8
    sun=bpy.data.lights.new("SicilianSun","SUN")
    obj=bpy.data.objects.new("SicilianSun",sun)
    scene.collection.objects.link(obj)
    obj.rotation_euler=(math.radians(26),math.radians(-20),math.radians(-27))
    sun.energy=2.0
    sun.angle=math.radians(5)
    camera_data=bpy.data.cameras.new("ArtDirectionCamera")
    camera_data.type="ORTHO"
    camera_data.clip_end=100000
    camera=bpy.data.objects.new("ArtDirectionCamera",camera_data)
    scene.collection.objects.link(camera)
    scene.camera=camera
    configs=(("STYLE_01",620,500,2,290),("STYLE_02",840,550,3,300),
             ("STYLE_03",700,520,2,285),("STYLE_04",560,490,2,275))
    for args in configs:
        house(*args)
        map_facade_across_house(args[0],args[1],args[2],args[3]*args[4])
        render_style(args[0])
    for items in k.OBJECTS.values():
        for obj in items:
            obj.hide_render=False
    # Keep all four ready-to-inspect examples visible side-by-side in the .blend.
    for index,style in enumerate(STYLES):
        for (lot,_),items in k.OBJECTS.items():
            if lot==style:
                for obj in items:
                    obj.location.x+=(index-1.5)*1400
                    if obj.get("module_type")=="scale_ruler":
                        obj.hide_render=True
    scene.render.filepath=""
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Mazzarino_4_Stili_Showroom.blend"))
    report={"blender":bpy.app.version_string,"houses":list(STYLES),
            "parts":{key:len(items) for key,items in PARTS.items()},
            "review_state":"visual-prototype: requires reference comparison before Unreal import",
            "total_objects":sum(len(v) for v in k.OBJECTS.values())}
    (OUT/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("M80_SHOWROOM",json.dumps({"houses":len(STYLES),"parts":len(PARTS),"objects":report["total_objects"]}))


if __name__=="__main__":
    main()
