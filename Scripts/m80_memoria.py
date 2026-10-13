"""Where the editor's memory goes in the town: opens L_M80_Paese_WP, counts the loaded actors by class and writes a
"memreport -full" (objects by class, textures, meshes, render targets), then presses Play and writes another one once
the player stands on the ground. Nothing is saved.
Output: Saved/Mazzarino80/Memoria/<engine>_<date>.json (actor counts, RAM) and Saved/Profiling/MemReports/*.memreport
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_memoria.py -TimeoutMinutes 40
"""
import collections
import datetime
import glob
import json
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Memoria"
REPORTS = ROOT / "Saved/Profiling/MemReports"
SYS = unreal.SystemLibrary


def actor_counts(world):
    by_class = collections.Counter()
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        by_class[a.get_class().get_name()] += 1
    return dict(by_class.most_common(25)), sum(by_class.values())


def memreport(world, report, key):
    before = set(glob.glob(str(REPORTS / "**/*.memreport"), recursive=True))
    SYS.execute_console_command(world, "memreport -full")
    for _ in range(120):
        yield 30
        new = [p for p in glob.glob(str(REPORTS / "**/*.memreport"), recursive=True) if p not in before]
        if new:
            report[key] = max(new, key=os.path.getmtime)
            return
    report[key] = None


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    version = SYS.get_engine_version()
    tag = "%s_%s" % (version.split("-")[0], datetime.datetime.now().strftime("%Y%m%d_%H%M"))
    report = {"engine": version, "memory_editor_empty": m80_seq.memory()}
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 120
    world = m80_seq.editor_world()
    report["memory_map_open"] = m80_seq.memory()
    report["editor_actors_by_class"], report["editor_actors"] = actor_counts(world)
    for s in memreport(world, report, "memreport_map_open"):
        yield s

    t0 = time.time()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    pawn = None
    while time.time() - t0 < 900:
        yield 10
        game = unreal.EditorLevelLibrary.get_game_world()
        pc = unreal.GameplayStatics.get_player_controller(game, 0) if game else None
        pawn = pc.get_controlled_pawn() if pc else None
        move = pawn.get_movement_component() if pawn else None
        if move and move.is_moving_on_ground():
            break
    report["play_seconds"] = round(time.time() - t0, 1)
    yield 300
    report["memory_play"] = m80_seq.memory()
    report["game_actors_by_class"], report["game_actors"] = actor_counts(game)
    for s in memreport(game, report, "memreport_play"):
        yield s
    (OUT / (tag + ".json")).write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "memoria_error.txt"))
