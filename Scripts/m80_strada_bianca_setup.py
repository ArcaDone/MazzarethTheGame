"""Panelled road paving: white limestone slabs framed by bands of small lava setts (one band along the middle, one
across every few metres, one along each edge), as on Mazzarino's new avenues. The "Pietra bianca e lavica (riquadri)"
surface of the "Strada (Mazzarino)" actor uses it.

Textures: python Scripts/m80_stairs_textures.py lastre_bianche cubetti_lavici (Saved/Mazzarino80/Stairs/Textures),
imported into /Game/Mazzarino80/Kit/Stairs/Textures. Master M_M80_StradaBiancaLavica, instance MI_M80_StradaBiancaLavica:
  Larghezza fascia (m)     width of the lava bands (0.30)
  Fasce ai bordi (0-1)     the bands along the two edges
  Lastre / Cubetti ripetizione (m)   size of one repeat of the slab and sett textures
  Tinta lastre, Tinta fasce, Luminosita, Intensita normale
The road writes into UV1 its half width (X) and the distance between the bands across (Y), so the pattern follows any
width and length; UV0 is metres along (U) and across from the middle (V).
Test roads in /Game/Mazzarino80/Kit/Stairs/L_M80_ProvaScalinate, folder "Strade/Pietra bianca" (remade each run);
renders in Saved/Mazzarino80/Roads/Render/bianca_*.png.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_strada_bianca_setup.py -ForceLit
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
KIT = "/Game/Mazzarino80/Kit/Stairs"
MAP = KIT + "/L_M80_ProvaScalinate"
SRC = ROOT / "Saved/Mazzarino80/Stairs/Textures"
RENDER = ROOT / "Saved/Mazzarino80/Roads/Render"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
FOLDER = "Strade/Pietra bianca"
SETS = ("LastreBianche", "CubettiLavici")


def import_textures():
    tasks = []
    for name in SETS:
        for m in ("D", "N", "ORM"):
            t = unreal.AssetImportTask()
            t.filename = str(SRC / ("T_M80_%s_%s.png" % (name, m)))
            t.destination_path = KIT + "/Textures"
            t.replace_existing = True
            t.automated = True
            t.save = False
            tasks.append(t)
    TOOLS.import_asset_tasks(tasks)
    for name in SETS:
        n = unreal.load_asset("%s/Textures/T_M80_%s_N" % (KIT, name))
        n.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        n.set_editor_property("srgb", False)
        n.set_editor_property("flip_green_channel", True)          # made OpenGL-style
        o = unreal.load_asset("%s/Textures/T_M80_%s_ORM" % (KIT, name))
        o.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        o.set_editor_property("srgb", False)
        for t in (n, o, unreal.load_asset("%s/Textures/T_M80_%s_D" % (KIT, name))):
            unreal.EditorAssetLibrary.save_loaded_asset(t)


def new_material(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)
        return m
    return TOOLS.create_asset(path.rsplit("/", 1)[1], path.rsplit("/", 1)[0], unreal.Material, unreal.MaterialFactoryNew())


def node(m, cls, x, y, **props):
    e = MEL.create_material_expression(m, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def scalar(m, x, y, name, value, group="Riquadri"):
    return node(m, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value, group=group)


def op(m, cls, x, y, a, b, a_out="", b_out=""):
    """Binary node fed by a and b (expressions or constants)."""
    e = node(m, cls, x, y)
    for pin, src, out in (("A", a, a_out), ("B", b, b_out)):
        if isinstance(src, (int, float)):
            e.set_editor_property("const_" + pin.lower(), float(src))
        else:
            MEL.connect_material_expressions(src, out, e, pin)
    return e


def one(m, cls, x, y, src, out=""):
    """Node with a single input."""
    e = node(m, cls, x, y)
    MEL.connect_material_expressions(src, out, e, "")
    return e


def lerp(m, x, y, a, b, alpha, a_out="", b_out=""):
    e = node(m, unreal.MaterialExpressionLinearInterpolate, x, y)
    MEL.connect_material_expressions(a, a_out, e, "A")
    MEL.connect_material_expressions(b, b_out, e, "B")
    MEL.connect_material_expressions(alpha, "", e, "Alpha")
    return e


def append(m, x, y, a, b):
    e = node(m, unreal.MaterialExpressionAppendVector, x, y)
    MEL.connect_material_expressions(a, "", e, "A")
    MEL.connect_material_expressions(b, "", e, "B")
    return e


def master():
    m = new_material(KIT + "/M_M80_StradaBiancaLavica")
    E = unreal
    st = unreal.MaterialSamplerType
    tc0 = node(m, E.MaterialExpressionTextureCoordinate, -3200, 0, coordinate_index=0)
    tc1 = node(m, E.MaterialExpressionTextureCoordinate, -3200, 300, coordinate_index=1)
    u = node(m, E.MaterialExpressionComponentMask, -3000, -50, r=True, g=False, b=False, a=False)
    MEL.connect_material_expressions(tc0, "", u, "")
    v = node(m, E.MaterialExpressionComponentMask, -3000, 50, r=False, g=True, b=False, a=False)
    MEL.connect_material_expressions(tc0, "", v, "")
    hw = node(m, E.MaterialExpressionComponentMask, -3000, 250, r=True, g=False, b=False, a=False)
    MEL.connect_material_expressions(tc1, "", hw, "")
    pl = node(m, E.MaterialExpressionComponentMask, -3000, 350, r=False, g=True, b=False, a=False)
    MEL.connect_material_expressions(tc1, "", pl, "")
    a = one(m, E.MaterialExpressionAbs, -2800, 50, v)                       # metres from the middle
    bw = scalar(m, -3000, 500, "Larghezza fascia (m)", 0.30)
    hb = op(m, E.MaterialExpressionMultiply, -2800, 500, bw, 0.5)
    sharp = 250.0                                                           # a 4 mm soft edge, no shimmering line

    # Bands across: every panel length along the road.
    q = op(m, E.MaterialExpressionDivide, -2800, -50, u, pl)
    uu = op(m, E.MaterialExpressionMultiply, -2450, -50, one(m, E.MaterialExpressionFrac, -2600, -50, q), pl)
    d_across = op(m, E.MaterialExpressionMin, -2250, -50, uu, op(m, E.MaterialExpressionSubtract, -2450, 50, pl, uu))
    m_across = one(m, E.MaterialExpressionSaturate, -1850, -50,
                   op(m, E.MaterialExpressionMultiply, -2000, -50, op(m, E.MaterialExpressionSubtract, -2100, -50, hb, d_across), sharp))
    # The band along the middle.
    m_mid = one(m, E.MaterialExpressionSaturate, -1850, 150,
                op(m, E.MaterialExpressionMultiply, -2000, 150, op(m, E.MaterialExpressionSubtract, -2100, 150, hb, a), sharp))
    # The bands along the edges: a full band width inside each edge.
    to_edge = op(m, E.MaterialExpressionSubtract, -2450, 300, hw, a)
    m_edge = one(m, E.MaterialExpressionSaturate, -1850, 300,
                 op(m, E.MaterialExpressionMultiply, -2000, 300, op(m, E.MaterialExpressionSubtract, -2100, 300, bw, to_edge), sharp))
    m_edge = op(m, E.MaterialExpressionMultiply, -1700, 300, m_edge, scalar(m, -1900, 420, "Fasce ai bordi", 1.0))
    mask = op(m, E.MaterialExpressionMax, -1500, 100, m_across, op(m, E.MaterialExpressionMax, -1650, 200, m_mid, m_edge))

    # Slabs: courses start at the edge of the band across, joints at the edge of the band along the middle; every
    # panel shifted across so they do not repeat.
    srep = scalar(m, -2600, 650, "Lastre ripetizione (m)", 1.2, "Texture")
    shift = one(m, E.MaterialExpressionFrac, -2250, 750,
                op(m, E.MaterialExpressionMultiply, -2400, 750, one(m, E.MaterialExpressionFloor, -2600, 750, q), 0.618))
    sx = op(m, E.MaterialExpressionAdd, -2050, 600,
            op(m, E.MaterialExpressionDivide, -2250, 600, op(m, E.MaterialExpressionSubtract, -2400, 600, a, hb), srep), shift)
    sy = op(m, E.MaterialExpressionDivide, -2250, 680, op(m, E.MaterialExpressionSubtract, -2400, 680, uu, hb), srep)
    slab_uv = append(m, -1850, 640, sx, sy)
    lava_uv = op(m, E.MaterialExpressionDivide, -1850, 900, tc0, scalar(m, -2050, 950, "Cubetti ripetizione (m)", 1.0, "Texture"))

    samp = {}
    for i, (name, uv) in enumerate((("Lastre", slab_uv), ("Cubetti", lava_uv))):
        tex = SETS[i]
        for j, (k, s) in enumerate((("D", st.SAMPLERTYPE_COLOR), ("N", st.SAMPLERTYPE_NORMAL), ("ORM", st.SAMPLERTYPE_MASKS))):
            e = node(m, E.MaterialExpressionTextureSampleParameter2D, -1450, -600 + (i * 3 + j) * 260,
                     parameter_name="%s %s" % (name, k), texture=unreal.load_asset("%s/Textures/T_M80_%s_%s" % (KIT, tex, k)),
                     sampler_type=s, group="Texture")
            MEL.connect_material_expressions(uv, "", e, "UVs")
            samp[name + k] = e

    t_slab = node(m, E.MaterialExpressionVectorParameter, -1150, -700, parameter_name="Tinta lastre",
                  default_value=unreal.LinearColor(1, 1, 1, 1), group="Colore")
    t_lava = node(m, E.MaterialExpressionVectorParameter, -1150, -500, parameter_name="Tinta fasce",
                  default_value=unreal.LinearColor(1, 1, 1, 1), group="Colore")
    c_slab = op(m, E.MaterialExpressionMultiply, -900, -650, samp["LastreD"], t_slab, "RGB")
    c_lava = op(m, E.MaterialExpressionMultiply, -900, -450, samp["CubettiD"], t_lava, "RGB")
    col = op(m, E.MaterialExpressionMultiply, -500, -550, lerp(m, -700, -550, c_slab, c_lava, mask),
             scalar(m, -700, -400, "Luminosita", 1.0, "Colore"))
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)

    n = lerp(m, -700, -150, samp["LastreN"], samp["CubettiN"], mask, "RGB", "RGB")
    flat = node(m, E.MaterialExpressionConstant3Vector, -700, 0, constant=unreal.LinearColor(0, 0, 1, 1))
    n2 = lerp(m, -500, -100, flat, n, scalar(m, -700, 80, "Intensita normale", 1.0, "Colore"))
    MEL.connect_material_property(n2, "", unreal.MaterialProperty.MP_NORMAL)

    orm = lerp(m, -700, 250, samp["LastreORM"], samp["CubettiORM"], mask, "RGB", "RGB")
    rough = node(m, E.MaterialExpressionComponentMask, -500, 300, r=False, g=True, b=False, a=False)
    MEL.connect_material_expressions(orm, "", rough, "")
    ao = node(m, E.MaterialExpressionComponentMask, -500, 400, r=True, g=False, b=False, a=False)
    MEL.connect_material_expressions(orm, "", ao, "")
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)

    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m, False)
    return m


def instance(parent):
    path = KIT + "/MI_M80_StradaBiancaLavica"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = TOOLS.create_asset("MI_M80_StradaBiancaLavica", KIT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    unreal.EditorAssetLibrary.save_loaded_asset(mi, False)


def road(label, points, **props):
    a = EAS.spawn_actor_from_class(unreal.M80Road, unreal.Vector(*points[0]))
    a.set_actor_label(label)
    a.set_folder_path(FOLDER)
    path = a.get_component_by_class(unreal.SplineComponent)
    path.set_spline_points([unreal.Vector(*p) for p in points], unreal.SplineCoordinateSpace.WORLD, True)
    for k, v in props.items():
        a.set_editor_property(k, v)
    a.rebuild()
    unreal.log("ROAD %s: %d righe" % (label, a.get_editor_property("piece_count")))
    return a


def build_roads():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    for a in EAS.get_all_level_actors():
        if str(a.get_folder_path()).startswith(FOLDER):
            a.destroy_actor()
    ground = unreal.load_asset("/Game/Mazzarino80/Vehicles/M_M80_ProvaGuida_Suolo") or unreal.load_asset(KIT + "/MI_M80_Cemento")
    g = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-500, -7900, -100))
    g.set_actor_label("Piano_pietra_bianca")
    g.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
    g.set_actor_scale3d(unreal.Vector(64, 36, 2))
    g.static_mesh_component.set_material(0, ground)
    g.set_folder_path(FOLDER + "/Terreno")
    S = unreal.M80RoadSurface
    # 4. Straight, 5.5 m wide (as the avenue in the photos); 5. a bend, 4.5 m, panels every 3 m.
    road("4_Pietra_bianca_lavica", [(-3200, -6900, 0), (2400, -6900, 0)], surface=S.WHITE_LAVA, width_cm=550)
    road("5_Pietra_bianca_curva", [(-3200, -8800, 0), (-1000, -8900, 0), (900, -8400, 0), (2200, -7700, 0)],
         surface=S.WHITE_LAVA, width_cm=450, panel_length_cm=300)


VIEWS = {
    "bianca_panoramica": ((-4200, -5200, 900), (0, -7600, 0)),
    "bianca_lungo_strada": ((-3600, -6900, 170), (0, -6900, 0)),
    "bianca_dettaglio": ((-1500, -6550, 160), (-800, -6950, 0)),
    "bianca_dall_alto": ((-700, -6900, 700), (-690, -6900, 0)),
    "bianca_curva": ((-2200, -10200, 600), (500, -8500, 0)),
}


def views():
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    for name, (eye, target) in VIEWS.items():
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        cap.capture(unreal.Vector(*eye), rot, RENDER / ("%s.png" % name))
        yield 2
    cap.destroy()


def steps():
    import_textures()
    yield 5
    instance(master())
    yield 5
    build_roads()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 600
    for _ in views():
        yield 2
    yield 200
    for _ in views():
        yield 2


m80_seq.Sequencer(steps(), log_file=str(ROOT / "Saved/Mazzarino80/Roads/bianca_error.txt"))
