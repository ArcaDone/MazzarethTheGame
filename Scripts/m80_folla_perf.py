"""Crowd performance test in L_M80_ProvaFolla (Play In Editor): townspeople (AM80Pedone, the whole cast in turn)
walking about the square in steps of PASSO, frame time measured at each step; how many are actually walking (the
navigation mesh works); side photos of an old man and an old woman (the bent back) next to a young one, and a view of
the square. The level gets a navigation mesh first if it has none (saved with it).
Env M80_PASSI=0,21,42,63,84 (pedestrians at each step), M80_MISURA=6 (seconds measured per step).
Out: Saved/Mazzarino80/Folla/Perf/perf.json + *.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_perf.py -ForceLit -TimeoutMinutes 40
"""
import glob
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
OUT = ROOT / "Saved/Mazzarino80/Folla/Perf"
V = unreal.Vector
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CAST = ["Anziano1", "Anziana1", "Uomo1", "Donna1", "Ragazzo1", "Ragazza1", "Anziano2", "Anziana2", "Uomo2", "Donna2",
        "Ragazzo2", "Ragazza2", "Anziano3", "Anziana3", "Uomo3", "Donna3", "Ragazzo3", "Ragazza3", "Anziano4", "Anziana4",
        "Uomo4"]
STEPS = [int(x) for x in os.environ.get("M80_PASSI", "0,21,42,63,84").split(",")]
MEASURE = float(os.environ.get("M80_MISURA", "6"))
CSV_DIR = ROOT / "Saved/Profiling/CSV"
HALF = 7000.0   # the floor of the test map is about 146 m across


def summarize(csv_path):
    """Means of the CSV profiler's main columns (as m80_termometro.py) and the heaviest game-thread parts."""
    lines = Path(csv_path).read_text(encoding="utf-8", errors="ignore").splitlines()
    header = lines[0].split(",")
    rows = [line.split(",") for line in lines[1:] if line and not line.startswith("[")]

    def mean(i):
        vals = []
        for r in rows:
            try:
                vals.append(float(r[i]))
            except (IndexError, ValueError):
                pass
        return round(sum(vals) / len(vals), 2) if vals else None

    out = {"csv_frames": len(rows)}
    for column, key in {"FrameTime": "frame_ms", "GameThreadTime": "game_ms", "RenderThreadTime": "render_ms",
                        "GPUTime": "gpu_ms", "RHI/DrawCalls": "draw_calls", "RHI/PrimitivesDrawn": "primitives"}.items():
        if column in header:
            out[key] = mean(header.index(column))
    parts = [(c, mean(i)) for i, c in enumerate(header) if c.startswith("Exclusive/GameThread/")]
    out["game_parts"] = sorted([p for p in parts if p[1]], key=lambda p: -p[1])[:12]
    return out


def now(world):
    return unreal.GameplayStatics.get_real_time_seconds(world)


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    yield 30
    report.setdefault("shots", []).append([name, bool(m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1))])


def look(world, pc, at, eye, name, report):
    cams = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))
    cam = cams[0] if cams else world.spawn_actor(unreal.CameraActor, eye, unreal.Rotator())
    cam.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, at), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    yield 3
    for s in shot(world, name, report):
        yield s
    pc.set_view_target_with_blend(pc.get_controlled_pawn(), 0.0)
    yield 2


def ensure_nav(report):
    world = m80_seq.editor_world()
    if list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.NavMeshBoundsVolume)):
        report["nav"] = "present"
    else:
        vol = EAS.spawn_actor_from_class(unreal.NavMeshBoundsVolume, V(0, 0, 300))
        vol.set_actor_scale3d(V(HALF * 2 / 200.0, HALF * 2 / 200.0, 1500 / 200.0))
        vol.set_actor_label("Navigazione_Folla")
        report["nav"] = "made"
    # Built now and saved with the level: Play has the navigation mesh from the start.
    report["nav_built"] = unreal.M80Pedone.build_navigation(world)


def spots():
    """Where people start: around the square's marker points (tables, chairs, groups, the walk, the games)."""
    world = m80_seq.editor_world()
    out = []
    for tag in ("M80Folla_Giro", "M80Folla_Gruppo", "M80Folla_Gioco", "M80Folla_Sedia", "M80Folla_Tavolo"):
        out += [a.get_actor_location() for a in unreal.GameplayStatics.get_all_actors_with_tag(world, tag)]
    return out or [V(0, 0, 0)]


def spawn(world, name, rng, where, report):
    base = rng.choice(where)
    loc = V(base.x + rng.uniform(-250, 250), base.y + rng.uniform(-250, 250), base.z)
    t = unreal.Transform(loc + V(0, 0, 95), unreal.Rotator(0, 0, rng.uniform(0, 360)))
    a = unreal.M80Pedone.spawn_pedone(world, name, t)
    if not a:
        report.setdefault("spawn_failed", []).append(name)
    return a


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {"steps": []}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    ensure_nav(report)
    yield 30
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10
    where = spots()
    report["spots"] = len(where)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 300
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    for atmo in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere):
        atmo.set_editor_property("bAdvanceInGame", False)
        atmo.set_hour(16.0)
    for cmd in ("t.MaxFPS 0", "r.VSync 0"):
        unreal.SystemLibrary.execute_console_command(world, cmd)
    rng = random.Random(7)
    people = []
    for n in STEPS:
        while len(people) < n:
            people.append(spawn(world, CAST[len(people) % len(CAST)], rng, where, report))
            if len(people) % 7 == 0:
                yield 1
        # Settle (streaming, first paths), then measure.
        t0 = now(world)
        while now(world) - t0 < 6.0:
            yield 1
        frames = []
        t0 = now(world)
        last = t0
        while now(world) - t0 < MEASURE:
            yield 1
            t = now(world)
            frames.append(t - last)
            last = t
        frames.sort()
        people = [a for a in people if a]
        walking = sum(1 for a in people if a.get_velocity().length() > 20)
        step = {"people": len(people), "walking": walking, "frames": len(frames),
                "ms_mean": round(1000 * sum(frames) / max(1, len(frames)), 2),
                "ms_p95": round(1000 * frames[int(len(frames) * 0.95)], 2) if frames else None}
        step["fps"] = round(1000 / step["ms_mean"], 1) if step["ms_mean"] else None
        before = set(glob.glob(str(CSV_DIR / "*.csv")))
        unreal.SystemLibrary.execute_console_command(world, "csvprofile start")
        yield 120
        unreal.SystemLibrary.execute_console_command(world, "csvprofile stop")
        yield 60
        new = [p for p in glob.glob(str(CSV_DIR / "*.csv")) if p not in before]
        step.update(summarize(max(new, key=os.path.getmtime)) if new else {"csv": "none"})
        report["steps"].append(step)
        (OUT / "perf.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        if len(people) >= 21 and "foto" not in report:
            report["foto"] = True
            # The bent old: an old man, an old woman and a young man, each from the side.
            for key in ("Anziano2", "Anziana1", "Ragazzo2"):
                a = next((p for p in people if str(p.get_editor_property("personaggio")) == key), None)
                if not a:
                    continue
                loc = a.get_actor_location()
                side = a.get_actor_right_vector()
                for s in look(world, pc, loc + V(0, 0, 10), loc + side * 330 + V(0, 0, 30), "fianco_" + key, report):
                    yield s
                for s in look(world, pc, loc + V(0, 0, 10), loc + a.get_actor_forward_vector() * 300 + V(0, 0, 40),
                              "fronte_" + key, report):
                    yield s
        if len(people) >= 42 and "vista" not in report:
            report["vista"] = True
            for s in look(world, pc, V(0, 0, 0), V(-2600, -2600, 1300), "piazza", report):
                yield s
    (OUT / "perf.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "perf_errore.txt"))
