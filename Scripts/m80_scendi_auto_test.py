"""Getting out of the Carabinieri's Alfa 155 (AM80CarAlfa155, behind the Fiat 500) in the town L_M80_Paese_WP, Play In Editor:
Vito gets in and out three times; after each getting out it watches him for 8 s: the controller's state, the climbing
component's state (it once caught the car's own side as a ledge and the capsule, pulled into the car, threw him into
the air), how high his feet rise over the car's base, dead or not. Nothing is saved.
Out: Saved/Mazzarino80/Veicoli/scendi_auto.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_scendi_auto_test.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Veicoli"
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
r = {"giri": []}


def save():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "scendi_auto.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


def now(world):
    return unreal.GameplayStatics.get_time_seconds(world)


def name(v):
    return str(v).split(".")[-1].split(":")[0].split(">")[0].strip()


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    LES.editor_request_begin_play()
    yield 30
    world = unreal.EditorLevelLibrary.get_game_world()
    while world is None or unreal.GameplayStatics.get_player_controller(world, 0) is None or \
            unreal.GameplayStatics.get_player_controller(world, 0).get_player_character() is None:
        yield 5
        world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    # Let the town around the car come in.
    t0 = now(world)
    while now(world) - t0 < 20:
        yield 5
    cars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80CarAlfa155)
    r["alfa"] = len(cars)
    if not cars:
        save()
        LES.editor_request_end_play()
        return
    car = cars[0]
    for giro in range(3):
        g = {"giro": giro + 1}
        r["giri"].append(g)
        walker = pc.get_player_character()
        door = car.get_actor_location() - car.get_actor_right_vector() * 220 + unreal.Vector(0, 0, 80)
        walker.set_actor_location(door, False, True)
        for _ in range(20):
            yield 1
        pc.interact()
        t0 = now(world)
        while now(world) - t0 < 12 and pc.get_controlled_pawn() != car:
            yield 1
        g["guida"] = pc.get_controlled_pawn() == car
        if not g["guida"]:
            break
        t0 = now(world)
        while now(world) - t0 < 2:
            yield 1
        ground = car.get_actor_location().z
        pc.interact()
        climb = walker.get_component_by_class(unreal.M80ClimbComponent)
        vitals = walker.get_component_by_class(unreal.M80VitalsComponent)
        half = walker.capsule_component.get_scaled_capsule_half_height()
        rise, states, climbs = -1e9, [], []
        t0 = now(world)
        while now(world) - t0 < 8:
            feet = walker.get_actor_location().z - half
            rise = max(rise, feet - ground)
            s, c = name(pc.get_editor_property("state")), name(climb.get_state()) if climb else "-"
            if not states or states[-1] != s:
                states.append(s)
            if not climbs or climbs[-1] != c:
                climbs.append(c)
            yield 1
        g.update({"stati": states, "arrampicata": climbs, "piedi_max_sopra_strada_cm": round(rise),
                  "morto": vitals.is_dead() if vitals else None,
                  "dist_auto_cm": round((walker.get_actor_location() - car.get_actor_location()).length())})
        save()
        if g["morto"]:
            break
    save()
    LES.editor_request_end_play()
    yield 30


m80_seq.Sequencer(steps(), log_file=str(OUT / "scendi_auto_errore.txt"))
