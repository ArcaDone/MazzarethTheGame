"""Blender 5.2: turns the downloaded game-ready cars of D:/Mazzarino80_Sorgenti/Auto (FBX at 1:100 with D/N textures,
material names of the original game) into .blend files that m80_prepare_vehicle.py takes like the other cars.
The Fiat 500 has its own script (m80_fiat500_sorgente.py: engine dropped, cabin texture painted).

- scales the car from 1:100 to real size;
- renames the materials so the importer recognises them (paint, chrome, glass, lights, rubber...) and sets their
  metallic/roughness by hand (the maps of the original game are not read by the pipeline), the paint colour per car;
- unlinks the texture alpha from the opaque materials (in these textures it is a mask, not transparency);
- the meshes are left as they are: no decimation, the normals of the file kept (m80_prepare_vehicle.py "budget": 0).
Run (the zip unpacked in <src>, the .blend written to <out>):
blender -b --factory-startup --python m80_auto_sorgente.py -- <key> <src>/FINAL_MODEL_xx.fbx <out>/<key>.blend
"""
import os
import re
import sys

import bpy
from mathutils import Matrix

KEY, SRC, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
# Body colours (linear): period colours, one per car.
PAINT = {
    "Mini": (0.03, 0.12, 0.05),          # British racing green, white roof
    "Maggiolino": (0.62, 0.33, 0.12),    # the file's sand orange
    "Golf": (0.38, 0.015, 0.012),        # Mars red
    "M3": (0.75, 0.75, 0.72),            # Alpine white
}[KEY]
# (pattern on the lower-case material name, new name, metallic, roughness, colour or None = the file's). First match wins.
RULES = [
    (r"carpaint_color_2", "Vernice_Tetto", 0.0, 0.35, (0.8, 0.8, 0.76)),
    (r"carpaint.*carbon", "Trama_Plastica", 0.0, 0.5, None),
    (r"carpaint.*smooth|plasticsmooth|^plastic$", "Plastica_Lucida", 0.0, 0.3, None),
    (r"carpaint.*trim|plasticrough|pastillas", "Plastica_Ruvida", 0.0, 0.7, None),
    (r"carpaint|beetle_1968_base", "Vernice_Carrozzeria", 0.0, 0.35, "paint"),
    (r"windowsurround", "Bordo_Vetri", 0.0, 0.4, (0.01, 0.01, 0.01)),
    (r"mirror|mirroir", "Specchio_Cromo", 1.0, 0.05, (0.9, 0.9, 0.9)),
    (r"lightglass.*orange|orange_glass", "Freccia_Vetro", 0.0, 0.1, None),
    (r"lightglass.*red|red_glass", "Stop_Vetro", 0.0, 0.1, None),
    (r"lightglass|glass_light|glass_n$", "Faro_Vetro", 0.0, 0.05, None),
    (r"glass|windows", "Vetro", 0.0, 0.05, None),
    (r"lightbucket|light_r$|light_max|lights_", "Fanaleria", 0.5, 0.3, None),
    (r"chrome|nickel|alumin|^exh", "Cromo", 1.0, 0.2, (0.9, 0.9, 0.9)),
    (r"disk|brake|break|calip|callip|phong19", "Freni_Metallo", 0.6, 0.5, None),
    (r"rim|tire_hub|wheel", "Cerchio", 0.6, 0.35, None),
    (r"tire|tyre|llanta", "Gomma", 0.0, 0.9, None),
    (r"badge", "Stemmi", 0.6, 0.3, None),
    (r"interior|internal|details_int", "Interni", 0.0, 0.6, None),
    (r"engine", "Motore", 0.4, 0.5, None),
    (r"plate", "Targa", 0.0, 0.5, None),
    (r"details_ext", "Dettagli_Esterni", 0.3, 0.4, None),
    (r"details_add", "Dettagli_Extra", 0.3, 0.4, None),
    (r"details_mat", "Dettagli", 0.3, 0.4, None),
    (r"chassis", "Telaio", 0.0, 0.8, None),
]
GLASS = ("Vetro", "Faro_Vetro", "Freccia_Vetro", "Stop_Vetro")


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None


def textured(m):
    return m.use_nodes and any(n.type == "TEX_IMAGE" and n.image for n in m.node_tree.nodes)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=SRC)
    # The FBX comes at 1:100 (3-4 cm long): to real size, the pipeline's tolerances are in metres.
    for o in bpy.data.objects:
        if o.parent is None:
            o.matrix_world = Matrix.Scale(100.0, 4) @ o.matrix_world
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    renamed = {}
    firsts = {}
    for m in list(bpy.data.materials):
        key = m.name.split(":")[-1].lower()
        rule = next((r for r in RULES if re.search(r[0], key)), None)
        if not rule:
            print("M80 material kept", m.name)
            continue
        _, name, metal, rough, colour = rule
        p = principled(m)
        if p:
            p.inputs["Metallic"].default_value = metal
            p.inputs["Roughness"].default_value = rough
            if name not in GLASS:
                for link in list(p.inputs["Alpha"].links):
                    m.node_tree.links.remove(link)
                p.inputs["Alpha"].default_value = 1.0
            if colour is not None:
                c = PAINT if colour == "paint" else colour
                p.inputs["Base Color"].default_value = tuple(c) + (1.0,)
                m.diffuse_color = tuple(c) + (1.0,)
        # Untextured materials of the same kind become one (chrome, black plastic...); textured ones keep their own,
        # numbered by Blender (.001).
        first = firsts.get(name)
        if first and not textured(m) and not textured(first):
            m.user_remap(first)
            bpy.data.materials.remove(m)
            renamed[key] = first.name
            continue
        m.name = name
        firsts.setdefault(name, m)
        renamed[key] = m.name
    print("M80 materials", renamed)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == "MESH" for p in o.data.polygons)
    print("M80 triangles", tris, "; saved", OUT)


main()
