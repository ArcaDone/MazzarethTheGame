"""Roofs for the Mazzarino 80 buildings: hip roofs covered in coppi (Sicilian canal tiles).

The roof planes get per-face UVs in metres (u along the eave, v up the slope), so a procedural coppi
shader lays the tile rows correctly on every slope: alternating channels, overlapping courses, tile by
tile colour, lichen and soot. Ridges and hips carry a row of ridge tiles as real geometry.
In the game the planes use a tiling coppi material (no unique bake), the ridge rows are kept as mesh.
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

import m80_arch_kit as K


def coppi_material():
    m = bpy.data.materials.get("Coppi_tetto_hi")
    if m:
        return m
    m = bpy.data.materials.new("Coppi_tetto_hi")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    uv = nt.nodes.new("ShaderNodeUVMap")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs[0], sep.inputs[0])

    def math_node(op, a=None, b=None, va=None, vb=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        if a is not None:
            nt.links.new(a, n.inputs[0])
        elif va is not None:
            n.inputs[0].default_value = va
        if b is not None:
            nt.links.new(b, n.inputs[1])
        elif vb is not None:
            n.inputs[1].default_value = vb
        return n

    # Channels across the eave: period 0.34 m (an over tile and an under tile).
    x = math_node("MULTIPLY", sep.outputs[0], vb=2 * math.pi / 0.34)
    cosx = math_node("COSINE", x.outputs[0])
    chan = math_node("MULTIPLY_ADD", cosx.outputs[0], vb=0.5)
    chan.inputs[2].default_value = 0.5
    # Courses up the slope every 0.40 m: each tile overlaps the next (sawtooth).
    y = math_node("DIVIDE", sep.outputs[1], vb=0.40)
    fr = math_node("FRACT", y.outputs[0])
    course = math_node("MULTIPLY", fr.outputs[0], vb=0.35)
    hgt = math_node("ADD", chan.outputs[0], course.outputs[0])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.05
    nt.links.new(hgt.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    # Tile by tile colour: cell id from floor(x / 0.17), floor(y / 0.40) through a white noise.
    cx = math_node("FLOOR", math_node("DIVIDE", sep.outputs[0], vb=0.17).outputs[0])
    cy = math_node("FLOOR", y.outputs[0])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(cx.outputs[0], comb.inputs[0])
    nt.links.new(cy.outputs[0], comb.inputs[1])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise")
    wn.noise_dimensions = "3D"
    nt.links.new(comb.outputs[0], wn.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (0.26, 0.10, 0.05, 1)
    e[1].position, e[1].color = 1.0, (0.44, 0.22, 0.11, 1)
    ramp.color_ramp.elements.new(0.6).color = (0.36, 0.15, 0.07, 1)
    nt.links.new(wn.outputs["Value"], ramp.inputs[0])
    # Lichen (pale grey-green) and soot in the channels.
    tc = nt.nodes.new("ShaderNodeTexCoord")
    lich = nt.nodes.new("ShaderNodeTexNoise")
    lich.inputs["Scale"].default_value = 1.6
    lich.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], lich.inputs["Vector"])
    lr = nt.nodes.new("ShaderNodeMapRange")
    lr.inputs["From Min"].default_value = 0.64
    lr.inputs["From Max"].default_value = 0.80
    nt.links.new(lich.outputs["Fac"], lr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(lr.outputs[0], mix.inputs["Factor"])
    nt.links.new(ramp.outputs[0], mix.inputs[6])
    mix.inputs[7].default_value = (0.24, 0.23, 0.19, 1)
    soot = nt.nodes.new("ShaderNodeMix")
    soot.data_type = "RGBA"
    soot.blend_type = "MULTIPLY"
    inv = math_node("SUBTRACT", vb=0, va=1.0)
    nt.links.new(chan.outputs[0], inv.inputs[1])
    sf = math_node("MULTIPLY", inv.outputs[0], vb=0.45)
    nt.links.new(sf.outputs[0], soot.inputs["Factor"])
    nt.links.new(mix.outputs[2], soot.inputs[6])
    soot.inputs[7].default_value = (0.35, 0.33, 0.30, 1)
    nt.links.new(soot.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    return m


def hip_roof(name, poly, eave, axis, pitch_deg, col_high, col_low, mat_low, overhang=0.0):
    """Hip roof with per-face slope UVs; returns (high, low). High adds ridge/hip tile rows."""
    pts = [Vector(p) for p in poly]
    area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))
    if area < 0:
        pts.reverse()
    ax = Vector(axis).normalized()
    nx = Vector((-ax.y, ax.x))
    c = sum(pts, Vector((0, 0))) / len(pts)
    along = [(p - c).dot(ax) for p in pts]
    across = [(p - c).dot(nx) for p in pts]
    mid = (max(across) + min(across)) / 2
    half = (max(across) - min(across)) / 2
    c = c + nx * mid
    a0, a1 = min(along) + half, max(along) - half
    if a1 < a0:
        a0 = a1 = (min(along) + max(along)) / 2
    rise = math.tan(math.radians(pitch_deg)) * half
    n = len(pts)

    def ridge(p):
        t = max(a0, min(a1, (p - c).dot(ax)))
        q = c + ax * t
        return Vector((q.x, q.y, eave + rise))

    objs = []
    for coll, mat, sfx in ((col_high, coppi_material(), "_hi"), (col_low, mat_low, "")):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            A3, B3 = Vector((a.x, a.y, eave)), Vector((b.x, b.y, eave))
            ra, rb = ridge(a), ridge(b)
            quad = [A3, B3, rb, ra] if (ra - rb).length > 1e-3 else [A3, B3, ra]
            vs = [bm.verts.new(p) for p in quad]
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            # UV in metres: u along the eave edge, v up the slope.
            t = (B3 - A3).normalized()
            nrm = f.normal if f.normal.z > 0 else -f.normal
            up = nrm.cross(t).normalized()
            if up.z < 0:
                up = -up
            for loop in f.loops:
                d = loop.vert.co - A3
                loop[uvl].uv = (d.dot(t), d.dot(up))
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        for f in bm.faces:
            if f.normal.z < 0:
                f.normal_flip()
        ob = K.bm_object(name + sfx, bm, coll, None, mat)
        objs.append(ob)
    hi = objs[0]
    # Ridge and hip rows: edges between faces at an angle.
    me = hi.data
    bm = bmesh.new()
    bm.from_mesh(me)
    rows = []
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.link_faces[0].normal.angle(e.link_faces[1].normal) > math.radians(12):
            rows.append((e.verts[0].co.copy(), e.verts[1].co.copy()))
    bm.free()
    if rows:
        cu = bpy.data.curves.new(name + "_colmi", "CURVE")
        cu.dimensions = "3D"
        cu.bevel_depth = 0.11
        cu.bevel_resolution = 3
        cu.fill_mode = "HALF"
        for a, b in rows:
            sp = cu.splines.new("POLY")
            sp.points.add(1)
            sp.points[0].co = (a.x, a.y, a.z + 0.02, 1)
            sp.points[1].co = (b.x, b.y, b.z + 0.02, 1)
        cu.materials.append(bpy.data.materials.get("Coppi") or coppi_material())
        ob = bpy.data.objects.new(name + "_colmi", cu)
        col_high.objects.link(ob)
    return objs
