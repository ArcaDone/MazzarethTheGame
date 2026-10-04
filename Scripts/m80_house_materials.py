"""Creates the house master material, its instances and assigns them to the four styles.

Textures are copied from the Megascans packs into /Game/Mazzarino80/Houses/Textures,
reduced to 2K and stored as JPEG source so the versioned copy stays small.

Per-house values come from custom primitive data written by AM80House:
  0-2 wall tint, 3 decay, 4-6 wood tint, 7 random.
Vertex colours from the generator: R height above ground, G facade mask, B element random.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
BASE = "/Game/Mazzarino80/Houses"
TEX_DIR = BASE + "/Textures"
MAT_DIR = BASE + "/Materials"
STYLE_DIR = BASE + "/Styles"
REPORT = ROOT / "Saved/Mazzarino80/HousesV2/materials_report.json"
MAX_SIZE = 2048

MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REGISTRY = unreal.AssetRegistryHelpers.get_asset_registry()

# Short name -> Megascans surface id; maps are looked up by name in the asset registry.
SURFACES = {
    "Ashlar": "ti4lfiso",
    "Rubble": "tf2kaa2n",
    "Plaster": "wfnjdgl",
    "FlakedPaint": "tlwmfipg",
    "Brick": "vcvodh0",
    "Roof": "tfqnfggs",
    "Trim": "vh2ifg1",
    "Wood": "scok0up0",
    "Iron": "tj2xahsbw",
}
NOISE = "/Game/Mazzarino80/Historic/Materials/T_M80_FacadeMacroNoise"


def find_texture(surface_id, suffix):
    """Finds the Megascans texture of a surface by id and map suffix (_D, _N, _ORDp)."""
    best = None
    for data in REGISTRY.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Texture2D")):
        name = str(data.asset_name)
        if surface_id in name and name.endswith(suffix) and not str(data.package_path).startswith(TEX_DIR):
            # Prefer the smallest source that is still >= 2K: loading 8K sources exhausts memory.
            score = ("2K" in name, "4K" in name, "8K" not in name, str(data.package_path).startswith("/Game/Megascans"))
            if best is None or score > best[0]:
                best = (score, str(data.package_name))
    return best[1] if best else None


def copy_texture(short, surface_id, suffix, report):
    """Copies a Megascans map into the versioned folder at <= 2K with a JPEG source."""
    target = "{}/{}/T_M80_{}{}".format(TEX_DIR, short, short, suffix.replace("ORDp", "ORD"))
    source = None
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        tex = unreal.load_asset(target)
    else:
        source = find_texture(surface_id, suffix)
        if not source:
            report.setdefault("missing", []).append(surface_id + suffix)
            return None
        tex = unreal.EditorAssetLibrary.duplicate_asset(source, target)
    before = unreal.M80EditorLibrary.get_texture_source_size(tex)
    resized = unreal.M80EditorLibrary.downsize_texture_source(tex, MAX_SIZE)
    jpeg = unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 92 if suffix == "_N" else 88)
    after = unreal.M80EditorLibrary.get_texture_source_size(tex)
    # Packed AO/roughness/displacement: linear Masks compression, matching the master's Masks samplers.
    masks = suffix == "_ORDp" and (tex.get_editor_property("compression_settings") != unreal.TextureCompressionSettings.TC_MASKS
                                   or tex.get_editor_property("srgb"))
    if masks:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("srgb", False)
    if resized or jpeg or source or masks:
        unreal.EditorAssetLibrary.save_loaded_asset(tex)
    report.setdefault("textures", {})[target] = {"source": source, "before": [before.x, before.y], "after": [after.x, after.y],
                                                 "resized": bool(resized), "jpeg": bool(jpeg)}
    return tex


class Graph:
    """Small helper to lay out and wire material expressions."""

    def __init__(self, material):
        self.m = material

    def node(self, cls, x, y, **props):
        expr = MEL.create_material_expression(self.m, cls, x, y)
        for key, value in props.items():
            expr.set_editor_property(key, value)
        return expr

    def link(self, src, src_out, dst, dst_in):
        if not MEL.connect_material_expressions(src, src_out, dst, dst_in):
            raise RuntimeError("Cannot connect {}.{} -> {}.{}".format(src.get_name(), src_out, dst.get_name(), dst_in))

    def scalar(self, name, default, x, y, group="Superficie"):
        return self.node(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=default, group=group)

    def vector(self, name, default, x, y, group="Colore", cpd_index=None):
        expr = self.node(unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name, default_value=default, group=group)
        if cpd_index is not None:
            expr.set_editor_property("use_custom_primitive_data", True)
            expr.set_editor_property("primitive_data_index", cpd_index)
        return expr

    def texture(self, name, tex, uv, x, y, sampler=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, group="Texture"):
        expr = self.node(unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, sampler_type=sampler, group=group)
        if tex:
            expr.set_editor_property("texture", tex)
        self.link(uv, "", expr, "UVs")
        return expr

    def op(self, cls, a, a_out, b, b_out, x, y):
        expr = self.node(cls, x, y)
        self.link(a, a_out, expr, "A")
        self.link(b, b_out, expr, "B")
        return expr

    def lerp(self, a, a_out, b, b_out, alpha, alpha_out, x, y):
        expr = self.node(unreal.MaterialExpressionLinearInterpolate, x, y)
        self.link(a, a_out, expr, "A")
        self.link(b, b_out, expr, "B")
        self.link(alpha, alpha_out, expr, "Alpha")
        return expr

    def const(self, value, x, y):
        return self.node(unreal.MaterialExpressionConstant, x, y, r=value)

    def mask(self, src, x, y, r=False, g=False, b=False, a=False):
        expr = self.node(unreal.MaterialExpressionComponentMask, x, y, r=r, g=g, b=b, a=a)
        self.link(src, "", expr, "")
        return expr

    def palette(self, prefix, position, x, y, defaults):
        """Three-colour gradient picked by position 0..1 (vector params <prefix>PaletteA/B/C)."""
        a, b, c = (self.vector(prefix + "Palette" + k, col, x - 300, y + i * 110, group="Palette") for i, (k, col) in enumerate(zip("ABC", defaults)))
        lo = self.node(unreal.MaterialExpressionSaturate, x - 100, y + 330)
        self.link(self.op(unreal.MaterialExpressionMultiply, position, "", self.const(2.0, x - 300, y + 380), "", x - 200, y + 330), "", lo, "")
        hi = self.node(unreal.MaterialExpressionSaturate, x - 100, y + 430)
        self.link(self.op(unreal.MaterialExpressionSubtract, lo, "", self.const(0.0, x - 300, y + 480), "", x - 200, y + 430), "", hi, "")
        hi2 = self.node(unreal.MaterialExpressionSaturate, x - 100, y + 520)
        two_x = self.op(unreal.MaterialExpressionMultiply, position, "", self.const(2.0, x - 300, y + 560), "", x - 200, y + 520)
        self.link(self.op(unreal.MaterialExpressionSubtract, two_x, "", self.const(1.0, x - 300, y + 600), "", x - 150, y + 560), "", hi2, "")
        ab = self.lerp(a, "", b, "", lo, "", x, y)
        return self.lerp(ab, "", c, "", hi2, "", x + 150, y)


def build_master(tex):
    path = MAT_DIR + "/M_M80_HouseMaster"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        # Instances and styles reference it: only rebuild the graph when explicitly asked.
        if os.environ.get("M80_REBUILD_MASTER") != "1":
            return unreal.load_asset(path)
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)
    else:
        m = TOOLS.create_asset("M_M80_HouseMaster", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_instanced_static_meshes", True)
    m.set_editor_property("used_with_nanite", True)
    g = Graph(m)
    MP = unreal.MaterialProperty
    normal_sampler = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
    masks_sampler = unreal.MaterialSamplerType.SAMPLERTYPE_MASKS

    uv0 = g.node(unreal.MaterialExpressionTextureCoordinate, -2400, 0)
    vcol = g.node(unreal.MaterialExpressionVertexColor, -2400, 1400)
    noise_tex = unreal.load_asset(NOISE)
    # UV1 = per-house data from the generator: X palette position, Y decay.
    uv1 = g.node(unreal.MaterialExpressionTextureCoordinate, -3400, -500, coordinate_index=1)
    unit_x = g.mask(uv1, -3250, -560, r=True)
    unit_y = g.mask(uv1, -3250, -440, g=True)
    wall_tint = g.palette("Wall", unit_x, -2600, -800,
        (unreal.LinearColor(1, 1, 1, 1), unreal.LinearColor(1, 0.93, 0.82, 1), unreal.LinearColor(0.9, 0.84, 0.76, 1)))
    wood_x = g.node(unreal.MaterialExpressionFrac, -2700, -300)
    g.link(g.op(unreal.MaterialExpressionMultiply, unit_x, "", g.const(7.13, -2850, -250), "", -2800, -300), "", wood_x, "")
    wood_tint = g.palette("Wood", wood_x, -2600, -300,
        (unreal.LinearColor(0.16, 0.30, 0.20, 1), unreal.LinearColor(0.27, 0.17, 0.10, 1), unreal.LinearColor(0.22, 0.33, 0.32, 1)))

    # Every house shifts the texture, so neighbouring walls never line up.
    house_shift = g.op(unreal.MaterialExpressionMultiply, unit_x, "",
        g.node(unreal.MaterialExpressionConstant2Vector, -3250, 80, r=13.7, g=7.1), "", -3100, 40)
    uv_shifted = g.op(unreal.MaterialExpressionAdd, uv0, "", house_shift, "", -2950, 0)
    tile = g.scalar("TileSize", 2.0, -2400, 120)
    uv = g.op(unreal.MaterialExpressionDivide, uv_shifted, "", tile, "", -2200, 40)
    under_tile = g.scalar("UnderTileSize", 2.0, -2400, 600, group="Degrado")
    uv_under = g.op(unreal.MaterialExpressionDivide, uv_shifted, "", under_tile, "", -2200, 560)
    # Anti-tiling: a second sample at another scale and offset, blended by large noise patches.
    uv_b = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, uv, "", g.const(0.87, -2200, 200), "", -2100, 160), "",
        g.node(unreal.MaterialExpressionConstant2Vector, -2200, 260, r=0.43, g=0.71), "", -2000, 160)
    uv_ub = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, uv_under, "", g.const(0.83, -2200, 700), "", -2100, 660), "",
        g.node(unreal.MaterialExpressionConstant2Vector, -2200, 760, r=0.29, g=0.57), "", -2000, 660)
    blend_uv = g.op(unreal.MaterialExpressionDivide, uv0, "", g.scalar("AntiTileScale", 4.5, -2400, 300, group="Superficie"), "", -2200, 330)
    blend_n = g.texture("AntiTileNoise", noise_tex, blend_uv, -2050, 330, group="Superficie")
    blend = g.node(unreal.MaterialExpressionSaturate, -1800, 330)
    g.link(g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionSubtract, blend_n, "R", g.const(0.5, -1950, 420), "", -1900, 380), "", g.const(4.0, -1950, 470), "", -1850, 400), "",
        g.const(0.5, -1900, 470), "", -1850, 450), "", blend, "")

    def dual(name, t, uv_a, uv_bb, x, y, sampler=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, group="Texture"):
        a = g.texture(name, t, uv_a, x, y, sampler, group)
        b = g.texture(name, t, uv_bb, x, y + 120, sampler, group)
        return g.lerp(a, "RGBA", b, "RGBA", blend, "", x + 250, y)

    base_d = dual("BaseColor", tex["Ashlar"]["_D"], uv, uv_b, -1700, -200)
    base_n = dual("Normal", tex["Ashlar"]["_N"], uv, uv_b, -1700, 50, normal_sampler)
    base_m = dual("Masks", tex["Ashlar"]["_ORDp"], uv, uv_b, -1700, 300, masks_sampler)
    under_d = dual("UnderBaseColor", tex["Brick"]["_D"], uv_under, uv_ub, -1700, 560, group="Degrado")
    under_n = dual("UnderNormal", tex["Brick"]["_N"], uv_under, uv_ub, -1700, 810, normal_sampler, group="Degrado")
    under_m = dual("UnderMasks", tex["Brick"]["_ORDp"], uv_under, uv_ub, -1700, 1060, masks_sampler, group="Degrado")
    base_d_rgb = g.mask(base_d, -1300, -200, r=True, g=True, b=True)
    under_d_rgb = g.mask(under_d, -1300, 560, r=True, g=True, b=True)
    base_n_rgb = g.mask(base_n, -1300, 50, r=True, g=True, b=True)
    under_n_rgb = g.mask(under_n, -1300, 810, r=True, g=True, b=True)

    # ---- decay mask: plaster falls off where noise and the plaster's own height agree
    noise_scale = g.scalar("DecayNoiseScale", 3.0, -2400, 1700, group="Degrado")
    uv_noise = g.op(unreal.MaterialExpressionDivide, uv0, "", noise_scale, "", -2200, 1700)
    noise = g.texture("DecayNoise", noise_tex, uv_noise, -2000, 1700, group="Degrado")
    disp = g.node(unreal.MaterialExpressionOneMinus, -1600, 1500)
    g.link(g.mask(base_m, -1750, 1500, b=True), "", disp, "")
    disp_w = g.op(unreal.MaterialExpressionMultiply, disp, "", g.const(0.15, -1600, 1580), "", -1450, 1500)
    height = g.op(unreal.MaterialExpressionAdd, noise, "R", disp_w, "", -1300, 1600)
    decay_amount = g.scalar("DecayAmount", 1.0, -1700, 1850, group="Degrado")
    decay = g.op(unreal.MaterialExpressionMultiply, unit_y, "", decay_amount, "", -1500, 1850)
    # Plaster falls off in a few large patches (big-scale noise) and near the ground, not everywhere.
    cluster_uv = g.op(unreal.MaterialExpressionDivide, uv0, "", g.scalar("DecayClusterScale", 7.0, -2400, 2000, group="Degrado"), "", -2200, 2000)
    cluster_n = g.texture("DecayCluster", noise_tex, cluster_uv, -2000, 2000, group="Degrado")
    cluster = g.node(unreal.MaterialExpressionSmoothStep, -1800, 2000)
    g.link(g.const(0.42, -1950, 2100), "", cluster, "Min")
    g.link(g.const(0.68, -1950, 2150), "", cluster, "Max")
    g.link(cluster_n, "G", cluster, "Value")
    low_in = g.node(unreal.MaterialExpressionSaturate, -1950, 2250)
    g.link(g.op(unreal.MaterialExpressionMultiply, vcol, "R", g.const(1.6, -2100, 2250), "", -2050, 2250), "", low_in, "")
    low = g.node(unreal.MaterialExpressionOneMinus, -1800, 2250)
    g.link(low_in, "", low, "")
    focus = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, cluster, "", g.const(1.4, -1650, 2100), "", -1600, 2050), "",
        g.op(unreal.MaterialExpressionMultiply, low, "", g.const(0.5, -1650, 2250), "", -1600, 2200), "", -1450, 2100)
    focus = g.op(unreal.MaterialExpressionAdd, focus, "", g.const(0.15, -1450, 2200), "", -1350, 2100)
    decay = g.op(unreal.MaterialExpressionMultiply, decay, "", focus, "", -1250, 1950)
    decay = g.op(unreal.MaterialExpressionMultiply, decay, "", vcol, "G", -1350, 1850)
    threshold = g.node(unreal.MaterialExpressionOneMinus, -1200, 1850)
    g.link(decay, "", threshold, "")
    diff = g.op(unreal.MaterialExpressionSubtract, height, "", threshold, "", -1050, 1700)
    sharp = g.op(unreal.MaterialExpressionMultiply, diff, "", g.scalar("DecaySharpness", 8.0, -1050, 1850, group="Degrado"), "", -900, 1700)
    mask = g.node(unreal.MaterialExpressionSaturate, -750, 1700)
    g.link(sharp, "", mask, "")
    mask = g.op(unreal.MaterialExpressionMultiply, mask, "", g.scalar("UseUnderLayer", 0.0, -750, 1850, group="Degrado"), "", -600, 1700)

    # ---- base colour
    base_tint = g.vector("BaseTint", unreal.LinearColor(1, 1, 1, 1), -1600, -500)
    col = g.op(unreal.MaterialExpressionMultiply, base_d_rgb, "", base_tint, "", -1400, -300)
    tinted = g.op(unreal.MaterialExpressionMultiply, col, "", wall_tint, "", -1250, -400)
    col = g.lerp(col, "", tinted, "", g.scalar("WallTintAmount", 0.0, -1250, -250, group="Colore"), "", -1100, -300)
    # painted wood: luminance of the texture times the per-house paint colour
    lum = g.node(unreal.MaterialExpressionDotProduct, -1100, -100)
    g.link(col, "", lum, "A")
    g.link(g.node(unreal.MaterialExpressionConstant3Vector, -1250, -50, constant=unreal.LinearColor(0.3, 0.59, 0.11, 1)), "", lum, "B")
    painted = g.op(unreal.MaterialExpressionMultiply, lum, "", wood_tint, "", -950, -100)
    painted = g.op(unreal.MaterialExpressionMultiply, painted, "", g.const(2.2, -950, 0), "", -800, -100)
    col = g.lerp(col, "", painted, "", g.scalar("WoodTintAmount", 0.0, -800, 0, group="Colore"), "", -650, -250)
    col = g.lerp(col, "", under_d_rgb, "", mask, "", -500, -200)
    # Vertical streaks of dirt washed down the walls (only on facade faces).
    streak_uv = g.op(unreal.MaterialExpressionMultiply, uv0, "", g.node(unreal.MaterialExpressionConstant2Vector, -700, -450, r=1.6, g=0.06), "", -600, -450)
    streak_n = g.texture("StreakNoise", noise_tex, streak_uv, -450, -450, group="Sporco")
    streak = g.node(unreal.MaterialExpressionSaturate, -200, -450)
    g.link(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, streak_n, "R", g.const(0.5, -350, -380), "", -300, -400), "",
        g.const(3.0, -350, -330), "", -250, -380), "", streak, "")
    streak = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, streak, "", vcol, "G", -100, -450), "",
        g.scalar("StreakAmount", 0.35, -200, -350, group="Sporco"), "", 0, -450)
    clean = g.node(unreal.MaterialExpressionOneMinus, 100, -450)
    g.link(streak, "", clean, "")
    col = g.op(unreal.MaterialExpressionMultiply, col, "", clean, "", 200, -300)
    # per element and large-scale variation
    var_amt = g.scalar("ElementVariation", 0.1, -700, 150, group="Colore")
    var_lo = g.node(unreal.MaterialExpressionOneMinus, -550, 150)
    g.link(var_amt, "", var_lo, "")
    var_hi = g.op(unreal.MaterialExpressionAdd, var_amt, "", g.const(1.0, -550, 250), "", -450, 220)
    elem = g.lerp(var_lo, "", var_hi, "", vcol, "B", -350, 150)
    col = g.op(unreal.MaterialExpressionMultiply, col, "", elem, "", -200, -150)
    macro_scale = g.scalar("MacroScale", 14.0, -900, 400, group="Colore")
    uv_macro = g.op(unreal.MaterialExpressionDivide, uv0, "", macro_scale, "", -750, 400)
    macro = g.texture("MacroNoise", noise_tex, uv_macro, -600, 400, group="Colore")
    macro_amt = g.scalar("MacroAmount", 0.12, -450, 550, group="Colore")
    m_lo = g.node(unreal.MaterialExpressionOneMinus, -300, 550)
    g.link(macro_amt, "", m_lo, "")
    m_hi = g.op(unreal.MaterialExpressionAdd, macro_amt, "", g.const(1.0, -300, 650), "", -200, 600)
    macro_f = g.lerp(m_lo, "", m_hi, "", macro, "R", -100, 450)
    col = g.op(unreal.MaterialExpressionMultiply, col, "", macro_f, "", 0, -100)
    # rising damp near the ground (vertex R = height above the local ground)
    damp_curve = g.node(unreal.MaterialExpressionSmoothStep, -300, 900)
    g.link(g.const(0.0, -450, 850), "", damp_curve, "Min")
    g.link(g.scalar("DampHeight", 0.32, -450, 950, group="Umidita"), "", damp_curve, "Max")
    g.link(vcol, "R", damp_curve, "Value")
    damp = g.node(unreal.MaterialExpressionOneMinus, -150, 900)
    g.link(damp_curve, "", damp, "")
    damp = g.op(unreal.MaterialExpressionMultiply, damp, "", g.scalar("DampAmount", 0.55, -150, 1000, group="Umidita"), "", 0, 900)
    damp_mul = g.lerp(g.const(1.0, 0, 750), "", g.const(0.5, 0, 800), "", damp, "", 150, 750)
    col = g.op(unreal.MaterialExpressionMultiply, col, "", damp_mul, "", 300, -100)
    # Moss and lichen: on upward faces (sills, cornices, coppi) and in the damp band, in noisy patches.
    up = g.node(unreal.MaterialExpressionSmoothStep, 150, 1300)
    g.link(g.const(0.45, 0, 1250), "", up, "Min")
    g.link(g.const(0.9, 0, 1300), "", up, "Max")
    g.link(g.mask(g.node(unreal.MaterialExpressionVertexNormalWS, -300, 1300), -150, 1300, b=True), "", up, "Value")
    moss_base = g.op(unreal.MaterialExpressionAdd, up, "", g.op(unreal.MaterialExpressionMultiply, damp, "", g.const(0.8, 150, 1450), "", 300, 1400), "", 450, 1300)
    moss_uv = g.op(unreal.MaterialExpressionDivide, uv0, "", g.scalar("MossScale", 3.0, 150, 1550, group="Muschio"), "", 300, 1550)
    moss_n = g.texture("MossNoise", noise_tex, moss_uv, 450, 1550, group="Muschio")
    moss_patch = g.node(unreal.MaterialExpressionSmoothStep, 650, 1550)
    g.link(g.const(0.45, 550, 1650), "", moss_patch, "Min")
    g.link(g.const(0.7, 550, 1700), "", moss_patch, "Max")
    g.link(moss_n, "R", moss_patch, "Value")
    moss = g.node(unreal.MaterialExpressionSaturate, 900, 1350)
    g.link(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, moss_base, "", moss_patch, "", 750, 1400), "",
        g.scalar("MossAmount", 0.6, 650, 1450, group="Muschio"), "", 800, 1350), "", moss, "")
    moss_col = g.op(unreal.MaterialExpressionMultiply, g.mask(g.vector("MossColor", unreal.LinearColor(0.16, 0.19, 0.07, 1), 550, 1150, group="Muschio"), 700, 1150, r=True, g=True, b=True), "",
        g.op(unreal.MaterialExpressionAdd, g.const(0.6, 700, 1250), "", moss_n, "G", 800, 1250), "", 900, 1150)
    col = g.lerp(col, "", moss_col, "", moss, "", 1050, -100)
    MEL.connect_material_property(col, "", MP.MP_BASE_COLOR)

    # ---- roughness, AO, metallic
    rough = g.lerp(g.mask(base_m, -650, 400, g=True), "", g.mask(under_m, -650, 450, g=True), "", mask, "", -500, 400)
    rough = g.op(unreal.MaterialExpressionMultiply, rough, "", g.scalar("RoughnessScale", 1.0, -500, 520), "", -350, 400)
    rough = g.lerp(rough, "", g.const(1.0, -200, 520), "", damp, "", 300, 400)
    rough = g.lerp(rough, "", g.const(1.0, 900, 520), "", moss, "", 1050, 400)
    MEL.connect_material_property(rough, "", MP.MP_ROUGHNESS)
    ao = g.lerp(g.mask(base_m, 150, 600, r=True), "", g.mask(under_m, 150, 650, r=True), "", mask, "", 300, 600)
    MEL.connect_material_property(ao, "", MP.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(g.scalar("Metallic", 0.0, 300, 700), "", MP.MP_METALLIC)

    # ---- normal
    nrm = g.lerp(base_n_rgb, "", under_n_rgb, "", mask, "", -500, 1100)
    flat = g.node(unreal.MaterialExpressionConstant3Vector, -500, 1250, constant=unreal.LinearColor(0, 0, 1, 1))
    nrm = g.lerp(flat, "", nrm, "", g.scalar("NormalStrength", 1.0, -350, 1300), "", 300, 1100)
    MEL.connect_material_property(nrm, "", MP.MP_NORMAL)

    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def build_glass():
    path = MAT_DIR + "/M_M80_HouseGlass"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    m = TOOLS.create_asset("M_M80_HouseGlass", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_nanite", True)
    g = Graph(m)
    vcol = g.node(unreal.MaterialExpressionVertexColor, -800, 0)
    dark = g.node(unreal.MaterialExpressionConstant3Vector, -800, 200, constant=unreal.LinearColor(0.015, 0.018, 0.02, 1))
    curtain = g.node(unreal.MaterialExpressionConstant3Vector, -800, 300, constant=unreal.LinearColor(0.12, 0.1, 0.08, 1))
    # Some windows show a pale curtain behind the glass (element random above 0.7).
    above = g.op(unreal.MaterialExpressionSubtract, vcol, "B", g.const(0.7, -650, 450), "", -650, 350)
    above = g.op(unreal.MaterialExpressionMultiply, above, "", g.const(40.0, -650, 500), "", -550, 350)
    step = g.node(unreal.MaterialExpressionSaturate, -450, 350)
    g.link(above, "", step, "")
    pick = g.lerp(dark, "", curtain, "", step, "", -300, 150)
    MEL.connect_material_property(pick, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(g.const(0.06, -300, 400), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(g.const(0.8, -300, 500), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def make_instance(name, master, textures, scalars=None, vectors=None, under=None):
    path = MAT_DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = TOOLS.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, master)
    for param, key in (("BaseColor", "_D"), ("Normal", "_N"), ("Masks", "_ORDp")):
        if textures.get(key):
            MEL.set_material_instance_texture_parameter_value(mi, param, textures[key])
    if under:
        for param, key in (("UnderBaseColor", "_D"), ("UnderNormal", "_N"), ("UnderMasks", "_ORDp")):
            if under.get(key):
                MEL.set_material_instance_texture_parameter_value(mi, param, under[key])
    for param, value in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, param, value)
    for param, value in (vectors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, param, value)
    # Parameter setters do not mark the package dirty: force the save.
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    return mi


def run():
    report = {}
    tex = {}
    for short, surface in SURFACES.items():
        tex[short] = {}
        for suffix in ("_D", "_N", "_ORDp"):
            tex[short][suffix] = copy_texture(short, surface, suffix, report)
            # Source images of 4K maps are large: release them before the next copy.
            unreal.SystemLibrary.collect_garbage()
            yield 2
    master = build_master(tex)
    glass = build_glass()
    yield 10
    LC = unreal.LinearColor
    mis = {
        "ashlar_material": make_instance("MI_M80_Wall_Ashlar", master, tex["Ashlar"],
            {"TileSize": 2.0, "WallTintAmount": 0.35, "ElementVariation": 0.0, "DampAmount": 0.5}),
        "rubble_material": make_instance("MI_M80_Wall_Rubble", master, tex["Rubble"],
            {"TileSize": 2.0, "WallTintAmount": 0.3, "ElementVariation": 0.0, "DampAmount": 0.5}),
        "plaster_material": make_instance("MI_M80_Wall_Plaster", master, tex["Plaster"],
            {"TileSize": 3.0, "WallTintAmount": 1.0, "UseUnderLayer": 1.0, "UnderTileSize": 2.0, "DecayAmount": 0.55,
             "DecayNoiseScale": 1.5, "DecaySharpness": 16.0, "ElementVariation": 0.0, "DampAmount": 0.6, "MacroAmount": 0.1},
            {"WallPaletteA": LC(0.93, 0.80, 0.58, 1), "WallPaletteB": LC(0.90, 0.66, 0.40, 1), "WallPaletteC": LC(0.86, 0.58, 0.46, 1)},
            under=tex["Rubble"]),
        # Smooth lime plaster in ochre tones; brick shows only where the decay mask opens it.
        "plaster_worn_material": make_instance("MI_M80_Wall_PlasterWorn", master, tex["Plaster"],
            {"TileSize": 3.0, "WallTintAmount": 1.0, "UseUnderLayer": 1.0, "UnderTileSize": 1.6, "DecayAmount": 0.75,
             "DecayNoiseScale": 1.2, "DecaySharpness": 16.0, "ElementVariation": 0.0, "DampAmount": 0.7, "MacroAmount": 0.12},
            {"WallPaletteA": LC(1.0, 0.86, 0.62, 1), "WallPaletteB": LC(1.0, 0.95, 0.78, 1), "WallPaletteC": LC(0.95, 0.76, 0.68, 1)},
            under=tex["Brick"]),
        "trim_material": make_instance("MI_M80_Trim_Sandstone", master, tex["Trim"],
            {"TileSize": 1.5, "ElementVariation": 0.12, "DampAmount": 0.4}, {"BaseTint": LC(1.0, 0.86, 0.64, 1)}),
        "roof_material": make_instance("MI_M80_Roof_Coppi", master, tex["Roof"],
            {"TileSize": 2.0, "ElementVariation": 0.28, "DampAmount": 0.0, "MacroAmount": 0.2, "MossAmount": 0.45}),
        "terrace_material": make_instance("MI_M80_Terrace", master, tex["Trim"],
            {"TileSize": 2.0, "ElementVariation": 0.0, "DampAmount": 0.0}, {"BaseTint": LC(0.92, 0.86, 0.78, 1)}),
        "wood_material": make_instance("MI_M80_Wood_Painted", master, tex["Wood"],
            {"TileSize": 1.0, "WoodTintAmount": 0.85, "ElementVariation": 0.15, "DampAmount": 0.0, "MossAmount": 0.0}),
        "iron_material": make_instance("MI_M80_Iron", master, tex["Iron"],
            {"TileSize": 1.0, "Metallic": 0.35, "ElementVariation": 0.25, "DampAmount": 0.0, "MossAmount": 0.0}),
        "raw_wall_material": make_instance("MI_M80_Wall_Raw", master, tex["Rubble"],
            {"TileSize": 2.0, "WallTintAmount": 0.2, "DampAmount": 0.6}, {"BaseTint": LC(0.85, 0.8, 0.72, 1)}),
        # Bare hollow bricks of the unfinished top floors.
        "brick_material": make_instance("MI_M80_Wall_Brick", master, tex["Brick"],
            {"TileSize": 1.5, "UseUnderLayer": 0.0, "WallTintAmount": 0.0, "ElementVariation": 0.1, "DampAmount": 0.3}),
        "glass_material": glass,
    }
    for data in REGISTRY.get_assets_by_path(STYLE_DIR):
        style = unreal.load_asset(str(data.package_name))
        if isinstance(style, unreal.M80HouseStyle):
            for prop, mat in mis.items():
                style.set_editor_property(prop, mat)
            unreal.EditorAssetLibrary.save_loaded_asset(style)
            report.setdefault("styles", []).append(str(data.package_name))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


m80_seq.Sequencer(run(), quit_when_done=os.environ.get("M80_QUIT", "1") == "1", log_file=str(REPORT.with_suffix(".error.txt")))
