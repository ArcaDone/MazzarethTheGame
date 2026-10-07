"""Palazzo Bartoli, piano nobile: rooms in the frame of the Corso facade (u along it, w into the
building, v above the street at the facade, 0.9 m above 169 m). Floor v 5.0, ceiling v 9.0.

Enfilade on the Corso (study, dining room, ballroom over the portal, bedroom), a corridor behind,
music room and library towards the courtyard, the west wing's corridor and the anteroom whose french
window opens on the courtyard gallery (the way in from the staircase).
"""
import math
import os
import random

import bmesh
import bpy

import m80_arch_kit as K
from m80_bartoli_interni import curtain, fresco, majolica, mat

PN_FLOOR, PN_CEIL = 5.0, 9.0
# Floors and walls from the photos of the rooms (textures of m80_bartoli_texture.py): floor, rotation of
# the floor pattern (degrees), wall colour, and an optional band around the floor (texture, inset, width).
FINITURE = {
    "Salone": ("Scacchiera", 0, "Bianco", ("MarmoNero", 0.35, 0.12)),
    "Anticamera": ("PietraGrigia", 45, "Menta", ("MarmoNero", 0.40, 0.10)),
    "Corridoio": ("PietraGrigia", 0, "Menta", None),
    "Corridoio_ovest": ("PietraGrigia", 0, "Menta", None),
    "Studio": ("CementinaOcra", 0, "Bianco", None),
    "Pranzo": ("CementinaOcra", 0, "Azzurro", None),
    "Musica": ("CementinaRosa", 0, "Blu", None),
    "Camera": ("CementinaRosa", 0, "Azzurro", None),
    "Biblioteca": ("CementinaPunti", 0, "Bianco", ("FasciaCementina", 0.40, 0.20)),
}
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Textures", "Bartoli", "Interni")
TEX_SIZE = {"Scacchiera": 0.33 * 2 ** 0.5 * 2, "CementinaRosa": 0.8, "CementinaOcra": 0.8, "CementinaPunti": 0.8,
            "FasciaCementina": 0.8, "PietraGrigia": 1.6, "MarmoNero": 1.0, "Intonaco": 2.0}


def tex_material(name, d, n, orm, normal_strength=1.0):
    """PBR material from the D / N / ORM maps (UVs are in texture repeats, set on the mesh)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def img(fname, data):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(TEX, fname), check_existing=True)
        if data:
            t.image.colorspace_settings.name = "Non-Color"
        return t

    nt.links.new(img(d, False).outputs[0], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(img(orm, True).outputs[0], sep.inputs[0])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = normal_strength
    nt.links.new(img(n, True).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    return m


def floor_material(key):
    return tex_material("PB_Pav_" + key, "T_PB_%s_D.jpg" % key, "T_PB_%s_N.png" % key, "T_PB_%s_ORM.png" % key)


def wall_material(colour):
    return tex_material("PB_Intonaco_" + colour, "T_PB_Intonaco%s_D.jpg" % colour, "T_PB_Intonaco_N.png",
                        "T_PB_Intonaco_ORM.png", 0.4)


def box_uv(ob, size, rot_deg=0.0):
    """World-scale UVs (one repeat = 'size' metres): floors and ceilings by plan (rotated), walls along
    their length and height."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    c, s_ = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    for poly in me.polygons:
        nx, ny, nz = (abs(a) for a in poly.normal)
        for li in poly.loop_indices:
            x, y, z = me.vertices[me.loops[li].vertex_index].co
            if nz >= max(nx, ny):
                a, b = x * c - y * s_, x * s_ + y * c
            elif nx >= ny:
                a, b = y, z
            else:
                a, b = x, z
            uv.data[li].uv = (a / size, b / size)


def floor_band(col, root, name, r, key, inset, width, z):
    """A band of marble or border tiles running round the room, 'inset' from the walls."""
    u0, u1, w0, w1 = r[0] + inset, r[1] - inset, r[2] + inset, r[3] - inset
    size = TEX_SIZE[key]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    # Four mitred strips; U runs along the strip, V across it (0..1 = the band's width for the border tiles).
    outer = [(u0, w0), (u1, w0), (u1, w1), (u0, w1)]
    inner = [(u0 + width, w0 + width), (u1 - width, w0 + width), (u1 - width, w1 - width), (u0 + width, w1 - width)]
    for i in range(4):
        a, b, bi, ai = outer[i], outer[(i + 1) % 4], inner[(i + 1) % 4], inner[i]
        f = bm.faces.new([bm.verts.new((p[0], p[1], z)) for p in (a, b, bi, ai)])
        along = math.hypot(b[0] - a[0], b[1] - a[1])
        vs = 1.0 if key == "FasciaCementina" else width / size
        for loop, (t, q) in zip(f.loops, ((0, 0), (along, 0), (along - width, vs), (width, vs))):
            loop[uvl].uv = (t / size, q if key == "FasciaCementina" else q)
        if f.normal.z < 0:
            f.normal_flip()
    return K.bm_object(name, bm, col, root, floor_material(key))


# Furniture and dressing are off by default: the interiors are bare rooms that take the wall and floor
# textures; M80_ARREDI=1 brings back the furnished version.
ARREDI = os.environ.get("M80_ARREDI", "0") == "1"
ROOMS = {
    # name: (u0, u1, w0, w1, floor colours, wall colour, ceiling)
    "Studio": (0.9, 4.95, 0.32, 6.8, ((0.55, 0.47, 0.30), (0.08, 0.20, 0.30), (0.45, 0.30, 0.10)), (0.42, 0.36, 0.24), "plain"),
    "Pranzo": (5.15, 9.0, 0.32, 6.8, ((0.62, 0.56, 0.42), (0.35, 0.08, 0.05), (0.10, 0.25, 0.12)), (0.40, 0.20, 0.12), "plain"),
    "Salone": (9.2, 17.1, 0.32, 6.8, ((0.66, 0.60, 0.46), (0.06, 0.16, 0.32), (0.55, 0.36, 0.08)), (0.38, 0.44, 0.36), "fresco"),
    "Camera": (17.3, 21.2, 0.32, 6.8, ((0.62, 0.58, 0.48), (0.30, 0.12, 0.20), (0.15, 0.28, 0.20)), (0.46, 0.36, 0.34), "plain"),
    "Corridoio": (0.9, 21.2, 7.0, 8.6, ((0.55, 0.50, 0.40), (0.20, 0.18, 0.15), (0.40, 0.30, 0.15)), (0.48, 0.44, 0.36), "plain"),
    "Musica": (0.9, 8.8, 8.8, 14.1, ((0.60, 0.55, 0.42), (0.10, 0.22, 0.25), (0.48, 0.30, 0.12)), (0.30, 0.34, 0.30), "plain"),
    "Biblioteca": (14.9, 21.2, 8.8, 14.1, ((0.50, 0.40, 0.28), (0.25, 0.10, 0.05), (0.20, 0.18, 0.10)), (0.25, 0.14, 0.08), "plain"),
    "Corridoio_ovest": (9.0, 13.8, 8.8, 18.0, ((0.55, 0.50, 0.40), (0.20, 0.18, 0.15), (0.40, 0.30, 0.15)), (0.48, 0.44, 0.36), "plain"),
    "Anticamera": (9.0, 13.8, 18.2, 22.5, ((0.58, 0.52, 0.40), (0.30, 0.10, 0.06), (0.12, 0.22, 0.18)), (0.44, 0.40, 0.30), "plain"),
}
# Doorways: (room, side, centre along that wall, width). Sides: S = w0 (facade side), N = w1, W = u0, E = u1.
DOORS = [("Studio", "E", 3.6, 1.3), ("Pranzo", "W", 3.6, 1.3), ("Pranzo", "E", 3.6, 1.3), ("Salone", "W", 3.6, 1.3),
         ("Salone", "E", 3.6, 1.3), ("Camera", "W", 3.6, 1.3),
         ("Studio", "N", 2.9, 1.1), ("Pranzo", "N", 7.1, 1.1), ("Salone", "N", 13.2, 1.6), ("Camera", "N", 19.2, 1.1),
         ("Corridoio", "S", 2.9, 1.1), ("Corridoio", "S", 7.1, 1.1), ("Corridoio", "S", 13.2, 1.6), ("Corridoio", "S", 19.2, 1.1),
         ("Corridoio", "N", 4.8, 1.1), ("Corridoio", "N", 11.4, 1.4), ("Corridoio", "N", 18.0, 1.1),
         ("Musica", "S", 4.8, 1.1), ("Corridoio_ovest", "S", 11.4, 1.4), ("Biblioteca", "S", 18.0, 1.1),
         ("Corridoio_ovest", "N", 11.4, 1.2), ("Anticamera", "S", 11.4, 1.2)]
# Gaps for the facade's windows on the outer walls.
WINDOWS = [("Studio", "S", 2.6, 1.12), ("Pranzo", "S", 7.1, 1.12), ("Salone", "S", 11.0, 1.12), ("Salone", "S", 15.25, 1.12),
           ("Camera", "S", 19.65, 1.10), ("Anticamera", "E", 20.05, 1.1), ("Corridoio_ovest", "E", 16.86, 1.1),
           ("Biblioteca", "N", 17.15, 1.1), ("Biblioteca", "N", 20.1, 1.1)]


def _wall(bm, side, r, gaps, z0, z1, gap_top):
    """One 10 cm wall inside the room, with gaps (door or window) and the lintel above each gap."""
    u0, u1, w0, w1 = r[:4]
    t = 0.1
    horizontal = side in ("S", "N")
    a, b = (u0, u1) if horizontal else (w0, w1)
    fixed = (w0 if side == "S" else w1 - t) if horizontal else (u0 if side == "W" else u1 - t)
    cur = a
    for c, wd in sorted(gaps):
        _seg(bm, horizontal, fixed, t, cur, c - wd / 2, z0, z1)
        _seg(bm, horizontal, fixed, t, c - wd / 2, c + wd / 2, gap_top, z1)
        cur = c + wd / 2
    _seg(bm, horizontal, fixed, t, cur, b, z0, z1)


def _seg(bm, horizontal, fixed, t, s0, s1, z0, z1):
    if s1 - s0 < 0.01:
        return
    if horizontal:
        K.box_bm(bm, s0, s1, fixed, fixed + t, z0, z1)
    else:
        K.box_bm(bm, fixed, fixed + t, s0, s1, z0, z1)


def piece(col, root, name, items, material, bevel=0.012):
    bm = bmesh.new()
    for it in items:
        K.box_bm(bm, *it)
    ob = K.bm_object(name, bm, col, root, material)
    if bevel:
        # No perfectly sharp edge on handmade furniture and stucco.
        b = ob.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = 3
        b.limit_method = "ANGLE"
        ob.data.shade_smooth()
        ob.data.set_sharp_from_angle(angle=0.6) if hasattr(ob.data, "set_sharp_from_angle") else None
    return ob


def build(frame):
    col = K.collection("PianoNobile")
    root = bpy.data.objects.new("PianoNobile_Frame", None)
    bpy.context.scene.collection.objects.link(root)
    root.matrix_world = frame.matrix_world.copy()
    z0, z1 = PN_FLOOR, PN_CEIL
    cornice = mat("Cornice_stucco", (0.62, 0.58, 0.50), 0.7)
    dado = mat("Zoccolatura", (0.18, 0.12, 0.08), 0.5)
    for name, r in ROOMS.items():
        u0, u1, w0, w1, fc, wc, ceil = r
        bm = bmesh.new()
        bm.faces.new([bm.verts.new(p) for p in ((u0, w0, z0), (u1, w0, z0), (u1, w1, z0), (u0, w1, z0))])
        fin = FINITURE.get(name)
        if fin and os.path.exists(os.path.join(TEX, "T_PB_%s_D.jpg" % fin[0])):
            fl = K.bm_object("PN_%s_pavimento" % name, bm, col, root, floor_material(fin[0]))
            box_uv(fl, TEX_SIZE[fin[0]], fin[1])
            if fin[3]:
                floor_band(col, root, "PN_%s_fascia" % name, r, fin[3][0], fin[3][1], fin[3][2], z0 + 0.002)
        else:
            K.bm_object("PN_%s_pavimento" % name, bm, col, root, majolica("Maiolica_" + name, *fc))
        cm = fresco("Affresco_" + name, (0.30, 0.42, 0.55), (0.6, 0.45, 0.2)) if ceil == "fresco" else mat("Soffitto_" + name, (0.62, 0.58, 0.50), 0.9)
        bm = bmesh.new()
        bm.faces.new([bm.verts.new(p) for p in ((u0, w0, z1), (u0, w1, z1), (u1, w1, z1), (u1, w0, z1))])
        K.bm_object("PN_%s_soffitto" % name, bm, col, root, cm)
        bm = bmesh.new()
        for side in ("S", "N", "W", "E"):
            wins = [(c, wd) for rn, sd, c, wd in WINDOWS if rn == name and sd == side]
            gaps = [(c, wd) for rn, sd, c, wd in DOORS if rn == name and sd == side]
            if wins:
                _wall(bm, side, r, wins, z0, z1, z0 + 2.85)
            else:
                _wall(bm, side, r, gaps, z0, z1, z0 + 2.6)
        if fin and os.path.exists(os.path.join(TEX, "T_PB_Intonaco%s_D.jpg" % fin[2])):
            wl = K.bm_object("PN_%s_pareti" % name, bm, col, root, wall_material(fin[2]))
            box_uv(wl, TEX_SIZE["Intonaco"])
        else:
            K.bm_object("PN_%s_pareti" % name, bm, col, root, mat("Parete_" + name, wc, 0.85))
        piece(col, root, "PN_%s_battiscopa" % name,
              [(u0, u1, w0 + 0.1, w0 + 0.12, z0, z0 + 0.12), (u0, u1, w1 - 0.12, w1 - 0.1, z0, z0 + 0.12),
               (u0 + 0.1, u0 + 0.12, w0, w1, z0, z0 + 0.12), (u1 - 0.12, u1 - 0.1, w0, w1, z0, z0 + 0.12)], dado)
        piece(col, root, "PN_%s_cornice" % name,
              [(u0, u1, w0 + 0.1, w0 + 0.25, z1 - 0.25, z1), (u0, u1, w1 - 0.25, w1 - 0.1, z1 - 0.25, z1),
               (u0 + 0.1, u0 + 0.25, w0, w1, z1 - 0.25, z1), (u1 - 0.25, u1 - 0.1, w0, w1, z1 - 0.25, z1)], cornice)
    _door_leaves(col, root)
    if ARREDI:
        _furnish(col, root)
        _dress(col, root)
    else:
        # Bare rooms (walls, floors, ceilings, doors): one light per room, only for the previews.
        for name, (u0, u1, w0, w1, *_rest) in ROOMS.items():
            lo = bpy.data.objects.new("PN_%s_luce" % name, bpy.data.lights.new("PN_%s_luce" % name, "POINT"))
            lo.data.energy = 25 * (u1 - u0) * (w1 - w0) ** 0.5
            lo.data.color = (1.0, 0.85, 0.65)
            lo.data.shadow_soft_size = 0.6
            col.objects.link(lo)
            lo.parent = root
            lo.location = ((u0 + u1) / 2, (w0 + w1) / 2, z1 - 0.5)
    return col


def _dress(col, root):
    """Curtains at the windows on the Corso, paintings, the ballroom's painted ceiling in a gilt frame."""
    drape = mat("Tende_damascate", (0.45, 0.30, 0.12), 0.8)
    for room, side, c, wd in WINDOWS:
        if side != "S":
            continue
        for k, (a, b) in enumerate(((c - wd / 2 - 0.75, c - wd / 2 + 0.05), (c + wd / 2 - 0.05, c + wd / 2 + 0.75))):
            curtain("PN_tenda_%s_%.1f_%d" % (room, c, k), a, b, 0.62, PN_FLOOR, PN_CEIL - 0.3, col, folds=5, parent=root, material=drape)
        piece(col, root, "PN_mantovana_%s_%.1f" % (room, c), [(c - wd / 2 - 0.8, c + wd / 2 + 0.8, 0.5, 0.66, PN_CEIL - 0.6, PN_CEIL - 0.25)], drape)
    gilt = mat("Dorato", (0.55, 0.40, 0.15), 0.35, 0.8)
    rnd = random.Random(5)
    walls = [("Salone", 10.0, 16.2, 6.68), ("Pranzo", 5.6, 8.6, 6.68), ("Studio", 2.0, 4.6, 6.68), ("Camera", 17.6, 20.6, 6.68),
             ("Musica", 1.5, 8.2, 13.98), ("Anticamera", 9.4, 13.4, 22.38)]
    for room, u0, u1, w in walls:
        n = max(1, int((u1 - u0) / 1.9))
        for k in range(n):
            uc = u0 + (u1 - u0) * (k + 0.5) / n
            wdt, hgt = rnd.uniform(0.7, 1.2), rnd.uniform(0.8, 1.4)
            z = PN_FLOOR + 1.5
            canvas = mat("Tela_%s_%d" % (room, k), (rnd.uniform(0.05, 0.25), rnd.uniform(0.04, 0.18), rnd.uniform(0.02, 0.12)), 0.6)
            piece(col, root, "PN_quadro_%s_%d" % (room, k), [(uc - wdt / 2 - 0.08, uc + wdt / 2 + 0.08, w - 0.05, w, z - 0.08, z + hgt + 0.08)], gilt)
            piece(col, root, "PN_tela_%s_%d" % (room, k), [(uc - wdt / 2, uc + wdt / 2, w - 0.06, w - 0.05, z, z + hgt)], canvas, bevel=0)
    # Ballroom ceiling: a painted sky in an oval-ish frame of gilt stucco.
    sky = mat("Affresco_cielo", (0.22, 0.38, 0.62), 0.9)
    piece(col, root, "Salone_affresco", [(10.6, 15.7, 1.6, 5.6, PN_CEIL - 0.02, PN_CEIL - 0.01)], sky, bevel=0)
    piece(col, root, "Salone_cornice_affresco", [(10.4, 15.9, 1.4, 1.6, PN_CEIL - 0.12, PN_CEIL), (10.4, 15.9, 5.6, 5.8, PN_CEIL - 0.12, PN_CEIL),
                                                 (10.4, 10.6, 1.4, 5.8, PN_CEIL - 0.12, PN_CEIL), (15.7, 15.9, 1.4, 5.8, PN_CEIL - 0.12, PN_CEIL)], gilt)


def _door_leaves(col, root):
    """Panelled double doors, opened against the wall, in the enfilade and corridor doorways."""
    wood = mat("Porta_laccata", (0.50, 0.46, 0.38), 0.5)
    frame = mat("Stipite_dorato", (0.50, 0.36, 0.14), 0.4, 0.6)
    for k, (room, side, c, wd) in enumerate(DOORS):
        r = ROOMS[room]
        if side not in ("E", "S"):
            continue           # one door per opening (the neighbour room has the matching gap)
        z0 = PN_FLOOR
        if side == "E":
            u = r[1]
            piece(col, root, "PN_porta%d_stipite" % k, [(u - 0.14, u + 0.14, c - wd / 2 - 0.12, c - wd / 2, z0, z0 + 2.72),
                                                        (u - 0.14, u + 0.14, c + wd / 2, c + wd / 2 + 0.12, z0, z0 + 2.72),
                                                        (u - 0.14, u + 0.14, c - wd / 2 - 0.12, c + wd / 2 + 0.12, z0 + 2.6, z0 + 2.72)], frame)
            half = wd / 2
            piece(col, root, "PN_porta%d_ante" % k, [(u + 0.12, u + 0.12 + half, c - wd / 2 - 0.05, c - wd / 2, z0, z0 + 2.58),
                                                     (u + 0.12, u + 0.12 + half, c + wd / 2, c + wd / 2 + 0.05, z0, z0 + 2.58)], wood)
        else:
            w = r[2]
            if room in ("Studio", "Pranzo", "Salone", "Camera"):
                continue       # S side of the front rooms is the facade
            piece(col, root, "PN_porta%d_stipite" % k, [(c - wd / 2 - 0.12, c - wd / 2, w - 0.14, w + 0.14, z0, z0 + 2.72),
                                                        (c + wd / 2, c + wd / 2 + 0.12, w - 0.14, w + 0.14, z0, z0 + 2.72),
                                                        (c - wd / 2 - 0.12, c + wd / 2 + 0.12, w - 0.14, w + 0.14, z0 + 2.6, z0 + 2.72)], frame)


def _table(col, root, name, u, w, lu, lw, h, wood):
    t = 0.07
    items = [(u - lu / 2, u + lu / 2, w - lw / 2, w + lw / 2, h - 0.05, h)]
    for su in (-1, 1):
        for sw in (-1, 1):
            cu, cw = u + su * (lu / 2 - 0.1), w + sw * (lw / 2 - 0.1)
            items.append((cu - t / 2, cu + t / 2, cw - t / 2, cw + t / 2, PN_FLOOR, h - 0.05))
    piece(col, root, name, items, wood)


def _chair(col, root, name, u, w, face, wood, cloth):
    z = PN_FLOOR
    items = [(u - 0.22, u + 0.22, w - 0.22, w + 0.22, z + 0.42, z + 0.48)]
    back = {"S": (0, 0.2), "N": (0, -0.2), "W": (0.2, 0), "E": (-0.2, 0)}[face]
    if back[1]:
        items.append((u - 0.22, u + 0.22, w + back[1] - 0.03, w + back[1] + 0.03, z + 0.48, z + 1.05))
    else:
        items.append((u + back[0] - 0.03, u + back[0] + 0.03, w - 0.22, w + 0.22, z + 0.48, z + 1.05))
    for su in (-1, 1):
        for sw in (-1, 1):
            items.append((u + su * 0.19 - 0.02, u + su * 0.19 + 0.02, w + sw * 0.19 - 0.02, w + sw * 0.19 + 0.02, z, z + 0.42))
    piece(col, root, name, items, wood)
    piece(col, root, name + "_cuscino", [(u - 0.2, u + 0.2, w - 0.2, w + 0.2, z + 0.48, z + 0.52)], cloth)


def _chandelier(col, root, name, u, w, z):
    glow = mat("Lampadario", (1, 0.85, 0.6), 0.2, emit=(1.0, 0.8, 0.5), strength=12.0)
    items = [(u - 0.01, u + 0.01, w - 0.01, w + 0.01, z, PN_CEIL)]
    for k in range(8):
        a = math.tau * k / 8
        cu, cw = u + 0.45 * math.cos(a), w + 0.45 * math.sin(a)
        items.append((cu - 0.03, cu + 0.03, cw - 0.03, cw + 0.03, z, z + 0.12))
    piece(col, root, name, items, glow)
    lo = bpy.data.objects.new(name + "_luce", bpy.data.lights.new(name + "_luce", "POINT"))
    lo.data.energy = 220
    lo.data.color = (1.0, 0.78, 0.5)
    lo.data.shadow_soft_size = 0.4
    col.objects.link(lo)
    lo.parent = root
    lo.location = (u, w, z - 0.1)


def _books(rnd, along, fixed, z, count_axis="u"):
    out = []
    a0, a1 = along
    for sh in range(z[2]):
        x = a0
        while x < a1:
            wdt = rnd.uniform(0.03, 0.07)
            h = rnd.uniform(0.22, 0.34)
            zz = z[0] + z[1] * sh
            if count_axis == "u":
                out.append((x, x + wdt, fixed[0], fixed[1], zz, zz + h))
            else:
                out.append((fixed[0], fixed[1], x, x + wdt, zz, zz + h))
            x += wdt + 0.004
    return out


def _furnish(col, root):
    rnd = random.Random(11)
    wood = mat("Noce", (0.09, 0.04, 0.018), 0.45)
    gilt = mat("Dorato", (0.55, 0.40, 0.15), 0.35, 0.8)
    damask = mat("Damasco", (0.32, 0.20, 0.06), 0.7)
    red = mat("Velluto_divano", (0.22, 0.02, 0.03), 0.8)
    linen = mat("Lino", (0.70, 0.66, 0.58), 0.9)
    books = mat("Libri", (0.25, 0.10, 0.06), 0.7)
    z = PN_FLOOR
    # Ballroom: rug, two sofas facing, low table, console with mirror, grand piano, two chandeliers.
    piece(col, root, "Salone_tappeto", [(10.2, 16.1, 1.6, 5.6, z, z + 0.01)], mat("Tappeto", (0.28, 0.06, 0.04), 0.9))
    for k, w in enumerate((2.2, 5.0)):
        bw = (w + 0.3, w + 0.4) if k else (w - 0.4, w - 0.3)
        piece(col, root, "Salone_divano%d" % k, [(11.4, 13.6, w - 0.4, w + 0.4, z, z + 0.45), (11.4, 13.6, bw[0], bw[1], z + 0.45, z + 1.0),
                                                  (11.3, 11.45, w - 0.4, w + 0.4, z, z + 0.7), (13.55, 13.7, w - 0.4, w + 0.4, z, z + 0.7)], red)
    _table(col, root, "Salone_tavolino", 12.5, 3.6, 1.0, 0.6, z + 0.45, gilt)
    piece(col, root, "Salone_consolle", [(16.4, 16.95, 3.0, 4.6, z + 0.8, z + 0.88), (16.5, 16.9, 3.1, 3.2, z, z + 0.8), (16.5, 16.9, 4.4, 4.5, z, z + 0.8)], gilt)
    piece(col, root, "Salone_specchio", [(16.95, 17.0, 3.1, 4.5, z + 1.2, z + 3.2)], mat("Specchio", (0.8, 0.8, 0.8), 0.02, 1.0))
    piece(col, root, "Salone_pianoforte", [(14.2, 15.8, 4.6, 6.2, z + 0.65, z + 1.0), (14.3, 14.4, 4.7, 4.8, z, z + 0.65),
                                            (15.6, 15.7, 4.7, 4.8, z, z + 0.65), (14.9, 15.0, 6.0, 6.1, z, z + 0.65)],
          mat("Laccato_nero", (0.01, 0.01, 0.01), 0.15))
    _chandelier(col, root, "Salone_lampadario1", 11.2, 3.6, z + 2.9)
    _chandelier(col, root, "Salone_lampadario2", 15.1, 3.6, z + 2.9)
    # Dining room.
    _table(col, root, "Pranzo_tavolo", 7.07, 3.6, 1.0, 2.6, z + 0.76, wood)
    for k, w in enumerate((2.6, 3.4, 4.2, 5.0)):
        _chair(col, root, "Pranzo_sedia_s%d" % k, 6.25, w, "W", wood, damask)
        _chair(col, root, "Pranzo_sedia_d%d" % k, 7.9, w, "E", wood, damask)
    piece(col, root, "Pranzo_credenza", [(5.3, 5.8, 1.6, 5.6, z, z + 1.0)], wood)
    _chandelier(col, root, "Pranzo_lampadario", 7.07, 3.6, z + 2.9)
    # Study.
    _table(col, root, "Studio_scrivania", 2.9, 3.0, 1.6, 0.8, z + 0.76, wood)
    _chair(col, root, "Studio_poltrona", 2.9, 3.8, "N", wood, red)
    piece(col, root, "Studio_libreria", [(1.0, 1.4, 1.0, 6.4, z, z + 2.6)], wood)
    piece(col, root, "Studio_libri", _books(rnd, (1.1, 6.3), (1.05, 1.35), (z + 0.1, 0.42, 6), "w"), books)
    _chandelier(col, root, "Studio_lampadario", 2.9, 3.6, z + 3.0)
    # Bedroom.
    piece(col, root, "Camera_letto", [(18.3, 20.2, 3.6, 5.8, z, z + 0.55), (18.3, 20.2, 5.7, 5.85, z, z + 1.6)], wood)
    piece(col, root, "Camera_lenzuola", [(18.35, 20.15, 3.65, 5.7, z + 0.55, z + 0.7)], linen)
    piece(col, root, "Camera_armadio", [(20.5, 21.05, 1.2, 3.2, z, z + 2.4)], wood)
    piece(col, root, "Camera_cassettone", [(17.45, 17.95, 1.4, 2.8, z, z + 0.95)], wood)
    _chandelier(col, root, "Camera_lampadario", 19.25, 3.6, z + 3.0)
    # Library.
    piece(col, root, "Biblioteca_scaffali", [(20.7, 21.1, 9.0, 13.9, z, z + 3.4), (15.0, 15.4, 9.0, 13.9, z, z + 3.4)], wood)
    piece(col, root, "Biblioteca_libri", _books(rnd, (9.1, 13.8), (20.6, 20.72), (z + 0.1, 0.42, 8), "w")
          + _books(rnd, (9.1, 13.8), (15.4, 15.52), (z + 0.1, 0.42, 8), "w"), books)
    _table(col, root, "Biblioteca_tavolo", 18.0, 11.2, 1.8, 1.0, z + 0.76, wood)
    _chandelier(col, root, "Biblioteca_lampadario", 18.0, 11.4, z + 3.0)
    # Music room, anteroom, corridors.
    piece(col, root, "Musica_spinetta", [(3.0, 5.0, 10.4, 11.2, z + 0.7, z + 0.95), (3.1, 3.2, 10.5, 10.6, z, z + 0.7), (4.8, 4.9, 10.5, 10.6, z, z + 0.7)], wood)
    for k in range(4):
        _chair(col, root, "Musica_sedia%d" % k, 2.0 + 1.3 * k, 12.6, "N", wood, damask)
    _chandelier(col, root, "Musica_lampadario", 4.85, 11.4, z + 3.0)
    piece(col, root, "Anticamera_panca", [(9.3, 9.8, 19.0, 21.4, z, z + 0.45)], wood)
    _chandelier(col, root, "Anticamera_lampadario", 11.4, 20.3, z + 3.0)
    for k, u in enumerate((4.0, 11.0, 18.0)):
        _chandelier(col, root, "Corridoio_lume%d" % k, u, 7.8, z + 3.3)
    _chandelier(col, root, "CorridoioOvest_lume", 11.4, 13.4, z + 3.3)
