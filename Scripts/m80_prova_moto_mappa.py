"""Test map for the two-wheelers: /Game/Mazzarino80/Vehicles/Maps/L_M80_ProvaMoto, a flat yard 400 m across (room for wheelies),
the player's start, a Piaggio Si in the middle facing a wall 80 m ahead (crashes), and a second Piaggio parked on the road
beside a 15 cm kerb (getting on and off from the sidewalk). Sun, sky and fog; the town's game mode (the player on foot).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_prova_moto_mappa.py
Then Scripts/m80_motorino_test.py.
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Vehicles/Maps/L_M80_ProvaMoto"
OUT = ROOT / "Saved/Mazzarino80/Veicoli/prova_moto_mappa.txt"
V = unreal.Vector
R = unreal.Rotator
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CUBE = "/Engine/BasicShapes/Cube"
GROUND = "/Game/Mazzarino80/Vehicles/M_M80_ProvaGuida_Suolo"


def box(label, centre, size_cm, mat=None):
    a = EAS.spawn_actor_from_object(unreal.load_asset(CUBE), centre, R(0, 0, 0))
    a.set_actor_scale3d(V(size_cm[0] / 100.0, size_cm[1] / 100.0, size_cm[2] / 100.0))
    a.set_actor_label(label)
    if mat:
        a.static_mesh_component.set_material(0, unreal.load_asset(mat))
    return a


def run():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        yield 30
        for a in unreal.GameplayStatics.get_all_actors_of_class(m80_seq.editor_world(), unreal.Actor):
            if not isinstance(a, unreal.WorldSettings):
                EAS.destroy_actor(a)
    else:
        les.new_level(MAP, False)
    yield 20
    world = m80_seq.editor_world()
    # The yard: its top at z = 0.
    box("Piazzale", V(0, 0, -50), (40000, 40000, 100), GROUND)
    # The wall ahead (+X) and the kerb with its sidewalk, to the left of the start.
    box("Muro", V(8000, 0, 150), (60, 1200, 300))
    box("Marciapiede", V(0, -1100, 7.5), (2000, 200, 15))
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 1000), R(-40, 0, 35))
    sun.set_actor_label("Sole")
    sun.light_component.set_editor_property("atmosphere_sun_light", True)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, V(0, 0, 0)).set_actor_label("Cielo")
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 500))
    sky.set_actor_label("LuceCielo")
    sky.light_component.set_editor_property("real_time_capture", True)
    EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V(0, 0, 0)).set_actor_label("Nebbia")
    EAS.spawn_actor_from_class(unreal.PlayerStart, V(-400, -300, 100), R(0, 0, 0)).set_actor_label("Partenza")
    EAS.spawn_actor_from_class(unreal.CameraActor, V(-600, 0, 300), R(-15, 0, 0)).set_actor_label("Fotocamera")   # the tests' photos
    EAS.spawn_actor_from_class(unreal.M80CarPiaggioSi, V(0, 0, 40), R(0, 0, 0)).set_actor_label("C_PiaggioSi")
    # On the road, its left side 11 cm from the kerb (the rider gets on standing on the sidewalk, 15 cm up).
    EAS.spawn_actor_from_class(unreal.M80CarPiaggioSi, V(0, -970, 40), R(0, 0, 0)).set_actor_label("C_PiaggioSi_Marciapiede")
    world.get_world_settings().set_editor_property("default_game_mode", unreal.M80GameMode.static_class())
    yield 10
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("ok " + MAP, encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
