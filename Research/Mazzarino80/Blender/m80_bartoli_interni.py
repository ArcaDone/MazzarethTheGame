"""Interiors of the Palazzo Bartoli block (local metres, z above 169 m).

Cinema (Cine-Teatro Bartolotta, imagined as a 1980s town cinema): foyer with box office and posters,
raked stalls of red velvet seats in two blocks, a gallery over the foyer, proscenium with a red
curtain and the screen, wood panelling, pilasters, wall lights, exits, coffered ceiling.
Palazzo Bartoli, piano nobile: an enfilade of rooms on the Corso (studio, dining room, ballroom,
bedroom), a corridor, the library on the courtyard, the anteroom on the gallery, bedroom and kitchen
in the west wing; majolica floors, painted walls with dado, cornices, coved and frescoed ceilings,
panelled double doors, furniture of a Sicilian noble house.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import m80_arch_facade as A
import m80_arch_kit as K


def mat(name, color, rough=0.8, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = A.principled(name, color, rough, metal)
    if emit:
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def boxes(name, items, material, col, smooth=False):
    """items: list of (x0, x1, y0, y1, z0, z1) in world coordinates."""
    bm = bmesh.new()
    for it in items:
        K.box_bm(bm, *it)
    return K.bm_object(name, bm, col, None, material, smooth=smooth)


def room_shell(name, x0, x1, y0, y1, z0, z1, wall_mat, floor_mat, ceil_mat, col, skip=()):
    """Inward-facing floor, ceiling and four walls of a box room (world-aligned)."""
    out = []
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
    bm.faces.new(v)
    out.append(K.bm_object(name + "_pavimento", bm, col, None, floor_mat))
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1))]
    bm.faces.new(v)
    out.append(K.bm_object(name + "_soffitto", bm, col, None, ceil_mat))
    bm = bmesh.new()
    walls = {"S": ((x0, y0), (x1, y0)), "E": ((x1, y0), (x1, y1)), "N": ((x1, y1), (x0, y1)), "O": ((x0, y1), (x0, y0))}
    for k, (a, b) in walls.items():
        if k in skip:
            continue
        v = [bm.verts.new(p) for p in ((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1))]
        bm.faces.new(list(reversed(v)))
    out.append(K.bm_object(name + "_pareti", bm, col, None, wall_mat))
    return out


# ---------------------------------------------------------------------------------------------
# Procedural interior materials

def terrazzo():
    m = bpy.data.materials.get("Terrazzo")
    if m:
        return m
    m = bpy.data.materials.new("Terrazzo")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    v = nt.nodes.new("ShaderNodeTexVoronoi")
    v.inputs["Scale"].default_value = 60
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (0.30, 0.27, 0.23, 1)
    r.color_ramp.elements[1].color = (0.55, 0.50, 0.42, 1)
    r.color_ramp.elements.new(0.5).color = (0.18, 0.10, 0.08, 1)
    nt.links.new(v.outputs["Color"], r.inputs[0])
    nt.links.new(r.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.25
    return m


def majolica(name, c1, c2, c3, tile=0.20):
    """Sicilian majolica floor: a four-petal motif on 20 cm tiles, three colours, worn gloss."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def m_(op, a, bv=None, bs=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        nt.links.new(a, n.inputs[0])
        if bs is not None:
            nt.links.new(bs, n.inputs[1])
        elif bv is not None:
            n.inputs[1].default_value = bv
        return n.outputs[0]

    # Local tile coords in [-1, 1].
    fx = m_("SUBTRACT", m_("MULTIPLY", m_("FRACT", m_("DIVIDE", sep.outputs[0], tile)), 2.0), 1.0)
    fy = m_("SUBTRACT", m_("MULTIPLY", m_("FRACT", m_("DIVIDE", sep.outputs[1], tile)), 2.0), 1.0)
    ax, ay = m_("ABSOLUTE", fx, 0), m_("ABSOLUTE", fy, 0)
    petal = m_("LESS_THAN", m_("MULTIPLY", ax, None, ay), 0.12)
    r2 = m_("ADD", m_("MULTIPLY", fx, None, fx), None, m_("MULTIPLY", fy, None, fy))
    ring = m_("LESS_THAN", m_("ABSOLUTE", m_("SUBTRACT", m_("POWER", r2, 0.5), 0.62), 0), 0.08)
    border = m_("GREATER_THAN", m_("MAXIMUM", ax, None, ay), 0.93)
    mix1 = nt.nodes.new("ShaderNodeMix")
    mix1.data_type = "RGBA"
    nt.links.new(petal, mix1.inputs["Factor"])
    mix1.inputs[6].default_value = (*c1, 1)
    mix1.inputs[7].default_value = (*c2, 1)
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    nt.links.new(ring, mix2.inputs["Factor"])
    nt.links.new(mix1.outputs[2], mix2.inputs[6])
    mix2.inputs[7].default_value = (*c3, 1)
    mix3 = nt.nodes.new("ShaderNodeMix")
    mix3.data_type = "RGBA"
    nt.links.new(border, mix3.inputs["Factor"])
    nt.links.new(mix2.outputs[2], mix3.inputs[6])
    mix3.inputs[7].default_value = (0.25, 0.22, 0.18, 1)
    nt.links.new(mix3.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.3
    return m


def fresco(name, base, accent):
    """Ceiling painted with a pale sky in a frame of ochre borders."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 0.35
    n.inputs["Detail"].default_value = 6
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*base, 1)
    r.color_ramp.elements[1].color = (0.75, 0.72, 0.62, 1)
    nt.links.new(n.outputs["Fac"], r.inputs[0])
    nt.links.new(r.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.9
    return m


# ---------------------------------------------------------------------------------------------
# Furniture

def seat_mesh():
    me = bpy.data.meshes.get("Poltrona_cinema")
    if me:
        return me
    bm = bmesh.new()
    K.box_bm(bm, -0.24, 0.24, -0.22, 0.22, 0.38, 0.48)            # cushion
    K.box_bm(bm, -0.24, 0.24, 0.20, 0.30, 0.45, 1.02)             # back
    for x in (-0.27, 0.24):
        K.box_bm(bm, x, x + 0.04, -0.20, 0.30, 0.0, 0.66)          # side / armrest
    me = bpy.data.meshes.new("Poltrona_cinema")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat("Velluto_rosso", (0.25, 0.012, 0.015), 0.95))
    return me


def instance(name, mesh, loc, rot_z, col):
    ob = bpy.data.objects.new(name, mesh)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    col.objects.link(ob)
    return ob


def curtain(name, x0, x1, y, z0, z1, col, folds=28, parent=None, material=None):
    bm = bmesh.new()
    n = folds * 6
    rows = 12
    vs = []
    for j in range(rows + 1):
        z = z0 + (z1 - z0) * j / rows
        row = []
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            dy = 0.09 * math.sin(i / 6 * math.tau) * (0.6 + 0.4 * j / rows)
            row.append(bm.verts.new((x, y + dy, z)))
        vs.append(row)
    for j in range(rows):
        for i in range(n):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    return K.bm_object(name, bm, col, parent, material or mat("Velluto_sipario", (0.30, 0.01, 0.012), 0.9), smooth=True)


def light(name, loc, energy, color=(1.0, 0.75, 0.45), kind="POINT", size=0.1, col=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    else:
        ld.shadow_soft_size = size
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    (col or bpy.context.scene.collection).objects.link(ob)
    return ob


# ---------------------------------------------------------------------------------------------
# Cinema

CINEMA_FLOOR = 6.35          # portico / foyer floor (top of the steps)


def cinema():
    col = K.collection("Cinema_Interno")
    wood = mat("Boiserie", (0.10, 0.045, 0.02), 0.5)
    wall = mat("Parete_cinema", (0.33, 0.10, 0.06), 0.85)
    gold = mat("Stucco_dorato", (0.55, 0.40, 0.18), 0.4, 0.6)
    ceil = mat("Soffitto_cinema", (0.55, 0.47, 0.36), 0.9)
    dark = mat("Nero_opaco", (0.01, 0.01, 0.01), 0.9)
    f0 = CINEMA_FLOOR
    # Foyer.
    room_shell("Cinema_foyer", -50.4, -44.4, -9.0, -2.4, f0, f0 + 3.6, wall, terrazzo(), ceil, col, skip=("N",))
    # The foyer's back wall with two doorways (red portieres) into the stalls.
    boxes("Cinema_foyer_muro", [(-50.4, -49.0, -2.45, -2.35, f0, f0 + 3.6), (-48.0, -46.8, -2.45, -2.35, f0, f0 + 3.6),
                                (-45.8, -44.4, -2.45, -2.35, f0, f0 + 3.6), (-49.0, -45.8, -2.45, -2.35, f0 + 2.4, f0 + 3.6)], wall, col)
    curtain("Cinema_portiera1", -49.0, -48.0, -2.3, f0, f0 + 2.4, col, folds=6)
    curtain("Cinema_portiera2", -46.8, -45.8, -2.3, f0, f0 + 2.4, col, folds=6)
    boxes("Cinema_cassa", [(-47.2, -44.6, -4.2, -2.6, f0, f0 + 1.1), (-47.2, -44.6, -4.2, -4.1, f0 + 1.1, f0 + 2.3)], wood, col)
    boxes("Cinema_cassa_vetro", [(-47.15, -44.65, -4.17, -4.15, f0 + 1.15, f0 + 2.25)], A.mats()["glass"], col)
    boxes("Cinema_targa_cassa", [(-46.4, -45.4, -4.25, -4.2, f0 + 2.35, f0 + 2.6)], gold, col)
    rnd = random.Random(7)
    for k, y in enumerate((-8.2, -6.6, -5.0)):
        c = (rnd.uniform(0.2, 0.7), rnd.uniform(0.05, 0.4), rnd.uniform(0.05, 0.3))
        boxes("Cinema_locandina%d" % k, [(-50.38, -50.33, y, y + 1.0, f0 + 0.9, f0 + 2.4)], mat("Locandina%d" % k, c, 0.5), col)
        boxes("Cinema_cornice%d" % k, [(-50.40, -50.36, y - 0.05, y + 1.05, f0 + 0.85, f0 + 2.45)], gold, col)
    # Ceiling lamps of the foyer (opal glass globes).
    for k, y in enumerate((-7.4, -4.6)):
        boxes("Cinema_foyer_plafoniera%d" % k, [(-47.6, -47.0, y - 0.3, y + 0.3, f0 + 3.4, f0 + 3.6)],
              mat("Vetro_opale", (0.9, 0.85, 0.7), 0.3, emit=(1.0, 0.85, 0.6), strength=8.0), col)
        light("Cinema_foyer_luce%d" % k, (-47.3, y, f0 + 3.2), 180, size=0.3, col=col)
    # Stairs up to the gallery along the west wall of the foyer.
    n = 26
    for k in range(n):
        y0 = -3.0 - 5.4 * k / n
        boxes("Cinema_scala%02d" % k, [(-50.4, -49.2, y0 - 5.4 / n, y0, f0, f0 + 4.05 * (k + 1) / n)], terrazzo(), col)
    # Auditorium: raked floor, walls, proscenium, stage, screen, curtain.
    x0, x1, y0, y1 = -50.8, -39.6, 1.0, 18.4
    z_back, z_front = f0, f0 - 1.0
    bm = bmesh.new()
    v = [bm.verts.new(p) for p in ((x0, y0, z_back), (x1, y0, z_back), (x1, 13.6, z_front), (x0, 13.6, z_front))]
    bm.faces.new(v)
    v = [bm.verts.new(p) for p in ((x0, 13.6, z_front), (x1, 13.6, z_front), (x1, 14.6, z_front), (x0, 14.6, z_front))]
    bm.faces.new(v)
    K.bm_object("Cinema_platea_pavimento", bm, col, None, mat("Moquette", (0.12, 0.02, 0.02), 0.95))
    top = 14.6
    room_shell("Cinema_sala", x0, x1, y0, y1, z_front, top, wall, mat("Moquette", (0.12, 0.02, 0.02)), ceil, col, skip=("S",))
    room_shell("Cinema_sottogalleria", -50.4, -44.4, -2.4, y0, z_back, f0 + 3.6, wall, mat("Moquette", (0.12, 0.02, 0.02)), ceil, col, skip=("N", "S"))
    room_shell("Cinema_vano_galleria", -50.4, -44.4, -9.0, y0, f0 + 3.6, top, wall, mat("Moquette", (0.12, 0.02, 0.02)), ceil, col, skip=("N",))
    boxes("Cinema_muro_sud", [(-44.4, x1, y0 - 0.1, y0, z_back, top)], wall, col)
    # Wainscot and pilasters with wall lights.
    items = []
    for x in (x0 + 0.02, x1 - 0.08):
        items.append((x, x + 0.06, y0, 14.2, z_front, z_front + 1.3))
    boxes("Cinema_boiserie", items, wood, col)
    for k, y in enumerate([y0 + 2.0 + 3.0 * i for i in range(5)]):
        for x, d in ((x0, 1), (x1, -1)):
            boxes("Cinema_lesena%d_%d" % (k, d), [(min(x, x + 0.25 * d), max(x, x + 0.25 * d), y - 0.25, y + 0.25, z_front, top - 0.4)], gold, col)
            boxes("Cinema_applique%d_%d" % (k, d), [(min(x + 0.25 * d, x + 0.45 * d), max(x + 0.25 * d, x + 0.45 * d), y - 0.12, y + 0.12, 10.0, 10.35)],
                  mat("Applique", (1.0, 0.8, 0.5), 0.3, emit=(1.0, 0.72, 0.4), strength=8.0), col)
            light("Cinema_luce%d_%d" % (k, d), (x + 0.6 * d, y, 10.2), 60)
    # Coffered ceiling and chandelier.
    items = []
    for i in range(6):
        x = x0 + 0.6 + (x1 - x0 - 1.2) * i / 5
        items.append((x - 0.12, x + 0.12, y0 - 9.0, y1, top - 0.45, top))
    for j in range(10):
        y = y0 - 8.5 + (y1 - y0 + 8.5) * j / 9
        items.append((x0, x1, y - 0.12, y + 0.12, top - 0.45, top))
    boxes("Cinema_cassettoni", items, gold, col)
    boxes("Cinema_lampadario", [(-45.6, -44.8, 8.0, 8.8, top - 2.2, top - 1.6)], mat("Lampadario", (1, 0.85, 0.6), 0.2, emit=(1.0, 0.8, 0.5), strength=12.0), col)
    light("Cinema_lampadario_luce", (-45.2, 8.4, top - 2.3), 400, size=0.6)
    # Proscenium wall with its arch, stage, screen, curtain.
    boxes("Cinema_boccascena", [(x0, -49.2, 14.4, 14.7, z_front, top), (-41.2, x1, 14.4, 14.7, z_front, top), (-49.2, -41.2, 14.4, 14.7, 12.3, top)], wall, col)
    boxes("Cinema_cornice_scena", [(-49.4, -49.1, 14.3, 14.45, z_front, 12.5), (-41.3, -41.0, 14.3, 14.45, z_front, 12.5), (-49.4, -41.0, 14.3, 14.45, 12.3, 12.6)], gold, col)
    boxes("Cinema_palco", [(x0, x1, 14.6, y1, z_front, z_front + 1.1)], mat("Legno_palco", (0.09, 0.05, 0.025), 0.6), col)
    boxes("Cinema_schermo", [(-48.4, -42.0, 17.9, 17.95, z_front + 1.6, z_front + 5.2)], mat("Schermo", (0.85, 0.85, 0.82), 0.9, emit=(0.6, 0.62, 0.7), strength=0.6), col)
    boxes("Cinema_mascheratura", [(-48.8, -41.6, 17.96, 18.0, z_front + 1.4, z_front + 5.4)], dark, col)
    curtain("Cinema_sipario_s", -49.2, -46.6, 14.9, z_front + 1.1, 12.3, col)
    curtain("Cinema_sipario_d", -43.8, -41.2, 14.9, z_front + 1.1, 12.3, col)
    curtain("Cinema_mantovana", -49.2, -41.2, 14.85, 11.4, 12.3, col, folds=40)
    # Seats: two blocks of 7 with a central aisle, 13 rows on the rake.
    seat = seat_mesh()
    n = 0
    for r in range(13):
        y = 1.6 + 0.95 * r
        z = z_back + (z_front - z_back) * (y - y0) / (13.6 - y0)
        for bx in (-50.0, -44.4):
            for k in range(7):
                instance("Poltrona_%d" % n, seat, (bx + 0.28 + 0.56 * k, y, z), math.pi, col)
                n += 1
    # Gallery over the foyer: five stepped rows, a front parapet, two columns.
    gz = f0 + 4.05
    for r in range(5):
        y = 0.2 - 1.0 * r
        z = gz + 0.35 * r
        boxes("Galleria_gradone%d" % r, [(x0, -44.4 if y < -0.3 else x1, y - 1.0, y, gz - 0.3, z)], mat("Moquette", (0.12, 0.02, 0.02)), col)
        for k in range(16 if y > -0.3 else 10):
            x = x0 + 0.5 + 0.56 * k
            if x > (-44.6 if y < -0.3 else x1 - 0.4):
                break
            instance("Poltrona_g%d" % n, seat, (x, y - 0.5, z), math.pi, col)
            n += 1
    boxes("Galleria_parapetto", [(x0, x1, 1.1, 1.3, gz - 0.4, gz + 0.95)], gold, col)
    boxes("Galleria_colonne", [(-48.5, -48.2, 1.0, 1.3, z_back, gz - 0.3), (-42.4, -42.1, 1.0, 1.3, z_back, gz - 0.3)], gold, col)
    boxes("Cabina_proiezione", [(-46.5, -44.6, -8.9, -7.6, gz + 1.8, top - 0.1)], wall, col)
    for k, x in enumerate((-46.0, -45.1)):
        boxes("Cabina_finestrella%d" % k, [(x, x + 0.3, -7.62, -7.58, gz + 2.6, gz + 2.9)], mat("Luce_proiettore", (1, 1, 0.9), 0.2, emit=(1, 0.95, 0.85), strength=20.0), col)
    # Exits with the green sign.
    for k, y in enumerate((5.0, 12.0)):
        boxes("Uscita_porta%d" % k, [(x0 + 0.01, x0 + 0.05, y - 0.8, y + 0.8, z_front + 0.3 * (y < 13.6), z_front + 2.4)], mat("Porta_uscita", (0.06, 0.12, 0.07), 0.6), col)
        boxes("Uscita_insegna%d" % k, [(x0 + 0.02, x0 + 0.12, y - 0.3, y + 0.3, z_front + 2.6, z_front + 2.85)],
              mat("Insegna_uscita", (0.1, 0.9, 0.3), 0.3, emit=(0.1, 1.0, 0.3), strength=6.0), col)
    print("cinema seats", n)
    if os.environ.get("M80_ARREDI", "0") != "1":
        # Bare hall: architecture only (raked floor, gallery steps, stage, proscenium, booth, coffers).
        fittings = ("Poltrona", "Cinema_portiera", "Cinema_sipario", "Cinema_mantovana", "Cinema_cassa", "Cinema_targa_cassa",
                    "Cinema_locandina", "Cinema_cornice")
        for ob in list(col.objects):
            if ob.type != "LIGHT" and ob.name.startswith(fittings):
                bpy.data.objects.remove(ob)
    return col
