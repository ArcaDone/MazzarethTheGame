"""Blender 5.2: turns the downloaded Fiat 500 F (D:/BlenderTest/AutoDaImportare/1965-fiat-500f, a game-ready FBX
with D/N/RME textures) into a .blend that m80_prepare_vehicle.py takes like the other cars (key Fiat500).

- scales it from 1:100 to real size;
- drops the engine and the front trunk contents (spare wheel, tank): hidden under closed lids, ~90k triangles;
- renames the materials so the importer recognises them (paint, chrome, glass, lights, rubber) and sets their
  metallic/roughness by hand (the RME maps are not read by the pipeline);
- the cabin texture keeps its details where its alpha is white and takes the body colour elsewhere (on the real
  car the dashboard and the inside of the doors are painted metal);
- no metallic 0.5 everywhere as the FBX brings it.
Run (the zip unpacked in <src>, the .blend written to <out>):
blender -b --factory-startup --python m80_fiat500_sorgente.py -- <src>/FINAL_MODEL_500f.fbx <out>/Fiat500.blend
"""
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix

SRC, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
DROP = ("SM_Engine_",)
PAINT = (0.08, 0.19, 0.8)
# FBX material -> (new name, metallic, roughness)
MATERIALS = {
    "MI_1272010001_002": ("Vernice_Carrozzeria", 0.0, 0.35),
    "MI_Exhaust1": ("Cromo", 1.0, 0.2),
    "MI_Rim1": ("Cerchio", 0.2, 0.35),
    "MI_Classic_Tyre1": ("Gomma", 0.0, 0.9),
    "MI_Change_Brake1": ("Freni_Metallo", 0.6, 0.5),
    "MI_Glass1": ("Vetro", 0.0, 0.05),
    "MI_Glass_Light1": ("Faro_Vetro", 0.0, 0.05),
    "orange_glass": ("Faro_Freccia_Vetro", 0.0, 0.1),
    "red_glass": ("Stop_Vetro", 0.0, 0.1),
    "MI_Light1": ("Fanaleria", 0.5, 0.3),
    "MI_Mirror_002": ("Specchio_Cromo", 1.0, 0.05),
    "MI_Cabin1": ("Interni", 0.0, 0.5),
    "MI_Cabin_Leather_A1": ("Sedili", 0.0, 0.6),
    "MI_Cabin_Leather_B1": ("Sedili_Retro", 0.0, 0.6),
    "MI_Cabin_Carpet_A1": ("Moquette", 0.0, 0.95),
    "MI_Dashboard1": ("Cruscotto", 0.0, 0.4),
    "MI_ChangeB_Decals_Roof_Cloth1": ("Tetto_Tela", 0.0, 0.85),
    "MI_Grid_A1": ("Griglia", 0.3, 0.6),
    "MI_Engine1": ("Stemmi", 0.6, 0.3),
    "MI_Engine_Leather_A1": ("Motore_Pelle", 0.0, 0.6),
    "leather": ("Pelle_Nera", 0.0, 0.6),
}


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None


def paint_where_masked(m):
    """Base colour = texture where its alpha is white, the body paint elsewhere; the alpha link is removed."""
    p = principled(m)
    al = p.inputs["Alpha"]
    for link in list(al.links):
        m.node_tree.links.remove(link)
    al.default_value = 1.0
    bc = p.inputs["Base Color"]
    if not bc.is_linked:
        return
    node = bc.links[0].from_node
    im = node.image
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    a = px[..., 3:4]
    paint = np.array(PAINT, dtype=np.float32)
    px[..., :3] = px[..., :3] * a + paint * (1 - a)
    px[..., 3] = 1.0
    new = bpy.data.images.new("T_Interni_D", w, h, alpha=False)
    new.pixels.foreach_set(px.ravel())
    new.pack()
    node.image = new


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=SRC)
    dropped = 0
    for o in list(bpy.data.objects):
        if any(o.name.split(":")[-1].startswith(d) for d in DROP):
            bpy.data.objects.remove(o, do_unlink=True)
            dropped += 1
    # The FBX comes at 1:100 (2.9 cm long): to real size, the pipeline's tolerances are in metres.
    for o in bpy.data.objects:
        if o.parent is None:
            o.matrix_world = Matrix.Scale(100.0, 4) @ o.matrix_world
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    done = set()
    for m in bpy.data.materials:
        key = m.name.split(":")[-1]
        if key not in MATERIALS or m.name in done:
            continue
        name, metal, rough = MATERIALS[key]
        p = principled(m)
        if p:
            p.inputs["Metallic"].default_value = metal
            p.inputs["Roughness"].default_value = rough
            if name == "Interni":
                paint_where_masked(m)
            elif name not in ("Vetro", "Faro_Vetro", "Faro_Freccia_Vetro", "Stop_Vetro"):
                # The other D textures carry no transparency the game needs.
                for link in list(p.inputs["Alpha"].links):
                    m.node_tree.links.remove(link)
                p.inputs["Alpha"].default_value = 1.0
            if name == "Vernice_Carrozzeria":
                p.inputs["Base Color"].default_value = PAINT + (1.0,)
        m.name = name
        done.add(name)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == "MESH" for p in o.data.polygons)
    print("M80 dropped", dropped, "objects; triangles left", tris, "; saved", OUT)


main()
