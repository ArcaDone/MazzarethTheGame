"""Puts the Carabinieri's Alfa 155 (AM80CarAlfa155) in the town (L_M80_Paese_WP): 6.5 m behind the parked Fiat 500
(Auto_Fiat500), facing the same way, on the ground (the first place, the route's start by the Matrice, was inside the
church and the car caught fire). An earlier one (label Auto_Alfa155_Carabinieri) is moved, not doubled. Cars are not
spatially loaded, so it is there whatever region is loaded.
Out: Saved/Mazzarino80/Veicoli/posiziona_alfa155.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_alfa155_posiziona.py
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
OUT = ROOT / "Saved/Mazzarino80/Veicoli"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LABEL = "Auto_Alfa155_Carabinieri"


def ground(world, x, y):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 40000), unreal.Vector(x, y, -10000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    return hit.to_tuple()[4].z if hit and hit.to_tuple()[0] else None


def steps():
    report = {}
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    m80_seq.load([d for d in descs if "Landscape" in (d.get_editor_property("native_class").get_name()
                                                      if d.get_editor_property("native_class") else "")])
    yield 60
    fiat = [x for x in EAS.get_all_level_actors() if x.get_class().get_name() == "M80CarFiat500"]
    report["fiat500"] = [[round(f.get_actor_location().x), round(f.get_actor_location().y)] for f in fiat]
    # The 500 nearest the Matrice.
    f = min(fiat, key=lambda c: (c.get_actor_location().x - 82000) ** 2 + (c.get_actor_location().y - 4000) ** 2)
    yaw = f.get_actor_rotation().yaw
    a = f.get_actor_location() - f.get_actor_forward_vector() * 650
    world = unreal.EditorLevelLibrary.get_editor_world()
    z = ground(world, a.x, a.y)
    report["ground_z"] = z
    loc = unreal.Vector(a.x, a.y, (z if z is not None else a.z) + 40)
    old = [x for x in EAS.get_all_level_actors() if x.get_actor_label() == LABEL]
    car = old[0] if old else EAS.spawn_actor_from_class(unreal.M80CarAlfa155, loc, unreal.Rotator(0, 0, yaw))
    car.set_actor_location_and_rotation(loc, unreal.Rotator(0, 0, yaw), False, True)
    car.set_actor_label(LABEL)
    car.set_folder_path("Veicoli")
    report["at"] = [round(loc.x), round(loc.y), round(loc.z)]
    report["yaw"] = round(yaw, 1)
    report["moved_existing"] = bool(old)
    report["saved"] = unreal.EditorLoadingAndSavingUtils.save_packages([car.get_outermost()], False)
    report["package"] = car.get_outermost().get_name()
    yield 5
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "posiziona_alfa155.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "posiziona_alfa155_errore.txt"))
