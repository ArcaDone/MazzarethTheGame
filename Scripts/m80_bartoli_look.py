"""Quick look at Palazzo Bartoli in its own level (L_M80_PalazzoBartoli, m80_bartoli_import.py): a few views of the
Corso facades and the courtyard. Out: Saved/Mazzarino80/Bartoli/Livello/<view>.png

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bartoli_look.py -ForceLit
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Bartoli/Livello"
MAP = "/Game/Mazzarino80/Buildings/Bartoli/L_M80_PalazzoBartoli"
# Local metres of the lot (x east, y north, z above the lot origin): eye, target, horizontal fov.
VIEWS = {
    "corso_fronte": ((-1.1, -46.5, 2.5), (-2.0, -29.4, 7.1), 62),
    "corso_vicino": ((3.0, -36.0, 2.5), (-3.0, -29.0, 5.0), 75),
    "portale": ((4.5, -33.0, 2.5), (3.4, -27.6, 4.0), 60),
    "radente": ((-16.0, -38.0, 2.5), (2.0, -28.5, 6.0), 55),
    "aereo": ((40.0, -70.0, 45.0), (0.0, -5.0, 6.0), 55),
}
MANIFEST = os.environ.get("M80_BARTOLI_MANIFEST", "M80_Bartoli.json")


def steps():
    m = json.loads((ROOT / "Saved/Mazzarino80/Bartoli/Export" / MANIFEST).read_text(encoding="utf-8"))
    ox, oy, oz = m["origin_world_cm"]
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    # Scene captures do not drive texture streaming: load every mip so the baked detail shows.
    m80_seq.console("r.TextureStreaming 0")
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight):
            a.set_actor_rotation(unreal.Rotator(pitch=-40.0, yaw=-110.0, roll=0.0), False)
    yield 400
    for _ in range(2):
        for name, (eye, target, fov) in VIEWS.items():
            e = unreal.Vector(ox + eye[0] * 100, oy - eye[1] * 100, oz + eye[2] * 100)
            t = unreal.Vector(ox + target[0] * 100, oy - target[1] * 100, oz + target[2] * 100)
            cap = m80_seq.ViewCapture(1600, 900, fov)
            cap.capture(e, unreal.MathLibrary.find_look_at_rotation(e, t), OUT / ("%s.png" % name))
            cap.destroy()
            yield 2
        yield 200


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
