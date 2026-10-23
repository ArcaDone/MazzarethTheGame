"""Blender 5.2: the bank (D:/Mazzarino80_Sorgenti/Edifici/banca.blend) split into pieces at its real size.

Run: blender -b "D:/Mazzarino80_Sorgenti/Edifici/banca.blend" --python m80_banca_pezzi.py -- [foto_dir]
The old Unity model is about 2.5 times too big (11.7 m doors): everything is scaled by SCALE, as in the first import,
and sorted into collections, one mesh each in Unreal (m80_prepare_vehicle.py key BancaModulare):
- BAN_Struttura   the building: walls, roof, balconies, windows, doors, awnings, gutters, entrance canopy and steps
- BAN_Giardino    the garden: its ground with the avenue and borders, palms, flags, statue, vases, plants
- BAN_Cancelli    the gates of the perimeter
- BAN_Insegne     the bank's lettering and logo
- BAN_RecintoPilastro, BAN_RecintoPannello  one openwork post and the spear railing between two posts, cut from a
                  straight stretch of the perimeter: the fence is drawn in Unreal along a spline (AM80ModularFence)
Not exported: BAN_RecinzioneOriginale (the original railings, for reference) and BAN_Escluso (sky box, street
pavements, objects the file only renders).
Saves D:/Mazzarino80_Sorgenti/Edifici/Banca/BancaPezzi.blend (refuses to overwrite it without M80_SOVRASCRIVI=1).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FOTO = ARGS[0] if ARGS else ""
DST = r"D:/Mazzarino80_Sorgenti/Edifici/Banca/BancaPezzi.blend"
SCALE = 0.4
FENCE_SOURCE = "Cancello.011"      # a straight stretch of the perimeter along x
GATES = ["Cancello.009", "Cancello.017", "Cancello.010", "Cancello.007", "Cancello.008", "Cancello.006", "Cancello.003"]
SIGNS = ["Scritta", "LogoBanca", "Text"]
GARDEN_COLLS = ["flags", "GScatter", "White Moss Dead Clump Low", "Ribwort Plantain Big Clump Low"]
GARDEN = ["BancaMain.003", "PavimentoEsterno"]
EXCLUDED = ["Cube.016", "Marciapiede", "Marciapiede.001"]


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


def world_copy(src, name):
    """A real mesh copy of src in world space (modifiers applied)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    me.transform(src.matrix_world)
    o = bpy.data.objects.new(name, me)
    return o


def cut(o, x0, x1):
    """Keep only the part of o between x0 and x1 (cut planes, the rails cut open)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for x, keep_above in ((x0, True), (x1, False)):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(x, 0, 0), plane_no=(1, 0, 0),
                               clear_inner=keep_above, clear_outer=not keep_above)
    bm.to_mesh(o.data)
    bm.free()


def fence_module():
    """Posts found where the railing is tallest (their finials); the module is one post and the stretch to the next."""
    src = bpy.data.objects.get(FENCE_SOURCE)
    if not src:
        return None
    whole = world_copy(src, "tmp")
    xs = [v.co.x for v in whole.data.vertices]
    zs = [v.co.z for v in whole.data.vertices]
    zmin, zmax = min(zs), max(zs)
    step = 0.05
    tall = {}
    for v in whole.data.vertices:
        if v.co.z > zmax - 0.12 * (zmax - zmin):
            tall.setdefault(int(math.floor(v.co.x / step)), 0)
            tall[int(math.floor(v.co.x / step))] += 1
    bins = sorted(tall)
    posts = []
    run = [bins[0]]
    for b in bins[1:]:
        if b - run[-1] <= 4:
            run.append(b)
        else:
            posts.append(run)
            run = [b]
    posts.append(run)
    posts = [((r[0] * step + (r[-1] + 1) * step) / 2, (r[-1] + 1 - r[0]) * step) for r in posts]
    posts.sort()
    # the stretch in the middle of the fence, between two posts as wide as most posts
    widths = sorted(w for _, w in posts)
    w_med = widths[len(widths) // 2]
    good = [p for p in posts if abs(p[1] - w_med) < 0.5 * w_med]
    mid = len(good) // 2
    (c0, w0), (c1, w1) = good[mid - 1], good[mid]
    half = max(w0, w1) / 2 + 0.02
    print("M80 pilastri trovati", len(posts), "passo", round(c1 - c0, 3), "larghezza", round(w_med, 3))
    post = world_copy(src, "RecintoPilastro")
    cut(post, c0 - half, c0 + half)
    panel = world_copy(src, "RecintoPannello")
    cut(panel, c0 + half, c1 - half)
    bpy.data.meshes.remove(whole.data)
    for o, cname in ((post, "BAN_RecintoPilastro"), (panel, "BAN_RecintoPannello")):
        collection(cname).objects.link(o)
        vs = [v.co for v in o.data.vertices]
        lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
        hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
        o.data.transform(Matrix.Translation(-Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))))
        print("M80 modulo", o.name, "m", [round(v, 3) for v in (hi - lo)])
    return post, panel


def main():
    if os.path.exists(DST) and os.environ.get("M80_SOVRASCRIVI") != "1":
        print("M80 BancaPezzi.blend esiste gia': M80_SOVRASCRIVI=1 per rifarlo")
        return
    sc = bpy.context.scene
    sc.render.use_compositing = False
    sc.render.use_sequencer = False
    S = Matrix.Scale(SCALE, 4)
    for o in [o for o in sc.objects if o.parent is None]:
        o.matrix_world = S @ o.matrix_world
    bpy.context.view_layer.update()
    shown = {o.name for o in sc.objects if o.visible_get() and not o.hide_render}
    esc = collection("BAN_Escluso", hidden=True)
    orig = collection("BAN_RecinzioneOriginale", hidden=True)
    groups = {"BAN_Cancelli": GATES, "BAN_Insegne": SIGNS, "BAN_Giardino": GARDEN}
    placed = set()
    module = fence_module()
    for o in list(sc.objects):
        if module and o in module:
            continue
        if o.type not in ("MESH", "CURVE", "FONT", "SURFACE", "META"):
            continue
        cname = next((c for c, names in groups.items() if o.name in names), None)
        if cname:
            move_to(o, collection(cname))
            # the logo is only rendered by the file: shown on purpose here
            o.hide_set(False)
            o.hide_render = False
        elif o.name in EXCLUDED or (o.name not in shown and not o.name.startswith("Scritta")):
            move_to(o, esc)
        elif o.name.startswith("Cancello"):
            move_to(o, orig)
        elif any(c.name in GARDEN_COLLS for c in o.users_collection) or o.name.startswith(("Palmier", "Statua", "Vaso")) \
                or "Pottery" in "".join(m.name for m in getattr(o.data, "materials", []) if m):
            move_to(o, collection("BAN_Giardino"))
        else:
            move_to(o, collection("BAN_Struttura"))
        placed.add(o.name)
    for c in list(sc.collection.children):
        if not c.name.startswith("BAN_"):
            sc.collection.children.unlink(c)
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=DST, copy=False)
    for c in sc.collection.children:
        tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in c.all_objects if o.type == "MESH")
        print("M80", c.name, len(c.all_objects), "oggetti", tris, "triangoli", "(nascosta)" if c.hide_render else "")
    if FOTO:
        views()


def views():
    sc = bpy.context.scene
    os.makedirs(FOTO, exist_ok=True)
    bpy.ops.mesh.primitive_cube_add(size=1)
    fig = bpy.context.object
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
    sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000

    def bounds(c):
        bb = [o.matrix_world @ Vector(v) for o in c.all_objects if o.type in ("MESH", "CURVE", "FONT") for v in o.bound_box]
        return (Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))),
                Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb))))

    for cname in ("BAN_Struttura", "BAN_Giardino", "BAN_Cancelli", "BAN_Insegne", "BAN_RecintoPilastro"):
        c = bpy.data.collections[cname]
        if not c.all_objects:
            continue
        for other in sc.collection.children:
            other.hide_render = other.name != cname and not (cname == "BAN_RecintoPilastro" and other.name == "BAN_RecintoPannello")
        lo, hi = bounds(c)
        if cname == "BAN_RecintoPilastro":
            pan = bpy.data.collections["BAN_RecintoPannello"].all_objects
            for o in pan:
                o.location.x += 2.0
            lo, hi = Vector((-2, -1, 0)), Vector((5, 1, 3.5))
        ctr = (lo + hi) / 2
        size = hi - lo
        r = max(size.x, size.y, size.z, 4.0)
        fig.location = (ctr.x - min(size.x, 6) / 2 - 1.0, lo.y - 1.0, lo.z + 0.9)
        cam.location = Vector((ctr.x + r * 0.45, lo.y - r * 1.1, lo.z + max(1.7, size.z * 0.6)))
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 30
        sc.render.filepath = os.path.join(FOTO, cname + ".png")
        bpy.ops.render.render(write_still=True)
    for other in sc.collection.children:
        other.hide_render = other.name in ("BAN_RecinzioneOriginale", "BAN_Escluso")
    bpy.data.objects.remove(fig)
    bpy.data.objects.remove(cam)


main()
