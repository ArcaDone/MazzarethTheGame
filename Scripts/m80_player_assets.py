"""Player and HUD assets (GTA-like game, step 17):
- /Game/Mazzarino80/Player/A_M80_Seduto_Guida: driving pose for the UEFN mannequin skeleton
  (Research/Mazzarino80/Blender/m80_sit_pose.py), played as a slot montage while in a car.
- /Game/Mazzarino80/UI/T_M80_Mappa: town map (Tools/Map/m80_make_map.py) and M_M80_Radar, the UI
  material that draws it as a rotating, rounded GTA-style radar (also used for the full map).
Report with the clothing material parameters: Saved/Mazzarino80/Player/assets_report.json.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Player/assets_report.json"
PLAYER = "/Game/Mazzarino80/Player"
UI = "/Game/Mazzarino80/UI"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SKELETON = "/Game/Characters/UEFN_Mannequin/Meshes/SK_UEFN_Mannequin"


def import_task(filename, dest, name, options=None):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(filename))
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    if options:
        t.set_editor_property("options", options)
    TOOLS.import_asset_tasks([t])
    return t.get_editor_property("imported_object_paths")


def import_anim():
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", False)
    ui.set_editor_property("import_animations", True)
    ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("skeleton", unreal.load_asset(SKELETON))
    ui.anim_sequence_import_data.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    ui.anim_sequence_import_data.set_editor_property("remove_redundant_keys", False)
    return import_task(ROOT / "Saved/Mazzarino80/Player/M80_Seduto_Guida.fbx", PLAYER, "A_M80_Seduto_Guida", ui)


def radar_material(tex):
    path = UI + "/M_M80_Radar"
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset("M_M80_Radar", UI, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_UI)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)

    def node(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e
    uv = node(unreal.MaterialExpressionTextureCoordinate, -1200, 0)
    center = node(unreal.MaterialExpressionVectorParameter, -1200, 150, parameter_name="Center", default_value=unreal.LinearColor(0.5, 0.5, 0, 0))
    zoom = node(unreal.MaterialExpressionScalarParameter, -1200, 300, parameter_name="Zoom", default_value=0.03)
    angle = node(unreal.MaterialExpressionScalarParameter, -1200, 400, parameter_name="Angle", default_value=0.0)
    aspect = node(unreal.MaterialExpressionScalarParameter, -1200, 500, parameter_name="Aspect", default_value=1.6)
    corner = node(unreal.MaterialExpressionScalarParameter, -1200, 600, parameter_name="Corner", default_value=0.18)
    opacity_p = node(unreal.MaterialExpressionScalarParameter, -1200, 700, parameter_name="Opacity", default_value=0.92)
    texobj = node(unreal.MaterialExpressionTextureObjectParameter, -1200, -200, parameter_name="Map", texture=tex)

    def custom(code, out_type, inputs, x, y):
        c = node(unreal.MaterialExpressionCustom, x, y, code=code, output_type=out_type)
        ins = []
        for n, _ in inputs:
            ci = unreal.CustomInput()
            ci.set_editor_property("input_name", n)
            ins.append(ci)
        c.set_editor_property("inputs", ins)
        for i, (n, src) in enumerate(inputs):
            MEL.connect_material_expressions(src, "", c, n)
        return c
    shape = node(unreal.MaterialExpressionScalarParameter, -1200, 800, parameter_name="Shape", default_value=0.0)
    # Shape 0: round radar fading out towards the rim (GTA style). Shape 1: rounded rectangle (full map).
    color_code = """
float2 s = (UV - 0.5) * 2.0; s.x *= Aspect;
float sa = sin(Angle), ca = cos(Angle);
float2 r = float2(s.x * ca - s.y * sa, s.x * sa + s.y * ca);
float2 m = Center.xy + r * Zoom;
float3 c = Texture2DSample(Map, MapSampler, saturate(m)).rgb;
float rad = length(s);
c *= lerp(1.0, lerp(1.0, 0.55, smoothstep(0.55, 1.0, rad)), 1.0 - Shape);
return c;
"""
    alpha_code = """
float2 s = (UV - 0.5) * 2.0; s.x *= Aspect;
float circle = 1.0 - smoothstep(0.72, 1.0, length(s));
float2 q = abs(s) - float2(Aspect, 1.0) + Corner;
float dist = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - Corner;
float rect = 1.0 - smoothstep(-0.015, 0.0, dist);
return Opacity * lerp(circle, rect, Shape);
"""
    ins = [("UV", uv), ("Center", center), ("Zoom", zoom), ("Angle", angle), ("Aspect", aspect), ("Shape", shape), ("Map", texobj)]
    col = custom(color_code, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ins, -700, 0)
    alp = custom(alpha_code, unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                 [("UV", uv), ("Aspect", aspect), ("Corner", corner), ("Opacity", opacity_p), ("Shape", shape)], -700, 400)
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(alp, "", unreal.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def params(mi):
    out = {"parent": mi.get_base_material().get_path_name()}
    for kind, names_fn, get_fn in (("scalar", MEL.get_scalar_parameter_names, MEL.get_material_instance_scalar_parameter_value),
                                   ("vector", MEL.get_vector_parameter_names, MEL.get_material_instance_vector_parameter_value),
                                   ("texture", MEL.get_texture_parameter_names, MEL.get_material_instance_texture_parameter_value)):
        vals = {}
        for n in names_fn(mi):
            v = get_fn(mi, n)
            vals[str(n)] = v.get_path_name() if hasattr(v, "get_path_name") else str(v)
        out[kind] = vals
    return out


def run():
    report = {"anim": [str(p) for p in import_anim()]}
    yield 5
    tex_paths = import_task(ROOT / "Research/Mazzarino80/Map/T_M80_Mappa.png", UI, "T_M80_Mappa")
    tex = unreal.load_asset(UI + "/T_M80_Mappa")
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property("address_x", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("address_y", unreal.TextureAddress.TA_CLAMP)
    tex.set_editor_property("never_stream", True)
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("virtual_texture_streaming", False)  # the radar's Custom node needs a plain Texture2D
    unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
    EAL.save_loaded_asset(tex)
    report["map"] = [str(p) for p in tex_paths]
    yield 5
    radar_material(tex)
    for p in ["/Game/MetaHumans/Kellan/Shared/Materials/MI_Fabric_Torso_Simplified", "/Game/MetaHumans/Kellan/Shared/Materials/MI_Fabric_Legs_Simplified",
              "/Game/MetaHumans/Kellan/Shared/Materials/MI_Fabric_Feet_Simplified"]:
        report[p] = params(unreal.load_asset(p))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
