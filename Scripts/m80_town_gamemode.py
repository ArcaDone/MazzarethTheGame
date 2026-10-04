"""Sets the town map's GameMode Override to "Mazzarino 80 (gioco)" (AM80GameMode) and saves it."""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

MAP = os.environ.get("M80_GM_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Player/gamemode.txt"


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("wrong map")
    yield 30
    ws = world.get_world_settings()
    before = ws.get_editor_property("default_game_mode")
    ws.set_editor_property("default_game_mode", unreal.M80GameMode)
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    OUT.write_text("before %s after %s" % (before, ws.get_editor_property("default_game_mode")), encoding="utf-8")
    yield 5


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
