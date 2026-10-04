"""Replaces the static-mesh terrain with an editable Landscape in the town map.

Creates /Game/Mazzarino80/Houses/Maps/L_M80_Paese (copy of Mazzarino80_Panoramica) on
first run, builds a Landscape that reproduces the terrain mesh (1 m quads), gives it a
simple slope-based material (soil on flat ground, rock on steep slopes) and hides the
old terrain mesh, keeping it in the map for reference.

Env: M80_LANDSCAPE_QUAD_CM (default 100), M80_LANDSCAPE_MAX_KM (default 3.0).
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SOURCE_MAP = "/Game/Levels/Mazzarino80_Panoramica"
MAP = "/Game/Mazzarino80/Houses/Maps/L_M80_Paese"
TERRAIN_MESH = "M80_Terreno"
TEX_DIR = "/Game/Mazzarino80/Terrain/Textures"
MAT_DIR = "/Game/Mazzarino80/Terrain/Materials"
OUT = ROOT / "Saved/Mazzarino80/Terrain/landscape_report.json"
QUAD = float(os.environ.get("M80_LANDSCAPE_QUAD_CM", "100"))
MAX_KM = float(os.environ.get("M80_LANDSCAPE_MAX_KM", "3.0"))
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REGISTRY = unreal.AssetRegistryHelpers.get_asset_registry()
SURFACES = {"Soil": "scmk3tp0", "Rock": "wgorbgd"}


def prepare_map():
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
        if not unreal.EditorLoadingAndSavingUtils.save_map(m80_seq.editor_world(), MAP):
            raise RuntimeError("Could not save " + MAP)
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    opened = m80_seq.editor_world().get_path_name()
    if not opened.startswith(MAP):
        raise RuntimeError("Expected {} to be open, got {}".format(MAP, opened))


def find_texture(surface_id, suffix):
    best = None
    for data in REGISTRY.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Texture2D")):
        name = str(data.asset_name)
        if surface_id in name and name.endswith(suffix) and not str(data.package_path).startswith(TEX_DIR):
            score = ("2K" in name, "4K" in name, "8K" not in name)
            if best is None or score > best[0]:
                best = (score, str(data.package_name))
    return best[1] if best else None


def copy_texture(short, surface_id, suffix):
    target = "{}/T_M80_{}{}".format(TEX_DIR, short, suffix.replace("ORDp", "ORD"))
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        return unreal.load_asset(target)
    source = find_texture(surface_id, suffix)
    if not source:
        return None
    tex = unreal.EditorAssetLibrary.duplicate_asset(source, target)
    unreal.M80EditorLibrary.downsize_texture_source(tex, 2048)
    unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 92 if suffix == "_N" else 88)
    unreal.EditorAssetLibrary.save_asset(target, only_if_is_dirty=False)
    unreal.SystemLibrary.collect_garbage()
    return tex


def build_material(tex):
    path = MAT_DIR + "/M_M80_Landscape"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    m = TOOLS.create_asset("M_M80_Landscape", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())

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

    def sample(name, t, uv, x, y, sampler):
        e = node(unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, sampler_type=sampler)
        if t:
            e.set_editor_property("texture", t)
        link(uv, "", e, "UVs")
        return e

    # World-aligned UVs in metres: no stretching on slopes seen from the street.
    wp = node(unreal.MaterialExpressionWorldPosition, -1600, 0)
    xy = node(unreal.MaterialExpressionComponentMask, -1450, 0, r=True, g=True)
    link(wp, "", xy, "")
    soil_uv = op(unreal.MaterialExpressionDivide, xy, "", scalar("SoilTileCm", 300.0, -1450, 100), "", -1300, 0)
    rock_uv = op(unreal.MaterialExpressionDivide, xy, "", scalar("RockTileCm", 500.0, -1450, 250), "", -1300, 250)
    C, N, L = (unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    sd = sample("SoilColor", tex["Soil"]["_D"], soil_uv, -1100, -300, C)
    sn = sample("SoilNormal", tex["Soil"]["_N"], soil_uv, -1100, -50, N)
    sm = sample("SoilMasks", tex["Soil"]["_ORDp"], soil_uv, -1100, 200, L)
    rd = sample("RockColor", tex["Rock"]["_D"], rock_uv, -1100, 450, C)
    rn = sample("RockNormal", tex["Rock"]["_N"], rock_uv, -1100, 700, N)
    rm = sample("RockMasks", tex["Rock"]["_ORDp"], rock_uv, -1100, 950, L)
    # Rock where the ground is steep: world normal Z below ~cos(35 deg).
    vn = node(unreal.MaterialExpressionVertexNormalWS, -1100, 1200)
    nz = node(unreal.MaterialExpressionComponentMask, -950, 1200, b=True)
    link(vn, "", nz, "")
    steep = op(unreal.MaterialExpressionSubtract, scalar("SlopeStart", 0.82, -950, 1300), "", nz, "", -800, 1200)
    steep = op(unreal.MaterialExpressionMultiply, steep, "", scalar("SlopeSharpness", 8.0, -800, 1300), "", -650, 1200)
    mask = node(unreal.MaterialExpressionSaturate, -500, 1200)
    link(steep, "", mask, "")
    MP = unreal.MaterialProperty
    MEL.connect_material_property(lerp(sd, "RGB", rd, "RGB", mask, "", -300, -100), "", MP.MP_BASE_COLOR)
    MEL.connect_material_property(lerp(sn, "RGB", rn, "RGB", mask, "", -300, 200), "", MP.MP_NORMAL)
    MEL.connect_material_property(lerp(sm, "G", rm, "G", mask, "", -300, 450), "", MP.MP_ROUGHNESS)
    MEL.connect_material_property(lerp(sm, "R", rm, "R", mask, "", -300, 650), "", MP.MP_AMBIENT_OCCLUSION)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    return m


def run():
    report = {"map": MAP}
    prepare_map()
    yield 60
    world = m80_seq.editor_world()
    if any(a.get_actor_label() == "M80_Landscape" for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Landscape)):
        report["skipped"] = "landscape already present"
    else:
        terrain = None
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
            mesh = actor.static_mesh_component.get_editor_property("static_mesh")
            if mesh and TERRAIN_MESH in mesh.get_name():
                terrain = actor
                break
        if not terrain:
            raise RuntimeError("Terrain mesh actor not found")
        origin, extent = terrain.get_actor_bounds(False)
        size_cm = min(2 * max(extent.x, extent.y), MAX_KM * 100000)
        comps = max(1, math.ceil(size_cm / (126 * QUAD)))
        report.update(terrain=terrain.get_actor_label(), terrain_size_m=[round(extent.x / 50), round(extent.y / 50)],
                      components=comps, quad_cm=QUAD, landscape_size_m=round(comps * 126 * QUAD / 100))

        tex = {short: {s: copy_texture(short, sid, s) for s in ("_D", "_N", "_ORDp")} for short, sid in SURFACES.items()}
        yield 5
        material = build_material(tex)
        yield 30
        landscape = unreal.M80EditorLibrary.create_landscape_from_terrain(
            terrain, unreal.Vector2D(origin.x, origin.y), QUAD, comps, comps, material)
        if not landscape:
            raise RuntimeError("Landscape creation failed")
        # Keep the old mesh for reference, but out of sight and out of the way of ground traces.
        terrain.set_actor_hidden_in_game(True)
        terrain.set_is_temporarily_hidden_in_editor(True)
        terrain.set_actor_enable_collision(False)
        terrain.static_mesh_component.set_editor_property("hidden_in_game", True)
        terrain.static_mesh_component.set_visibility(False)
        terrain.tags = list(terrain.tags) + ["M80IgnoreGround"]
        report["landscape"] = landscape.get_actor_label()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
