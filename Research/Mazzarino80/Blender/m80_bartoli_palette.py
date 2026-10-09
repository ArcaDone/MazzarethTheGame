"""Palazzo Bartoli: albedo swatches of every material of the high-poly block, to compare with the Unreal materials.

Opens Saved/Mazzarino80/Bartoli/bartoli_alta.blend (m80_palazzo_bartoli.py -- alta) and writes, for each material
used by the facades, roofs, courtyard, staircase and fittings, a 1.6 m swatch of its base colour as the renderer
sees it (sRGB): walls are cut from their albedo image, the procedural materials are baked (Cycles, diffuse colour)
on a flat 1.6 m plate.
Run: blender -b --factory-startup --python m80_bartoli_palette.py
Out: Saved/Mazzarino80/Bartoli/Palette/<material>.png + palette.json (mean sRGB, objects using it).
"""
import json
import os

import bmesh
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SAVED = os.path.join(ROOT, "Saved", "Mazzarino80", "Bartoli")
OUT = os.path.join(SAVED, "Palette")
SIZE = 256
SKIP = ("Interno", "Interno_buio", "Vicini", "Terreno", "Bosso", "Chioma", "Corteccia", "Glicine", "Edera", "Acqua",
        "Cotto_facciata")


def used_materials():
    """Materials of the parts that go to the game (high-poly and fittings), with the objects using them."""
    out = {}
    for col in bpy.data.collections:
        if not (col.name.endswith("_High") or col.name.endswith("_Detail")):
            continue
        for ob in col.all_objects:
            if ob.type not in ("MESH", "CURVE", "FONT"):
                continue
            for slot in ob.material_slots:
                m = slot.material
                if m and m.name not in SKIP:
                    out.setdefault(m.name, set()).add(col.name.rsplit("_", 1)[0])
    return out


def albedo_image(m):
    if not m.use_nodes:
        return None
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.name.endswith("_albedo"):
            return n.image
    return None


def crop(img, wall):
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)[..., :3]
    # Walls: 110 px/m, a patch 2.5-4.1 m above the street in the middle; ground: the centre of the patch.
    per_m = 110 if wall else w / max(1.0, w * 0.03)
    n = int(1.6 * per_m)
    if wall:
        y0 = min(max(0, int(2.5 * per_m)), max(0, h - n))
    else:
        y0 = max(0, h // 2 - n // 2)
    x0 = max(0, w // 2 - n // 2)
    patch = px[y0:y0 + n, x0:x0 + n]
    return patch


def plate():
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=64, y_segments=64, size=0.8)
    me = bpy.data.meshes.new("Campione")
    bm.to_mesh(me)
    bm.free()
    # UV 0-1 for the bake target; a second set in metres for the shaders that read UVs (coppi).
    bake_uv = me.uv_layers.new(name="Bake")
    metres = me.uv_layers.new(name="Metri")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        bake_uv.data[loop.index].uv = ((co.x + 0.8) / 1.6, (co.y + 0.8) / 1.6)
        metres.data[loop.index].uv = (co.x + 0.8, co.y + 0.8)
    bake_uv.active = True
    metres.active_render = True
    ob = bpy.data.objects.new("Campione", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bake(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)
    img = bpy.data.images.new("Campione_" + m.name, SIZE, SIZE, alpha=False)
    img.colorspace_settings.name = "sRGB"
    node = m.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = img
    m.node_tree.nodes.active = node
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True, margin=0)
    m.node_tree.nodes.remove(node)
    px = np.empty(SIZE * SIZE * 4, np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(SIZE, SIZE, 4)[..., :3]


def save_png(name, rgb):
    h, w = rgb.shape[:2]
    img = bpy.data.images.new("out_" + name, w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = np.clip(rgb, 0, 1)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(OUT, name + ".png")
    img.file_format = "PNG"
    img.save()


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SAVED, "bartoli_alta.blend"))
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 4
    sc.render.bake.margin = 0
    sc.render.bake.use_selected_to_active = False
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as e:  # noqa: BLE001
        print("GPU not available:", e)
    os.makedirs(OUT, exist_ok=True)
    mats = used_materials()
    ob = plate()
    report = {}
    for name, users in sorted(mats.items()):
        m = bpy.data.materials[name]
        img = albedo_image(m)
        if img is not None:
            rgb = crop(img, name.endswith("_muro_hi"))
            source = "immagine"
        elif m.use_nodes:
            rgb = bake(ob, m)
            source = "bake"
        else:
            rgb = np.ones((SIZE, SIZE, 3), np.float32) * np.array(m.diffuse_color[:3])
            source = "colore"
        safe = name.replace(" ", "_").replace(".", "_")
        save_png(safe, rgb)
        report[name] = {"file": safe + ".png", "mean_srgb": [round(float(v), 4) for v in rgb.reshape(-1, 3).mean(0)],
                        "source": source, "used_by": sorted(users)}
        print("swatch", name, report[name]["mean_srgb"], source)
    with open(os.path.join(OUT, "palette.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)


main()
