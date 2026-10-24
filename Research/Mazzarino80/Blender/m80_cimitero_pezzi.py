"""Blender 5.2: Mazzarino's cemetery (D:/Cimitero_Mazzarino/highpoly/Cimitero_Mazzarino_HIGH_POLY.blend) split into the
pieces Unreal needs to put it together again, and to fill its plots with a spline (AM80CemeteryField).

Run: blender -b "D:/Cimitero_Mazzarino/highpoly/Cimitero_Mazzarino_HIGH_POLY.blend" --python m80_cimitero_pezzi.py
The master file is never saved: the pieces go into D:/Mazzarino80_Sorgenti/Edifici/Cimitero/CimiteroPezzi.blend
(refuses to overwrite it without M80_SOVRASCRIVI=1), one object each, for m80_prepare_vehicle.py key Cimitero:
- where they stand in the master (the import keeps their places relative to the entrance): Ingresso (the monumental
  entrance, its wings and porch), Cancello (the iron gate), Gallerie (the three galleries of loculi), Cappelle (the 29
  family chapels along the walls), Viali (the paved walks, the square in front and its low walls, benches, kerbs);
- the wall as a module for AM80ModularFence: RecintoPannello (2.1 m of the dry-stone wall: core, courses of the master's
  own block prototypes, coping) and RecintoPilastro (a pier of the same blocks with a cap);
- the tomb library, one object per kind for the plots: Tomba_<code> (U01-U22 old graves, N01-N10 new ones and their
  three wear variants _U1.._U3), Cappella_<code> (CU01-CU09, CN01-CN03), Monumento_MU01; laid out on a grid so no two
  look the same to the import's duplicate check.
The new kinds' marbles, granite and bronze are procedural (noise and waves): each is baked once on a 2 x 2 m tile
(Cycles, colour only) into tex/<material>.png and the material becomes that image on a box UV of the same scale, the
only thing the import can carry.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

DST = r"D:/Mazzarino80_Sorgenti/Edifici/Cimitero/CimiteroPezzi.blend"
TEX = r"D:/Mazzarino80_Sorgenti/Edifici/Cimitero/tex"
UV_M = 2.0            # box UV of the baked materials: 1 UV = 2 m (the bake tile)
BAKE_PX = 1024
GRID = 6.0            # library layout pitch (m)
random.seed(80)
sys.stdout.reconfigure(line_buffering=True)


def coll(prefix):
    return next(c for c in bpy.data.collections if c.name.startswith(prefix))


def merged(objs, name, offset=None):
    """One new object from the evaluated meshes of objs, in world space (materials merged by identity)."""
    deps = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    mats = []
    for o in objs:
        if o.type != "MESH":
            continue
        try:
            eo = o.evaluated_get(deps)
        except Exception:  # noqa: BLE001 - not in the view layer (hidden library, temporary copies)
            eo = o
        me = eo.to_mesh()
        me.transform(o.matrix_world)
        if o.matrix_world.determinant() < 0:
            me.flip_normals()
        remap = []
        for m in me.materials:
            m = m.original if m else None     # an evaluated mesh points at the evaluated copies of the materials
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        n0 = len(bm.faces)
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        for i in range(n0, len(bm.faces)):
            f = bm.faces[i]
            f.material_index = remap[f.material_index] if f.material_index < len(remap) else 0
        eo.to_mesh_clear()
    if offset is not None:
        bmesh.ops.translate(bm, verts=bm.verts, vec=offset)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    return ob


# ---------------------------------------------------------------- procedural materials -> images
def has_image_colour(m):
    if not m or not m.node_tree:
        return True
    return any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes)


def bake(m, sc):
    """Colour of a procedural material on a 2 x 2 m tile, saved as an image (use_baked switches the material)."""
    os.makedirs(TEX, exist_ok=True)
    path = os.path.join(TEX, m.name.replace(" ", "_") + ".png")
    me = bpy.data.meshes.new("M80_Tile")
    bm = bmesh.new()
    h = UV_M / 2
    vs = [bm.verts.new(v) for v in ((-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for lp, co in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uv].uv = co
    bm.to_mesh(me)
    bm.free()
    tile = bpy.data.objects.new("M80_Tile", me)
    sc.collection.objects.link(tile)
    me.materials.append(m)
    img = bpy.data.images.new(m.name + "_bake", BAKE_PX, BAKE_PX)
    nt = m.node_tree
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = img
    nt.nodes.active = node
    vl = sc.view_layers[0]
    for o in sc.objects:
        o.select_set(False, view_layer=vl)
    tile.select_set(True, view_layer=vl)
    vl.objects.active = tile
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 4
    sc.render.bake.use_pass_direct = False
    sc.render.bake.use_pass_indirect = False
    sc.render.bake.use_pass_color = True
    with bpy.context.temp_override(scene=sc, view_layer=vl, active_object=tile, object=tile, selected_objects=[tile],
                                   selected_editable_objects=[tile]):
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=0)
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    nt.nodes.remove(node)
    bpy.data.objects.remove(tile)
    print("M80 cotto", m.name, "->", path)
    return path


def use_baked(m, path):
    """The material becomes the baked image on the box UV, its roughness and metalness kept."""
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    rough = bsdf.inputs["Roughness"].default_value if bsdf else 0.6
    metal = bsdf.inputs["Metallic"].default_value if bsdf else 0.0
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=False)
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(p.outputs["BSDF"], out.inputs["Surface"])


def box_uv(ob):
    """A box-projected UV as the only UV map (1 UV = UV_M metres), for the baked tiles."""
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            c = lp.vert.co
            lp[uv].uv = ((c.x, c.y) if ax == 2 else ((c.y, c.z) if ax == 0 else (c.x, c.z)))
            lp[uv].uv /= UV_M
    bm.to_mesh(me)
    bm.free()


# ---------------------------------------------------------------- the wall module from the master's blocks
def wall_module(src, out_coll):
    blocks = [o for o in src.objects if o.name.startswith("Blocco recinto prototipo")]
    core_src = next(o for o in src.objects if o.name.startswith("Giunto pieno"))
    cop_src = next(o for o in src.objects if o.name.startswith("Copertina muro"))
    core_mat = core_src.data.materials[0] if core_src.data.materials else None
    cop_mat = cop_src.data.materials[0] if cop_src.data.materials else None
    bl = blocks[0].dimensions                         # 1.04 x 0.46 x 0.36

    def box(bm, mats, mat, c, s):
        r = bmesh.ops.create_cube(bm, size=1.0)
        idx = mats.index(mat) if mat in mats else len(mats)
        if mat not in mats:
            mats.append(mat)
        for v in r["verts"]:
            v.co = Vector((c[0] + v.co.x * s[0], c[1] + v.co.y * s[1], c[2] + v.co.z * s[2]))
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = idx

    def put_block(parts, x0, x1, z0, along_x=True, y0=0.0):
        b = random.choice(blocks)
        o = b.copy()
        o.data = b.data
        L = x1 - x0
        # the prototype lies along its longest axis: scale it to the course's piece
        dims = b.dimensions
        sx = L / dims.x
        o.matrix_world = (Matrix.Translation(((x0 + x1) / 2, y0, z0 + dims.z / 2)) @
                          (Matrix.Rotation(math.pi / 2, 4, "Z") if not along_x else Matrix()) @
                          Matrix.Diagonal((sx * 0.985, 1.0, 1.0, 1.0)) @
                          Matrix.Translation(-(sum((Vector(v) for v in b.bound_box), Vector()) / 8)))
        parts.append(o)

    # panel: 2.1 m, four courses of blocks staggered, the core behind them, the coping on top
    LEN, H = 2.1, 1.44
    parts = []
    z = 0.0
    row = 0
    while z < H - 0.01:
        cuts = [0.0, 1.05, 2.1] if row % 2 == 0 else [0.0, 0.525, 1.575, 2.1]
        for a, b in zip(cuts, cuts[1:]):
            put_block(parts, a - LEN / 2, b - LEN / 2, z)
        z += bl.z
        row += 1
    panel = merged(parts, "RecintoPannello")
    for o in parts:
        bpy.data.objects.remove(o)
    bm = bmesh.new()
    bm.from_mesh(panel.data)
    mats = list(panel.data.materials)
    box(bm, mats, core_mat, (0, 0, 0.7), (LEN, 0.37, 1.49))
    box(bm, mats, cop_mat, (0, 0, H + 0.06), (LEN, 0.55, 0.18))
    bm.to_mesh(panel.data)
    bm.free()
    panel.data.materials.clear()
    for m in mats:
        panel.data.materials.append(m)
    out_coll.objects.link(panel)
    # pier: 0.62 m square, blocks crossing course by course, a cap
    parts = []
    z = 0.0
    row = 0
    while z < H + 0.2:
        put_block(parts, -0.31, 0.31, z, along_x=row % 2 == 0)
        z += bl.z
        row += 1
    pier = merged(parts, "RecintoPilastro")
    for o in parts:
        bpy.data.objects.remove(o)
    bm = bmesh.new()
    bm.from_mesh(pier.data)
    mats = list(pier.data.materials)
    box(bm, mats, core_mat, (0, 0, (z) / 2), (0.5, 0.5, z))
    box(bm, mats, cop_mat, (0, 0, z + 0.08), (0.74, 0.74, 0.16))
    bm.to_mesh(pier.data)
    bm.free()
    pier.data.materials.clear()
    for m in mats:
        pier.data.materials.append(m)
    out_coll.objects.link(pier)


def code(name):
    """'N01 • Stele ad arco • Usura 2' -> ('Tomba', 'N01_U2')."""
    parts = [p.strip() for p in name.split("•")]
    c = parts[0]
    wear = next((p for p in parts if p.startswith("Usura")), None)
    if wear:
        c += "_U" + wear.split()[-1]
    kind = "Cappella" if c.startswith("C") else ("Monumento" if c.startswith("M") else "Tomba")
    return kind, c


def main():
    if os.path.exists(DST) and os.environ.get("M80_SOVRASCRIVI") != "1":
        print("M80 CimiteroPezzi.blend esiste gia': M80_SOVRASCRIVI=1 per rifarlo")
        return
    out = bpy.data.scenes.new("M80_PEZZI")
    pieces = out.collection
    # site pieces, in place
    groups = {
        "Ingresso": [coll("02 ")],
        "Cancello": [coll("03 ")],
        "Gallerie": [coll("07 ")],
        "Cappelle": [coll("06 ")],
        "Viali": [coll("04 "), coll("09 ")],
    }
    for name, cs in groups.items():
        objs = [o for c in cs for o in c.all_objects if o.type == "MESH"]
        if name == "Viali":
            objs += [o for o in coll("01 ").objects if o.name.startswith("Piazzale")]
        ob = merged(objs, name)
        pieces.objects.link(ob)
        print("M80", name, len(objs), "oggetti", sum(len(p.vertices) - 2 for p in ob.data.polygons), "triangoli")
    wall_module(coll("08 "), pieces)
    # the library, on a grid
    lib = [o for o in coll("90 ").objects if o.type == "MESH"]
    for i, o in enumerate(sorted(lib, key=lambda o: o.name)):
        kind, c = code(o.name)
        off = Vector(((i % 10) * GRID + 200.0, (i // 10) * GRID, 0.0))
        ob = merged([o], "%s_%s" % (kind, c), offset=off)
        pieces.objects.link(ob)
    # procedural materials (the new kinds' marbles, and some of the site's plasters and metals) -> baked images
    baked = {}
    for ob in list(pieces.objects):
        for m in ob.data.materials:
            if m and not has_image_colour(m) and m.name not in baked:
                baked[m.name] = (m, bake(m, out))
    for m, path in baked.values():
        use_baked(m, path)
    for ob in pieces.objects:
        names = {m.name for m in ob.data.materials if m}
        own = names - set(baked)
        if names & set(baked) and (not own or not ob.data.uv_layers):
            box_uv(ob)          # all its colours baked (or no UV at all): the tiles' box UV is the only one
        elif names & set(baked):
            print("M80 misto", ob.name, "cotti", sorted(names & set(baked)), "immagini", sorted(own))
    for ob in pieces.objects:
        print("M80 pezzo", ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons), [m.name if m else None for m in ob.data.materials][:5])
    # only the pieces go into the new file (removing the master's scenes crashes this Blender)
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    bpy.data.libraries.write(DST, {out}, path_remap="ABSOLUTE", compress=True)
    print("M80 salvato", DST)


main()
