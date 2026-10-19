"""Screenshot of the town (L_M80_Paese_WP) in Play In Editor from where Vito starts, 40 s after Play: to compare with
the packaged game's view from the same place.
Out: Saved/Mazzarino80/Cotto/partenza_pie.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_foto_partenza_pie.py -ForceLit
"""
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Cotto"


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 30
    world = unreal.EditorLevelLibrary.get_game_world()
    while world is None or unreal.GameplayStatics.get_player_controller(world, 0) is None:
        yield 5
        world = unreal.EditorLevelLibrary.get_game_world()
    t0 = time.time()
    while time.time() - t0 < 40:
        yield 5
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    for _ in range(30):
        yield 1
    m80_seq.collect_screenshot(OUT / "partenza_pie.png", since - 1)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(steps(), log_file=str(OUT / "partenza_pie_errore.txt"))
