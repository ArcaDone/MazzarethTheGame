"""Blender 4.3: typical Sicilian house props, exported to M80_Sicilia.fbx (houses V3, step 14.1).

Run: blender -b --factory-startup --python m80_sicilia_blender.py
Every mesh uses the atlas Textures/T_M80_SiciliaAtlas.png (cells in sicilia_atlas.json, from
m80_sicilia_textures.py) with three material slots: "Glazed" (majolica, glass), "Matte" (terracotta,
stone, wood, rope) and "Iron". Units are metres; the front faces -Y.
Floor props: pivot at the base centre. Wall props: back on the Y = 0 plane (the wall), growing towards -Y.
Hanging props (panaru, peperoncini): pivot at the top of the rope.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy

HERE = Path(__file__).resolve().parent
OUT = HERE / "M80_Sicilia.fbx"
CELLS = json.loads((HERE / "sicilia_atlas.json").read_text(encoding="utf-8"))
GLAZED, MATTE, IRON = 0, 1, 2


def rect(cell, inset=0.0):
    """Atlas cell (x0, y0, x1, y1 from the top-left) -> Blender UV rect (u0, v0, u1, v1) with v up."""
    x0, y0, x1, y1 = CELLS[cell]
    dx, dy = (x1 - x0) * inset, (y1 - y0) * inset
    return (x0 + dx, 1 - y1 + dy, x1 - dx, 1 - y0 - dy)


class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")

    def face(self, verts, mat, uvs):
        f = self.bm.faces.new(verts)
        f.material_index = mat
        for loop, uv in zip(f.loops, uvs):
            loop[self.uv].uv = uv
        return f

    def lathe(self, profile, mat, cell, segments=24, center=(0, 0, 0), u_offset=0.0, v_range=None, inset=0.08):
        """Surface of revolution of profile [(radius, z)], UV: angle across the cell, height up the cell."""
        u0, v0, u1, v1 = rect(cell, inset)
        zs = [p[1] for p in profile]
        zmin, zmax = (v_range or (min(zs), max(zs)))
        rings = []
        for k in range(segments + 1):
            a = 2 * math.pi * k / segments - math.pi / 2 + u_offset * 2 * math.pi
            ring = [self.bm.verts.new((center[0] + r * math.cos(a), center[1] + r * math.sin(a), center[2] + z)) for r, z in profile]
            rings.append(ring)
        for k in range(segments):
            for j in range(len(profile) - 1):
                uvs = []
                for kk, jj in ((k, j), (k + 1, j), (k + 1, j + 1), (k, j + 1)):
                    u = u0 + (u1 - u0) * kk / segments
                    v = v0 + (v1 - v0) * (profile[jj][1] - zmin) / max(1e-6, zmax - zmin)
                    uvs.append((u, v))
                verts = [rings[k][j], rings[k + 1][j], rings[k + 1][j + 1], rings[k][j + 1]]
                if len({id(v) for v in verts}) == 4 and (profile[j][0] > 1e-5 or profile[j + 1][0] > 1e-5):
                    try:
                        self.face(verts, mat, uvs)
                    except ValueError:
                        pass

    def box(self, center, half, mat, cell, axes=None):
        cx, cy, cz = center
        hx, hy, hz = half
        ax = axes or ((1, 0, 0), (0, 1, 0), (0, 0, 1))

        def p(sx, sy, sz):
            return tuple(c + sx * hx * ax[0][i] + sy * hy * ax[1][i] + sz * hz * ax[2][i] for i, c in enumerate((cx, cy, cz)))
        v = {s: self.bm.verts.new(p(*s)) for s in [(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]}
        u0, v0, u1, v1 = rect(cell, 0.1)
        quad = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        for idx in (((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)), ((1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)),
                    ((-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)), ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)),
                    ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)), ((-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1))):
            self.face([v[s] for s in idx], mat, quad)

    def panel(self, corners, mat, cell, inset=0.0):
        """Flat quad (4 corners, counter-clockwise seen from the front) with the whole cell on it."""
        u0, v0, u1, v1 = rect(cell, inset)
        self.face([self.bm.verts.new(c) for c in corners], mat, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])

    def tube(self, points, radius, mat, cell, sides=8):
        u0, v0, u1, v1 = rect(cell, 0.1)
        rings = []
        for i, p in enumerate(points):
            a = points[min(i + 1, len(points) - 1)]
            b = points[max(i - 1, 0)]
            d = [a[k] - b[k] for k in range(3)]
            n = math.sqrt(sum(x * x for x in d)) or 1
            d = [x / n for x in d]
            ref = (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0)
            s1 = (d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0])
            n1 = math.sqrt(sum(x * x for x in s1)) or 1
            s1 = [x / n1 for x in s1]
            s2 = (d[1] * s1[2] - d[2] * s1[1], d[2] * s1[0] - d[0] * s1[2], d[0] * s1[1] - d[1] * s1[0])
            rings.append([self.bm.verts.new(tuple(p[k] + radius * (math.cos(2 * math.pi * j / sides) * s1[k] + math.sin(2 * math.pi * j / sides) * s2[k])
                                                  for k in range(3))) for j in range(sides)])
        for i in range(len(rings) - 1):
            for j in range(sides):
                self.face([rings[i][j], rings[i][(j + 1) % sides], rings[i + 1][(j + 1) % sides], rings[i + 1][j]], mat,
                          [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])

    def blob(self, center, radius, mat, cell, squash=1.0):
        prof = [(radius * math.sin(math.pi * t / 6), -radius * squash * math.cos(math.pi * t / 6)) for t in range(7)]
        self.lathe(prof, mat, cell, 8, center)

    def finish(self, name, recalc=True):
        bmesh.ops.remove_doubles(self.bm, verts=self.bm.verts, dist=1e-5)
        if recalc:  # open double-sided sheets (cloth) keep the winding they were built with
            bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for s in ("M_Glazed", "M_Matte", "M_Iron"):
            mesh.materials.append(bpy.data.materials.get(s) or bpy.data.materials.new(s))
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        return obj


def testa_di_moro():
    b = Builder()
    prof = [(0.0, 0.0), (0.075, 0.0), (0.085, 0.015), (0.07, 0.04), (0.085, 0.07), (0.115, 0.14), (0.125, 0.22), (0.115, 0.30), (0.10, 0.345), (0.112, 0.36), (0.112, 0.40)]
    b.lathe(prof, GLAZED, "moor_face", 32, u_offset=0.5, inset=0.0)  # face centre towards -Y
    b.lathe([(0.10, 0.395), (0.0, 0.395)], MATTE, "sw_soil", 16)
    for k in range(7):  # lemons and leaves of the crown
        a = 2 * math.pi * k / 7
        b.blob((0.085 * math.cos(a), 0.085 * math.sin(a), 0.43), 0.032, GLAZED, "sw_glaze_yellow", 1.25)
        b.box((0.1 * math.cos(a + 0.4), 0.1 * math.sin(a + 0.4), 0.415), (0.035, 0.012, 0.004), GLAZED, "sw_glaze_green",
              ((math.cos(a + 0.4), math.sin(a + 0.4), 0.35), (-math.sin(a + 0.4), math.cos(a + 0.4), 0), (0, 0, 1)))
    return b.finish("SM_M80_TestaDiMoro")


def pigna():
    b = Builder()
    b.lathe([(0.0, 0.0), (0.09, 0.0), (0.09, 0.03), (0.06, 0.05), (0.07, 0.09), (0.0, 0.09)], GLAZED, "majolica_c", 16)
    cone = [(0.0, 0.08), (0.08, 0.10), (0.115, 0.16), (0.12, 0.22), (0.10, 0.29), (0.065, 0.35), (0.025, 0.39), (0.0, 0.40)]
    b.lathe(cone, GLAZED, "pine", 20, inset=0.0)
    b.blob((0, 0, 0.415), 0.02, GLAZED, "sw_glaze_yellow")
    return b.finish("SM_M80_Pigna")


def grasta(name, flowers):
    b = Builder()
    pot = [(0.0, 0.0), (0.08, 0.0), (0.11, 0.18), (0.13, 0.19), (0.13, 0.22), (0.115, 0.22), (0.1, 0.2)]
    b.lathe(pot, MATTE, "sw_terracotta", 20)
    b.lathe([(0.1, 0.2), (0.0, 0.2)], MATTE, "sw_soil", 12)
    for k in range(9):
        a = 2.4 * k
        r = 0.04 + 0.05 * (k % 3) / 2
        b.blob((r * math.cos(a), r * math.sin(a), 0.25 + 0.02 * (k % 2)), 0.06, MATTE, "sw_leaf", 0.7)
    if flowers:
        for k in range(7):
            a = 0.9 * k
            b.blob((0.07 * math.cos(a), 0.07 * math.sin(a), 0.33 + 0.02 * (k % 2)), 0.025, MATTE, "sw_geranium", 0.8)
    return b.finish(name)


def quartara():
    b = Builder()
    prof = [(0.0, 0.0), (0.07, 0.0), (0.12, 0.08), (0.16, 0.2), (0.15, 0.3), (0.09, 0.4), (0.055, 0.44), (0.05, 0.47), (0.065, 0.5), (0.05, 0.5)]
    b.lathe(prof, MATTE, "sw_terracotta", 24)
    for s in (-1, 1):
        pts = [(s * 0.055, 0, 0.46), (s * 0.12, 0, 0.47), (s * 0.15, 0, 0.42), (s * 0.15, 0, 0.32)]
        b.tube(pts, 0.012, MATTE, "sw_terracotta_dark", 6)
    return b.finish("SM_M80_Quartara")


def bummulo():
    b = Builder()
    prof = [(0.0, 0.0), (0.06, 0.0), (0.11, 0.07), (0.12, 0.15), (0.09, 0.24), (0.035, 0.29), (0.03, 0.33), (0.04, 0.35), (0.03, 0.35)]
    b.lathe(prof, GLAZED, "sw_glaze_green", 20)
    b.tube([(0.03, 0, 0.32), (0.1, 0, 0.32), (0.12, 0, 0.24), (0.1, 0, 0.18)], 0.01, GLAZED, "sw_glaze_green", 6)
    return b.finish("SM_M80_Bummulo")


def panaru():
    b = Builder()
    rope = 3.2
    b.tube([(0, 0, 0), (0, 0, -rope)], 0.006, MATTE, "sw_rope", 5)
    for s in (-1, 1):
        b.tube([(0, 0, -rope), (s * 0.15, 0, -rope - 0.12)], 0.005, MATTE, "sw_rope", 4)
    basket = [(0.12, -rope - 0.32), (0.16, -rope - 0.18), (0.17, -rope - 0.12)]
    b.lathe([(0.0, -rope - 0.32)] + basket, MATTE, "sw_wicker", 20)
    b.lathe(list(reversed([(0.11, -rope - 0.31), (0.15, -rope - 0.18), (0.16, -rope - 0.125)])), MATTE, "sw_wicker", 20)
    b.tube([(0.165 * math.cos(2 * math.pi * k / 16), 0.165 * math.sin(2 * math.pi * k / 16), -rope - 0.12) for k in range(17)], 0.012, MATTE, "sw_wood", 5)
    return b.finish("SM_M80_Panaru")


def edicola():
    b = Builder()
    w, h, d = 0.26, 0.62, 0.10
    for s in (-1, 1):  # pilasters
        b.box((s * (w + 0.04), -d * 0.5, h * 0.5), (0.04, d * 0.5, h * 0.5), MATTE, "sw_stone")
    b.box((0, -d * 0.6, -0.03), (w + 0.1, d * 0.6, 0.03), MATTE, "sw_stone")  # shelf
    for k in range(9):  # round arch
        a0, a1 = math.pi * k / 9, math.pi * (k + 1) / 9
        am = (a0 + a1) / 2
        c = (-(w + 0.04) * math.cos(am), -d * 0.5, h + (w + 0.04) * math.sin(am))
        b.box(c, (0.06, d * 0.5, 0.045), MATTE, "sw_stone", ((math.sin(am), 0, math.cos(am)), (0, 1, 0), (-math.cos(am), 0, math.sin(am))))
    b.panel([(-w, -0.005, 0.0), (w, -0.005, 0.0), (w, -0.005, h + 0.2), (-w, -0.005, h + 0.2)], GLAZED, "icon")
    b.lathe([(0.0, 0.0), (0.03, 0.0), (0.035, 0.06), (0.03, 0.08), (0.0, 0.08)], GLAZED, "sw_red_glass", 12, (0, -0.06, 0.0))
    b.tube([(0, -0.06, 0.08), (0, -0.06, 0.095)], 0.004, IRON, "sw_iron", 4)
    return b.finish("SM_M80_Edicola")


def civico(index):
    b = Builder()
    x0, y0, x1, y1 = CELLS["numbers"]
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    cell = [x0 + (index % 2) * hx, y0 + (index // 2) * hy, x0 + (index % 2 + 1) * hx, y0 + (index // 2 + 1) * hy]
    CELLS["_num"] = cell
    s = 0.075
    b.box((0, -0.005, 0), (s, 0.005, s), MATTE, "sw_glaze_white")
    b.panel([(-s, -0.0105, -s), (s, -0.0105, -s), (s, -0.0105, s), (-s, -0.0105, s)], GLAZED, "_num", 0.03)
    return b.finish("SM_M80_Civico_{}".format(index + 1))


def batacchio():
    b = Builder()
    # Rosette built around Z, then turned so it faces -Y with its back on the wall.
    b.lathe([(0.0, 0.0), (0.06, 0.0), (0.05, 0.012), (0.02, 0.022), (0.0, 0.025)], IRON, "sw_brass", 16)
    import mathutils
    bmesh.ops.rotate(b.bm, verts=list(b.bm.verts), cent=(0, 0, 0), matrix=mathutils.Matrix.Rotation(math.radians(90), 3, "X"))
    # Ring hanging from the rosette.
    b.tube([(0.055 * math.sin(2 * math.pi * k / 20), -0.035, -0.06 + 0.055 * math.cos(2 * math.pi * k / 20)) for k in range(21)], 0.008, IRON, "sw_brass", 6)
    return b.finish("SM_M80_Batacchio")


def stemma():
    b = Builder()
    shield = [(-0.28, 0.6), (0.28, 0.6), (0.28, 0.25), (0.2, 0.08), (0.0, 0.0), (-0.2, 0.08), (-0.28, 0.25)]
    front = [b.bm.verts.new((x, -0.08, z)) for x, z in shield]
    back = [b.bm.verts.new((x, 0.0, z)) for x, z in shield]
    u0, v0, u1, v1 = rect("sw_stone", 0.1)
    b.face(front, MATTE, [(u0 + (u1 - u0) * (x + 0.3) / 0.6, v0 + (v1 - v0) * z / 0.6) for x, z in shield])
    b.face(list(reversed(back)), MATTE, [(u0, v0)] * len(back))
    for i in range(len(shield)):
        j = (i + 1) % len(shield)
        b.face([front[i], back[i], back[j], front[j]], MATTE, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    b.box((0, -0.1, 0.32), (0.16, 0.02, 0.025), MATTE, "sw_stone_dark")  # band
    b.box((0, -0.1, 0.42), (0.025, 0.02, 0.1), MATTE, "sw_stone_dark")
    b.lathe([(0.0, 0.0), (0.17, 0.0), (0.17, 0.05), (0.13, 0.05), (0.15, 0.12), (0.0, 0.12)], MATTE, "sw_stone", 12, (0, -0.05, 0.6))  # crown
    for s in (-1, 1):  # scrolls
        b.tube([(s * 0.28, -0.05, 0.5), (s * 0.4, -0.05, 0.42), (s * 0.38, -0.05, 0.28), (s * 0.31, -0.05, 0.3)], 0.03, MATTE, "sw_stone", 8)
    return b.finish("SM_M80_Stemma")


def lanterna():
    b = Builder()
    b.tube([(0, 0, 0), (0, -0.2, 0.04), (0, -0.33, 0.12), (0, -0.36, 0.2)], 0.012, IRON, "sw_iron", 6)
    b.tube([(0, 0, -0.12), (0, -0.15, -0.02), (0, -0.25, 0.06)], 0.008, IRON, "sw_iron", 5)
    c = (0, -0.36, -0.02)
    b.lathe([(0.0, 0.0), (0.06, 0.0), (0.09, 0.2), (0.0, 0.2)], GLAZED, "sw_glass_amber", 6, c)
    b.lathe([(0.0, 0.2), (0.11, 0.2), (0.11, 0.215), (0.04, 0.29), (0.0, 0.3)], IRON, "sw_iron", 6, c)
    b.lathe([(0.0, -0.02), (0.07, -0.02), (0.07, 0.0), (0.0, 0.0)], IRON, "sw_iron", 6, c)
    for k in range(6):
        a = 2 * math.pi * k / 6
        b.tube([(c[0] + 0.062 * math.cos(a), c[1] + 0.062 * math.sin(a), c[2]), (c[0] + 0.092 * math.cos(a), c[1] + 0.092 * math.sin(a), c[2] + 0.2)], 0.006, IRON, "sw_iron", 4)
    return b.finish("SM_M80_Lanterna")


def doccione():
    """Terracotta spout: a half pipe sticking out of the wall (towards -Y), open on top."""
    b = Builder()
    pts = 8
    u0, v0, u1, v1 = rect("sw_terracotta", 0.1)
    arc = [(math.cos(math.pi * k / pts), -math.sin(math.pi * k / pts)) for k in range(pts + 1)]
    for r in (0.075, 0.062):
        for k in range(pts):
            (x0, z0), (x1, z1) = arc[k], arc[k + 1]
            b.face([b.bm.verts.new((x0 * r, 0.0, z0 * r)), b.bm.verts.new((x1 * r, 0.0, z1 * r)),
                    b.bm.verts.new((x1 * r, -0.5, z1 * r)), b.bm.verts.new((x0 * r, -0.5, z0 * r))],
                   MATTE, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    return b.finish("SM_M80_Doccione")


def strattu():
    b = Builder()
    b.box((0, 0, 0.012), (0.42, 0.25, 0.012), MATTE, "sw_wood")
    for i in range(6):
        for j in range(4):
            b.blob((-0.34 + i * 0.135, -0.18 + j * 0.12, 0.03), 0.07, GLAZED, "sw_paste", 0.18)
    return b.finish("SM_M80_Strattu")


def peperoncini():
    b = Builder()
    b.tube([(0, 0, 0), (0, -0.01, -0.75)], 0.004, MATTE, "sw_rope", 4)
    for k in range(26):
        z = -0.06 - k * 0.026
        a = k * 2.3
        tip = (0.05 * math.cos(a), -0.02 + 0.05 * math.sin(a), z - 0.06)
        b.tube([(0, -0.01, z), ((tip[0]) * 0.5, -0.015 + tip[1] * 0.5, z - 0.03), tip], 0.011, GLAZED, "sw_pepper", 5)
    return b.finish("SM_M80_Peperoncini")


def panni(name, items, seed):
    """Washing hung on a line: sheets, towels and shirts as gently waving cloth (pivot on the line, centre)."""
    import random
    rnd = random.Random(seed)
    b = Builder()
    x = -0.6
    for kind, colour in items:
        w = {"lenzuolo": 0.9, "asciugamano": 0.45, "maglia": 0.42, "pantaloni": 0.32}[kind]
        h = {"lenzuolo": 1.1, "asciugamano": 0.6, "maglia": 0.62, "pantaloni": 0.85}[kind]
        cols, rows = 6, 6
        u0, v0, u1, v1 = rect("sw_" + colour, 0.15)
        grid = []
        for r in range(rows + 1):
            row = []
            for c in range(cols + 1):
                t, z = c / cols, -h * r / rows
                px = x + w * t
                if kind == "maglia" and r <= 2 and (t < 0.2 or t > 0.8):
                    px = x + w * t + (-0.1 if t < 0.2 else 0.1) * (r / 2)  # sleeves
                wave = 0.03 * math.sin(t * math.pi * 2 + seed) * (r / rows) + rnd.uniform(-0.004, 0.004)
                row.append((px, wave, z))
            grid.append(row)
        front = [[b.bm.verts.new(p) for p in row] for row in grid]
        back = [[b.bm.verts.new((p[0], p[1] + 0.002, p[2])) for p in row] for row in grid]
        for r in range(rows):
            for c in range(cols):
                if kind == "pantaloni" and r >= 3 and c == cols // 2:
                    continue  # the gap between the legs
                if kind == "maglia" and r >= 3 and (c == 0 or c == cols - 1):
                    continue  # under the sleeves
                b.face([front[r][c], front[r][c + 1], front[r + 1][c + 1], front[r + 1][c]], MATTE, [(u0, v1), (u1, v1), (u1, v0), (u0, v0)])
                b.face([back[r + 1][c], back[r + 1][c + 1], back[r][c + 1], back[r][c]], MATTE, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        for px in (x + 0.03, x + w - 0.03):  # clothes pegs
            b.box((px, 0, 0.0), (0.008, 0.008, 0.03), MATTE, "sw_wood")
        x += w + 0.08
    return b.finish(name, recalc=False)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = [testa_di_moro(), pigna(), grasta("SM_M80_Grasta_Gerani", True), grasta("SM_M80_Grasta_Basilico", False), quartara(), bummulo(),
            panaru(), edicola(), batacchio(), stemma(), lanterna(), doccione(), strattu(), peperoncini(),
            panni("SM_M80_Panni_A", [("lenzuolo", "whitewash"), ("asciugamano", "glaze_blue"), ("maglia", "geranium")], 1),
            panni("SM_M80_Panni_B", [("maglia", "whitewash"), ("pantaloni", "glaze_blue"), ("asciugamano", "lemon"), ("maglia", "leaf")], 2),
            panni("SM_M80_Panni_C", [("asciugamano", "whitewash"), ("lenzuolo", "glaze_white"), ("pantaloni", "black")], 3)]
    objs += [civico(i) for i in range(4)]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(filepath=str(OUT), use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True)
    print("EXPORTED", OUT, len(objs))


main()
