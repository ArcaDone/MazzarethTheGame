"""Test level for the noble balconies of the house generator: /Game/Mazzarino80/Kit/Balconi/L_M80_ProvaBalconiSignorili.

Six palazzi (style Palazzo urbano, all balconies noble): volute, mascheroni and acanthus consoles, each with the
straight and the goose-breast railing, plus an ordinary house for comparison. Renders in
Saved/Mazzarino80/Balconi/Render/<view>.png.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_noble_balconies_test.py -ForceLit
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Kit/Balconi/L_M80_ProvaBalconiSignorili"
STYLE = "/Game/Mazzarino80/Houses/Styles/DA_M80Style_02_PalazzoUrbano"
RENDER = ROOT / "Saved/Mazzarino80/Balconi/Render"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
NB, NR = unreal.M80NobleBalcony, unreal.M80NobleRailing
W, D, GAP = 1400.0, 1000.0, 600.0

HOUSES = [
    ("Volute_dritta", NB.VOLUTE, NR.STRAIGHT, 1.0),
    ("Volute_petto_oca", NB.VOLUTE, NR.BOMBE, 1.0),
    ("Mascheroni_dritta", NB.MASCHERONI, NR.STRAIGHT, 1.0),
    ("Mascheroni_petto_oca", NB.MASCHERONI, NR.BOMBE, 1.0),
    ("Acanto_dritta", NB.ACANTO, NR.STRAIGHT, 1.0),
    ("Acanto_petto_oca", NB.ACANTO, NR.BOMBE, 1.0),
    ("Normale", NB.RANDOM, NR.STYLE, 0.0),
]


def build_level():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -40, 60))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(2.0)
    EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    ground = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cube"), unreal.Vector(5000, 0, -50))
    ground.set_actor_scale3d(unreal.Vector(160, 60, 1))
    mat = unreal.load_asset("/Game/Mazzarino80/Kit/Stairs/MI_M80_Cemento")
    if mat:
        ground.static_mesh_component.set_material(0, mat)
    style = unreal.load_asset(STYLE)
    houses = []
    for i, (label, kind, railing, noble) in enumerate(HOUSES):
        x0 = i * (W + GAP)
        a = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.M80House, unreal.Vector(x0, 0, 0))
        a.set_actor_label("Palazzo_" + label)
        a.set_editor_property("live_rebuild", False)
        # Edge 0 (x0,0)->(x0+W,0) is the main facade, facing -Y.
        a.set_footprint_world([unreal.Vector(x0, 0, 0), unreal.Vector(x0 + W, 0, 0), unreal.Vector(x0 + W, D, 0),
                               unreal.Vector(x0, D, 0)])
        p = a.get_editor_property("house")
        p.set_editor_property("style", style)
        p.set_editor_property("floors", 3)
        p.set_editor_property("seed", 7 + i)
        p.set_editor_property("front_edge", 0)
        p.set_editor_property("balcony_chance_override", 1.0)
        p.set_editor_property("noble_balcony_override", noble)
        p.set_editor_property("noble_balcony_kind", kind)
        p.set_editor_property("noble_railing", railing)
        a.set_editor_property("house", p)
        a.rebuild()
        unreal.log("NOBLE %s: %s" % (label, a.get_editor_property("build_info")))
        houses.append(a)
    return houses


def views():
    out = {"panoramica": ((4800, -5200, 1500), (4800, 0, 600))}
    for i, (label, _, _, _) in enumerate(HOUSES):
        cx = i * (W + GAP) + W / 2
        out[label] = ((cx + 350, -1250, 260), (cx - 50, 0, 620))
        out[label + "_dettaglio"] = ((cx + 120, -420, 300), (cx - 120, 0, 430))
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    for name, (eye, target) in out.items():
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        cap.capture(unreal.Vector(*eye), rot, RENDER / ("%s.png" % name))
        yield 2
    cap.destroy()


def steps():
    RENDER.mkdir(parents=True, exist_ok=True)
    build_level()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().startswith(MAP), world.get_path_name()
    yield 600
    for _ in views():
        yield 2
    yield 300
    for _ in views():
        yield 2


m80_seq.Sequencer(steps(), log_file=str(RENDER / "error.txt"))
