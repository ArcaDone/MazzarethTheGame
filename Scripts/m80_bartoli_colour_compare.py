"""Colour check: the materials of the town (house styles, stairs and sidewalk kit, noble balconies) next to the albedo of
the Palazzo Bartoli materials (Research/Mazzarino80/Blender/m80_bartoli_palette.py), all under the same Unreal light.

Level /Game/Mazzarino80/Buildings/Bartoli/L_M80_ConfrontoColori: a wall of 1.6 m plates facing -Y, one row per
family (stone walls, plaster, cut stone, lava stone, roofs, wood, iron). Left of the gap the Unreal materials (house
master with the style tints as custom primitive data), right the Bartoli swatches (M_M80_Campione).
Captures (orthographic, one shot so the exposure is the same for every plate): base colour and lit.
Out: Saved/Mazzarino80/Bartoli/ConfrontoColori/{base,lit}.png, layout.json, styles.json.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bartoli_colour_compare.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
PALETTE = ROOT / "Saved/Mazzarino80/Bartoli/Palette"
OUT = ROOT / "Saved/Mazzarino80/Bartoli/ConfrontoColori"
FOLDER = "/Game/Mazzarino80/Buildings/Bartoli/Palette"
MAP = "/Game/Mazzarino80/Buildings/Bartoli/L_M80_ConfrontoColori"
STYLES = "/Game/Mazzarino80/Houses/Styles"
HM = "/Game/Mazzarino80/Houses/Materials"
KIT = "/Game/Mazzarino80/Kit"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
PITCH, TILE, GAP_COLS = 200.0, 160.0, 1

# Families: Unreal materials (path, wall-tint list key or None, wood tint key or None) and Bartoli swatches.
FAMILIES = [
    ("Muri in pietra", [HM + "/MI_M80_Wall_Ashlar", HM + "/MI_M80_Wall_Rubble", KIT + "/Stairs/MI_M80_MuroConci", HM + "/MI_M80_Wall_Raw"],
     ["C_Corso_muro_hi", "D_Corso_muro_hi", "B_Corso_muro_hi", "Muro_cinta0_muro_hi", "N_Giardino1_muro_hi"]),
    ("Intonaci", ["plaster"], ["Crema_Salita_muro_hi", "Crema_Sud_muro_hi", "Cortile_Ovest_muro_hi", "Cortile_Est_muro_hi",
                               "N_Butera_muro_hi", "Intonaco_androne", "Intonaco_belvedere", "Intonaco_giallo_hi", "Cinema_Fronte_muro_hi"]),
    ("Pietra da taglio", [HM + "/MI_M80_Trim_Sandstone", KIT + "/Balconi/MI_M80_Balcone_Lastra_Volute", KIT + "/Balconi/MI_M80_Balcone_Mensola_Volute"],
     ["Arenaria_hi", "Arenaria_portale_hi", "Pietra_bianca_hi", "Marmo_hi"]),
    ("Pietra lavica", [KIT + "/Stairs/MI_M80_PietraLavica", KIT + "/Stairs/MI_M80_Lavica_secondaria", KIT + "/Stairs/M_M80_LavicaCompleta",
                       KIT + "/Stairs/MI_M80_Basolato", KIT + "/Sidewalk/M_M80_Marciapiede", KIT + "/Stairs/MI_M80_Cemento"],
     ["Pietra_lavica_hi", "Cortile_hi"]),
    ("Tetti e cotto", [HM + "/MI_M80_Roof_Coppi", HM + "/MI_M80_Terrace"], ["Coppi_tetto_hi", "Coppi", "Terracotta"]),
    ("Legno e persiane", ["wood", KIT + "/Stairs/MI_M80_Legno"], ["Persiane_verdi", "Legno_portone", "Legno_chiaro", "Telai"]),
    ("Ferro e vetro", [HM + "/MI_M80_Iron", KIT + "/Stairs/MI_M80_Ferro", HM + "/M_M80_HouseGlass"], ["Ferro", "Serranda", "Vetro"]),
]


def style_dump():
    out = {}
    for data in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(STYLES):
        s = unreal.load_asset(str(data.package_name))
        rec = {"wall_tints": [[round(c.r, 3), round(c.g, 3), round(c.b, 3)] for c in s.get_editor_property("wall_tints")],
               "wood_tints": [[round(c.r, 3), round(c.g, 3), round(c.b, 3)] for c in s.get_editor_property("wood_tints")],
               "finish": str(s.get_editor_property("default_finish"))}
        for k in ("ashlar_material", "rubble_material", "plaster_material", "plaster_worn_material", "trim_material", "roof_material",
                  "terrace_material", "wood_material", "glass_material", "iron_material", "raw_wall_material"):
            m = s.get_editor_property(k)
            rec[k] = m.get_path_name().split(".")[0] if m else None
        out[str(data.asset_name)] = rec
    return out


def material_params(path):
    m = unreal.load_asset(path)
    rec = {"class": m.get_class().get_name()}
    if isinstance(m, unreal.MaterialInstanceConstant):
        rec["parent"] = m.get_editor_property("parent").get_path_name().split(".")[0]
        rec["scalars"] = {str(n): round(MEL.get_material_instance_scalar_parameter_value(m, n), 3)
                          for n in MEL.get_scalar_parameter_names(m)}
        rec["vectors"] = {}
        for n in MEL.get_vector_parameter_names(m):
            c = MEL.get_material_instance_vector_parameter_value(m, n)
            rec["vectors"][str(n)] = [round(c.r, 3), round(c.g, 3), round(c.b, 3)]
        rec["textures"] = {}
        for n in MEL.get_texture_parameter_names(m):
            t = MEL.get_material_instance_texture_parameter_value(m, n)
            rec["textures"][str(n)] = t.get_path_name().split(".")[0] if t else None
    return rec


def swatch_material(textures):
    """M_M80_Campione: base colour from a texture, rough stone-like surface, flat normal."""
    path = FOLDER + "/M_M80_Campione"
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    mat = TOOLS.create_asset("M_M80_Campione", FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
    tex.set_editor_property("parameter_name", "Colore")
    tex.set_editor_property("texture", textures[0])
    MEL.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, 200)
    rough.set_editor_property("r", 0.85)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat, False)
    return mat


def import_swatches(names):
    tasks = []
    for n in names:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(PALETTE / (n + ".png")))
        t.set_editor_property("destination_path", FOLDER)
        t.set_editor_property("destination_name", "T_M80_Campione_" + n)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("automated", True)
        t.set_editor_property("save", True)
        tasks.append(t)
    TOOLS.import_asset_tasks(tasks)
    return {n: unreal.load_asset("%s/T_M80_Campione_%s" % (FOLDER, n)) for n in names}


def plate(x, z, material, cpd=None):
    # The plane's normal (+Z) turned to -Y, towards the camera.
    rot = unreal.MathLibrary.make_rot_from_zx(unreal.Vector(0, -1, 0), unreal.Vector(1, 0, 0))
    a = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), unreal.Vector(x, 0, z), rot)
    a.set_actor_scale3d(unreal.Vector(TILE / 100.0, TILE / 100.0, 1))
    comp = a.static_mesh_component
    comp.set_material(0, material)
    for i, v in enumerate(cpd or []):
        comp.set_default_custom_primitive_data_float(i, v)
    return a


def build(styles):
    palette = json.loads((PALETTE / "palette.json").read_text(encoding="utf-8"))
    names = sorted({n for _, _, b in FAMILIES for n in b})
    files = {n: palette[n]["file"][:-4] for n in names}
    tex = import_swatches(sorted(set(files.values())))
    master = swatch_material(list(tex.values()))
    if EAL.does_asset_exist(MAP):
        EAL.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, -500, 2000), unreal.Rotator(0, -40, 70))
    sun.set_actor_rotation(unreal.Rotator(pitch=-40.0, yaw=70.0, roll=0.0), False)
    light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    light.set_editor_property("atmosphere_sun_light", True)
    light.set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    # Unreal tints: every wall tint of the styles on the plaster, every wood tint on the painted wood.
    wall_tints, wood_tints = [], []
    for s in styles.values():
        for t in s["wall_tints"]:
            if t not in wall_tints:
                wall_tints.append(t)
        for t in s["wood_tints"]:
            if t not in wood_tints:
                wood_tints.append(t)
    layout = {"pitch_cm": PITCH, "tile_cm": TILE, "rows": []}
    row = 0
    for family, ue, bartoli in FAMILIES:
        items = []
        for entry in ue:
            if entry == "plaster":
                items += [("Intonaco UE %s" % i, HM + "/MI_M80_Wall_Plaster", list(t) + [0.25, 0.32, 0.42, 0.30, 0.5]) for i, t in enumerate(wall_tints)]
                items.append(("Intonaco consumato UE", HM + "/MI_M80_Wall_PlasterWorn", list(wall_tints[0]) + [0.5, 0.32, 0.42, 0.30, 0.5]))
            elif entry == "wood":
                items += [("Legno UE %s" % i, HM + "/MI_M80_Wood_Painted", [1, 1, 1, 0.25] + list(t) + [0.5]) for i, t in enumerate(wood_tints)]
            else:
                items.append((entry.rsplit("/", 1)[1], entry, list(wall_tints[0]) + [0.25, 0.32, 0.42, 0.30, 0.5]))
        # Long families wrap onto several rows; the Bartoli swatches start after a gap.
        cells = [("ue",) + it for it in items] + [None] * GAP_COLS + [("bartoli", n, None, None) for n in bartoli]
        cols = 12
        for k in range(0, len(cells), cols):
            chunk = cells[k:k + cols]
            rec = {"family": family, "row": row, "cells": []}
            for c, cell in enumerate(chunk):
                if cell is None:
                    continue
                x, z = c * PITCH, -row * PITCH
                if cell[0] == "ue":
                    _, label, path, cpd = cell
                    plate(x, z, unreal.load_asset(path), cpd)
                    rec["cells"].append({"col": c, "side": "ue", "label": label, "asset": path})
                else:
                    name = cell[1]
                    mi_name = "MI_M80_Campione_" + files[name]
                    mi_path = "%s/%s" % (FOLDER, mi_name)
                    mi = unreal.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else \
                        TOOLS.create_asset(mi_name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
                    MEL.set_material_instance_parent(mi, master)
                    MEL.set_material_instance_texture_parameter_value(mi, "Colore", tex[files[name]])
                    EAL.save_loaded_asset(mi, False)
                    plate(x, z, mi)
                    rec["cells"].append({"col": c, "side": "bartoli", "label": name, "mean_srgb": palette[name]["mean_srgb"]})
            layout["rows"].append(rec)
            row += 1
    layout["n_rows"] = row
    layout["n_cols"] = 12
    return layout


def capture(layout):
    world = m80_seq.editor_world()
    w_cm = layout["n_cols"] * PITCH
    h_cm = layout["n_rows"] * PITCH
    px_per_cm = 1.0
    width, height = int(w_cm * px_per_cm), int(h_cm * px_per_cm)
    cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
    comp = cam.get_editor_property("capture_component2d")
    comp.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
    comp.set_editor_property("ortho_width", w_cm)
    comp.set_editor_property("capture_every_frame", False)
    # Centre of the wall of plates, seen from the front (-Y looking +Y).
    cx = (layout["n_cols"] - 1) * PITCH / 2
    cz = -(layout["n_rows"] - 1) * PITCH / 2
    cam.set_actor_location_and_rotation(unreal.Vector(cx, -3000, cz), unreal.Rotator(0, 0, 90), False, False)
    cam.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)
    layout["image"] = {"width": width, "height": height, "px_per_cm": px_per_cm, "origin_cm": [cx - w_cm / 2, cz + h_cm / 2]}
    for source, name in ((unreal.SceneCaptureSource.SCS_BASE_COLOR, "base.png"), (unreal.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR, "lit.png")):
        rt = unreal.RenderingLibrary.create_render_target2d(world, width, height, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        comp.set_editor_property("texture_target", rt)
        comp.set_editor_property("capture_source", source)
        comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, str(OUT), name)
        yield 5
    cam.destroy_actor()


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    styles = style_dump()
    (OUT / "styles.json").write_text(json.dumps(styles, indent=1), encoding="utf-8")
    params = {}
    for _, ue, _ in FAMILIES:
        for p in ue:
            if p.startswith("/Game"):
                params[p] = material_params(p)
    for p in (HM + "/MI_M80_Wall_Plaster", HM + "/MI_M80_Wall_PlasterWorn", HM + "/MI_M80_Wood_Painted"):
        params[p] = material_params(p)
    (OUT / "materials.json").write_text(json.dumps(params, indent=1), encoding="utf-8")
    layout = build(styles)
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 300
    for _ in capture(layout):
        yield 5
    yield 200
    # Second pass once every shader and texture has streamed in.
    cap = capture(layout)
    for _ in cap:
        yield 5
    (OUT / "layout.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
