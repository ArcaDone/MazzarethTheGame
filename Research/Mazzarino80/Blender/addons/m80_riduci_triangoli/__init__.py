"""M80 Riduci triangoli: lowers the triangle count of the selected meshes with a live preview, then bakes the lost
detail into a normal map.

Sidebar (N) > M80 > Riduci triangoli. "Anteprima" puts a modifier on each selected mesh, so moving the sliders
reshapes them at once in the viewport (with their wireframe, to judge the triangles); "Mostra anteprima" flips back
to the original to compare; "Applica" bakes it in (keeping a copy of the originals in the hidden collection
"M80 Originali"); "Annulla" takes it off.
Methods:
  Riduci           Decimate / Collapse: keeps UVs, materials and the shape. Either a share of triangles kept
                   ("Dettaglio") or a total to reach ("Obiettivo"): the total is shared out among groups of parts found
                   by name (body, wheels, interior, lights, brakes, seals, underbody, glass), each with a priority, so
                   hidden parts give up more than the body. "Minimo per oggetto" spares small parts.
  Superfici piane  Decimate / Planar: merges faces that lie flat within an angle (panels, floors); UVs and
                   material borders are kept.
  Retopologia      Remesh / Voxel: a new even surface of triangles of the size asked; UVs and materials are lost,
                   for closed objects (rocks, sculptures) whose texture is baked again afterwards.
"Cuoci dettagli" (after Applica): every reduced mesh gets a new first UV map "M80_Bake" (all of them packed together
in one square), the original's surface is baked from its copy in "M80 Originali" into one tangent-space normal map
(saved as PNG), and the materials get it on their Normal input. The original UVs stay, second, for the textures; in
Unreal UV0 is then M80_Bake, whose tangents match the bake.
Built as a Blender extension (blender_manifest.toml): zip the folder and Install from Disk.
"""
import math
import os
import re
import tempfile
import time

import bpy
import numpy as np
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty

MOD = "M80 Riduci"
NRM = "M80 Normali"
BACKUP = "M80 Originali"
BAKE_UV = "M80_Bake"

# Groups of parts, found by the object's (or mesh's) name, first match wins; "m80_gruppo" on an object overrides it.
# Priority: how much of its triangles a group keeps compared with the body (1).
GROUPS = (
    ("interni", "Interni", r"interior|seat|steering|gauge|needle|headliner|dashboard|cagerace|_fuel_|_speed_|_tach_|sedil|volant|cruscott", 0.3),
    ("fari", "Fari e fanali", r"headlight|taillight|light|lamp|reflector|faro|fanal", 0.7),
    ("vetri", "Vetri", r"window|windshield|glass|vetr|parabrezza", 5.0),
    # Round: cut hard they turn polygonal at once (a 155's wheels needed 3 to keep the rims' holes).
    ("ruote", "Ruote", r"tire|tyre|wheel|rim_|_rim|gomm|ruot|cerchi", 3.0),
    ("freni", "Freni", r"caliper|rotor|brake|disc|disk|pinz|fren", 0.25),
    ("guarnizioni", "Guarnizioni", r"weatherstrip|rubber_trim|seal|guarnizion", 0.2),
    ("sotto", "Sotto e scarico", r"undercarriage|underbody|exhaust|chassis|scaric|sottoscocca", 0.25),
    ("carrozzeria", "Carrozzeria", r"", 1.0),
)
# Share of the baked texture per group (scale of their UV islands before packing): the body is seen up close and
# carries the livery, the interior is seen through the glass.
TEXEL = {"carrozzeria": 1.0, "fari": 1.0, "ruote": 0.8, "vetri": 0.4, "interni": 0.35, "freni": 0.4,
         "guarnizioni": 0.3, "sotto": 0.25}


def mesh_tris(mesh):
    n = len(mesh.polygons)
    if not n:
        return 0
    sides = np.empty(n, np.int32)
    mesh.polygons.foreach_get("loop_total", sides)
    return int(sides.sum()) - 2 * n


def group_of(ob):
    g = ob.get("m80_gruppo")
    if g and any(g == k for k, _, _, _ in GROUPS):
        return g
    name = (ob.name + " " + ob.data.name).lower()
    for key, _, pattern, _ in GROUPS:
        if not pattern or re.search(pattern, name):
            return key
    return "carrozzeria"


def selected_meshes(context):
    return [o for o in context.selected_objects if o.type == 'MESH']


def selected_in(vl):
    return [o for o in vl.objects if o.type == 'MESH' and o.select_get(view_layer=vl)]


def previewed(objs):
    return [o for o in objs if MOD in o.modifiers]


def base_tris(ob):
    return ob.get("m80_tris") or mesh_tris(ob.data)


def keep_last(ob):
    """The reduction after the object's own modifiers, the weighted normals after it."""
    for name in (MOD, NRM):
        i = ob.modifiers.find(name)
        if i >= 0:
            ob.modifiers.move(i, len(ob.modifiers) - 1)


def allocate(objs, s, target):
    """Ratios per object so the total comes to target: ratio = k x group priority (within the object's minimum and 1),
    k found by bisection."""
    items = []
    for ob in objs:
        b = base_tris(ob)
        if not b:
            continue
        w = max(getattr(s, "prio_" + group_of(ob)), 1e-3)
        items.append((ob, b, w, min(1.0, max(s.minimo / b, ob.get("m80_min_ratio", 0.0)))))
    if not items:
        return {}

    def ratios(k):
        return {ob: min(1.0, max(lo, k * w)) for ob, b, w, lo in items}

    def total(k):
        return sum(b * min(1.0, max(lo, k * w)) for ob, b, w, lo in items)

    lo_k, hi_k = 0.0, 1.0 / min(w for _, _, w, _ in items)
    if total(hi_k) <= target:
        return ratios(hi_k)
    for _ in range(40):
        mid = 0.5 * (lo_k + hi_k)
        if total(mid) > target:
            hi_k = mid
        else:
            lo_k = mid
    return ratios(lo_k)


def configure(ob, s, ratio=None):
    want = 'REMESH' if s.metodo == 'REMESH' else 'DECIMATE'
    m = ob.modifiers.get(MOD)
    if m and m.type != want:
        ob.modifiers.remove(m)
        m = None
    if m is None:
        m = ob.modifiers.new(MOD, want)
    base = base_tris(ob)
    if s.metodo == 'COLLAPSE':
        m.decimate_type = 'COLLAPSE'
        if ratio is None:
            ratio = max(s.dettaglio / 100.0, ob.get("m80_min_ratio", 0.0))
            if base:
                ratio = max(ratio, min(1.0, s.minimo / base))
        m.ratio = ratio
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
        sc = ob.matrix_world.to_scale()
        scale = max(abs(sc.x), abs(sc.y), abs(sc.z), 1e-6)
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


def by_target(s):
    return s.metodo == 'COLLAPSE' and s.modalita == 'TARGET'


def push(objs, s):
    """Settings onto the previewed meshes (the total shared out among them when aiming at a total)."""
    objs = previewed(objs)
    if by_target(s):
        r = allocate(objs, s, s.obiettivo * s.correzione)
        for ob in objs:
            configure(ob, s, r.get(ob, 1.0))
    else:
        for ob in objs:
            configure(ob, s)


# --- triangle count, refreshed a moment after a change (the modifiers are evaluated by then) ---

_pending = [False]
_last_sel = [None]
_steps = [0]
GSTATS = {}


def window_scene():
    wm = bpy.context.window_manager
    win = wm.windows[0] if wm and wm.windows else None
    return (win.scene, win.view_layer) if win else (bpy.context.scene, bpy.context.view_layer)


def local_bounds(mesh):
    n = len(mesh.vertices)
    if not n:
        return None
    co = np.empty(n * 3, np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    return co.min(0), co.max(0)


SPIKED = []


def spiked(ob, me):
    """A collapse gone wrong throws a corner out past the original's shape (a 155's roll cage stood 35 cm out of the
    roof): the reduced mesh reaching more than 1 cm (or 2% of its size) outside the original's box."""
    a, b = local_bounds(me), local_bounds(ob.data)
    if a is None or b is None:
        return False
    tol = max(0.01, 0.02 * float(np.linalg.norm(b[1] - b[0])))
    return float(max((b[0] - a[0]).max(), (a[1] - b[1]).max())) > tol


def measure(scene, vl):
    """Triangles of the selected meshes before and after (as seen now), per group too; SPIKED lists the meshes whose
    reduction broke their shape."""
    s = scene.m80_riduci
    vl.update()
    dg = vl.depsgraph
    before = after = objs = 0
    GSTATS.clear()
    SPIKED.clear()
    for ob in selected_in(vl):
        objs += 1
        b = mesh_tris(ob.data)
        a = b
        if MOD in ob.modifiers and ob.modifiers[MOD].show_viewport:
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            a = mesh_tris(me)
            if s.metodo == 'COLLAPSE' and ob.modifiers[MOD].ratio < 1.0 and spiked(ob, me):
                SPIKED.append(ob)
            ev.to_mesh_clear()
        before += b
        after += a
        g = GSTATS.setdefault(group_of(ob), [0, 0, 0])
        g[0] += b
        g[1] += a
        g[2] += 1
    s.prima, s.dopo, s.oggetti = before, after, objs


def off_target(s):
    return by_target(s) and s.dopo > 0 and s.prima > s.obiettivo and abs(s.dopo - s.obiettivo) > 0.02 * s.obiettivo


def correct(s):
    """The decimation never lands exactly on the ratio asked: aim again, scaled by what came out."""
    s.correzione = min(3.0, max(0.3, s.correzione * s.obiettivo / max(s.dopo, 1)))


def guard():
    """The meshes whose shape broke keep more of their triangles (twice as many, up to all) from now on."""
    for ob in SPIKED:
        r = ob.modifiers[MOD].ratio if MOD in ob.modifiers else 1.0
        ob["m80_min_ratio"] = min(1.0, max(r * 2.0, 0.02))
    return bool(SPIKED)


def settle(scene, vl, rounds=8):
    """Push, measure and correct until the total is within 2% and no shape is broken (used by the buttons and the
    tests)."""
    s = scene.m80_riduci
    for _ in range(rounds):
        push(selected_in(vl), s)
        measure(scene, vl)
        fixed = guard()
        if not off_target(s) and not fixed:
            break
        if off_target(s):
            correct(s)


def redraw():
    for w in bpy.context.window_manager.windows:
        for area in w.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def count_now():
    _pending[0] = False
    scene, vl = window_scene()
    if scene is None or vl is None:
        return None
    s = scene.m80_riduci
    measure(scene, vl)
    fixed = guard()
    if (off_target(s) or fixed) and _steps[0] < 6 and previewed(selected_in(vl)):
        _steps[0] += 1
        if off_target(s):
            correct(s)
        push(selected_in(vl), s)
        schedule_count(0.05)
    redraw()
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
    _steps[0] = 0
    push(selected_meshes(context), self)
    schedule_count()


def on_wire(self, context):
    for ob in previewed(selected_meshes(context)):
        ob.show_wire = self.filo
        ob.show_all_edges = True


def on_normal_strength(self, context):
    for m in bpy.data.materials:
        if m.use_nodes and m.node_tree:
            n = m.node_tree.nodes.get("M80 Normale")
            if n:
                n.inputs["Strength"].default_value = 1.0 if self.mostra_normali else 0.0


class M80RiduciSettings(bpy.types.PropertyGroup):
    metodo: EnumProperty(name="Metodo", update=on_change, items=(
        ('COLLAPSE', "Riduci (tiene UV e materiali)", "Toglie triangoli mantenendo forma, UV e materiali: auto, oggetti con texture"),
        ('PLANAR', "Superfici piane", "Unisce le facce quasi piane entro un angolo: pannelli, pavimenti, muri"),
        ('REMESH', "Retopologia (perde le UV)", "Rifà la superficie con triangoli tutti della stessa misura: oggetti chiusi, poi la texture va rifatta"),
    ))
    modalita: EnumProperty(name="Modalità", update=on_change, items=(
        ('PERC', "Dettaglio %", "La stessa percentuale di triangoli per tutte le mesh selezionate"),
        ('TARGET', "Obiettivo", "Un numero totale di triangoli, diviso tra i gruppi secondo la loro priorità"),
    ))
    dettaglio: FloatProperty(name="Dettaglio", description="Quanti triangoli tenere: meno = triangoli più grandi",
                             default=50.0, min=0.5, max=100.0, subtype='PERCENTAGE', precision=1, update=on_change)
    obiettivo: IntProperty(name="Triangoli totali", description="Quanti triangoli in tutto per le mesh selezionate",
                           default=28000, min=100, max=10000000, update=on_change)
    correzione: FloatProperty(default=1.0)
    minimo: IntProperty(name="Minimo per oggetto", description="Gli oggetti piccoli non scendono sotto questi triangoli",
                        default=60, min=0, max=100000, update=on_change)
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
    copia: BoolProperty(name="Tieni copia degli originali", description="Applicando, gli originali restano nella collezione nascosta 'M80 Originali' (servono per cuocere i dettagli)", default=True)
    gruppi_aperti: BoolProperty(name="Gruppi", default=True)
    # Baking.
    bake_size: EnumProperty(name="Texture", default='4096', items=(
        ('1024', "1024", ""), ('2048', "2048", ""), ('4096', "4096", ""), ('8192', "8192", "")))
    bake_dist: FloatProperty(name="Distanza (cm)", description="Quanto lontano dalla superficie ridotta cercare quella originale",
                             default=1.5, min=0.05, max=50.0)
    bake_nome: StringProperty(name="Nome", description="Nome della normal map (vuoto: quello dell'oggetto attivo)", default="")
    bake_cartella: StringProperty(name="Cartella", description="Dove salvare la normal map (vuoto: accanto al file .blend)", default="", subtype='DIR_PATH')
    mostra_normali: BoolProperty(name="Mostra normal map", description="Spento: le superfici senza la normal map, per confrontare",
                                 default=True, update=on_normal_strength)
    prima: IntProperty(default=0)
    dopo: IntProperty(default=0)
    oggetti: IntProperty(default=0)


for _key, _label, _pattern, _prio in GROUPS:
    M80RiduciSettings.__annotations__["prio_" + _key] = FloatProperty(
        name=_label, description="Priorità: quanti triangoli tiene rispetto alla carrozzeria (1)", default=_prio,
        min=0.01, max=10.0, update=on_change)


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
        settle(context.scene, context.view_layer)
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
                for key in ("m80_tris", "m80_originale"):
                    if key in dup:
                        del dup[key]
                coll.objects.link(dup)
                ob["m80_originale"] = dup.name
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
            for key in ("m80_tris", "m80_min_ratio"):
                if key in ob:
                    del ob[key]
            done += 1
        measure(context.scene, context.view_layer)
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
            for key in ("m80_tris", "m80_min_ratio"):
                if key in ob:
                    del ob[key]
        schedule_count()
        return {'FINISHED'}


# --- baking the original's detail into a normal map ---

def original_of(ob):
    name = ob.get("m80_originale")
    return bpy.data.objects.get(name) if name else None


def bakeable(objs):
    return [o for o in objs if original_of(o) is not None and MOD not in o.modifiers]


def uv_data(layer, n_loops):
    a = np.empty(n_loops * 2, np.float32)
    layer.uv.foreach_get("vector", a)
    return a


def bake_uv_first(me):
    """M80_Bake as the first UV map (Unreal's UV0, from which its tangents come); the old maps follow, unchanged,
    the first of them still the one the textures render with."""
    old = me.uv_layers.get(BAKE_UV)
    if old:
        me.uv_layers.remove(old)
    n = len(me.loops)
    render = next((l.name for l in me.uv_layers if l.active_render), None)
    keep = [(l.name, uv_data(l, n)) for l in me.uv_layers]
    for name, _ in keep:
        me.uv_layers.remove(me.uv_layers[name])
    me.uv_layers.new(name=BAKE_UV)
    for name, data in keep:
        l = me.uv_layers.new(name=name)
        l.uv.foreach_set("vector", data)
    if keep:
        me.uv_layers[render or keep[0][0]].active_render = True
    me.uv_layers.active = me.uv_layers[BAKE_UV]


def unwrap_together(context, targets):
    """One new UV map over all the targets, their islands packed together in one square (sized by real area)."""
    for ob in targets:
        bake_uv_first(ob.data)
    vl = context.view_layer
    for o in vl.objects:
        if o.select_get():
            o.select_set(False)
    for ob in targets:
        ob.select_set(True)
    vl.objects.active = targets[0]
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.reveal()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.001, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    # Islands sized by the group's share, then packed all together to fill the square (with the mesh selection
    # standing for the UV selection, else the packing leaves unselected islands where they are, small).
    for ob in targets:
        layer = ob.data.uv_layers[BAKE_UV]
        uv = uv_data(layer, len(ob.data.loops)) * TEXEL.get(group_of(ob), 1.0)
        layer.uv.foreach_set("vector", uv)
    ts = context.scene.tool_settings
    sync = ts.use_uv_select_sync
    ts.use_uv_select_sync = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    # The default margin method left the islands as smart_project placed them (15% of the square used); a margin as a
    # fraction of the square and concave shapes fill about half of it.
    bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION', margin=0.0015,
                            shape_method='CONCAVE')
    bpy.ops.object.mode_set(mode='OBJECT')
    ts.use_uv_select_sync = sync


def strip_m80_nodes(m):
    nt = m.node_tree
    for n in [n for n in nt.nodes if n.name.startswith("M80 ")]:
        nt.nodes.remove(n)


def materials_of(objs):
    mats = []
    for ob in objs:
        if not any(slot.material for slot in ob.material_slots):
            m = bpy.data.materials.get("M80 Senza materiale") or bpy.data.materials.new("M80 Senza materiale")
            m.use_nodes = True
            if ob.material_slots:
                ob.material_slots[0].material = m
            else:
                ob.data.materials.append(m)
        for slot in ob.material_slots:
            m = slot.material
            if m and m not in mats:
                if not m.use_nodes:
                    m.use_nodes = True
                mats.append(m)
    return mats


def connect_normal(m, img, strength):
    nt = m.node_tree
    tex = nt.nodes.get("M80 Bake")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.name = uv.label = "M80 UV"
    uv.uv_map = BAKE_UV
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.name = nm.label = "M80 Normale"
    nm.space = 'TANGENT'
    nm.uv_map = BAKE_UV
    nm.inputs["Strength"].default_value = strength
    x = min((n.location.x for n in nt.nodes), default=0) - 300
    uv.location, tex.location, nm.location = (x - 400, -600), (x - 200, -600), (x + 100, -600)
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], nm.inputs["Color"])
    for b in nt.nodes:
        if b.type != 'BSDF_PRINCIPLED':
            continue
        sock = b.inputs["Normal"]
        if sock.is_linked:
            src = sock.links[0].from_node
            # FBX imports often leave an empty Normal Map node there (no image): ours takes its place.
            if src.type == 'NORMAL_MAP' and not src.inputs["Color"].is_linked:
                nt.links.remove(sock.links[0])
        if not sock.is_linked:
            nt.links.new(nm.outputs["Normal"], sock)


class M80_OT_riduci_cuoci(bpy.types.Operator):
    bl_idname = "m80.riduci_cuoci"
    bl_label = "Cuoci dettagli"
    bl_description = ("Cuoce i dettagli delle mesh originali (in 'M80 Originali') in una normal map sulle mesh ridotte "
                      "selezionate: nuova UV 'M80_Bake' per prima, una texture per tutte, collegata ai materiali")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(bakeable(selected_meshes(context)))

    def execute(self, context):
        s = context.scene.m80_riduci
        targets = bakeable(selected_meshes(context))
        active = context.active_object if context.active_object in targets else targets[0]
        t0 = time.time()
        folder = bpy.path.abspath(s.bake_cartella) if s.bake_cartella else (bpy.path.abspath("//") if bpy.data.filepath else tempfile.gettempdir())
        img, failed = bake_normals(context, targets, targets, int(s.bake_size), s.bake_dist, s.bake_nome or active.name, folder,
                                   1.0 if s.mostra_normali else 0.0)
        for o in context.view_layer.objects:
            if o.select_get():
                o.select_set(False)
        for ob in targets:
            ob.select_set(True)
        context.view_layer.objects.active = active
        msg = "Normal map %s (%d mesh, %.0f s)" % (img.filepath_raw, len(targets), time.time() - t0)
        if failed:
            msg += "; non cotte: %d (vedi console)" % len(failed)
        self.report({'WARNING'} if failed else {'INFO'}, msg)
        return {'FINISHED'}


def bake_normals(context, objs, targets, size, dist_cm, name, folder, strength=1.0, unwrap=True):
    """objs: the meshes that share the new texture (unwrapped together into M80_Bake when unwrap); targets: those of
    them baked from their originals (the others keep a flat normal). Returns (image, failures)."""
    scene, vl = context.scene, context.view_layer
    for ob in objs:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
    mats = materials_of(objs)
    for m in mats:
        strip_m80_nodes(m)          # an earlier bake's normal map must not shade the originals being baked
    if unwrap:
        unwrap_together(context, objs)
    name = "M80_%s_Normal" % re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.generated_color = (0.5, 0.5, 1.0, 1.0)
    img.colorspace_settings.name = 'Non-Color'
    for m in mats:
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.name = n.label = "M80 Bake"
        n.image = img
        n.interpolation = 'Linear'
        m.node_tree.nodes.active = n
    lc = vl.layer_collection.children.get(BACKUP)
    was_excluded = lc.exclude if lc else False
    if lc:
        lc.exclude = False
    engine = scene.render.engine
    scene.render.engine = 'CYCLES'
    dist = dist_cm / 100.0 / (scene.unit_settings.scale_length or 1.0)
    margin = max(2, size // 1024)          # under half the gap between islands
    failed = []
    try:
        for i, ob in enumerate(targets):
            orig = original_of(ob)
            if orig is None:
                continue
            for o in vl.objects:
                if o.select_get():
                    o.select_set(False)
            orig.hide_set(False)
            orig.select_set(True)
            ob.select_set(True)
            vl.objects.active = ob
            try:
                bpy.ops.object.bake(type='NORMAL', use_selected_to_active=True, cage_extrusion=dist,
                                    max_ray_distance=dist * 2.0, margin=margin, use_clear=False,
                                    normal_space='TANGENT', target='IMAGE_TEXTURES')
            except RuntimeError as e:
                failed.append("%s: %s" % (ob.name, str(e).strip()))
            if i % 10 == 0:
                print("M80 cuoci %d/%d" % (i + 1, len(targets)))
    finally:
        scene.render.engine = engine
        if lc:
            lc.exclude = was_excluded
    for f in failed:
        print("M80 cuoci:", f)
    os.makedirs(folder, exist_ok=True)
    img.filepath_raw = os.path.join(folder, name + ".png")
    img.file_format = 'PNG'
    img.save()
    for m in mats:
        connect_normal(m, img, strength)
    return img, failed


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
            col.row(align=True).prop(s, "modalita", expand=True)
            if s.modalita == 'PERC':
                col.prop(s, "dettaglio", slider=True)
                row = col.row(align=True)
                for v in (75, 50, 25, 10, 5):
                    row.operator("m80.riduci_dettaglio", text="%d%%" % v).valore = v
            else:
                col.prop(s, "obiettivo")
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
        box.label(text="%d mesh selezionate" % (s.oggetti or len(meshes)))
        if s.prima:
            pct = 100.0 * (s.dopo - s.prima) / s.prima
            box.label(text="Triangoli: %s  →  %s" % (fmt(s.prima), fmt(s.dopo)))
            box.label(text="Differenza: %+.0f%%" % pct)
        kept = [o for o in prev if o.get("m80_min_ratio")]
        if kept:
            box.label(text="Forma protetta: %d mesh (più triangoli)" % len(kept), icon='MOD_DECIM')

        if by_target(s):
            gb = lay.box()
            gb.prop(s, "gruppi_aperti", icon='TRIA_DOWN' if s.gruppi_aperti else 'TRIA_RIGHT', emboss=False,
                    text="Priorità dei gruppi")
            if s.gruppi_aperti:
                for key, label, _, _ in GROUPS:
                    st = GSTATS.get(key)
                    if not st:
                        continue
                    r = gb.row(align=True)
                    r.prop(s, "prio_" + key, text=label)
                    r.label(text="%s → %s" % (fmt(st[0]), fmt(st[1])))

        if not prev:
            lay.operator("m80.riduci_anteprima", icon='HIDE_OFF')
        else:
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

        bk = lay.box()
        bk.label(text="Dettagli in normal map", icon='TEXTURE')
        if not bakeable(meshes):
            bk.label(text="Prima riduci e applica (con la copia)")
        c = bk.column(align=True)
        c.prop(s, "bake_size")
        c.prop(s, "bake_dist")
        c.prop(s, "bake_nome")
        c.prop(s, "bake_cartella")
        r = bk.row()
        r.scale_y = 1.3
        r.operator("m80.riduci_cuoci", icon='RENDER_STILL')
        bk.prop(s, "mostra_normali", toggle=True)


CLASSES = (M80RiduciSettings, M80_OT_riduci_anteprima, M80_OT_riduci_dettaglio, M80_OT_riduci_applica,
           M80_OT_riduci_annulla, M80_OT_riduci_cuoci, M80_PT_riduci)


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
