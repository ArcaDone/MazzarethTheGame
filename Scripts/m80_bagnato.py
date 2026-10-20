"""Wet ground after rain for the floors of the town: the Atmosfera's "Bagnato" (0-1) writes the parameter "Bagnato" of
MPC_M80_Atmosfera, and the base materials of roads, sidewalks, steps and the landscape read it: on surfaces facing up
the colour darkens and the surface turns glossy (Lumen's reflections do the rest). Walls stay as they are.
Each material gets the nodes once (the base colour's last node is marked "M80 bagnato"); on materials built with
material attributes (the Megascans surfaces) the attributes are broken, wetted and made again. Saves only what it
changed.
Out: Saved/Mazzarino80/Memoria/bagnato.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bagnato.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Memoria"
MPC = "/Game/Mazzarino80/Sky/MPC_M80_Atmosfera"
MARK = "M80 bagnato"
# Floors of the town (their base materials are changed): roads, sidewalks and kerbs, steps, the landscape.
FLOORS = [
    "/Game/Mazzarino80/RoadSource/Migrated/Materials/Material",
    "/Game/Megascans/Surfaces/Hawaiian_Lava_Stone_tjnfdbkr/MI_Hawaiian_Lava_Stone_tjnfdbkr_2K",
    "/Game/Mazzarino80/Kit/Sidewalk/M_M80_Marciapiede",
    "/Game/Mazzarino80/Terrain/Materials/M_M80_Landscape",
    "/Game/Mazzarino80/Kit/Stairs/MI_M80_PietraLavica",
    "/Game/Mazzarino80/Kit/Stairs/MI_M80_Basolato",
    "/Game/Mazzarino80/Kit/Stairs/MI_M80_Lavica_secondaria",
    "/Game/Mazzarino80/Kit/Stairs/MI_M80_Cemento",
]
DARK = 0.55        # colour of a soaked floor, relative to dry
GLOSS = 0.06       # roughness of a soaked floor
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
MP = unreal.MaterialProperty


def ensure_mpc_param(mpc, name):
    params = list(mpc.get_editor_property("scalar_parameters"))
    if any(str(p.get_editor_property("parameter_name")) == name for p in params):
        return False
    p = unreal.CollectionScalarParameter()
    p.set_editor_property("parameter_name", name)
    p.set_editor_property("default_value", 0.0)
    params.append(p)
    mpc.set_editor_property("scalar_parameters", params)
    EAL.save_loaded_asset(mpc)
    return True


def input_of(m, prop):
    node = MEL.get_material_property_input_node(m, prop)
    if not node:
        return None, ""
    return node, str(MEL.get_material_property_input_node_output_name(m, prop) or "")


# Pins of Break/Make Material Attributes passed through unchanged.
ATTRIBUTES = ["Metallic", "Specular", "Anisotropy", "EmissiveColor", "Opacity", "OpacityMask", "Normal", "Tangent",
              "WorldPositionOffset", "SubsurfaceColor", "ClearCoat", "ClearCoatRoughness", "AmbientOcclusion", "Refraction",
              "PixelDepthOffset", "ShadingModel", "Displacement"] + ["CustomizedUV%d" % i for i in range(8)]


def add_wet(m, mpc):
    """Darkens the base colour and lowers the roughness where the surface faces up, by MPC Bagnato."""
    node = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)  # noqa: E731
    make = None
    if m.get_editor_property("use_material_attributes"):
        attrs, attrs_out = input_of(m, MP.MP_MATERIAL_ATTRIBUTES)
        if not attrs:
            return "no material attributes input"
        if str(attrs.get_editor_property("desc")) == MARK:
            return "already wet"
        brk = node(unreal.MaterialExpressionBreakMaterialAttributes, -1200, 600)
        MEL.connect_material_expressions(attrs, attrs_out, brk, "")
        make = node(unreal.MaterialExpressionMakeMaterialAttributes, -400, 600)
        make.set_editor_property("desc", MARK)
        passed = [a for a in ATTRIBUTES if MEL.connect_material_expressions(brk, a, make, a)]
        base, base_out, rough, rough_out = brk, "BaseColor", brk, "Roughness"
    else:
        base, base_out = input_of(m, MP.MP_BASE_COLOR)
        if not base:
            return "no base colour input"
        if str(base.get_editor_property("desc")) == MARK:
            return "already wet"
        rough, rough_out = input_of(m, MP.MP_ROUGHNESS)
    x, y = -2900, -200
    normal = node(unreal.MaterialExpressionVertexNormalWS, x, y)
    up_z = node(unreal.MaterialExpressionComponentMask, x + 180, y)
    for ch, on in (("r", False), ("g", False), ("b", True), ("a", False)):
        up_z.set_editor_property(ch, on)
    MEL.connect_material_expressions(normal, "", up_z, "")
    shifted = node(unreal.MaterialExpressionSubtract, x + 360, y)
    shifted.set_editor_property("const_b", 0.55)
    MEL.connect_material_expressions(up_z, "", shifted, "A")
    steep = node(unreal.MaterialExpressionMultiply, x + 520, y)
    steep.set_editor_property("const_b", 3.0)
    MEL.connect_material_expressions(shifted, "", steep, "A")
    up = node(unreal.MaterialExpressionSaturate, x + 680, y)
    MEL.connect_material_expressions(steep, "", up, "")
    wet_param = node(unreal.MaterialExpressionCollectionParameter, x + 520, y + 140)
    wet_param.set_editor_property("collection", mpc)
    wet_param.set_editor_property("parameter_name", "Bagnato")
    wet = node(unreal.MaterialExpressionMultiply, x + 840, y + 60)
    MEL.connect_material_expressions(up, "", wet, "A")
    MEL.connect_material_expressions(wet_param, "", wet, "B")
    darken = node(unreal.MaterialExpressionLinearInterpolate, x + 1000, y)
    darken.set_editor_property("const_a", 1.0)
    darken.set_editor_property("const_b", DARK)
    MEL.connect_material_expressions(wet, "", darken, "Alpha")
    colour = node(unreal.MaterialExpressionMultiply, x + 1160, y - 100)
    colour.set_editor_property("desc", MARK)
    MEL.connect_material_expressions(base, base_out, colour, "A")
    MEL.connect_material_expressions(darken, "", colour, "B")
    gloss = node(unreal.MaterialExpressionLinearInterpolate, x + 1160, y + 150)
    gloss.set_editor_property("const_a", 0.5)       # the roughness when nothing was connected
    gloss.set_editor_property("const_b", GLOSS)
    gloss.set_editor_property("desc", MARK)
    if rough:
        MEL.connect_material_expressions(rough, rough_out, gloss, "A")
    MEL.connect_material_expressions(wet, "", gloss, "Alpha")
    if make:
        MEL.connect_material_expressions(colour, "", make, "BaseColor")
        MEL.connect_material_expressions(gloss, "", make, "Roughness")
        MEL.connect_material_property(make, "", MP.MP_MATERIAL_ATTRIBUTES)
        result = "changed (attributes, passed through: %d)" % len(passed)
    else:
        MEL.connect_material_property(colour, "", MP.MP_BASE_COLOR)
        MEL.connect_material_property(gloss, "", MP.MP_ROUGHNESS)
        result = "changed"
    MEL.recompile_material(m)
    return result


def steps():
    report = {"materials": {}, "landscape_params": {}}
    mpc = unreal.load_asset(MPC)
    report["mpc_param_added"] = ensure_mpc_param(mpc, "Bagnato")
    done = set()
    for path in FLOORS:
        a = unreal.load_asset(path)
        if not a:
            report["materials"][path] = "not found"
            continue
        m = a.get_base_material() if isinstance(a, unreal.MaterialInstance) else a
        key = m.get_path_name()
        if key in done:
            continue
        done.add(key)
        try:
            result = add_wet(m, mpc)
        except Exception as e:  # noqa: BLE001
            result = "error: %s" % e
        report["materials"][key] = result
        if result.startswith("changed"):
            EAL.save_loaded_asset(m)
        yield 2
    land = unreal.load_asset("/Game/Mazzarino80/Terrain/Materials/M_M80_Landscape")
    report["landscape_params"] = {"scalar": [str(n) for n in MEL.get_scalar_parameter_names(land)],
                                  "vector": [str(n) for n in MEL.get_vector_parameter_names(land)],
                                  "texture": [str(n) for n in MEL.get_texture_parameter_names(land)]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "bagnato.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "bagnato_errore.txt"))
