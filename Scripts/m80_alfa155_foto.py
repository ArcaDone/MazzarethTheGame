"""Photos of the Carabinieri's Alfa 155 as imported (AM80CarAlfa155) in the drive test map L_M80_ProvaGuida: one spawned
for the photos, front three-quarter, side, back, roof; nothing is saved.
Out: Saved/Mazzarino80/Veicoli/Alfa155/UE/*.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_alfa155_foto.py -ForceLit
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Veicoli/Alfa155/UE"
MAP = "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AT = unreal.Vector(0, -2500, 40)
# Eye offsets from the car (front is +X, left -Y), cm.
VIEWS = {
    "1_tre_quarti_davanti": ((420, -380, 170), (0, 0, 70)),
    "2_fianco": ((0, -700, 120), (0, 0, 70)),
    "3_tre_quarti_dietro": ((-430, 360, 180), (0, 0, 70)),
    "4_tetto": ((150, -250, 330), (-20, 0, 140)),
}


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    car = EAS.spawn_actor_from_class(unreal.M80CarAlfa155, AT, unreal.Rotator(0, 0, 0))
    yield 200
    cap = m80_seq.ViewCapture(1600, 900, 60.0)
    for name, (eye, tgt) in VIEWS.items():
        e = AT + unreal.Vector(*eye)
        rot = unreal.MathLibrary.find_look_at_rotation(e, AT + unreal.Vector(*tgt))
        cap.capture(e, rot, OUT / (name + ".png"))
        yield 3
    yield 100
    for name, (eye, tgt) in VIEWS.items():
        e = AT + unreal.Vector(*eye)
        rot = unreal.MathLibrary.find_look_at_rotation(e, AT + unreal.Vector(*tgt))
        cap.capture(e, rot, OUT / (name + ".png"))
        yield 3
    cap.destroy()
    EAS.destroy_actor(car)


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
