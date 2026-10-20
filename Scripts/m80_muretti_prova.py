"""Dry-stone walls, the red iron fence and the road lamp "a frusta": imports the lamp (m80_lampione_frusta_setup.py),
makes the kit materials MI_M80_PietraSecco (own texture set of m80_stairs_textures.py) and MI_M80_FerroRosso (red-tinted
scan) as listed in m80_stairs_setup.KIT_MATERIALS and builds the test level /Game/Mazzarino80/Kit/Stairs/L_M80_ProvaMuretti (rebuilt each run):
- A: dry-stone wall from the ground, 1 m tall with an uneven top, over flat ground and up a slope;
- B: dry-stone wall from the spline down to the ground, with the red fence on top;
- C: the red fence alone on the ground, up the slope;
- D: a low dry-stone wall with the red fence on it (the parapet of the photos);
- four whip lamps along a road: 6, 9 and 12 m sodium, 9 m mercury.
Renders (day and night) go to Saved/Mazzarino80/Muretti/Render.
The stones of the dry-stone walls (m80_pietre_secco.py) are imported into Kit/Stairs as SM_M80_PietraSecco_N with
MI_M80_PietraSecco_Massi (ROCK); MI_M80_PietraSecco, the dark core behind them, is the generated texture.
Env M80_CANDIDATI=1: first renders a row of walls, one per candidate rock in ROCKS (transient materials, removed
before the level is saved), to compare them.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_muretti_prova.py -ForceLit
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402
import m80_stairs_setup as kit  # noqa: E402
import m80_lampione_frusta_setup as frusta  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = kit.KIT + "/L_M80_ProvaMuretti"
OUT = ROOT / "Saved/Mazzarino80/Muretti"
RENDER = OUT / "Render"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MEL = unreal.MaterialEditingLibrary
MS = "/Game/Megascans/Surfaces/"
STONE_FBX = "D:/Mazzarino80_Sorgenti/Muretti/M80_PietreSecco.fbx"
# The stones' rock: scanned surface, tiling per metre, albedo tint (the stones have cube-projected UVs, 1 unit per metre).
ROCK = (MS + "Roman_Stone_Wall_tf2kaa2n/MI_Roman_Stone_Wall_tf2kaa2n_4K", 1.0, (1.0, 1.12, 1.5))
# Megascans "Albedo Controls" left neutral (G is not saturation: 0.45 made the stones darker and redder).
ALBEDO_CONTROLS = (1.0, 1.0, 1.0, 0.0)
ROCKS = [(MS + p, tint) for p, tint in (
    ("Rough_Stone_Floor_vixidai/MI_Rough_Stone_Floor_vixidai_2K", None),
    ("Rough_Stone_Floor_vixidai/MI_Rough_Stone_Floor_vixidai_2K", (1.6, 1.55, 1.45)),
    ("Ancient_Temple_Wall_tiwmdezg/MI_Ancient_Temple_Wall_tiwmdezg_2K", None),
    ("Ancient_Temple_Wall_tiwmdezg/MI_Ancient_Temple_Wall_tiwmdezg_2K", (1.3, 1.27, 1.2)),
    ("Roman_Stone_Wall_tf2kaa2n/MI_Roman_Stone_Wall_tf2kaa2n_4K", (1.2, 1.2, 1.2)),
    ("Lichened_Rock_wgorbgd/MI_Lichened_Rock_wgorbgd_2K", (1.6, 1.55, 1.45)))]
K, S, F, W = unreal.M80StairsKind, unreal.M80StairsSide, unreal.M80FenceKind, unreal.M80StairsWallFinish


def scan_params(mi, tiling, tint):
    MEL.set_material_instance_vector_parameter_value(mi, "Tiling/Offset", unreal.LinearColor(tiling, tiling, 0, 0))
    if tint:
        MEL.set_material_instance_vector_parameter_value(mi, "Albedo Tint", unreal.LinearColor(*tint, 1))


def kit_materials():
    kit.import_textures(("PietraSecco",))
    for name in ("PietraSecco", "FerroRosso"):
        source, tiling, tint, _ = kit.KIT_MATERIALS[name]
        if source in kit.SETS:
            mi = kit.instance(name, unreal.load_asset(kit.KIT + "/M_M80_KitPietra"))
            for k in ("D", "N", "ORM"):
                MEL.set_material_instance_texture_parameter_value(mi, k, unreal.load_asset("%s/Textures/T_M80_%s_%s" % (kit.KIT, source, k)))
            MEL.set_material_instance_scalar_parameter_value(mi, "TileM", kit.SETS[source])
        else:
            mi = kit.instance(name, unreal.load_asset(source))
            scan_params(mi, tiling, tint)
        if name == "PietraSecco":
            # The core seen in the gaps between the stones: almost black, like the shadow deep in a real dry-stone wall.
            MEL.set_material_instance_vector_parameter_value(mi, "Tinta", unreal.LinearColor(0.05, 0.045, 0.04, 1))
        unreal.EditorAssetLibrary.save_loaded_asset(mi, False)


def import_stones():
    fbx = unreal.FbxImportUI()
    fbx.set_editor_property("import_mesh", True)
    fbx.set_editor_property("import_materials", False)
    fbx.set_editor_property("import_textures", False)
    fbx.set_editor_property("import_as_skeletal", False)
    fbx.static_mesh_import_data.set_editor_property("combine_meshes", False)
    fbx.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", STONE_FBX)
    task.set_editor_property("destination_path", kit.KIT)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", fbx)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mi = kit.instance("PietraSecco_Massi", unreal.load_asset(ROCK[0]))
    scan_params(mi, ROCK[1], ROCK[2])
    # The tint (ROCK) cools the scan's golden sandstone towards the grey limestone of the country walls.
    MEL.set_material_instance_vector_parameter_value(mi, "Albedo Controls", unreal.LinearColor(*ALBEDO_CONTROLS))
    unreal.EditorAssetLibrary.save_loaded_asset(mi, False)
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    scan = unreal.load_asset(ROCK[0])
    out = {"scalari": {str(n): MEL.get_material_instance_scalar_parameter_value(scan, n) for n in MEL.get_scalar_parameter_names(scan.get_base_material())},
           "vettori": {str(n): str(MEL.get_material_instance_vector_parameter_value(scan, n)) for n in MEL.get_vector_parameter_names(scan.get_base_material())}}
    for k in range(8):
        mesh = unreal.load_asset("%s/SM_M80_PietraSecco_%d" % (kit.KIT, k))
        if not mesh:
            out[k] = "not imported"
            continue
        mesh.set_material(0, mi)
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", True)
        sub.set_nanite_settings(mesh, settings, apply_changes=True)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
        box = mesh.get_bounding_box()
        out[k] = [round(box.max.x - box.min.x), round(box.max.y - box.min.y), round(box.max.z - box.min.z)]
    return out


def transient(source, tiling, tint, n):
    mi = unreal.new_object(unreal.MaterialInstanceConstant, name="M80Prova%d" % n)
    MEL.set_material_instance_parent(mi, unreal.load_asset(source))
    scan_params(mi, tiling, tint)
    return mi


def lamp(label, x, height, mercury=False):
    a = EAS.spawn_actor_from_class(unreal.M80StreetLight, unreal.Vector(x, -1000, 0), unreal.Rotator(0, 0, -90))
    a.set_actor_label(label)
    a.set_folder_path("Lampioni")
    a.set_editor_property("pole_height_m", height)
    a.set_editor_property("mercury", mercury)
    a.set_editor_property("kind", unreal.M80LampKind.WHIP)
    return a


def build_level():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -38, 130))
    sun.set_actor_label("Sole")
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.set_actor_label("Cielo")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(2.0)
    EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    ground = unreal.load_asset("/Game/Mazzarino80/Vehicles/M_M80_ProvaGuida_Suolo") or unreal.load_asset(kit.KIT + "/MI_M80_Cemento")
    road = unreal.load_asset(kit.KIT + "/MI_M80_Cemento")
    kit.box("Suolo", (500, 1000, -50), (9000, 9000, 100), mat=ground)
    # Slope rising 10 degrees towards +X under the walls (from the ground near x = 700 to 1.7 m at x = 1800).
    kit.box("Pendio", (1100, 300, 0), (1400, 2000, 100), rot=(0, 10, 0), mat=ground)
    kit.box("Strada", (300, -1500, -48), (6000, 700, 100), mat=road)
    kit.stairs("A_Muretto_secco_dal_terreno", [(-1500, 0, 0), (0, 60, 0), (1800, 0, 0)], kind=K.WALL_FROM_GROUND,
               wall_height_cm=100, wall_thickness_cm=55, wall_finish=W.DRY_STONE, top_uneven_cm=12)
    kit.stairs("B_Muro_secco_dalla_spline", [(-1500, 400, 150), (300, 400, 200), (1800, 400, 320)], kind=K.WALL_FROM_SPLINE,
               wall_thickness_cm=50, wall_finish=W.DRY_STONE, top_uneven_cm=6, fence_kind=F.RED_IRON_RAILS, post_spacing_cm=200)
    kit.stairs("C_Staccionata_rossa", [(-1500, 800, 0), (1800, 800, 0)], kind=K.WALL_FROM_GROUND, wall_height_cm=0,
               fence_kind=F.RED_IRON_RAILS, post_spacing_cm=200, fence_height_cm=110)
    kit.stairs("D_Parapetto_con_staccionata", [(-1500, 1200, 0), (1800, 1200, 0)], kind=K.WALL_FROM_GROUND, wall_height_cm=55,
               wall_thickness_cm=40, wall_finish=W.DRY_STONE, fence_kind=F.RED_IRON_RAILS, post_spacing_cm=200)
    lamp("Frusta_6m", -1500, 6.0)
    lamp("Frusta_9m", -300, 9.0)
    lamp("Frusta_12m", 900, 12.0)
    lamp("Frusta_9m_mercurio", 2100, 9.0, mercury=True)


def candidates():
    """A row of dry-stone walls, one per candidate rock (left to right as listed)."""
    actors = []
    for i, (source, tint) in enumerate(ROCKS):
        x = -1050 + i * 320
        a = kit.stairs("Prova_roccia_%d" % i, [(x, 2500, 0), (x + 260, 2500, 0)], kind=K.WALL_FROM_GROUND,
                       wall_height_cm=110, wall_thickness_cm=50, wall_finish=W.DRY_STONE, top_uneven_cm=8)
        mi = transient(source, 1.0, tint, i)
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if c.get_name().startswith("DryStone"):
                c.set_material(0, mi)
        actors.append(a)
    return actors


DAY = {
    "panoramica": ((-2600, -2300, 900), (300, 600, 50)),
    "A_muretto_secco": ((-500, -500, 160), (300, 0, 60)),
    "A_muretto_dettaglio": ((-900, -170, 120), (-700, 0, 60)),
    "A_muretto_di_fronte": ((-400, -330, 75), (-400, 0, 60)),
    "A_testata": ((-1750, -200, 110), (-1500, 0, 50)),
    "A_muretto_pendio": ((2400, -500, 350), (1200, 0, 120)),
    "B_muro_spline_staccionata": ((-600, 150, 260), (400, 400, 220)),
    "D_parapetto": ((-700, 950, 150), (200, 1200, 70)),
    "C_staccionata_pendio": ((2500, 1000, 300), (1200, 800, 150)),
    "lampioni": ((-3200, -2900, 450), (300, -1000, 550)),
    "lampione_testa": ((-700, -1900, 850), (-300, -1150, 880)),
}
NIGHT = {"notte_lampioni": ((-3300, -1600, 220), (1500, -1000, 300)), "notte_dall_alto": ((-2500, -3000, 1500), (300, -1200, 0))}
CANDIDATE_VIEWS = {"candidati_roccia": ((0, 1150, 260), (0, 2500, 70))}
CANDIDATE_VIEWS.update({"candidato_%d" % i: ((-920 + i * 320, 2180, 130), (-920 + i * 320, 2500, 60)) for i in range(6)})


def shoot(views, cap):
    for name, (eye, target) in views.items():
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        m80_seq.set_view(unreal.Vector(*eye), rot)
        yield 60
        cap.capture(unreal.Vector(*eye), rot, RENDER / ("%s.png" % name))
        yield 2


def night(world, on):
    sun = [a for a in EAS.get_all_level_actors() if a.get_actor_label() == "Sole"][0]
    sky = [a for a in EAS.get_all_level_actors() if a.get_actor_label() == "Cielo"][0]
    sun.set_actor_rotation(unreal.Rotator(0, 20 if on else -38, 130), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(0.0 if on else 7.0)
    sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(0.05 if on else 2.0)
    unreal.MaterialLibrary.set_scalar_parameter_value(world, unreal.load_asset("/Game/Mazzarino80/Sky/MPC_M80_Atmosfera"), "Lampioni", 1.0 if on else 0.0)
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.M80StreetLight):
            a.set_night(1.0 if on else 0.0)


def steps():
    report = {"lamp": frusta.import_lamp(), "pietre": import_stones()}
    yield 5
    kit_materials()
    yield 5
    build_level()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 600                                   # shaders of the new materials and the sky capture
    world = m80_seq.editor_world()
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    if os.environ.get("M80_CANDIDATI") == "1":
        extra = candidates()
        yield 400
        yield from shoot(CANDIDATE_VIEWS, cap)
        for a in extra:
            a.destroy_actor()
        yield 5
    yield from shoot(DAY, cap)
    night(world, True)
    pp = cap.comp.get_editor_property("post_process_settings")
    for k, v in (("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", -1.0),
                 ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", -1.0)):
        pp.set_editor_property(k, v)
    cap.comp.set_editor_property("post_process_settings", pp)
    yield 120
    yield from shoot(NIGHT, cap)
    night(world, False)
    cap.destroy()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    report["triangoli"] = {a.get_actor_label(): a.get_component_by_class(unreal.DynamicMeshComponent).get_dynamic_mesh().get_triangle_count()
                           for a in EAS.get_all_level_actors() if isinstance(a, unreal.M80Stairs)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prova.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
