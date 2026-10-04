"""Blender 4.3: table of the objects of a .blend in world space (centre, size, render triangles,
parent chain) -> text file. Run: blender -b <file.blend> --python m80_objects_table.py -- <out.txt>"""
import sys

import bpy
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
dg = bpy.context.evaluated_depsgraph_get()
rows = []
for o in bpy.context.scene.objects:
    if o.type not in ("MESH", "CURVE", "EMPTY", "ARMATURE"):
        continue
    if o.type in ("MESH", "CURVE"):
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    else:
        lo = hi = o.matrix_world.translation
    tris = 0
    if o.type == "MESH" and not o.hide_render:
        try:
            m = o.evaluated_get(dg).to_mesh()
            tris = sum(len(p.vertices) - 2 for p in m.polygons)
            o.evaluated_get(dg).to_mesh_clear()
        except Exception:  # noqa: BLE001
            tris = -1
    c = (lo + hi) / 2
    s = hi - lo
    chain = []
    p = o.parent
    while p:
        chain.append(p.name)
        p = p.parent
    rows.append((o.name, o.type, int(o.hide_render) + (0 if o.visible_get() else 2), tris, c, s, "/".join(chain), [round(v, 3) for v in o.matrix_world.to_scale()]))
rows.sort(key=lambda r: -max(r[5]))
with open(OUT, "w", encoding="utf-8") as f:
    for n, t, h, tr, c, s, ch, sc in rows:
        f.write("%-30s %-8s hid=%d tris=%8d c=(%7.2f %7.2f %6.2f) s=(%6.2f %6.2f %6.2f) scale=%s par=%s\n" % (
            n[:30], t, h, tr, c.x, c.y, c.z, s.x, s.y, s.z, sc, ch))
print("M80 table", OUT, len(rows))
