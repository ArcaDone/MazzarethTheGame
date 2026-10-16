"""Blender 5.2: City Sample crowd garments (exported from the City Sample project by Scripts/m80_citysample_export.py)
fitted onto our MetaHumans and dressed in our fabrics, as parametric outfits like m80_vestiti.py's.

The City Sample garments are skinned to the same MetaHuman skeleton, in the same A pose, on bodies of their own
(the "body" mesh they ship is only the hands: the rest of the skin is cut away under the clothes). Each garment
follows the joints from their body to ours (every vertex moves by its bones' joint offsets, weighted by its skin
weights), then is pushed out of our body's skin. Skin pieces inside a garment mesh (legs under a skirt) are dropped.
Their UVs are an atlas: our fabric (a tiling texture of tile_m metres) repeats ColoreScala times per UV unit, and
the garment's own normal map (seams, wrinkles, buttons) and occlusion (packed A, red) come along for the Unreal
material M_M80_StoffaCS (Scripts/m80_vestiti_import.py).

Run: blender -b --factory-startup --python m80_citysample_vesti.py -- [Key,Key...]
Out: Saved/Mazzarino80/Folla/Vestiti/<Key>/ as m80_vestiti.py (SM_M80_<Key>{,_LOD1..3}.fbx, Textures/, <Key>.json)
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_folla_oggetti as common  # noqa: E402
import m80_vestiti as V  # noqa: E402

ROOT = common.ROOT
CS = os.path.join(ROOT, "Saved", "Mazzarino80", "CitySample")
OUT = V.OUT
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = [k for k in (ARGS[0].split(",") if ARGS else []) if k]
TEX = 512
LODS = [None, 9000, 4000, 1600]     # LOD0 as City Sample made it, then the crowd's budget
MARGIN = 0.008
# Layers within an outfit: key -> [(inner key, its slot or None for all, my slot or None for all)]: those faces of mine
# are kept LAYER_GAP out of the inner garment (a shirt tucked into a skirt or trousers, a jacket over the trousers).
LAYERS = {
    "CS_Pantaloni": [("CS_CamiciaGiacca", "Cotone_Camicia", None)],
    "CS_CamiciaGiacca": [("CS_Pantaloni", None, "Lana_Giacca")],
    "CS_Gonna": [("CS_Camicetta", None, None)],
}
LAYER_GAP = 0.005
LAYER_REACH = 0.03
CACHE = {}      # key -> [(slot, vertices, faces)] of the garments built in this run, world space

# Our fabric for each City Sample material, by a word of its name: (slot name, kind, colour(s), tile metres).
# The slot name's prefix picks the fabric preset in Unreal (Lana, Cotone, Maglia, Seta, Jeans, Cuoio).
GARMENTS = {
    "CS_CamiciaGiacca": ("Sandro", "m_tal_nrw_buttonDown_tie_blazer", {
        "buttonDown": ("Cotone_Camicia", "weave", (0.62, 0.72, 0.84), 0.05),
        "Suspenders": ("Seta_Cravatta", "regimental", ((0.30, 0.06, 0.07), (0.75, 0.68, 0.50)), 0.12),
        "blazer": ("Lana_Giacca", "tweed", ((0.24, 0.22, 0.20), (0.36, 0.33, 0.29), (0.15, 0.14, 0.13)), 0.12),
    }),
    "CS_Pantaloni": ("Sandro", "m_tal_nrw_slacks_belt", {
        "slacks": ("Lana_Pantaloni", "weave", (0.20, 0.19, 0.18), 0.04),
        "socks": ("Maglia_Calze", "knit", (0.06, 0.06, 0.07), 0.04),
        "belt": ("Cuoio_Cintura", "leather", (0.20, 0.11, 0.06), 0.2),
    }),
    "CS_Stringate": ("Sandro", "m_tal_nrw_oxfords", {
        "oxford": ("Cuoio_Scarpe", "leather", (0.12, 0.06, 0.035), 0.15),
    }),
    "CS_Camicetta": ("Donna1", "f_tal_nrw_buttonDown", {
        "buttonDown": ("Cotone_Camicetta", "weave", (0.90, 0.86, 0.78), 0.05),
    }),
    "CS_Gonna": ("Donna1", "f_tal_nrw_skirt", {
        "skirt": ("Lana_Gonna", "tartan", ((0.22, 0.20, 0.30), [(0.0, 0.1, (0.45, 0.12, 0.12), 0.6),
                                                                 (0.5, 0.04, (0.75, 0.65, 0.40), 0.5)]), 0.15),
    }),
    "CS_Ballerine": ("Donna1", "f_tal_nrw_dressFlats", {
        "": ("Cuoio_Ballerine", "leather", (0.10, 0.07, 0.06), 0.15),
    }),
}


def fabric_pixels(kind, spec, rng):
    if kind == "weave":
        return V.weave(TEX, spec, rng, scale=2, depth=0.05)
    if kind == "knit":
        return V.knit(TEX, spec, rng)
    if kind == "tweed":
        return common.tweed(TEX, spec, rng)
    if kind == "leather":
        return common.leather(TEX, spec, rng)
    if kind == "tartan":
        base, lines = spec
        return common.tartan(TEX, base, lines, rng)
    if kind == "regimental":
        a, b = spec
        y, x = np.mgrid[0:TEX, 0:TEX]
        band = ((x + y) % (TEX // 4)) < TEX // 24
        rgb = np.ones((TEX, TEX, 3)) * np.array(a)
        rgb[band] = b
        return rgb * (0.94 + 0.12 * common.noise(TEX, TEX, 48, rng)[..., None])
    raise ValueError(kind)


def joints(arm_ob):
    return {b.name: np.array((arm_ob.matrix_world @ b.head_local)[:]) for b in arm_ob.data.bones}


def report():
    with open(os.path.join(CS, "report.json"), encoding="utf-8") as f:
        return json.load(f)


def metres_per_uv(me, poly_ids):
    """Side of one UV unit in metres on these faces (3D area over UV area)."""
    uv = me.uv_layers[0].data
    a3 = auv = 0.0
    for i in poly_ids:
        p = me.polygons[i]
        a3 += p.area
        pts = [uv[li].uv for li in p.loop_indices]
        s = 0.0
        for k in range(len(pts)):
            x0, y0 = pts[k]
            x1, y1 = pts[(k + 1) % len(pts)]
            s += x0 * y1 - x1 * y0
        auv += abs(s) * 0.5
    return math.sqrt(a3 / auv) if auv > 1e-9 else 1.0


def layer_out(me, key):
    """Pushes my faces (or those of one slot) out of the inner garments of LAYERS already built in this run."""
    done = {"applied": [], "missing": []}
    for inner, inner_slot, my_slot in LAYERS.get(key, []):
        if inner not in CACHE:
            done["missing"].append(inner)
            continue
        verts, faces = [], []
        for slot, co, fs in CACHE[inner]:
            if inner_slot and slot != inner_slot:
                continue
            base = len(verts)
            verts.extend(co)
            faces.extend(tuple(i + base for i in f) for f in fs)
        if not faces:
            continue
        bvh = BVHTree.FromPolygons(verts, faces)
        mine = {i for i, m in enumerate(me.materials) if m and (my_slot is None or m.name.split(".")[0] == my_slot)}
        check = {vi for p in me.polygons if p.material_index in mine for vi in p.vertices}
        moved = 0
        for vi in check:
            v = me.vertices[vi]
            loc, nrm, _, _ = bvh.find_nearest(v.co, LAYER_REACH)
            if loc is None:
                continue
            d = (v.co - loc).dot(nrm)
            if d < LAYER_GAP:
                v.co = v.co + nrm * (LAYER_GAP - d)
                moved += 1
        me.update()
        done["applied"].append({"inner": inner, "moved": moved})
    return done


def build(key, target, source, fabrics, rep):
    body = V.Body(target)
    tgt = dict(body.joint)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CS, "fbx", source + ".fbx"))
    arm = next(o for o in bpy.context.selected_objects if o.type == "ARMATURE")
    ob = next(o for o in bpy.context.selected_objects if o.type == "MESH")
    src = joints(arm)
    world = ob.matrix_world.copy()
    ob.parent = None
    ob.matrix_world.identity()
    ob.data.transform(world)
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    bpy.data.objects.remove(arm)
    me = ob.data
    info_cs = rep["meshes"][source]["materials"]

    # Skin pieces out; the rest renamed to our fabric slots.
    skin = {i for i, m in enumerate(me.materials) if m and m.name.startswith("M_Body")}
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in skin], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    for i in reversed(range(len(me.materials))):
        if not any(p.material_index == i for p in me.polygons):
            ob.active_material_index = i
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.material_slot_remove()

    # Joint offsets from their body to ours, blended by the skin weights.
    groups = {g.index: g.name for g in ob.vertex_groups}
    delta = {gi: (tgt[n] - src[n]) for gi, n in groups.items() if n in tgt and n in src}
    co = np.array([v.co[:] for v in me.vertices])
    move = np.zeros_like(co)
    for v in me.vertices:
        tot = 0.0
        acc = np.zeros(3)
        for g in v.groups:
            d = delta.get(g.group)
            if d is not None and g.weight > 0:
                acc += d * g.weight
                tot += g.weight
        if tot > 0:
            move[v.index] = acc / tot
    co += move
    me.vertices.foreach_set("co", co.ravel())
    me.update()
    rep_key = {"source": source, "body": target, "moved_mm_max": round(float(np.linalg.norm(move, axis=1).max()) * 1000, 1)}

    bm = bmesh.new()
    bm.from_mesh(me)
    pushed = 0
    for v in bm.verts:
        loc, nrm, _, _ = body.bvh.find_nearest(v.co)
        if loc is None:
            continue
        d = (v.co - loc).dot(nrm)
        if d < MARGIN:
            v.co = v.co + nrm * (MARGIN - d)
            pushed += 1
    bm.to_mesh(me)
    bm.free()
    rep_key["pushed_out"] = pushed
    for o in list(ob.vertex_groups):
        ob.vertex_groups.remove(o)

    # Materials: ours, with the City Sample normal map and occlusion recorded for Unreal.
    rng = np.random.default_rng(abs(hash(key)) % (2 ** 32))
    cs_info = {}
    new_mats = []
    for idx, m in enumerate(me.materials):
        name = m.name if m else ""
        word = next((w for w in fabrics if w and w.lower() in name.lower()), "" if "" in fabrics else None)
        if word is None:
            word = next(iter(fabrics))
        slot, kind, spec, tile_m = fabrics[word]
        polys = [p.index for p in me.polygons if p.material_index == idx]
        mpu = metres_per_uv(me, polys) if polys else 1.0
        img = common.image(slot, fabric_pixels(kind, spec, rng))
        mat = common.material(slot, img=img, rough=0.85)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        tex = next(n for n in nodes if n.type == "TEX_IMAGE")
        mapping = nodes.new("ShaderNodeMapping")
        coord = nodes.new("ShaderNodeTexCoord")
        mapping.inputs["Scale"].default_value = (mpu / tile_m, mpu / tile_m, 1)
        links.new(coord.outputs["UV"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        mat.use_backface_culling = False
        new_mats.append(mat)
        csm = next((x for x in info_cs if x["name"] and x["name"].rsplit(".", 1)[-1] == name.split(".")[0]), None)
        texs = (csm or {}).get("textures", {})
        tga = lambda p: (p.rsplit(".", 1)[-1] + ".tga") if p else None  # noqa: E731
        cs_info[slot] = {"cs_material": name, "metres_per_uv": round(mpu, 4), "tile_m": tile_m,
                         "colour_scale": round(mpu / tile_m, 3), "normal": tga(texs.get("Tex_Normals")),
                         "packed": tga(texs.get("PACKED A"))}
    for i, m in enumerate(new_mats):
        me.materials[i] = m
    for p in me.polygons:
        p.use_smooth = True
    # Same slot twice (two City Sample materials onto one fabric) is fine: Unreal keeps both slots.
    rep_key["slots"] = cs_info
    rep_key["layers"] = layer_out(me, key)
    CACHE[key] = [(m.name.split(".")[0], [v.co.copy() for v in me.vertices],
                   [tuple(p.vertices) for p in me.polygons if p.material_index == i]) for i, m in enumerate(me.materials)]
    rep_key["triangles"] = sum(len(p.vertices) - 2 for p in me.polygons)

    out = os.path.join(OUT, key)
    os.makedirs(out, exist_ok=True)
    V.preview(body, [ob], os.path.join(out, "anteprima_"))
    bpy.data.objects.remove(body.ob)
    ob.name = me.name = "SM_M80_" + key
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    common.OUT = OUT
    info = common.export(ob, key, {"body": target, "lods": LODS, "citysample": cs_info})
    for n, tris in enumerate(LODS[1:], start=1):
        lod = ob.copy()
        lod.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(lod)
        V.decimate(lod, tris)
        lod.name = lod.data.name = "SM_M80_%s_LOD%d" % (key, n)
        bpy.ops.object.select_all(action="DESELECT")
        lod.select_set(True)
        bpy.ops.export_scene.fbx(filepath=os.path.join(out, lod.name + ".fbx"), use_selection=True, apply_unit_scale=True,
                                 apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Y", axis_up="Z",
                                 object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True,
                                 path_mode="COPY", embed_textures=False)
        info["lod%d_triangles" % n] = sum(len(p.vertices) - 2 for p in lod.data.polygons)
    with open(os.path.join(out, key + ".json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=1)
    rep_key["info"] = info
    print("VESTITO_CS", json.dumps(rep_key))
    return rep_key


def main():
    rep = report()
    done = {}
    for key, (target, source, fabrics) in GARMENTS.items():
        if ONLY and key not in ONLY:
            continue
        done[key] = build(key, target, source, fabrics, rep)
    # Second pass for the garments whose inner layer was built after them.
    for key, entry in list(done.items()):
        if entry["layers"]["missing"]:
            target, source, fabrics = GARMENTS[key]
            done[key] = build(key, target, source, fabrics, rep)
    with open(os.path.join(OUT, "citysample_report.json"), "w", encoding="utf-8") as f:
        json.dump(done, f, indent=1)


if __name__ == "__main__":
    main()
