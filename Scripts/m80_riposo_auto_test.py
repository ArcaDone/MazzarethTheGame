"""Vehicles at rest away from the player (AM80Car dormant: no vehicle physics beyond 120 m, back within 100 m), in the drive
test map L_M80_ProvaGuida (Play In Editor): Vito is moved 200 m away, every vehicle must stop simulating and stay where it
was; Vito comes back, they simulate again, he gets in the Fiat 500 and drives it for 3 s.
Out: Saved/Mazzarino80/Veicoli/riposo_auto.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_riposo_auto_test.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Veicoli"
MAP = "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida"
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
r = {}


def now(world):
    return unreal.GameplayStatics.get_time_seconds(world)


def wait(world, seconds):
    t0 = now(world)
    while now(world) - t0 < seconds:
        yield 1


def state(cars):
    return {c.get_actor_label(): {"fisica": c.get_component_by_class(unreal.SkeletalMeshComponent).is_simulating_physics(),
                                  "z": round(c.get_actor_location().z, 1)} for c in cars}


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    LES.editor_request_begin_play()
    yield 30
    world = unreal.EditorLevelLibrary.get_game_world()
    while world is None or unreal.GameplayStatics.get_player_controller(world, 0) is None or \
            unreal.GameplayStatics.get_player_controller(world, 0).get_player_character() is None:
        yield 5
        world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    walker = pc.get_player_character()
    cars = sorted(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car), key=lambda c: c.get_actor_label())
    yield from wait(world, 3.0)
    r["vicino"] = state(cars)
    home = walker.get_actor_location()
    walker.set_actor_location(unreal.Vector(20000, 0, home.z), False, True)
    yield from wait(world, 3.0)
    r["lontano_200m"] = state(cars)
    walker.set_actor_location(home, False, True)
    yield from wait(world, 3.0)
    r["di_nuovo_vicino"] = state(cars)
    fiat = [c for c in cars if isinstance(c, unreal.M80CarFiat500)]
    if fiat:
        car = fiat[0]
        walker.set_actor_location(car.get_actor_location() - car.get_actor_right_vector() * 200 + unreal.Vector(0, 0, 90), False, True)
        yield from wait(world, 0.5)
        pc.interact()
        t0 = now(world)
        while now(world) - t0 < 12 and pc.get_controlled_pawn() != car:
            yield 1
        r["salito_500"] = pc.get_controlled_pawn() == car
        mv = car.get_component_by_class(unreal.ChaosWheeledVehicleMovementComponent)
        top = 0.0
        t0 = now(world)
        while r["salito_500"] and now(world) - t0 < 3.0:
            mv.set_throttle_input(1.0)
            top = max(top, abs(car.get_speed_kmh()))
            yield 1
        r["500_kmh_max"] = round(top, 1)
    r["vivo"] = True
    LES.editor_request_end_play()
    yield 30
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "riposo_auto.json").write_text(json.dumps(r, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "riposo_auto_errore.txt"))
