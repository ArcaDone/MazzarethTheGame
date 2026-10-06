"""Blender 4.3: the cast-iron street lamps of Mazzarino, exported to M80_Lamps.fbx, with preview renders.

Run: blender -b --factory-startup --python m80_lamps_blender.py
- SM_M80_Lampione_Muro: hexagonal lantern with frosted glass on a wrought-iron scroll bracket.
  Wall prop convention of the Sicilian kit: back on the Y = 0 plane (the wall), growing towards -Y;
  the pivot is on the wall at the height of the bracket bar.
- SM_M80_Lampione_Palo: candelabra on a stone plinth: footed base, twisted fluted shaft, scrolled
  capital and three square lanterns (two on arms, one on top). Pivot at the base centre.
Material slots: 0 "Iron" (dark green cast iron), 1 "Glass" (frosted, lit at night), 2 "Stone" (plinth).
Units are metres. The glass centres (light positions, metres from the pivot) go to M80_Lamps.json.
Textures: each lamp is unwrapped and its photographic look is baked with Cycles from procedural
materials that follow the shape: green paint with chips on the edges (bare iron and rust under it),
grime and rust in the hollows, rust runs, cast pitting; sandstone plinth. Output per lamp, 2K:
Textures/Lamps/T_M80_<name>_D.jpg (colour), _N.png (normal), _ORM.jpg (AO, roughness, metallic).
Previews (Cycles): Previews/lampione_muro.png, Previews/lampione_palo.png.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
OUT = HERE / "M80_Lamps.fbx"
INFO = HERE / "M80_Lamps.json"
PREVIEWS = HERE / "Previews"
IRON, GLASS, STONE = 0, 1, 2


class Mesh:
    """Collects geometry in one bmesh; every part gets a material index."""

    def __init__(self):
        self.bm = bmesh.new()

    def add_bm(self, other, mat, matrix=Matrix()):
        other.transform(matrix)
        mesh = bpy.data.meshes.new("tmp")
        other.to_mesh(mesh)
        for poly in mesh.polygons:
            poly.material_index = mat
        self.bm.from_mesh(mesh)
        bpy.data.meshes.remove(mesh)
        other.free()

    def lathe(self, profile, sides, mat, matrix=Matrix(), twist=0.0, flutes=0, flute_depth=0.0, rotate=0.0):
        """Surface of revolution through (radius, z) points; optional flutes and twist (radians per metre)."""
        bm = bmesh.new()
        rings = []
        for r, z in profile:
            ring = []
            for i in range(sides):
                a = 2 * math.pi * i / sides + rotate + twist * z
                rr = r * (1 + flute_depth * math.cos(flutes * (2 * math.pi * i / sides))) if flutes else r
                ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                bm.faces.new((a[i], a[j], b[j], b[i]))
        if profile[0][0] > 1e-4:
            bm.faces.new(list(reversed(rings[0])))
        if profile[-1][0] > 1e-4:
            bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self.add_bm(bm, mat, matrix)

    def box(self, size, mat, matrix=Matrix()):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * 0.08, segments=2, affect="EDGES", profile=0.5)
        self.add_bm(bm, mat, matrix)

    def sphere(self, radius, mat, matrix=Matrix(), squash=1.0):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=radius)
        bmesh.ops.scale(bm, vec=Vector((1, 1, squash)), verts=bm.verts)
        self.add_bm(bm, mat, matrix)

    def tube(self, points, radius, mat, sides=10):
        """A round bar along a polyline (wrought iron)."""
        bm = bmesh.new()
        pts = [Vector(p) for p in points]
        rings = []
        for k, p in enumerate(pts):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            n = t.cross(Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
            b = t.cross(n)
            rings.append([bm.verts.new(p + (n * math.cos(2 * math.pi * i / sides) + b * math.sin(2 * math.pi * i / sides)) * radius)
                          for i in range(sides)])
        for a, c in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                bm.faces.new((a[i], a[j], c[j], c[i]))
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        self.add_bm(bm, mat)

    def to_object(self, name):
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        for poly in mesh.polygons:
            poly.use_smooth = True
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        for mat in MATERIALS:
            obj.data.materials.append(mat)
        return obj


def spiral(centre, plane_u, plane_v, r0, r1, turns, start=0.0, steps=40):
    """Points of a flat spiral (a scroll) in the plane spanned by plane_u, plane_v."""
    c, u, v = Vector(centre), Vector(plane_u), Vector(plane_v)
    out = []
    for k in range(steps + 1):
        t = k / steps
        a = start + 2 * math.pi * turns * t
        r = r0 + (r1 - r0) * t
        out.append(c + (u * math.cos(a) + v * math.sin(a)) * r)
    return out


def scroll_on(m, touch, plane_u, r0, r1, turns, below=True, radius=0.008):
    """A scroll welded to a bar: its outer end starts at `touch` (a point on the bar) and curls
    inwards below it (or above it)."""
    up = Vector((0, 0, 1))
    centre = Vector(touch) - up * r0 if below else Vector(touch) + up * r0
    start = math.pi / 2 if below else -math.pi / 2
    m.tube(spiral(centre, plane_u, up, r0, r1, turns, start=start, steps=36), radius, IRON, 8)


def arc(p0, p1, bulge, plane_n, steps=24):
    """Circular-looking curve from p0 to p1 bowed sideways by `bulge` along plane_n x (p1-p0)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    side = Vector(plane_n).cross(d).normalized()
    return [p0 + d * (k / steps) + side * bulge * math.sin(math.pi * k / steps) for k in range(steps + 1)]


def lantern(m, base, sides, r_bottom, r_top, height):
    """Tapered lantern standing on `base` (a Vector): frosted glass body, iron frame, cap and finial.
    Returns the centre of the glass."""
    bx, by, bz = base
    T = Matrix.Translation(base)
    rot = math.pi / sides
    # Bottom collar and little cup under the glass.
    m.lathe([(0.0, 0.0), (0.035, 0.0), (0.05, 0.04), (r_bottom * 0.55, 0.07), (r_bottom * 1.05, 0.085), (r_bottom * 1.05, 0.1), (0.0, 0.1)],
            sides, IRON, T, rotate=rot)
    # Glass body (a little inset from the frame).
    g0, g1 = 0.1, 0.1 + height
    m.lathe([(r_bottom * 0.97, g0), (r_top * 0.97, g1)], sides, GLASS, T, rotate=rot)
    # Frame: vertical bars on the corners, rings top and bottom.
    for i in range(sides):
        a = 2 * math.pi * i / sides + rot
        p = Vector((bx + r_bottom * math.cos(a), by + r_bottom * math.sin(a), bz + g0))
        q = Vector((bx + r_top * math.cos(a), by + r_top * math.sin(a), bz + g1))
        m.tube([p, q], 0.008, IRON, 6)
    m.lathe([(r_top * 0.95, g1), (r_top * 1.08, g1), (r_top * 1.12, g1 + 0.025), (r_top * 0.95, g1 + 0.025)], sides, IRON, T, rotate=rot)
    # Cap: overhanging roof, a short neck and the finial.
    c0 = g1 + 0.025
    m.lathe([(r_top * 1.2, c0), (r_top * 1.2, c0 + 0.02), (r_top * 0.5, c0 + 0.12), (0.06, c0 + 0.16), (0.04, c0 + 0.17),
             (0.07, c0 + 0.19), (0.075, c0 + 0.21), (0.0, c0 + 0.25)], sides, IRON, T, rotate=rot)
    m.sphere(0.03, IRON, Matrix.Translation((bx, by, bz + c0 + 0.27)))
    m.lathe([(0.012, c0 + 0.28), (0.0, c0 + 0.33)], 8, IRON, T)
    # Small scrolls under the collar (as in the photos).
    for i in range(4):
        a = 2 * math.pi * i / 4 + math.pi / 4
        u = Vector((math.cos(a), math.sin(a), 0))
        m.tube(spiral(Vector(base) + u * 0.06 + Vector((0, 0, 0.0)), u, Vector((0, 0, 1)), 0.035, 0.008, 1.1, start=math.pi / 2, steps=18),
               0.006, IRON, 6)
    return Vector((bx, by, bz + (g0 + g1) / 2))


def lampione_muro():
    m = Mesh()
    arm = 0.95
    # Wall plate and the horizontal bar.
    m.box((0.07, 0.03, 0.62), IRON, Matrix.Translation((0, -0.015, -0.27)))
    for z in (0.0, -0.54):
        m.sphere(0.011, IRON, Matrix.Translation((0, -0.032, z)), squash=0.6)
    m.tube([(0, -0.02, 0.0), (0, -arm, 0.0)], 0.016, IRON, 10)
    m.sphere(0.022, IRON, Matrix.Translation((0, -arm, 0.0)))
    # Lower curved strut from the wall to the bar, with scrolls along it.
    strut = arc((0, -0.02, -0.55), (0, -arm * 0.82, -0.02), 0.22, (1, 0, 0))
    m.tube(strut, 0.011, IRON, 8)
    toward = Vector((0, -1, 0))
    away = Vector((0, 1, 0))
    # Scrolls hanging from the bar (welded to it), getting smaller towards the lantern.
    scroll_on(m, (0, -0.2, -0.016), toward, 0.14, 0.02, 1.35)
    scroll_on(m, (0, -0.47, -0.016), away, 0.1, 0.016, 1.3)
    scroll_on(m, (0, -0.68, -0.016), toward, 0.07, 0.012, 1.25, radius=0.007)
    # Curl at the foot of the strut, against the wall plate.
    m.tube(spiral((0, -0.07, -0.5), toward, Vector((0, 0, 1)), 0.055, 0.01, 1.2, start=math.pi * 1.1, steps=30), 0.008, IRON, 8)
    # Leaves where the strut meets the bar.
    m.sphere(0.02, IRON, Matrix.Translation((0, -arm * 0.82, -0.02)), squash=0.7)
    # Spike from the end of the bar up to the lantern.
    tip = Vector((0, -arm + 0.07, 0.0))
    m.tube([tip, tip + Vector((0, 0, 0.12))], 0.012, IRON, 8)
    glass = lantern(m, tip + Vector((0, 0, 0.12)), 6, 0.13, 0.22, 0.44)
    return m.to_object("SM_M80_Lampione_Muro"), [glass]


def lampione_palo():
    m = Mesh()
    # Stone plinth.
    m.box((0.62, 0.62, 0.32), STONE, Matrix.Translation((0, 0, 0.16)))
    m.box((0.56, 0.56, 0.04), STONE, Matrix.Translation((0, 0, 0.34)))
    # Cast base with four clawed feet (rounded lumps with scrolls) and a bellied pedestal.
    z0 = 0.36
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        u = Vector((math.cos(a), math.sin(a), 0))
        m.sphere(0.11, IRON, Matrix.Translation(u * 0.2 + Vector((0, 0, z0 + 0.07))), squash=0.6)
        m.sphere(0.06, IRON, Matrix.Translation(u * 0.29 + Vector((0, 0, z0 + 0.04))), squash=0.7)
        m.tube(spiral(u * 0.15 + Vector((0, 0, z0 + 0.2)), u, Vector((0, 0, 1)), 0.09, 0.02, 1.2, start=math.pi * 1.5), 0.012, IRON, 6)
    m.lathe([(0.2, z0), (0.22, z0 + 0.08), (0.16, z0 + 0.2), (0.17, z0 + 0.36), (0.12, z0 + 0.5), (0.1, z0 + 0.62),
             (0.13, z0 + 0.7), (0.13, z0 + 0.75), (0.085, z0 + 0.8)], 16, IRON)
    # Acanthus-like flared section, then the twisted fluted shaft with rings.
    m.lathe([(0.085, z0 + 0.8), (0.11, z0 + 0.95), (0.09, z0 + 1.15), (0.07, z0 + 1.3)], 24, IRON, flutes=12, flute_depth=0.12)
    s0, s1 = z0 + 1.3, z0 + 3.35
    m.lathe([(0.075, s0), (0.08, s0 + 0.04), (0.075, s0 + 0.08)], 16, IRON)
    m.lathe([(0.062, s0 + 0.08 + k * (s1 - s0 - 0.08) / 60) for k in range(61)], 54, IRON, twist=5.5, flutes=9, flute_depth=0.14)
    m.lathe([(0.068, s1), (0.085, s1 + 0.05), (0.07, s1 + 0.1)], 16, IRON)
    # Capital: an urn with leaves, then the arms.
    c = s1 + 0.1
    m.lathe([(0.07, c), (0.13, c + 0.12), (0.15, c + 0.22), (0.1, c + 0.32), (0.06, c + 0.36), (0.09, c + 0.4), (0.05, c + 0.46)], 16, IRON,
            flutes=8, flute_depth=0.1)
    glasses = []
    arm_z = c + 0.42
    for side in (-1, 1):
        u = Vector((side, 0, 0))
        # The arm: up and out in an S, ending with a vertical stem under the lantern.
        end = Vector((side * 0.78, 0, arm_z + 0.5))
        path = [Vector((0, 0, arm_z)) + u * 0.04]
        for k in range(1, 25):
            t = k / 24
            path.append(Vector((side * 0.78 * t, 0, arm_z + 0.5 * (t * t) - 0.18 * math.sin(math.pi * t))))
        m.tube(path, 0.02, IRON, 10)
        m.tube([end, end + Vector((0, 0, 0.1))], 0.016, IRON, 8)
        # Big scroll filling the space under the arm, and a small one near the top.
        def arm_point(t):
            return Vector((side * 0.78 * t, 0, arm_z + 0.5 * (t * t) - 0.18 * math.sin(math.pi * t)))
        scroll_on(m, arm_point(0.4) - Vector((0, 0, 0.018)), -u, 0.15, 0.025, 1.35, radius=0.011)
        scroll_on(m, arm_point(0.78) + Vector((0, 0, 0.018)), u, 0.08, 0.014, 1.25, below=False, radius=0.009)
        glasses.append(lantern(m, end + Vector((0, 0, 0.1)), 4, 0.12, 0.2, 0.42))
    # Central upright with the top lantern.
    top = Vector((0, 0, arm_z + 0.62))
    m.tube([Vector((0, 0, arm_z - 0.02)), top], 0.022, IRON, 10)
    for side in (-1, 1):
        u = Vector((side, 0, 0))
        m.tube(spiral(Vector((side * 0.11, 0, arm_z + 0.3)), -u, Vector((0, 0, 1)), 0.09, 0.016, 1.3, start=0.0, steps=36), 0.009, IRON, 8)
    glasses.append(lantern(m, top, 4, 0.12, 0.2, 0.42))
    return m.to_object("SM_M80_Lampione_Palo"), glasses


TEX = HERE / "Textures" / "Lamps"
SIZE = 2048


def node(tree, kind, loc=(0, 0), **inputs):
    n = tree.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def noise(tree, scale, detail=6.0, rough=0.6, stretch=(1, 1, 1)):
    """Noise texture on object coordinates (optionally stretched, e.g. long in Z for rust runs)."""
    coord = node(tree, "ShaderNodeTexCoord")
    mapping = node(tree, "ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = stretch
    tree.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    n = node(tree, "ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough)
    tree.links.new(mapping.outputs["Vector"], n.inputs["Vector"])
    return n


def ramp(tree, socket, a, b):
    """Maps socket from [a, b] to [0, 1] (clamped)."""
    r = node(tree, "ShaderNodeMapRange", **{"From Min": a, "From Max": b})
    tree.links.new(socket, r.inputs["Value"])
    return r.outputs["Result"]


def mix_col(tree, fac, c1, c2):
    m = tree.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    tree.links.new(fac, m.inputs["Factor"])
    for sock, c in ((m.inputs[6], c1), (m.inputs[7], c2)):
        if isinstance(c, tuple):
            sock.default_value = c
        else:
            tree.links.new(c, sock)
    return m.outputs[2]


def mix_val(tree, fac, a, b):
    """a + fac * (b - a); a and b are floats or sockets."""
    d = node(tree, "ShaderNodeMath")
    d.operation = "SUBTRACT"
    m = node(tree, "ShaderNodeMath")
    m.operation = "MULTIPLY_ADD"
    for sock, v in ((d.inputs[0], b), (d.inputs[1], a), (m.inputs[2], a)):
        if isinstance(v, float):
            sock.default_value = v
        else:
            tree.links.new(v, sock)
    tree.links.new(fac, m.inputs[0])
    tree.links.new(d.outputs[0], m.inputs[1])
    return m.outputs[0]


def maximum(tree, a, b):
    m = node(tree, "ShaderNodeMath")
    m.operation = "MAXIMUM"
    tree.links.new(a, m.inputs[0])
    tree.links.new(b, m.inputs[1])
    return m.outputs[0]


def multiply(tree, a, b):
    m = node(tree, "ShaderNodeMath")
    m.operation = "MULTIPLY"
    for sock, v in ((m.inputs[0], a), (m.inputs[1], b)):
        if isinstance(v, float):
            sock.default_value = v
        else:
            tree.links.new(v, sock)
    return m.outputs[0]


def iron_material():
    """Old cast iron painted dark green: chips on the edges, rust and grime in the hollows, rust runs."""
    mat = bpy.data.materials.new("Iron")
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    out = node(t, "ShaderNodeOutputMaterial")
    bsdf = node(t, "ShaderNodeBsdfPrincipled")
    t.links.new(bsdf.outputs[0], out.inputs[0])
    geo = node(t, "ShaderNodeNewGeometry")
    ao = node(t, "ShaderNodeAmbientOcclusion", Distance=0.015)
    ao.samples = 16
    # Edges: pointiness above average, broken up so the chips are irregular; a few larger flakes anywhere.
    edge = ramp(t, geo.outputs["Pointiness"], 0.57, 0.68)
    chip_edge = multiply(t, edge, ramp(t, noise(t, 55.0, 8.0, 0.7).outputs["Fac"], 0.56, 0.66))
    flakes = ramp(t, noise(t, 9.0, 4.0, 0.55).outputs["Fac"], 0.7, 0.72)
    chips = maximum(t, chip_edge, flakes)
    # Hollows (low AO) collect grime and rust; rust runs drip down.
    cavity = ramp(t, ao.outputs["AO"], 0.55, 0.2)
    runs = ramp(t, noise(t, 14.0, 5.0, 0.6, stretch=(1, 1, 0.08)).outputs["Fac"], 0.68, 0.82)
    rust_on = maximum(t, multiply(t, maximum(t, cavity, runs), 0.35), multiply(t, chip_edge, 0.5))
    rust_col = mix_col(t, noise(t, 120.0, 10.0, 0.75).outputs["Fac"], (0.16, 0.055, 0.02, 1), (0.32, 0.12, 0.04, 1))
    # Paint: dark bottle green with a slow tonal variation.
    paint = mix_col(t, noise(t, 3.0, 3.0, 0.5).outputs["Fac"], (0.02, 0.042, 0.036, 1), (0.036, 0.062, 0.054, 1))
    # Sun-faded paint on top surfaces (paler, a little grey).
    sep = node(t, "ShaderNodeSeparateXYZ")
    t.links.new(node(t, "ShaderNodeNewGeometry").outputs["Normal"], sep.inputs[0])
    facing_up = ramp(t, sep.outputs["Z"], 0.5, 1.0)
    paint = mix_col(t, multiply(t, facing_up, 0.4), paint, (0.06, 0.08, 0.075, 1))
    col = mix_col(t, chips, paint, (0.045, 0.042, 0.04, 1))
    col = mix_col(t, rust_on, col, rust_col)
    grime = mix_col(t, cavity, (1, 1, 1, 1), (0.45, 0.42, 0.38, 1))
    mult = t.nodes.new("ShaderNodeMix")
    mult.data_type = "RGBA"
    mult.blend_type = "MULTIPLY"
    mult.inputs["Factor"].default_value = 1.0
    t.links.new(col, mult.inputs[6])
    t.links.new(grime, mult.inputs[7])
    t.links.new(mult.outputs[2], bsdf.inputs["Base Color"])
    # Satin paint, polished bare edges, dull rust.
    t.links.new(mix_val(t, rust_on, mix_val(t, chips, 0.48, 0.35), 0.9), bsdf.inputs["Roughness"])
    metal = mix_val(t, rust_on, mix_val(t, chips, 0.0, 0.85), 0.0)
    t.links.new(metal, bsdf.inputs["Metallic"])
    # Relief: casting pits and the paint edge around the chips.
    height = node(t, "ShaderNodeMath")
    height.operation = "ADD"
    t.links.new(noise(t, 260.0, 6.0, 0.6).outputs["Fac"], height.inputs[0])
    t.links.new(chips, height.inputs[1])
    bump = node(t, "ShaderNodeBump", Strength=0.35, Distance=0.002)
    t.links.new(height.outputs[0], bump.inputs["Height"])
    t.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return mat, metal


def stone_material():
    """Golden sandstone of the plinth: grains, darker patches and pits."""
    mat = bpy.data.materials.new("Stone")
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    out = node(t, "ShaderNodeOutputMaterial")
    bsdf = node(t, "ShaderNodeBsdfPrincipled", Roughness=0.88)
    t.links.new(bsdf.outputs[0], out.inputs[0])
    grain = noise(t, 180.0, 10.0, 0.7)
    col = mix_col(t, noise(t, 6.0, 4.0, 0.55).outputs["Fac"], (0.34, 0.27, 0.17, 1), (0.45, 0.36, 0.24, 1))
    col = mix_col(t, ramp(t, grain.outputs["Fac"], 0.4, 0.7), col, (0.29, 0.23, 0.15, 1))
    vor = node(t, "ShaderNodeTexVoronoi", Scale=40.0)
    col = mix_col(t, ramp(t, vor.outputs["Distance"], 0.08, 0.0), col, (0.22, 0.18, 0.13, 1))
    t.links.new(col, bsdf.inputs["Base Color"])
    bump = node(t, "ShaderNodeBump", Strength=0.6, Distance=0.004)
    t.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    t.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    return mat, None


def glass_material():
    mat = bpy.data.materials.new("Glass")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.85, 0.83, 0.76, 1)
    bsdf.inputs["Roughness"].default_value = 0.35
    return mat, None


def make_materials():
    mats = [iron_material(), glass_material(), stone_material()]
    METAL_SOCKETS.update({m.name: sock for m, sock in mats})
    return [m for m, _ in mats]


def unwrap(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, correct_aspect=True, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake(obj, name):
    """Bakes colour, normal, AO, roughness and metallic of obj into 2K images and writes the files."""
    import numpy as np
    TEX.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.render.bake.margin = 8
    images = {}

    def target(key, colour):
        img = bpy.data.images.new(f"{name}_{key}", SIZE, SIZE, alpha=False)
        img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        for mat in obj.data.materials:
            nodes = mat.node_tree.nodes
            n = nodes.get("BakeTarget") or nodes.new("ShaderNodeTexImage")
            n.name = "BakeTarget"
            n.image = img
            nodes.active = n
        images[key] = img

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    target("D", True)
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, use_clear=True)
    target("N", False)
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", use_clear=True)
    target("R", False)
    bpy.ops.object.bake(type="ROUGHNESS", use_clear=True)
    target("AO", False)
    bpy.ops.object.bake(type="AO", use_clear=True)
    # Metallic: bake the metal mask as emission, then restore the shaders.
    target("M", False)
    saved = []
    for mat in obj.data.materials:
        t = mat.node_tree
        out = next(n for n in t.nodes if n.type == "OUTPUT_MATERIAL")
        old = out.inputs[0].links[0].from_socket
        emit = t.nodes.new("ShaderNodeEmission")
        sock = METAL_SOCKETS.get(mat.name)
        if sock is not None:
            t.links.new(sock, emit.inputs["Color"])
        else:
            emit.inputs["Color"].default_value = (0, 0, 0, 1)
        t.links.new(emit.outputs[0], out.inputs[0])
        saved.append((t, out, old, emit))
    bpy.ops.object.bake(type="EMIT", use_clear=True)
    for t, out, old, emit in saved:
        t.links.new(old, out.inputs[0])
        t.nodes.remove(emit)
    # AO, roughness and metallic in one texture (R, G, B), as Unreal's ORM.
    px = {}
    for k in ("AO", "R", "M"):
        arr = np.empty(SIZE * SIZE * 4, dtype=np.float32)
        images[k].pixels.foreach_get(arr)
        px[k] = arr
    orm = bpy.data.images.new(f"{name}_ORM", SIZE, SIZE, alpha=False)
    orm.colorspace_settings.name = "Non-Color"
    packed = np.ones(SIZE * SIZE * 4, dtype=np.float32)
    packed[0::4], packed[1::4], packed[2::4] = px["AO"][0::4], px["R"][0::4], px["M"][0::4]
    orm.pixels.foreach_set(packed)
    settings = scene.render.image_settings
    settings.quality = 92
    for key, img, fmt, ext in (("D", images["D"], "JPEG", "jpg"), ("N", images["N"], "PNG", "png"), ("ORM", orm, "JPEG", "jpg")):
        settings.file_format = fmt
        settings.color_mode = "RGB"
        img.save_render(str(TEX / f"T_M80_{name}_{key}.{ext}"), scene=scene)


def preview(obj, path, distance, height):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    centre = sum((obj.matrix_world @ Vector(v) for v in obj.bound_box), Vector()) / 8
    cam = bpy.data.objects.get("PreviewCam") or bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    if cam.name not in scene.collection.objects:
        scene.collection.objects.link(cam)
    cam.location = centre + Vector((distance * 0.75, -distance, height))
    cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    scene.camera = cam
    if not bpy.data.objects.get("PreviewSun"):
        sun = bpy.data.objects.new("PreviewSun", bpy.data.lights.new("PreviewSun", "SUN"))
        sun.data.energy = 4.0
        sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
        scene.collection.objects.link(sun)
        world = bpy.data.worlds.new("Sky")
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.65, 0.8, 1)
        world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
        scene.world = world
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.view_settings.view_transform = "AgX"
    scene.render.resolution_x, scene.render.resolution_y = 900, 1200
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def use_gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
            except TypeError:
                continue
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == kind
                bpy.context.scene.cycles.device = "GPU"
                return kind
    except Exception as e:  # noqa: BLE001
        print("GPU not available:", e)
    return "CPU"


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATERIALS[:] = make_materials()
    print("Cycles device:", use_gpu())
    wall, wall_lights = lampione_muro()
    pole, pole_lights = lampione_palo()
    INFO.write_text(json.dumps({"SM_M80_Lampione_Muro": [list(v) for v in wall_lights],
                                "SM_M80_Lampione_Palo": [list(v) for v in pole_lights]}, indent=1), encoding="utf-8")
    for obj, name in ((wall, "Lampione_Muro"), (pole, "Lampione_Palo")):
        unwrap(obj)
        bake(obj, name)
    PREVIEWS.mkdir(exist_ok=True)
    preview(wall, PREVIEWS / "lampione_muro.png", 1.8, 0.3)
    preview(pole, PREVIEWS / "lampione_palo.png", 6.0, 0.5)
    for o in bpy.context.scene.objects:
        o.hide_render = False
    bpy.ops.object.select_all(action="DESELECT")
    for obj in (wall, pole):
        obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT), use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", object_types={"MESH"}, mesh_smooth_type="FACE", bake_space_transform=True)
    print("M80 lamps exported:", OUT)


METAL_SOCKETS = {}
MATERIALS = []
main()
