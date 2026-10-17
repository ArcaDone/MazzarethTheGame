"""Parks the drivable town cars in L_M80_ProvaFolla (Fiat 500, Mini, Maggiolino, Golf GTI, BMW M3): the townspeople take
the free ones for a drive (AM80Pedone::VaiAGuidare), the player can take any of them. Spots on the open ground of the square
and the streets around it, clear of houses, tables and chairs (box overlap), on the ground (trace). Run again: the cars
placed before (tag M80Folla_Auto) are replaced.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_auto.py -TimeoutMinutes 15
Report: Saved/Mazzarino80/Folla/auto.json
"""
import json
import math
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CARS = [unreal.M80CarFiat500, unreal.M80CarMaggiolino, unreal.M80CarMini, unreal.M80CarGolf, unreal.M80CarM3]
TAG = "M80Folla_Auto"
REPORT = os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/Folla/auto.json")
V = unreal.Vector
report = {"cars": {}}


def free(world, at, yaw):
    """Room for a car (5 x 2.4 m, 1.6 m high) at `at` turned by yaw, and ground under its middle."""
    hit = unreal.SystemLibrary.line_trace_single(world, at + V(0, 0, 300), at - V(0, 0, 300),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    ground = hit.to_tuple()[4].z   # location
    # The box is axis-aligned: cars stand along X or Y only, so the extent swaps with the yaw.
    ext = V(260, 130, 80) if abs(math.sin(math.radians(yaw))) < 0.5 else V(130, 260, 80)
    types = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2,
             unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY5]
    # (A bool and an out array in C++: Python gets the array, or None when nothing overlaps.)
    actors = unreal.SystemLibrary.box_overlap_actors(world, V(at.x, at.y, ground + 100), ext, types, None, [])
    others = [a for a in (actors or []) if a.get_actor_label() != "Pavimento" and not isinstance(a, unreal.M80Folla)]
    return None if others else ground


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    for a in unreal.GameplayStatics.get_all_actors_with_tag(world, TAG):
        EAS.destroy_actor(a)
    yield 5
    spots = []
    # Rings around the square's middle (the card tables are there), from the inside out.
    for r in range(900, 2600, 150):
        for k in range(24):
            a = math.radians(k * 15)
            spots.append((V(math.cos(a) * r, math.sin(a) * r, 0), k * 15))
    placed = []
    for cls in CARS:
        for at, ang in spots:
            if any((at - p).length() < 700 for p in placed):
                continue
            # Parked along the ring (tangent), as along a kerb.
            yaw = round((ang + 90) / 90) * 90 % 360
            ground = free(world, at, yaw)
            if ground is None:
                continue
            car = EAS.spawn_actor_from_class(cls, V(at.x, at.y, ground + 40), unreal.Rotator(0, 0, yaw))
            if not car:
                continue
            car.tags = [unreal.Name(TAG)]
            car.set_actor_label("Auto_" + cls.__name__.replace("M80Car", ""))
            placed.append(at)
            report["cars"][car.get_actor_label()] = [round(at.x), round(at.y), round(ground), yaw]
            break
        yield 2
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)


m80_seq.Sequencer(run(), log_file=REPORT.replace(".json", "_errore.txt"))
