"""Blender 5.2: the Alfa Romeo 155 Q4 (downloaded game model, 220k triangles) made into a Carabinieri car for the game.

1. Import the FBX, point its textures at <textures_dir> (the file's paths lead to the original game's folders), set
   the materials by hand (the file makes every one a rough metal): chrome, glass, rubber, lights, interior.
2. Reduce it to ~30k triangles with the M80 Riduci triangoli add-on (Research/Mazzarino80/Blender/addons), the total
   shared out among groups (body, wheels, interior...), the originals kept for the bake.
3. Carabinieri kit, as on a photo of a real 155: a blue beacon on the roof, the chrome searchlight, the CC plates.
4. Livery on the paint (materials body, body_2): dark blue metallic, white roof, the thin red waist line with its
   zigzag and 112 on the rear wings, CARABINIERI and the flame on the doors, CARABINIERI on the boot (images of
   m80_alfa155_livrea.py, projected from the sides and the back in the car's own space).
5. One new UV map for the whole car (M80_Bake, first: Unreal's UV0), baked into one set of 4096 textures:
   _Normal (the original's surface on the reduced one), _D (colour: livery, the original's textures, the kit), _M
   (paint only: R metallic, G roughness, B stickers, which are not metallic and less glossy). The materials then
   read the textures through M80_Bake, so the export carries them.
6. Photos (EEVEE, an outdoor HDRI, a metallic clear-coated paint) into <photo_dir>.
Run:
python m80_alfa155_livrea.py <out_dir>/Livrea
blender -b --factory-startup --python m80_alfa155_carabinieri.py -- <fbx> <textures_dir> <out_dir> <photo_dir>
Env: M80_TRIANGOLI (30000), M80_TEXTURE (4096), M80_SOLO_FOTO=1 (open <out_dir>/Alfa155_Carabinieri.blend, photos only),
M80_DOPO_NORMALI=1 (start again from <out_dir>/Lavoro/Dopo_normali.blend, saved after the long normal bake: livery,
colour bakes and photos only), M80_ORIGINALE=1 (photos of the full model with the same kit and livery).
"""
import math
import os
import sys
import time

import bpy
import bmesh
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
FBX, TEX, OUT, PHOTOS = ARGS[:4]
TARGET = int(os.environ.get("M80_TRIANGOLI", "30000"))
SIZE = int(os.environ.get("M80_TEXTURE", "4096"))
NAME = "Alfa155_Carabinieri"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "addons"))
import m80_riduci_triangoli as R  # noqa: E402

BLUE = (0.02, 0.034, 0.10, 1.0)            # the Carabinieri's night blue (linear; metallic, so a little lighter)
WHITE = (0.80, 0.80, 0.78, 1.0)
PAINT = ("body", "body_2")
GLASS = ("window", "glass", "Faro_Vetro")
# Livery images' frame (m80_alfa155_livrea.py): metres in the car's space.
Y0, Y1, Z0, Z1, XR = -2.35, 2.15, -0.20, 1.35, 0.9
# name -> (metallic, roughness, colour when no texture feeds it)
MATS = {
    "black": (0.0, 0.55, (0.015, 0.015, 0.015)),
    "black_glass": (0.0, 0.15, (0.01, 0.01, 0.01)),
    "bottom": (0.0, 0.7, None),
    "bumper_frame": (0.0, 0.6, None),
    "chrome_2": (1.0, 0.08, (0.9, 0.9, 0.9)),
    "Cromo": (1.0, 0.12, (0.85, 0.85, 0.85)),
    "gauge_needle": (0.0, 0.4, None),
    "head_light": (0.0, 0.1, None),
    "Material #2": (0.2, 0.5, None),
    "Material #3": (0.0, 0.6, None),
    "Material #4": (0.3, 0.15, None),
    "Material #5": (0.0, 0.9, None),
    "Material #6": (0.0, 0.65, None),
    "Material #7": (0.8, 0.35, None),
    "mirrorLeft": (1.0, 0.02, (0.9, 0.9, 0.9)),
    "mirrorRight": (1.0, 0.02, (0.9, 0.9, 0.9)),
    "mirrorMiddle": (1.0, 0.02, (0.9, 0.9, 0.9)),
    "plastic": (0.0, 0.3, None),
    "reverse_light_lod0": (0.0, 0.1, None),
    "tail_light_lod0": (0.0, 0.1, None),
    "rubber": (0.0, 0.85, (0.02, 0.02, 0.02)),
    "rubber_trim": (0.0, 0.8, (0.02, 0.02, 0.02)),
    "sidewall": (0.0, 0.85, (0.025, 0.025, 0.025)),
    "tread": (0.0, 0.9, (0.02, 0.02, 0.02)),
    "wheel_black": (0.0, 0.6, (0.02, 0.02, 0.02)),
    "solid": (0.0, 0.7, (0.02, 0.02, 0.02)),
}


def log(*a):
    print("M80 ALFA", *a, flush=True)


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.node_tree else None


def output(m):
    return next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None) or \
        next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)


def link(nt, src, dst):
    if isinstance(src, (int, float)):
        dst.default_value = src
    elif isinstance(src, tuple):
        dst.default_value = src
    else:
        nt.links.new(src, dst)


def unlink(nt, sock):
    for l in list(sock.links):
        nt.links.remove(l)


def mesh_objects():
    """The car's meshes (not the originals kept for the bake). From the scene: the view layer's list lags behind
    objects just linked."""
    backup = bpy.data.collections.get(R.BACKUP)
    return [o for o in bpy.context.scene.objects if o.type == 'MESH' and not (backup and o.name in backup.objects)]


# ---------------------------------------------------------------------------------------------
# 1) Import and materials

def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    R.register()
    try:
        cp = bpy.context.preferences.addons['cycles'].preferences
        cp.compute_device_type = 'OPTIX'
        cp.get_devices()
        for d in cp.devices:
            d.use = True
        bpy.context.scene.cycles.device = 'GPU'
    except Exception as e:  # noqa: BLE001
        log("no GPU", e)
    bpy.context.scene.cycles.samples = 1


def fix_images():
    """The file's textures by name in TEX; the reflection maps of the original game (not shipped) go."""
    missing = []
    for im in list(bpy.data.images):
        base = os.path.basename(im.filepath.replace("\\", "/"))
        path = os.path.join(TEX, base)
        if os.path.exists(path):
            im.filepath = path
            im.reload()
        elif im.source == 'FILE':
            missing.append(im)
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        for n in list(m.node_tree.nodes):
            if n.type == 'TEX_IMAGE' and n.image in missing:
                m.node_tree.nodes.remove(n)
    for im in missing:
        bpy.data.images.remove(im)
    log("textures missing (removed):", len(missing))


def materials():
    # Chrome pieces share the body's detail atlas material: their own chrome instead.
    chrome = bpy.data.materials.new("Cromo")
    chrome.use_nodes = True
    for o in mesh_objects():
        if "chrome" in o.name.lower():
            for s in o.material_slots:
                if s.material and s.material.name == "Material #2":
                    s.material = chrome
    # Headlight and fog-light lenses clear (they share the tail lights' textured material), the reflectors behind
    # them chrome.
    lens = material("Faro_Vetro", (0.9, 0.9, 0.9), rough=0.02, alpha=0.12)
    for o in mesh_objects():
        n = o.name.lower()
        if any(k in n for k in ("glasslhl", "glassrhl", "bumperfa_detail_glass_clear", "bumperfa_glass")):
            for s in o.material_slots:
                s.material = lens
        elif "headlight" in n and "reflector" in n:
            for s in o.material_slots:
                s.material = chrome
    for m in bpy.data.materials:
        if not m.use_nodes:
            m.use_nodes = True
        p = principled(m)
        if p is None or m in (lens,):
            continue
        nt = m.node_tree
        # In these textures the alpha is a mask, not transparency.
        unlink(nt, p.inputs["Alpha"])
        p.inputs["Alpha"].default_value = 1.0
        if m.name in GLASS:
            unlink(nt, p.inputs["Base Color"])
            p.inputs["Base Color"].default_value = (0.02, 0.025, 0.03, 1)
            p.inputs["Metallic"].default_value = 0.0
            p.inputs["Roughness"].default_value = 0.05
            p.inputs["Alpha"].default_value = 0.3
            m.surface_render_method = 'BLENDED'
            continue
        if m.name in PAINT:
            continue
        metal, rough, col = MATS.get(m.name, (0.0, 0.5, None))
        for k in ("Metallic", "Roughness"):
            unlink(nt, p.inputs[k])
        p.inputs["Metallic"].default_value = metal
        p.inputs["Roughness"].default_value = rough
        if col is not None:
            unlink(nt, p.inputs["Base Color"])
            p.inputs["Base Color"].default_value = (*col, 1.0)


# ---------------------------------------------------------------------------------------------
# 2) Reduction

def reduce():
    # A road car: the race roll cage of the game model goes.
    for o in [o for o in mesh_objects() if "cagerace" in o.name.lower()]:
        bpy.data.objects.remove(o)
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(o.type == 'MESH')
    vl.objects.active = mesh_objects()[0]
    s = bpy.context.scene.m80_riduci
    s.metodo = 'COLLAPSE'
    s.modalita = 'TARGET'
    s.minimo = 60
    s.prio_ruote = 1.3
    s.obiettivo = TARGET
    bpy.ops.m80.riduci_anteprima()
    log("reduced %d -> %d" % (s.prima, s.dopo), {k: v[1] for k, v in R.GSTATS.items()},
        "shape kept:", [o.name for o in mesh_objects() if o.get("m80_min_ratio")])
    bpy.ops.m80.riduci_applica()


# ---------------------------------------------------------------------------------------------
# 3) Carabinieri kit

def material(name, base, metal=0.0, rough=0.5, emit=None, strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = principled(m)
    p.inputs["Base Color"].default_value = (*base, 1.0)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = rough
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1.0)
        p.inputs["Emission Strength"].default_value = strength
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
        m.surface_render_method = 'BLENDED'
    return m


def cylinder(name, x, y, z0, r, h, mat, cap_dome=False):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r, radius2=r, depth=h)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2))
    if cap_dome:
        dome = bmesh.new()
        bmesh.ops.create_uvsphere(dome, u_segments=24, v_segments=12, radius=r)
        for v in [v for v in dome.verts if v.co.z < -1e-6]:
            v.co.z = 0.0
        bmesh.ops.translate(dome, verts=dome.verts, vec=(0, 0, h))
        me = bpy.data.meshes.new("tmp")
        dome.to_mesh(me)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        dome.free()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for f in me.polygons:
        f.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    o.location = (x, y, z0)
    bpy.context.scene.collection.objects.link(o)
    me.uv_layers.new(name="UV_Originale_1")
    return o


def plate_box(name, image, x, y, z, w, h, facing, mat_name):
    """A plate: a thin box whose outer face (towards facing = -1 front, +1 back) shows the image."""
    m = material(mat_name, (1.0, 1.0, 1.0), rough=0.4)
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(OUT, "Livrea", image))
    m.node_tree.links.new(t.outputs["Color"], principled(m).inputs["Base Color"])
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * 0.008, v.co.z * h))
    uv = bm.loops.layers.uv.new("UV_Originale_1")
    for f in bm.faces:
        for l in f.loops:
            if f.normal.y * facing > 0.5:
                # Seen from the front +X is on the viewer's right, from behind on the left.
                l[uv].uv = (0.5 - facing * l.vert.co.x / w, 0.5 + l.vert.co.z / h)
            else:
                l[uv].uv = (0.01, 0.5)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    o.location = (x, y, z)
    bpy.context.scene.collection.objects.link(o)
    return o


def surface(origin, direction):
    """Where a ray from origin meets the car (the kit is set on the real surfaces, not on guessed heights)."""
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = bpy.context.scene.ray_cast(dg, Vector(origin), Vector(direction).normalized())
    return loc if hit else None


def plate_y(xy, direction, z, h, pick):
    """The bumper's surface along Y over a plate's height (rays across its width and height)."""
    ys = [hit.y for dx in (-0.15, 0.0, 0.15) for dz in (-0.45, 0.0, 0.45)
          for hit in [surface((xy[0] + dx, xy[1], z + dz * h), direction)] if hit is not None]
    return pick(ys) if ys else None


def spotlight(name, x, y, z, chrome, lens):
    """The roof searchlight: a chrome pot on a short stem, its lens forward (-Y)."""
    stem = cylinder(name + "_Stelo", x, y, z, 0.015, 0.05, chrome)
    body = cylinder(name, 0, 0, 0, 0.065, 0.13, chrome)
    body.rotation_euler = (math.radians(90), 0, 0)      # the cylinder's +Z turned to -Y
    body.location = (x, y + 0.065, z + 0.11)
    glass = cylinder(name + "_Vetro", 0, 0, 0, 0.058, 0.004, lens)
    glass.rotation_euler = (math.radians(90), 0, 0)
    glass.location = (x, y - 0.066, z + 0.11)
    return [stem, body, glass]


def kit():
    """As on the photo of a real 155 of the Carabinieri: one blue beacon on the roof, the chrome searchlight, the CC
    plates."""
    blue = material("Lampeggiante", (0.03, 0.12, 0.85), rough=0.1, emit=(0.05, 0.25, 1.0), strength=8.0, alpha=0.9)
    base = material("Supporto", (0.02, 0.02, 0.02), rough=0.45)
    chrome = bpy.data.materials.get("Cromo") or material("Cromo", (0.85, 0.85, 0.85), metal=1.0, rough=0.12)
    lens = material("Faro_Ricerca_Vetro", (0.9, 0.9, 0.85), rough=0.05, emit=(1.0, 0.95, 0.8), strength=0.5)
    objs = []
    # The beacon over the B pillars, on the right; the searchlight at the front left of the roof.
    top = surface((-0.32, 0.25, 3.0), (0, 0, -1))
    z = top.z - 0.005 if top else 1.24
    objs.append(cylinder("Lampeggiante_Base", -0.32, 0.25, z, 0.085, 0.03, base))
    objs.append(cylinder("Lampeggiante", -0.32, 0.25, z + 0.03, 0.068, 0.085, blue, cap_dome=True))
    top = surface((0.34, -0.25, 3.0), (0, 0, -1))
    objs += spotlight("Faro_Ricerca", 0.34, -0.25, top.z - 0.005 if top else 1.21, chrome, lens)
    # Plates on the bumpers, in front of the bumper's most forward (backward) point over the plate's height: from
    # its middle alone the lip above hid half of the rear plate.
    front = plate_y((0.0, -4.0), (0, 1, 0), 0.20, 0.11, min)
    if front is not None:
        objs.append(plate_box("Targa_Anteriore", "Targa_Ant.png", 0.0, front - 0.006, 0.20, 0.52, 0.11, -1, "Targa_Ant"))
    back = plate_y((0.0, 4.0), (0, -1, 0), 0.25, 0.20, max)
    if back is not None:
        objs.append(plate_box("Targa_Posteriore", "Targa_Post.png", 0.0, back + 0.006, 0.25, 0.34, 0.20, 1, "Targa_Post"))
    log("kit: roof", round(z, 3), "plates", front is not None, back is not None)
    return objs


# ---------------------------------------------------------------------------------------------
# 4) Livery

class Graph:
    def __init__(self, nt):
        self.nt = nt
        self.y = 900

    def new(self, kind, x=-1400, **props):
        n = self.nt.nodes.new(kind)
        n.location = (x, self.y)
        self.y -= 160
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def math(self, op, a, b=None, clamp=False):
        n = self.new("ShaderNodeMath", operation=op, use_clamp=clamp)
        link(self.nt, a, n.inputs[0])
        if b is not None:
            link(self.nt, b, n.inputs[1])
        return n.outputs[0]

    def ramp(self, v, a, b):
        """0 below a, 1 above b, smooth between (b < a turns it round)."""
        n = self.new("ShaderNodeMapRange", interpolation_type='SMOOTHSTEP', clamp=True)
        link(self.nt, v, n.inputs["Value"])
        n.inputs["From Min"].default_value = a
        n.inputs["From Max"].default_value = b
        return n.outputs["Result"]

    def mix(self, fac, a, b):
        n = self.new("ShaderNodeMix", data_type='RGBA', blend_type='MIX')
        ins = [s for s in n.inputs if s.type == 'RGBA']
        link(self.nt, fac, n.inputs["Factor"] if "Factor" in n.inputs else n.inputs[0])
        link(self.nt, a, ins[0])
        link(self.nt, b, ins[1])
        return next(s for s in n.outputs if s.type == 'RGBA')

    def image(self, img, u, v):
        c = self.new("ShaderNodeCombineXYZ")
        link(self.nt, u, c.inputs[0])
        link(self.nt, v, c.inputs[1])
        t = self.new("ShaderNodeTexImage", x=-900, image=img, extension='CLIP', interpolation='Cubic')
        self.nt.links.new(c.outputs[0], t.inputs["Vector"])
        return t


def livery(empty):
    imgs = {}
    for k in ("SX", "DX", "Retro"):
        im = bpy.data.images.load(os.path.join(OUT, "Livrea", "Livrea_%s.png" % k))
        im.alpha_mode = 'STRAIGHT'
        imgs[k] = im
    for name in PAINT:
        m = bpy.data.materials.get(name)
        if not m:
            continue
        nt = m.node_tree
        p = principled(m)
        g = Graph(nt)
        tc = g.new("ShaderNodeTexCoord", object=empty)
        pos = g.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], pos.inputs[0])
        geo = g.new("ShaderNodeNewGeometry")
        nrm = g.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Normal"], nrm.inputs[0])
        x, y, z = pos.outputs
        nx, ny, nz = nrm.outputs
        v = g.math('DIVIDE', g.math('SUBTRACT', Z1, z), Z1 - Z0)
        v = g.math('SUBTRACT', 1.0, v)                    # image rows run down, UV v up
        u_sx = g.math('DIVIDE', g.math('SUBTRACT', y, Y0), Y1 - Y0)
        u_dx = g.math('DIVIDE', g.math('SUBTRACT', Y1, y), Y1 - Y0)
        u_re = g.math('DIVIDE', g.math('SUBTRACT', XR, x), 2 * XR)
        t_sx, t_dx, t_re = g.image(imgs["SX"], u_sx, v), g.image(imgs["DX"], u_dx, v), g.image(imgs["Retro"], u_re, v)
        # Each projection only where the surface faces its way (no smearing over the top).
        a_sx = g.math('MULTIPLY', t_sx.outputs["Alpha"], g.ramp(nx, 0.45, 0.6))
        a_dx = g.math('MULTIPLY', t_dx.outputs["Alpha"], g.ramp(nx, -0.45, -0.6))
        a_re = g.math('MULTIPLY', t_re.outputs["Alpha"], g.ramp(ny, 0.45, 0.65))
        # White roof: up-facing, above the windows' top, between the windscreen and the rear window.
        roof = g.math('MULTIPLY', g.ramp(z, 1.10, 1.13), g.ramp(nz, 0.35, 0.55))
        roof = g.math('MULTIPLY', roof, g.math('MULTIPLY', g.ramp(y, -0.55, -0.45), g.ramp(y, 1.15, 1.05)))
        col = g.mix(roof, BLUE, WHITE)
        col = g.mix(a_sx, col, t_sx.outputs["Color"])
        col = g.mix(a_dx, col, t_dx.outputs["Color"])
        col = g.mix(a_re, col, t_re.outputs["Color"])
        decal = g.math('MAXIMUM', a_sx, g.math('MAXIMUM', a_dx, a_re))
        # (The original's paint texture, nodamage_lod0, is a dark dirt map in this file: not used, it blackened the
        # paint and the stickers.)
        unlink(nt, p.inputs["Base Color"])
        out = g.new("ShaderNodeMix", data_type='RGBA', blend_type='MIX')   # a named handle for the bake
        out.name = out.label = "Livrea Colore"
        out.inputs["Factor"].default_value = 0.0
        nt.links.new(col, [s for s in out.inputs if s.type == 'RGBA'][0])
        col = next(s for s in out.outputs if s.type == 'RGBA')
        nt.links.new(col, p.inputs["Base Color"])
        # Metallic paint, white roof less so, stickers flat vinyl.
        metal = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, decal), g.math('SUBTRACT', 0.7, g.math('MULTIPLY', roof, 0.55)))
        rough = g.math('ADD', 0.30, g.math('MULTIPLY', decal, 0.2))
        mask = g.new("ShaderNodeCombineXYZ")
        mask.name = mask.label = "Livrea Maschera"
        nt.links.new(metal, mask.inputs[0])
        nt.links.new(rough, mask.inputs[1])
        nt.links.new(decal, mask.inputs[2])
        unlink(nt, p.inputs["Metallic"])
        unlink(nt, p.inputs["Roughness"])
        nt.links.new(metal, p.inputs["Metallic"])
        nt.links.new(rough, p.inputs["Roughness"])
        p.inputs["Coat Weight"].default_value = 1.0
        p.inputs["Coat Roughness"].default_value = 0.03


# ---------------------------------------------------------------------------------------------
# 5) Bakes

def bake_emit(objs, mats, img, source):
    """Bakes, as emission, what source(material) returns (a socket or a colour) into img through M80_Bake."""
    sc = bpy.context.scene
    keep = {}
    for m in mats:
        nt = m.node_tree
        o = output(m)
        keep[m] = o.inputs["Surface"].links[0].from_socket if o.inputs["Surface"].is_linked else None
        em = nt.nodes.new("ShaderNodeEmission")
        em.name = "Cuoci Emissione"
        src = source(m)
        if isinstance(src, tuple):
            em.inputs["Color"].default_value = src
        else:
            nt.links.new(src, em.inputs["Color"])
        nt.links.new(em.outputs[0], o.inputs["Surface"])
        t = nt.nodes.new("ShaderNodeTexImage")
        t.name = "Cuoci Immagine"
        t.image = img
        nt.nodes.active = t
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(o in objs)
    vl.objects.active = objs[0]
    engine, device = sc.render.engine, sc.cycles.device
    sc.render.engine = 'CYCLES'
    # On the GPU (OptiX) a bake of many objects into one image kept only the last object's pixels: on the CPU all of
    # them land. use_clear would clear the image for every object.
    sc.cycles.device = 'CPU'
    bpy.ops.object.bake(type='EMIT', margin=max(2, SIZE // 1024), use_clear=False, target='IMAGE_TEXTURES')
    sc.render.engine, sc.cycles.device = engine, device
    for m in mats:
        nt = m.node_tree
        o = output(m)
        if keep[m] is not None:
            nt.links.new(keep[m], o.inputs["Surface"])
        for n in ("Cuoci Emissione", "Cuoci Immagine"):
            if n in nt.nodes:
                nt.nodes.remove(nt.nodes[n])


def base_colour(m):
    p = principled(m)
    if p is None:
        return (0.5, 0.5, 0.5, 1.0)
    i = p.inputs["Base Color"]
    return i.links[0].from_socket if i.is_linked else tuple(i.default_value)


def paint_mask(m):
    n = m.node_tree.nodes.get("Livrea Maschera")
    return n.outputs[0] if n else (0.0, 0.0, 0.0, 1.0)


def new_image(name, colour, non_color):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=False)
    im.generated_color = colour
    if non_color:
        im.colorspace_settings.name = 'Non-Color'
    return im


def save(im, folder):
    im.filepath_raw = os.path.join(folder, im.name + ".png")
    im.file_format = 'PNG'
    im.save()


def textures_through_bake(mats, d, mm):
    """The materials read the baked colour (and the paint its mask) through M80_Bake: what the export carries."""
    for m in mats:
        nt = m.node_tree
        p = principled(m)
        if p is None:
            continue
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = R.BAKE_UV
        uv.location = (-1900, 1300)
        t = nt.nodes.new("ShaderNodeTexImage")
        t.name = t.label = "Atlante Colore"
        t.image = d
        t.location = (-1700, 1300)
        nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
        if m.name not in GLASS:
            unlink(nt, p.inputs["Base Color"])
            nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
        if m.name in PAINT:
            tm = nt.nodes.new("ShaderNodeTexImage")
            tm.name = tm.label = "Atlante Maschera"
            tm.image = mm
            tm.location = (-1700, 1000)
            nt.links.new(uv.outputs["UV"], tm.inputs["Vector"])
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            sep.location = (-1450, 1000)
            nt.links.new(tm.outputs["Color"], sep.inputs[0])
            unlink(nt, p.inputs["Metallic"])
            unlink(nt, p.inputs["Roughness"])
            nt.links.new(sep.outputs[0], p.inputs["Metallic"])
            nt.links.new(sep.outputs[1], p.inputs["Roughness"])


# ---------------------------------------------------------------------------------------------
# 6) Photos

def photos():
    sc = bpy.context.scene
    os.makedirs(PHOTOS, exist_ok=True)
    w = bpy.data.worlds.new("Cielo")
    w.use_nodes = True
    env = w.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(os.path.dirname(bpy.app.binary_path), "%d.%d" % bpy.app.version[:2],
                                                  "datafiles", "studiolights", "world", "courtyard.exr"))
    bg = w.node_tree.nodes["Background"]
    w.node_tree.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    sc.world = w
    sun = bpy.data.objects.new("Sole", bpy.data.lights.new("Sole", 'SUN'))
    sun.data.energy = 3.5
    sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    sc.collection.objects.link(sun)
    ground = bpy.data.meshes.new("Suolo")
    ground.from_pydata([(-30, -30, -0.18), (30, -30, -0.18), (30, 30, -0.18), (-30, 30, -0.18)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("Suolo", ground)
    sc.collection.objects.link(g)
    gm = material("Asfalto", (0.10, 0.10, 0.10), rough=0.85)
    ground.materials.append(gm)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.taa_render_samples = 64
    try:
        sc.eevee.use_raytracing = True
    except Exception:  # noqa: BLE001
        pass
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
    views = {
        "1_tre_quarti_davanti": ((-4.2, -4.6, 1.5), (0, -0.3, 0.55), 50),
        "2_tre_quarti_dietro": ((3.9, 4.8, 1.7), (0, 0.4, 0.6), 50),
        "3_fianco_sinistro": ((7.4, -0.05, 0.9), (0, -0.05, 0.55), 50),
        "4_fianco_destro": ((-7.4, -0.05, 0.9), (0, -0.05, 0.55), 50),
        "5_dietro": ((0.4, 6.3, 1.3), (0, 1.5, 0.6), 50),
        "6_tetto": ((2.6, -2.2, 3.0), (0, 0.3, 1.2), 50),
        "7_porta": ((2.2, -1.6, 0.85), (0.8, -0.2, 0.6), 50),
        "8_davanti": ((0.6, -6.2, 1.1), (0, -1.5, 0.5), 50),
    }
    for name, (eye, tgt, lens) in views.items():
        eye, tgt = Vector(eye), Vector(tgt)
        cam.location = eye
        cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = lens
        sc.render.filepath = os.path.join(PHOTOS, name + ".png")
        bpy.ops.render.render(write_still=True)
        log("photo", name)


# ---------------------------------------------------------------------------------------------

def main():
    t0 = time.time()
    if os.environ.get("M80_SOLO_FOTO"):
        bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
        photos()
        return
    work = os.path.join(OUT, "Lavoro", "Dopo_normali.blend")
    tex = os.path.join(OUT, "Textures")
    if os.environ.get("M80_DOPO_NORMALI"):
        bpy.ops.wm.open_mainfile(filepath=work)
        R.register()
        for im in bpy.data.images:          # the livery as it is now on disk
            if im.source == 'FILE':
                im.reload()
        finish(tex, t0)
        return
    setup()
    bpy.ops.import_scene.fbx(filepath=FBX)
    fix_images()
    materials()
    if os.environ.get("M80_ORIGINALE"):
        # The full model with the same kit and livery, for comparing with the reduced one.
        for o in [o for o in mesh_objects() if "cagerace" in o.name.lower()]:
            bpy.data.objects.remove(o)
        kit()
        empty = bpy.data.objects.new("Livrea_Spazio", None)
        bpy.context.scene.collection.objects.link(empty)
        livery(empty)
        photos()
        return
    reduce()
    kit_objs = kit()
    bpy.context.view_layer.update()
    empty = bpy.data.objects.new("Livrea_Spazio", None)
    bpy.context.scene.collection.objects.link(empty)
    livery(empty)
    objs = [o for o in mesh_objects()]
    targets = [o for o in objs if R.original_of(o) is not None]
    log("bake: %d meshes (%d from originals, %d kit)" % (len(objs), len(targets), len(kit_objs)))
    img_n, failed = R.bake_normals(bpy.context, objs, targets, SIZE, 1.5, NAME, tex)
    log("normal map", img_n.filepath_raw, "failed", len(failed), "%.0f s" % (time.time() - t0))
    os.makedirs(os.path.dirname(work), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=work, copy=True)
    finish(tex, t0)


KIT = ("Lampeggiante", "Faro_Ricerca", "Targa_")


def finish(tex, t0):
    objs = mesh_objects()
    kit_objs = [o for o in objs if o.name.startswith(KIT)]
    mats = R.materials_of(objs)
    d = new_image("M80_%s_D" % NAME, (0.5, 0.5, 0.5, 1.0), False)
    bake_emit(objs, mats, d, base_colour)
    save(d, tex)
    mm = new_image("M80_%s_M" % NAME, (0.0, 0.0, 0.0, 1.0), True)
    bake_emit(objs, mats, mm, paint_mask)
    save(mm, tex)
    textures_through_bake(mats, d, mm)
    tris = sum(R.mesh_tris(o.data) for o in objs)
    log("triangles %d (car %d, kit %d)" % (tris, tris - sum(R.mesh_tris(o.data) for o in kit_objs), sum(R.mesh_tris(o.data) for o in kit_objs)))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"))
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile()
    photos()
    log("done %.0f s" % (time.time() - t0))


main()
