"""Night test of the recovered lamp kinds of "Lampione (Mazzarino)" (Lamp_city, Lampione della Madonna) next to the town's
pole lamp, in L_M80_ProvaCarretti (it has the Atmosfera): placed for the photos only, the map is not saved.
Photos at 21:00 and at noon (glass off) to Saved/Mazzarino80/Lampioni/*.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_lampioni_prova.py -ForceLit
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Lampioni"
MAP = "/Game/Mazzarino80/Vehicles/Maps/L_M80_ProvaCarretti"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector
K = unreal.M80LampKind


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    atmo = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere)[0]
    lamps = []
    for x, kind in ((1000, K.POLE), (1500, K.CITY), (2000, K.GARDEN)):
        a = EAS.spawn_actor_from_class(unreal.M80StreetLight, V(x, 1500, 0))
        a.set_editor_property("kind", kind)
        lamps.append(a)
    views = {"insieme": (V(1500, 300, 260), V(1500, 1500, 170)),
             "lamp_city": (V(1500, 1050, 230), V(1500, 1500, 200)),
             "lampione_madonna": (V(2000, 1180, 160), V(2000, 1500, 120))}
    for hour, tag in ((21.0, "notte"), (12.0, "giorno")):
        atmo.set_hour(hour)
        yield 200
        cap = m80_seq.ViewCapture(1600, 900, 60)
        for name, (eye, at) in views.items():
            rot = unreal.MathLibrary.find_look_at_rotation(eye, at)
            m80_seq.set_view(eye, rot)
            yield 30
            cap.capture(eye, rot, OUT / ("%s_%s.png" % (name, tag)))
            yield 2
        cap.destroy()
    for a in lamps:
        a.destroy_actor()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)


m80_seq.Sequencer(steps(), log_file=str(OUT / "prova_error.txt"))
