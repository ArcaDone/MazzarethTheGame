"""M80 Riduci triangoli: lowers the triangle count of the selected meshes with a live preview.

Sidebar (N) > M80 > Riduci triangoli. "Anteprima" puts a modifier on each selected mesh, so moving the sliders
reshapes them at once in the viewport (with their wireframe, to judge the triangles); "Mostra anteprima" flips back
to the original to compare; "Applica" bakes it in (keeping a copy of the originals in the hidden collection
"M80 Originali"); "Annulla" takes it off.
Methods:
  Riduci           Decimate / Collapse: keeps UVs, materials and the shape; "Dettaglio" = share of triangles kept,
                   "Minimo per oggetto" spares small parts (a needle of 26 triangles is not cut to 3).
  Superfici piane  Decimate / Planar: merges faces that lie flat within an angle (panels, floors); UVs and
                   material borders are kept.
  Retopologia      Remesh / Voxel: a new even surface of triangles of the size asked; UVs and materials are lost,
                   for closed objects (rocks, sculptures) whose texture is baked again afterwards.
Built as a Blender extension (blender_manifest.toml): zip the folder and Install from Disk.
"""
import math

import bpy
import numpy as np
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

MOD = "M80 Riduci"
NRM = "M80 Normali"
BACKUP = "M80 Originali"


def mesh_tris(mesh):
    n = len(mesh.polygons)
    if not n:
        return 0
    sides = np.empty(n, np.int32)
    mesh.polygons.foreach_get("loop_total", sides)
    return int(sides.sum()) - 2 * n


def selected_meshes(context):
    return [o for o in context.selected_objects if o.type == 'MESH']


def previewed(objs):
    return [o for o in objs if MOD in o.modifiers]


def keep_last(ob):
    """The reduction after the object's own modifiers, the weighted normals after it."""
    for name in (MOD, NRM):
        i = ob.modifiers.find(name)
        if i >= 0:
            ob.modifiers.move(i, len(ob.modifiers) - 1)


def configure(ob, s):
    want = 'REMESH' if s.metodo == 'REMESH' else 'DECIMATE'
    m = ob.modifiers.get(MOD)
    if m and m.type != want:
        ob.modifiers.remove(m)
        m = None
    if m is None:
        m = ob.modifiers.new(MOD, want)
    base = ob.get("m80_tris") or mesh_tris(ob.data)
    if s.metodo == 'COLLAPSE':
        m.decimate_type = 'COLLAPSE'
        r = s.dettaglio / 100.0
        if base:
            r = max(r, min(1.0, s.minimo / base))
        m.ratio = r
        m.use_collapse_triangulate = s.triangola
        m.use_symmetry = s.simmetria
        m.symmetry_axis = s.asse
    elif s.metodo == 'PLANAR':
        m.decimate_type = 'DISSOLVE'
        m.angle_limit = math.radians(s.angolo)
        m.delimit = {'MATERIAL', 'SEAM', 'UV'}
    else:
        m.mode = 'VOXEL'
        # The size is asked in world centimetres: the modifier works in the object's own space.
        unit = bpy.context.scene.unit_settings.scale_length or 1.0
        scale = max(abs(ob.matrix_world.to_scale().x), abs(ob.matrix_world.to_scale().y), abs(ob.matrix_world.to_scale().z), 1e-6)
        m.voxel_size = max(s.voxel / 100.0 / unit / scale, 1e-4)
        m.adaptivity = 0.0
        m.use_smooth_shade = True
    m.show_viewport = s.mostra
    n = ob.modifiers.get(NRM)
    if s.normali and n is None:
        n = ob.modifiers.new(NRM, 'WEIGHTED_NORMAL')
        n.keep_sharp = True
    elif not s.normali and n is not None:
        ob.modifiers.remove(n)
        n = None
    if n is not None:
        n.show_viewport = s.mostra
    keep_last(ob)


# --- triangle count, refreshed a moment after a change (the modifiers are evaluated by then) ---

_pending = [False]
_last_sel = [None]


def count_now():
    _pending[0] = False
    wm = bpy.context.window_manager
    win = wm.windows[0] if wm and wm.windows else None
    scene = win.scene if win else bpy.context.scene
    vl = win.view_layer if win else bpy.context.view_layer
    if scene is None or vl is None:
        return None
    s = scene.m80_riduci
    dg = vl.depsgraph
    before = after = objs = 0
    for ob in vl.objects:
        if ob.type != 'MESH' or not ob.select_get(view_layer=vl):
            continue
        objs += 1
        b = mesh_tris(ob.data)
        before += b
        if MOD in ob.modifiers and ob.modifiers[MOD].show_viewport:
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            after += mesh_tris(me)
            ev.to_mesh_clear()
        else:
            after += b
    s.prima, s.dopo, s.oggetti = before, after, objs
    for w in wm.windows:
        for area in w.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return None


def schedule_count(delay=0.15):
    if not _pending[0]:
        _pending[0] = True
        bpy.app.timers.register(count_now, first_interval=delay)


@persistent
def on_depsgraph(scene, depsgraph):
    # Only a new selection needs a new count (moving objects about does not).
    try:
        sel = tuple(sorted(o.name for o in scene.objects if o.type == 'MESH' and o.select_get()))
    except Exception:
        return
    if sel != _last_sel[0]:
        _last_sel[0] = sel
        schedule_count(0.3)


def on_change(self, context):
    for ob in previewed(selected_meshes(context)):
        configure(ob, self)
    schedule_count()


def on_wire(self, context):
    for ob in previewed(selected_meshes(context)):
        ob.show_wire = self.filo
        ob.show_all_edges = True


class M80RiduciSettings(bpy.types.PropertyGroup):
    metodo: EnumProperty(name="Metodo", update=on_change, items=(
        ('COLLAPSE', "Riduci (tiene UV e materiali)", "Toglie triangoli mantenendo forma, UV e materiali: auto, oggetti con texture"),
        ('PLANAR', "Superfici piane", "Unisce le facce quasi piane entro un angolo: pannelli, pavimenti, muri"),
        ('REMESH', "Retopologia (perde le UV)", "Rifà la superficie con triangoli tutti della stessa misura: oggetti chiusi, poi la texture va rifatta"),
    ))
    dettaglio: FloatProperty(name="Dettaglio", description="Quanti triangoli tenere: meno = triangoli più grandi",
                             default=50.0, min=0.5, max=100.0, subtype='PERCENTAGE', precision=1, update=on_change)
    minimo: IntProperty(name="Minimo per oggetto", description="Gli oggetti piccoli non scendono sotto questi triangoli",
                        default=150, min=0, max=100000, update=on_change)
    triangola: BoolProperty(name="Solo triangoli", description="Il risultato tutto in triangoli (come in Unreal)", default=True, update=on_change)
    simmetria: BoolProperty(name="Simmetria", description="Riduce in modo uguale le due metà (auto, personaggi)", default=False, update=on_change)
    asse: EnumProperty(name="Asse", items=(('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")), default='X', update=on_change)
    angolo: FloatProperty(name="Angolo", description="Facce entro questo angolo diventano una: più alto = triangoli più grandi",
                          default=5.0, min=0.1, max=45.0, update=on_change)
    voxel: FloatProperty(name="Misura triangoli (cm)", description="Lato dei triangoli della nuova superficie",
                         default=2.0, min=0.05, max=100.0, update=on_change)
    normali: BoolProperty(name="Normali pesate", description="Sistema l'ombreggiatura delle superfici ridotte (spigoli netti, facce lisce)",
                          default=True, update=on_change)
    mostra: BoolProperty(name="Mostra anteprima", description="Spento: torna a vedere l'originale per confrontare", default=True, update=on_change)
    filo: BoolProperty(name="Mostra triangoli", description="Il filo di ferro sulle mesh in anteprima", default=True, update=on_wire)
    copia: BoolProperty(name="Tieni copia degli originali", description="Applicando, gli originali restano nella collezione nascosta 'M80 Originali'", default=True)
    prima: IntProperty(default=0)
    dopo: IntProperty(default=0)
    oggetti: IntProperty(default=0)


class M80_OT_riduci_anteprima(bpy.types.Operator):
    bl_idname = "m80.riduci_anteprima"
    bl_label = "Anteprima"
    bl_description = "Mostra le mesh selezionate ridotte, dal vivo: muovi i cursori per cambiare"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(selected_meshes(context))

    def execute(self, context):
        s = context.scene.m80_riduci
        for ob in selected_meshes(context):
            if MOD not in ob.modifiers:
                ob["m80_tris"] = mesh_tris(ob.data)
            configure(ob, s)
            ob.show_wire = s.filo
            ob.show_all_edges = True
        schedule_count()
        return {'FINISHED'}


class M80_OT_riduci_dettaglio(bpy.types.Operator):
    bl_idname = "m80.riduci_dettaglio"
    bl_label = "Dettaglio"
    bl_description = "Imposta il dettaglio"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    valore: FloatProperty()

    def execute(self, context):
        context.scene.m80_riduci.dettaglio = self.valore
        return {'FINISHED'}


class M80_OT_riduci_applica(bpy.types.Operator):
    bl_idname = "m80.riduci_applica"
    bl_label = "Applica"
    bl_description = "Rende definitiva la riduzione sulle mesh selezionate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(previewed(selected_meshes(context)))

    def execute(self, context):
        s = context.scene.m80_riduci
        objs = previewed(selected_meshes(context))
        if s.copia:
            coll = bpy.data.collections.get(BACKUP)
            if coll is None:
                coll = bpy.data.collections.new(BACKUP)
                context.scene.collection.children.link(coll)
            for ob in objs:
                dup = ob.copy()
                dup.data = ob.data.copy()
                for name in (MOD, NRM):
                    if name in dup.modifiers:
                        dup.modifiers.remove(dup.modifiers[name])
                dup.show_wire = False
                dup.name = ob.name + " (originale)"
                coll.objects.link(dup)
            lc = context.view_layer.layer_collection.children.get(BACKUP)
            if lc:
                lc.exclude = True
        done = 0
        for ob in objs:
            if ob.data.users > 1:
                ob.data = ob.data.copy()           # shared mesh data cannot take an applied modifier
            with context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
                for name in (MOD, NRM):
                    if name in ob.modifiers:
                        bpy.ops.object.modifier_apply(modifier=name)
            ob.show_wire = False
            if "m80_tris" in ob:
                del ob["m80_tris"]
            done += 1
        schedule_count()
        self.report({'INFO'}, "Ridotte %d mesh" % done)
        return {'FINISHED'}


class M80_OT_riduci_annulla(bpy.types.Operator):
    bl_idname = "m80.riduci_annulla"
    bl_label = "Annulla"
    bl_description = "Toglie l'anteprima dalle mesh selezionate"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(previewed(selected_meshes(context)))

    def execute(self, context):
        for ob in previewed(selected_meshes(context)):
            for name in (MOD, NRM):
                if name in ob.modifiers:
                    ob.modifiers.remove(ob.modifiers[name])
            ob.show_wire = False
            if "m80_tris" in ob:
                del ob["m80_tris"]
        schedule_count()
        return {'FINISHED'}


def fmt(n):
    return "{:,}".format(n).replace(",", ".")


class M80_PT_riduci(bpy.types.Panel):
    bl_label = "Riduci triangoli"
    bl_idname = "M80_PT_riduci"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "M80"

    def draw(self, context):
        s = context.scene.m80_riduci
        lay = self.layout
        meshes = selected_meshes(context)
        if not meshes:
            lay.label(text="Seleziona una o più mesh", icon='INFO')
            return
        prev = previewed(meshes)
        lay.prop(s, "metodo", text="")
        col = lay.column(align=True)
        if s.metodo == 'COLLAPSE':
            col.prop(s, "dettaglio", slider=True)
            row = col.row(align=True)
            for v in (75, 50, 25, 10, 5):
                row.operator("m80.riduci_dettaglio", text="%d%%" % v).valore = v
            col.separator()
            col.prop(s, "minimo")
            col.prop(s, "triangola")
            row = col.row(align=True)
            row.prop(s, "simmetria")
            sub = row.row(align=True)
            sub.active = s.simmetria
            sub.prop(s, "asse", expand=True)
        elif s.metodo == 'PLANAR':
            col.prop(s, "angolo")
        else:
            col.prop(s, "voxel")
            box = col.box()
            box.label(text="Perde UV e materiali:", icon='ERROR')
            box.label(text="per oggetti chiusi, poi bake")
        lay.prop(s, "normali")

        box = lay.box()
        box.label(text="%d mesh selezionate" % s.oggetti if s.oggetti else "%d mesh selezionate" % len(meshes))
        if s.prima:
            pct = 100.0 * (s.dopo - s.prima) / s.prima
            box.label(text="Triangoli: %s  →  %s" % (fmt(s.prima), fmt(s.dopo)))
            box.label(text="Differenza: %+.0f%%" % pct)

        if not prev:
            lay.operator("m80.riduci_anteprima", icon='HIDE_OFF')
            return
        if len(prev) < len(meshes):
            lay.operator("m80.riduci_anteprima", text="Anteprima anche sulle altre", icon='ADD')
        row = lay.row(align=True)
        row.prop(s, "mostra", toggle=True, icon='HIDE_OFF' if s.mostra else 'HIDE_ON')
        row.prop(s, "filo", toggle=True, icon='MOD_WIREFRAME')
        lay.prop(s, "copia")
        row = lay.row(align=True)
        row.scale_y = 1.4
        row.operator("m80.riduci_applica", icon='CHECKMARK')
        row.operator("m80.riduci_annulla", icon='X')


CLASSES = (M80RiduciSettings, M80_OT_riduci_anteprima, M80_OT_riduci_dettaglio, M80_OT_riduci_applica,
           M80_OT_riduci_annulla, M80_PT_riduci)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.m80_riduci = PointerProperty(type=M80RiduciSettings)
    if on_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(on_depsgraph)


def unregister():
    if on_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph)
    del bpy.types.Scene.m80_riduci
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
