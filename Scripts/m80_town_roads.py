"""Roads painted on the landscape instead of road meshes (town map L_M80_Paese).

- M_M80_Landscape gets a paint layer "Strada" (Concrete_Pavers, LandscapeLayerSample): the old
  soil/rock slope mix stays everywhere else. The layer is a normal landscape paint layer: it can be
  painted or erased by hand in Landscape mode > Paint > "Strada".
- The layer is filled along every road spline (Mazzarino80/Strade_spline, width from "Larghezza").
- The road splines stay in the map as editable guides (no mesh, no collision): houses use them to
  find their street side, sidewalks and traffic can follow them. Re-run with M80_ROADS_CLEAR=0 to add
  strokes for new/edited splines without erasing hand painting.
- The old merged road mesh reference (M80_Strade) is deleted.
Env: M80_ROADS_MAP, M80_ROADS_CLEAR (default 1), M80_ROADS_EDGE_CM (default 70).
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = os.environ.get("M80_ROADS_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
TEX_DIR = "/Game/Mazzarino80/Terrain/Textures"
MAT = "/Game/Mazzarino80/Terrain/Materials/M_M80_Landscape"
LAYER_ASSET = "/Game/Mazzarino80/Terrain/Layers/LI_M80_Strada"
LAYER = "Strada"
CLEAR = os.environ.get("M80_ROADS_CLEAR", "1") == "1"
EDGE = float(os.environ.get("M80_ROADS_EDGE_CM", "70"))
OUT = ROOT / "Saved/Mazzarino80/Terrain/roads_report.json"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
REGISTRY = unreal.AssetRegistryHelpers.get_asset_registry()
SURFACES = {"Soil": "scmk3tp0", "Rock": "wgorbgd", "Pavers": "vl0fceco"}


def find_texture(surface_id, suffix):
    best = None
    for data in REGISTRY.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Texture2D")):
        name = str(data.asset_name)
        if surface_id in name and name.endswith(suffix) and not str(data.package_path).startswith(TEX_DIR):
            score = ("2K" in name, "4K" in name, "8K" not in name)
            if best is None or score > best[0]:
                best = (score, str(data.package_name))
    return best[1] if best else None


def texture(short, surface_id, suffix):
    target = "{}/T_M80_{}{}".format(TEX_DIR, short, suffix.replace("ORDp", "ORD"))
    if EAL.does_asset_exist(target):
        return unreal.load_asset(target)
    source = find_texture(surface_id, suffix)
    if not source:
        raise RuntimeError("Texture {}{} not found".format(surface_id, suffix))
    tex = EAL.duplicate_asset(source, target)
    unreal.M80EditorLibrary.downsize_texture_source(tex, 2048)
    unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 92 if suffix == "_N" else 88)
    if suffix == "_ORDp":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    EAL.save_asset(target, only_if_is_dirty=False)
    return tex


def sampler_for(t):
    """The sampler type must match the texture settings or the material does not compile."""
    T, S = unreal.TextureCompressionSettings, unreal.MaterialSamplerType
    if t.get_editor_property("virtual_texture_streaming"):
        t.set_editor_property("virtual_texture_streaming", False)  # landscape samplers here are not virtual
        EAL.save_loaded_asset(t)
    cs = t.get_editor_property("compression_settings")
    if cs == T.TC_NORMALMAP:
        return S.SAMPLERTYPE_NORMAL
    if cs == T.TC_MASKS:
        return S.SAMPLERTYPE_MASKS
    if cs == T.TC_GRAYSCALE:
        return S.SAMPLERTYPE_LINEAR_GRAYSCALE if not t.get_editor_property("srgb") else S.SAMPLERTYPE_GRAYSCALE
    return S.SAMPLERTYPE_COLOR if t.get_editor_property("srgb") else S.SAMPLERTYPE_LINEAR_COLOR


def build_material(tex):
    """Soil/rock by slope (as before) + the "Strada" paint layer with concrete pavers."""
    m = unreal.load_asset(MAT)
    MEL.delete_all_material_expressions(m)

    def node(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(a, ao, b, bi):
        if not MEL.connect_material_expressions(a, ao, b, bi):
            raise RuntimeError("link failed {} -> {}".format(ao, bi))

    def op(cls, a, ao, b, bo, x, y):
        e = node(cls, x, y)
        link(a, ao, e, "A")
        link(b, bo, e, "B")
        return e

    def lerp(a, ao, b, bo, t, to, x, y):
        e = node(unreal.MaterialExpressionLinearInterpolate, x, y)
        link(a, ao, e, "A")
        link(b, bo, e, "B")
        link(t, to, e, "Alpha")
        return e

    def scalar(name, v, x, y):
        return node(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=v)

    def sample(name, t, uv, x, y, _hint=None):
        e = node(unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, sampler_type=sampler_for(t), texture=t)
        e.set_editor_property("sampler_source", unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS)
        link(uv, "", e, "UVs")
        return e

    wp = node(unreal.MaterialExpressionWorldPosition, -1900, 0)
    xy = node(unreal.MaterialExpressionComponentMask, -1750, 0, r=True, g=True)
    link(wp, "", xy, "")
    uv = {k: op(unreal.MaterialExpressionDivide, xy, "", scalar(k + "TileCm", v, -1750, y), "", -1600, y)
          for k, v, y in (("Soil", 300.0, 100), ("Rock", 500.0, 250), ("Pavers", 240.0, 400))}
    C, N, M = (unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    s = {}
    y = -600
    for k in ("Soil", "Rock", "Pavers"):
        s[k] = (sample(k + "Color", tex[k]["_D"], uv[k], -1300, y, C), sample(k + "Normal", tex[k]["_N"], uv[k], -1300, y + 250, N),
                sample(k + "Masks", tex[k]["_ORDp"], uv[k], -1300, y + 500, M))
        y += 800
    vn = node(unreal.MaterialExpressionVertexNormalWS, -1300, 1900)
    nz = node(unreal.MaterialExpressionComponentMask, -1150, 1900, b=True)
    link(vn, "", nz, "")
    steep = op(unreal.MaterialExpressionSubtract, scalar("SlopeStart", 0.82, -1150, 2000), "", nz, "", -1000, 1900)
    steep = op(unreal.MaterialExpressionMultiply, steep, "", scalar("SlopeSharpness", 8.0, -1000, 2000), "", -850, 1900)
    slope = node(unreal.MaterialExpressionSaturate, -700, 1900)
    link(steep, "", slope, "")
    road = node(unreal.MaterialExpressionLandscapeLayerSample, -700, 2100, parameter_name=LAYER, preview_weight=0.0)
    # Tint the pavers a little towards warm dusty stone.
    tint = node(unreal.MaterialExpressionVectorParameter, -1000, 1500, parameter_name="PaversTint", default_value=unreal.LinearColor(1.0, 0.95, 0.86, 1))
    pav_col = op(unreal.MaterialExpressionMultiply, s["Pavers"][0], "RGB", tint, "", -850, 1500)
    MP = unreal.MaterialProperty
    outs = [
        (lerp(lerp(s["Soil"][0], "RGB", s["Rock"][0], "RGB", slope, "", -400, -200), "", pav_col, "", road, "", -150, -200), MP.MP_BASE_COLOR),
        (lerp(lerp(s["Soil"][1], "RGB", s["Rock"][1], "RGB", slope, "", -400, 100), "", s["Pavers"][1], "RGB", road, "", -150, 100), MP.MP_NORMAL),
        (lerp(lerp(s["Soil"][2], "G", s["Rock"][2], "G", slope, "", -400, 400), "", s["Pavers"][2], "G", road, "", -150, 400), MP.MP_ROUGHNESS),
        (lerp(lerp(s["Soil"][2], "R", s["Rock"][2], "R", slope, "", -400, 650), "", s["Pavers"][2], "R", road, "", -150, 650), MP.MP_AMBIENT_OCCLUSION),
    ]
    for e, prop in outs:
        MEL.connect_material_property(e, "", prop)
    MEL.recompile_material(m)
    EAL.save_asset(MAT, only_if_is_dirty=False)
    return m


def run():
    report = {"map": MAP, "clear": CLEAR}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    if not m80_seq.editor_world().get_path_name().startswith(MAP):
        raise RuntimeError("Expected {} open".format(MAP))
    yield 30
    tex = {k: {sfx: texture(k, sid, sfx) for sfx in ("_D", "_N", "_ORDp")} for k, sid in SURFACES.items()}
    build_material(tex)
    yield 60
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    landscape = next(a for a in actors if isinstance(a, unreal.Landscape))
    layer = unreal.M80EditorLibrary.ensure_landscape_layer(landscape, LAYER, LAYER_ASSET, True)
    if not layer:
        raise RuntimeError("Could not create the landscape layer")
    EAL.save_loaded_asset(layer, only_if_is_dirty=False)
    roads = [a for a in actors if a.get_class().get_name() == "MazzarinoRoadSpline"]
    splines, halves = [], []
    by_type = {}
    for r in roads:
        sp = r.get_component_by_class(unreal.SplineComponent)
        w = float(r.get_editor_property("width_meters"))
        kind = str(r.get_editor_property("osm_highway"))
        by_type[kind] = by_type.get(kind, 0) + 1
        splines.append(sp)
        halves.append(w * 50.0)
    report["roads"] = len(roads)
    report["roads_by_type"] = by_type
    report["painted_vertices"] = unreal.M80EditorLibrary.paint_landscape_layer_along_splines(landscape, layer, splines, halves, EDGE, CLEAR)
    yield 30
    # The splines stay as guides: no mesh, no collision.
    for r in roads:
        r.set_editor_property("road_mesh", None)
        r.set_editor_property("road_backing_mesh", None)
        r.set_editor_property("road_collision", False)
        r.rebuild_road()
    deleted = []
    for a in actors:
        if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label() == "M80_Strade":
            deleted.append(a.get_actor_label())
            a.destroy_actor()
    report["deleted"] = deleted
    yield 30
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
