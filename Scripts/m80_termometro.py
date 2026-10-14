"""The town's thermometer: how long Play takes and how heavy the town is, the same way every time, to compare engine
versions and to notice when new content costs too much.
Opens L_M80_Paese_WP, presses Play (in the viewport, as the user does) and times the phases until the player can move,
then in three places (where the player starts at noon, the Matrice square at 20:30 with the lamps on, a view from high
over the town at 20:30) waits for World Partition to finish loading, records 300 frames with the CSV profiler, the
editor's memory and the video memory, and takes a photo. Scalability is the editor's own (recorded, not changed).
Output: Saved/Mazzarino80/Termometro/<engine>_<date>.json and photos
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_termometro.py -ForceLit
"""
import ctypes
import ctypes.wintypes as wt
import datetime
import glob
import json
import math
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Termometro"
CSV_DIR = ROOT / "Saved/Profiling/CSV"
MATRICE = "M80_Recuperato_Matrice"
FRAMES = 300
V = unreal.Vector
SYS = unreal.SystemLibrary
K32 = ctypes.WinDLL("kernel32")
K32.GetCurrentProcess.restype = wt.HANDLE
K32.GetProcessTimes.argtypes = [wt.HANDLE] + [ctypes.POINTER(wt.FILETIME)] * 4


def process_age():
    """Seconds since the editor process started (how long the editor took to open before this script ran)."""
    times = [wt.FILETIME() for _ in range(4)]
    K32.GetProcessTimes(K32.GetCurrentProcess(), *[ctypes.pointer(t) for t in times])
    created = (times[0].dwHighDateTime << 32 | times[0].dwLowDateTime) / 1e7 - 11644473600
    return round(time.time() - created, 1)


def summarize(csv_path):
    """Average and 95th percentile of the main columns of one CSV capture."""
    lines = Path(csv_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    header = lines[0].split(",")
    rows = [line.split(",") for line in lines[1:] if line and not line.startswith("[")]
    wanted = {"FrameTime": "frame_ms", "GameThreadTime": "game_ms", "RenderThreadTime": "render_ms", "GPUTime": "gpu_ms",
              "RHI/DrawCalls": "draw_calls", "RHI/PrimitivesDrawn": "primitives"}
    out = {"frames": len(rows)}
    for column, key in wanted.items():
        if column not in header:
            continue
        i = header.index(column)
        vals = []
        for r in rows:
            try:
                vals.append(float(r[i]))
            except (IndexError, ValueError):
                pass
        if vals:
            vals.sort()
            out[key] = round(sum(vals) / len(vals), 2)
            out[key + "_p95"] = round(vals[max(0, int(len(vals) * 0.95) - 1)], 2)
    if out.get("frame_ms"):
        out["fps"] = round(1000.0 / out["frame_ms"], 1)
    return out


def look_rot(eye, at):
    d = at - eye
    return unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))


STREAMING_ERROR = []


def streaming_done(world):
    """World Partition's own answer when Python can reach it, else None (the reason is kept once)."""
    try:
        wp = unreal.SubsystemBlueprintLibrary.get_world_subsystem(world, unreal.WorldPartitionSubsystem)
        return bool(wp.is_all_streaming_completed())
    except Exception as e:  # noqa: BLE001
        if not STREAMING_ERROR:
            STREAMING_ERROR.append(repr(e))
        return None


def streaming_grids(world):
    """The World Partition runtime grids (cell size, loading range in m), when Python can read them."""
    try:
        wp = world.get_world_settings().get_editor_property("world_partition")
        grids = wp.get_editor_property("runtime_hash").get_editor_property("grids")
        return [{"name": str(g.get_editor_property("grid_name")), "cell_m": g.get_editor_property("cell_size") / 100,
                 "loading_range_m": g.get_editor_property("loading_range") / 100} for g in grids]
    except Exception as e:  # noqa: BLE001
        return repr(e)


# Python cannot ask World Partition whether it finished, so the wait is fixed: after Play the town keeps loading for
# a while (30 s measured 3 fps where 120 s measured 69).
def wait_streaming(world, report, key, limit=120.0):
    t0 = time.time()
    frames = 0
    while time.time() - t0 < limit:
        if streaming_done(world):
            break
        frames += 1
        yield 1
    report[key] = {"seconds": round(time.time() - t0, 1), "frames": frames, "completed": streaming_done(world)}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    version = SYS.get_engine_version()
    report = {"engine": version, "date": datetime.datetime.now().isoformat(timespec="seconds"),
              "editor_open_seconds": process_age(), "memory_editor_empty": m80_seq.memory()}
    tag = "%s_%s" % (version.split("-")[0], datetime.datetime.now().strftime("%Y%m%d_%H%M"))

    t0 = time.time()
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    report["map_open_seconds"] = round(time.time() - t0, 1)
    yield 60
    report["memory_map_open"] = m80_seq.memory()
    report["streaming_grids"] = streaming_grids(m80_seq.editor_world())
    # Where the Matrice square is: the recovered Matrice's frame (as in m80_matrice_test.py).
    descs = [d for d in m80_seq.actor_descs() if str(d.label) == MATRICE]
    if not descs:
        raise RuntimeError("No %s in the town" % MATRICE)
    m80_seq.load(descs)
    yield 30
    world = m80_seq.editor_world()
    old = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == MATRICE)
    t = old.get_actor_transform()

    def w(bx, by, bz):
        return t.transform_location(V(bx * 100.0, -by * 100.0, bz * 100.0))
    square, facade = w(0.5, -40.0, 0.0), w(0.5, -14.0, 9.0)
    high_eye, high_at = w(0.5, -160.0, 90.0), w(0.5, 120.0, 0.0)

    # Play, timed until the player stands on the ground.
    t0 = time.time()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    phases = {}
    game = pawn = None
    while time.time() - t0 < 900:
        yield 1
        game = game or unreal.EditorLevelLibrary.get_game_world()
        if game and "game_world" not in phases:
            phases["game_world"] = round(time.time() - t0, 1)
        if game and not pawn:
            pc = unreal.GameplayStatics.get_player_controller(game, 0)
            pawn = pc.get_controlled_pawn() if pc else None
            if pawn:
                phases["pawn"] = round(time.time() - t0, 1)
        if pawn and "streaming" not in phases and streaming_done(game) is not False:
            phases["streaming"] = round(time.time() - t0, 1)
        if pawn and "streaming" in phases:
            move = pawn.get_movement_component()
            if move and hasattr(move, "is_moving_on_ground") and move.is_moving_on_ground():
                phases["on_ground"] = round(time.time() - t0, 1)
                break
    report["play_seconds"] = phases
    report["streaming_api"] = STREAMING_ERROR[0] if STREAMING_ERROR else "ok"
    if not pawn:
        raise RuntimeError("Play did not give a player in 15 minutes")
    report["start_location"] = [round(c) for c in pawn.get_actor_location().to_tuple()]
    report["viewport"] = list(unreal.WidgetLayoutLibrary.get_viewport_size(game).to_tuple())
    report["scalability"] = {c: SYS.get_console_variable_int_value(c) for c in (
        "sg.ViewDistanceQuality", "sg.ShadowQuality", "sg.GlobalIlluminationQuality", "sg.ReflectionQuality",
        "sg.TextureQuality", "sg.EffectsQuality", "sg.FoliageQuality", "sg.ShadingQuality", "sg.PostProcessQuality")}
    report["screen_percentage"] = SYS.get_console_variable_float_value("r.ScreenPercentage")
    for c in ("t.MaxFPS 0", "r.VSync 0"):
        SYS.execute_console_command(game, c)
    atmo = unreal.GameplayStatics.get_all_actors_of_class(game, unreal.M80Atmosphere)
    for a in atmo:
        a.set_editor_property("bAdvanceInGame", False)
    pc = unreal.GameplayStatics.get_player_controller(game, 0)
    path = OUT / (tag + ".json")
    path.write_text(json.dumps(report, indent=1), encoding="utf-8")

    def place(name, hour, stand, look, fly=False):
        for a in atmo:
            a.set_hour(hour)
        if stand is not None:
            # High up the player flies (Python cannot spawn a camera in the game world): the view is his camera's.
            pawn.get_movement_component().set_movement_mode(unreal.MovementMode.MOVE_FLYING if fly else unreal.MovementMode.MOVE_WALKING)
            pawn.set_actor_location(V(stand.x, stand.y, stand.z + 120), False, True)
            pc.set_control_rotation(look_rot(stand, look))
        view = {"hour": hour}
        report.setdefault("views", {})[name] = view
        for s in wait_streaming(game, view, "streaming"):
            yield s
        yield 120
        before = set(glob.glob(str(CSV_DIR / "*.csv")))
        SYS.execute_console_command(game, "csvprofile start")
        yield FRAMES
        SYS.execute_console_command(game, "csvprofile stop")
        yield 60
        new = [p for p in glob.glob(str(CSV_DIR / "*.csv")) if p not in before]
        view.update(summarize(max(new, key=os.path.getmtime)) if new else {"error": "no csv"})
        view["memory"] = m80_seq.memory()
        since = time.time()
        SYS.execute_console_command(game, "HighResShot 1280x720")
        yield 30
        view["photo"] = bool(m80_seq.collect_screenshot(OUT / ("%s_%s.png" % (tag, name)), since - 1))
        path.write_text(json.dumps(report, indent=1), encoding="utf-8")

    for s in place("partenza_mezzogiorno", 12.0, None, None):
        yield s
    for s in place("piazza_matrice_sera", 20.5, square, facade):
        yield s
    for s in place("panorama_sera", 20.5, high_eye, high_at, fly=True):
        yield s
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "termometro_error.txt"))
