"""Weapons for the GTA-like game (plan phase 1).

- Imports Saved/Mazzarino80/Weapons/M80_*.fbx (Research/Mazzarino80/Blender/m80_weapons.py) as
  /Game/Mazzarino80/Weapons/SM_M80_* with metal and wood/plastic materials (SOCKET_Muzzle -> socket).
- M_M80_Foro: bullet hole decal (procedural, no texture); M_M80_Bagliore: glowing disc under pickups;
  /Game/Mazzarino80/Vehicles/M_M80_Bruciato: burnt car shell.
- Sounds: Saved/Mazzarino80/Audio/M80_*.wav (Tools/Audio/m80_make_sounds.py) -> /Game/Mazzarino80/Audio.
- Retargets the ALS get-ups and landing roll from the ALS mannequin to the sample's UEFN mannequin (/Game/Mazzarino80/Player/Anim/A_M80_*), through a new retargeter
  RTG_M80_ALS_to_UEFN (UE4 mannequin IK rig -> UEFN IK rig, target aligned to the source pose).
  (The ALS aim sweeps are not used: on their own, without ALS' layering, the arms come out wrong; the
  aim is two-bone IK in M80OverlayAnim.cpp.)
Report: Saved/Mazzarino80/Weapons/setup_report.json.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Weapons"
DST = "/Game/Mazzarino80/Weapons"
ANIM = "/Game/Mazzarino80/Player/Anim"
OUT = SRC / "setup_report.json"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

ALS = "/Game/AdvancedLocomotionV4/CharacterAssets/MannequinSkeleton"
ALS_MESH = ALS + "/Meshes/Mannequin"
UEFN_MESH = "/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin"
RIG_SRC = "/Game/Characters/UE4_Mannequin/Rigs/IK_UE4_Mannequin_Retarget"
RIG_DST = "/Game/Characters/UEFN_Mannequin/Rigs/IK_UEFN_Mannequin"
RTG = ANIM + "/RTG_M80_ALS_to_UEFN"
ANIMS = {
    "A_M80_Rialzati_Schiena": ALS + "/AnimationExamples/Actions/ALS_CLF_GetUp_Back",
    "A_M80_Rialzati_Pancia": ALS + "/AnimationExamples/Actions/ALS_CLF_GetUp_Front",
    "A_M80_Capriola": ALS + "/AnimationExamples/Actions/ALS_N_LandRoll_F",
}
# Weapon -> (grip material, colour, roughness)
GRIPS = {
    "Revolver": ("Legno", (0.16, 0.07, 0.03), 0.55),
    "Beretta": ("Plastica", (0.012, 0.012, 0.012), 0.6),
    "Lupara": ("Legno", (0.16, 0.07, 0.03), 0.55),
    "Coltello": ("Corno", (0.06, 0.04, 0.03), 0.4),
    "Mazza": ("Frassino", (0.55, 0.38, 0.2), 0.5),
}


def simple_material(name, color, rough, metal=0.0, spec=0.5):
    path = DST + "/" + name
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, DST, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    for prop, val, y in ((unreal.MaterialProperty.MP_BASE_COLOR, color, 0), (unreal.MaterialProperty.MP_ROUGHNESS, rough, 200),
                         (unreal.MaterialProperty.MP_METALLIC, metal, 300), (unreal.MaterialProperty.MP_SPECULAR, spec, 400)):
        if isinstance(val, tuple):
            e = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, y)
            e.set_editor_property("constant", unreal.LinearColor(*val, 1))
        else:
            e = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, y)
            e.set_editor_property("r", val)
        MEL.connect_material_property(e, "", prop)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def hole_decal():
    """Bullet hole: dark core, chipped grey ring, from the decal UVs."""
    name = "M_M80_Foro"
    path = DST + "/" + name
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, DST, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    uv = MEL.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -900, 0)

    def custom(code, y):
        c = MEL.create_material_expression(m, unreal.MaterialExpressionCustom, -600, y)
        c.set_editor_property("code", code)
        c.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", "UV")
        c.set_editor_property("inputs", [ci])
        MEL.connect_material_expressions(uv, "", c, "UV")
        return c
    angle = "float2 d = UV - 0.5; float r = length(d) * 2.0; float a = atan2(d.y, d.x);"
    jag = "float j = 0.06 * sin(a * 7.0) + 0.04 * sin(a * 13.0 + 1.3);"
    opacity = custom(angle + jag + "float core = 1.0 - smoothstep(0.16, 0.2, r + j * 0.3);"
                     "float ring = (1.0 - smoothstep(0.28 + j, 0.8 + j, r)) * 0.6;"
                     "return saturate(max(core, ring));", 0)
    colour = custom(angle + jag + "float core = 1.0 - smoothstep(0.16, 0.22, r + j * 0.3);"
                    "return lerp(0.18, 0.015, core);", 250)
    MEL.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 400)
    r.set_editor_property("r", 0.9)
    MEL.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)


def glow_material():
    """Pickup disc: unlit, additive, soft edge (radial from the cylinder's UVs), colour parameter."""
    name = "M_M80_Bagliore"
    path = DST + "/" + name
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name, DST, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    col = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -900, 0)
    col.set_editor_property("parameter_name", "Colore")
    col.set_editor_property("default_value", unreal.LinearColor(1, 0.8, 0.3, 1))
    pos = MEL.create_material_expression(m, unreal.MaterialExpressionLocalPosition, -900, 300)
    c = MEL.create_material_expression(m, unreal.MaterialExpressionCustom, -600, 300)
    c.set_editor_property("code", "float r = length(P.xy) / 50.0; return saturate(1.0 - r) * saturate(1.0 - r) * 2.5;")
    c.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", "P")
    c.set_editor_property("inputs", [ci])
    MEL.connect_material_expressions(pos, "", c, "P")
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 100)
    MEL.connect_material_expressions(col, "", mul, "A")
    MEL.connect_material_expressions(c, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)


def burnt_material():
    global DST
    keep = DST
    DST = "/Game/Mazzarino80/Vehicles"
    simple_material("M_M80_Bruciato", (0.012, 0.011, 0.01), 0.92, 0.2, 0.3)
    DST = keep


def import_sounds(report):
    """Synthesised placeholder sounds (Tools/Audio/m80_make_sounds.py) -> /Game/Mazzarino80/Audio."""
    src = ROOT / "Saved/Mazzarino80/Audio"
    done = []
    for wav in sorted(src.glob("M80_*.wav")):
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(wav))
        t.set_editor_property("destination_path", "/Game/Mazzarino80/Audio")
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", True)
        TOOLS.import_asset_tasks([t])
        a = unreal.load_asset("/Game/Mazzarino80/Audio/" + wav.stem)
        if a and wav.stem == "M80_Motore":
            a.set_editor_property("looping", True)
            EAL.save_loaded_asset(a)
        done.append(wav.stem if a else wav.stem + " (failed)")
    report["sounds"] = done


def import_weapon(name):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.static_mesh_import_data.set_editor_property("combine_meshes", True)
    ui.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(SRC / ("M80_%s.fbx" % name)))
    t.set_editor_property("destination_path", DST)
    t.set_editor_property("destination_name", "SM_M80_" + name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", ui)
    TOOLS.import_asset_tasks([t])
    mesh = unreal.load_asset(DST + "/SM_M80_" + name)
    metal = simple_material("M_M80_Arma_Metallo", (0.03, 0.03, 0.032), 0.32, 1.0, 0.5)
    grip_name, grip_col, grip_rough = GRIPS[name]
    grip = simple_material("M_M80_Arma_" + grip_name, grip_col, grip_rough, 0.0, 0.4)
    mesh.set_material(0, metal)
    if len(mesh.static_materials) > 1:
        mesh.set_material(1, grip)
    if name == "Mazza":
        mesh.set_material(0, grip)
    EAL.save_loaded_asset(mesh)
    b = mesh.get_bounding_box()
    socks = ["Muzzle"] if mesh.find_socket("Muzzle") else []
    return {"box": [round(v, 1) for v in (b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z)], "sockets": [str(s) for s in socks],
            "materials": len(mesh.static_materials)}


def retargeter(report):
    if EAL.does_asset_exist(RTG):
        EAL.delete_asset(RTG)
    rtg = TOOLS.create_asset("RTG_M80_ALS_to_UEFN", ANIM, unreal.IKRetargeter, unreal.IKRetargetFactory())
    ctrl = unreal.IKRetargeterController.get_controller(rtg)
    ctrl.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, unreal.load_asset(RIG_SRC))
    ctrl.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, unreal.load_asset(RIG_DST))
    ctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, unreal.load_asset(ALS_MESH))
    ctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, unreal.load_asset(UEFN_MESH))
    ctrl.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    try:
        ctrl.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
        report["auto_align"] = True
    except Exception as e:  # noqa: BLE001
        report["auto_align"] = "error: %s" % e
    EAL.save_loaded_asset(rtg)
    return rtg


def retarget_anims(rtg, report):
    srcs = [unreal.load_asset(p) for p in ANIMS.values()]
    srcs_data = [unreal.EditorAssetLibrary.find_asset_data(p) for p in ANIMS.values()]
    for name in ANIMS:
        if EAL.does_asset_exist(ANIM + "/" + name):
            EAL.delete_asset(ANIM + "/" + name)
    out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(srcs_data, unreal.load_asset(ALS_MESH), unreal.load_asset(UEFN_MESH), rtg,
                                                                 "", "", "M80RT_", "", False)
    done = {}
    for name, src in zip(ANIMS, srcs):
        cand = [a for a in out if str(a.asset_name) == "M80RT_" + src.get_name()]
        if not cand:
            done[name] = "missing"
            continue
        old = str(cand[0].package_name)
        EAL.rename_asset(old, ANIM + "/" + name)
        a = unreal.load_asset(ANIM + "/" + name)
        EAL.save_loaded_asset(a)
        done[name] = {"length": round(a.get_play_length(), 3), "skeleton": a.get_editor_property("skeleton").get_name()}
    report["anims"] = done


def run():
    report = {"weapons": {}}
    for name in GRIPS:
        report["weapons"][name] = import_weapon(name)
        yield 2
    hole_decal()
    glow_material()
    burnt_material()
    import_sounds(report)
    yield 2
    rtg = retargeter(report)
    yield 5
    retarget_anims(rtg, report)
    yield 5
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
