"""Blender 5.2: the hospital (D:/Mazzarino80_Sorgenti/Edifici/ospedale.blend) split into pieces at its real size.

Run: blender -b "D:/Mazzarino80_Sorgenti/Edifici/ospedale.blend" --python m80_ospedale_pezzi.py -- [foto_dir]
The model was about twice its real size (7 m storeys, an 8.6 m door): to fill its lot in the town it had to be enlarged
and the entrance steps came out 1.5 m high. Here everything is scaled by SCALE (3.5 m storeys) and sorted into
collections, one mesh each in Unreal (m80_prepare_vehicle.py key OspedaleModulare):
- OSP_Struttura   the building: bodies, roofs, doors and windows, air conditioners, fire escape, ramps and their railings
- OSP_Annesso     the low building at the back of the lot ("DietroGabbiotto")
- OSP_Gabbiotto   the gatehouse
- OSP_Cancello    the gate pillars, the two leaves and the side gate
- OSP_Insegne     the gold lettering of the facade
- OSP_RecintoPilastro, OSP_RecintoPannello  one pillar and one railing panel of the perimeter fence, at the origin: the
                  fence itself is drawn in Unreal along a spline that repeats them
Kept in the file but not exported: OSP_RecinzioneOriginale (the whole original perimeter, for reference) and
OSP_Escluso (the ambulance, imported later as a vehicle, and the ground and pavement planes).
Saves D:/Mazzarino80_Sorgenti/Edifici/Ospedale/OspedalePezzi.blend (refuses to overwrite it without
M80_SOVRASCRIVI=1: the user may have edited it). With foto_dir: views of each piece next to a 1.80 m figure.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FOTO = ARGS[0] if ARGS else ""
DST = r"D:/Mazzarino80_Sorgenti/Edifici/Ospedale/OspedalePezzi.blend"
SCALE = 0.5

GROUPS = {
    "OSP_Annesso": ["DietroGabbiotto"],
    "OSP_Gabbiotto": ["Gabbiotto"],
    "OSP_Cancello": ["COlonneingresso", "ColonneIngresso1.002", "Cube.004", "ringhierasingola2.002", "ringhierasingola2.003"],
    "OSP_Insegne": ["Ospedale_circoscrizionale"],
    "OSP_RecinzioneOriginale": ["PilastriCOnfine", "PilastriCOnfine2", "PilastriCOnfine3", "Pilastro", "Plane.002", "Plane.003",
                                "Plane.009", "Plane.011", "Plane.012", "RinghieraFreccia", "RInghieraFreccia",
                                "ringhieramultipla", "ringhierasingola2.001"],
    "OSP_Escluso": ["Plane", "Plane.001"],
}
MODULE = {"OSP_RecintoPilastro": "Pilastro", "OSP_RecintoPannello": "ringhierasingola2.001"}


def collection(name, hidden=False):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    c.hide_render = hidden
    vl = bpy.context.view_layer.layer_collection.children.get(name)
    if vl:
        vl.hide_viewport = hidden
    return c


def move_to(o, c):
    for old in list(o.users_collection):
        old.objects.unlink(o)
    c.objects.link(o)


def main():
    if os.path.exists(DST) and os.environ.get("M80_SOVRASCRIVI") != "1":
        print("M80 OspedalePezzi.blend esiste gia': M80_SOVRASCRIVI=1 per rifarlo")
        return
    sc = bpy.context.scene
    # real size: everything scaled about the origin (children follow their parents)
    S = Matrix.Scale(SCALE, 4)
    for o in [o for o in sc.objects if o.parent is None]:
        o.matrix_world = S @ o.matrix_world
    bpy.context.view_layer.update()
    placed = set()
    for cname, names in GROUPS.items():
        c = collection(cname, hidden=cname in ("OSP_RecinzioneOriginale", "OSP_Escluso"))
        for n in names:
            o = bpy.data.objects.get(n)
            if o:
                move_to(o, c)
                placed.add(n)
    esc = collection("OSP_Escluso", hidden=True)
    for o in list(sc.objects):
        if any(c.name in ("Ambulance",) for c in o.users_collection) or (o.parent and o.parent.name in placed and False):
            move_to(o, esc)
            placed.add(o.name)
    # the fence module: copies of one pillar and one panel, standing on the origin
    for cname, src in MODULE.items():
        c = collection(cname)
        s = bpy.data.objects.get(src)
        if not s:
            continue
        o = s.copy()
        o.data = s.data.copy()
        o.name = cname.replace("OSP_", "")
        c.objects.link(o)
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
        lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        o.matrix_world = Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))) @ o.matrix_world
        print("M80 modulo", o.name, "m", [round(v, 3) for v in (hi - lo)])
    # everything else is the building
    st = collection("OSP_Struttura")
    module_objs = {c.replace("OSP_", "") for c in MODULE}
    for o in list(sc.objects):
        if o.name in placed or o.name in module_objs or o.type not in ("MESH", "CURVE", "FONT", "EMPTY"):
            continue
        if not any(c.name.startswith("OSP_") for c in o.users_collection):
            move_to(o, st)
    for c in list(sc.collection.children):
        if not c.name.startswith("OSP_") and not c.all_objects:
            sc.collection.children.unlink(c)
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=DST, copy=False)
    for c in sc.collection.children:
        if c.name.startswith("OSP_"):
            tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in c.all_objects if o.type == "MESH")
            print("M80", c.name, len(c.all_objects), "oggetti", tris, "triangoli", "(nascosta)" if c.hide_render else "")
    if FOTO:
        views()


def views():
    sc = bpy.context.scene
    os.makedirs(FOTO, exist_ok=True)
    bpy.ops.mesh.primitive_cube_add(size=1)
    fig = bpy.context.object
    fig.name = "Persona_180"
    fig.scale = (0.5, 0.3, 1.8)
    m = bpy.data.materials.new("Persona")
    m.diffuse_color = (1, 0, 0, 1)
    fig.data.materials.append(m)
    cam = bpy.data.objects.new("C", bpy.data.cameras.new("C"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000

    def bounds(c):
        bb = [o.matrix_world @ Vector(v) for o in c.all_objects if o.type in ("MESH", "CURVE", "FONT") for v in o.bound_box]
        return (Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))),
                Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb))))

    for cname in ("OSP_Struttura", "OSP_Cancello", "OSP_Gabbiotto", "OSP_Annesso", "OSP_RecintoPilastro"):
        c = bpy.data.collections[cname]
        for other in sc.collection.children:
            other.hide_render = other.name != cname and not (cname == "OSP_RecintoPilastro" and other.name == "OSP_RecintoPannello")
        lo, hi = bounds(c)
        if cname == "OSP_RecintoPilastro":
            pan = bpy.data.collections["OSP_RecintoPannello"]
            for o in pan.all_objects:
                o.location.x += 1.0
            lo, hi = Vector((-1, -1, 0)), Vector((2.5, 1, 2.2))
        ctr = (lo + hi) / 2
        size = hi - lo
        fig.location = (lo.x - 1.0, lo.y - 1.5, lo.z + 0.9)
        r = max(size.x, size.z, 4.0)
        cam.location = Vector((ctr.x + r * 0.5, lo.y - r * 1.25, lo.z + max(1.7, size.z * 0.45)))
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 30
        sc.render.filepath = os.path.join(FOTO, cname + ".png")
        bpy.ops.render.render(write_still=True)
    for other in sc.collection.children:
        other.hide_render = other.name in ("OSP_RecinzioneOriginale", "OSP_Escluso")
    bpy.data.objects.remove(fig)
    bpy.data.objects.remove(cam)


main()
