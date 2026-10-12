"""Combat test in L_M80_ProvaAzione (Play In Editor), photographed from the player's own camera (what the player sees):
on foot, aiming the Beretta at a wall (over-the-shoulder camera, crosshair), a burst (holes), walking and running with
the gun, the lupara aimed. Output: Saved/Mazzarino80/Player/Test/combattimento/*.png and combattimento.json.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_combattimento_test.py -ForceLit
"""
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
MAP = os.environ.get("M80_PLAY_MAP", "/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione")
OUT = ROOT / "Saved/Mazzarino80/Player/Test/combattimento"
W = unreal.M80Weapon


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    yield 30
    got = m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    report.setdefault("shots", []).append([name, bool(got)])


def wait(world, seconds, each=None):
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < seconds:
        if each:
            each()
        yield 1


def side(world, pc, pawn, name, report, each=None):
    """The character seen from its right side (a camera for a moment), to judge the poses."""
    cam = world_cam(world)
    base = pawn.get_actor_location()
    eye = base + pawn.get_actor_right_vector() * 260 + pawn.get_actor_forward_vector() * 80 + unreal.Vector(0, 0, 30)
    d = base - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    for s in wait(world, 0.1, each):
        yield s
    for s in shot(world, name, report):
        yield s
    pc.set_view_target_with_blend(pawn, 0.0)
    yield 2


def world_cam(world):
    """The CameraTest actor of the test map."""
    return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))[0]


def face_wall(world, pc, pawn):
    """Turns the player (and the control rotation) to the nearest wall 4-25 m away."""
    base = pawn.get_actor_location() + unreal.Vector(0, 0, 40)
    best = None
    for k in range(36):
        a = math.radians(k * 10)
        d = unreal.Vector(math.cos(a), math.sin(a), 0)
        h = unreal.SystemLibrary.line_trace_single(world, base, base + d * 2500, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn],
                                                   unreal.DrawDebugTrace.NONE, True)
        t = h.to_tuple() if h else None
        if t and t[0]:
            dist = (t[4] - base).length()
            if 400 < dist and (best is None or dist < best[0]):
                best = (dist, k * 10.0)
    yaw = best[1] if best else 0.0
    pc.set_control_rotation(unreal.Rotator(0, -5, yaw))
    pawn.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    return best[0] if best else None


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {"map": MAP}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 600
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world:
        raise RuntimeError("PIE did not start")
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = pc.get_controlled_pawn()
    inv = pc.get_inventory()
    report["camera_manager"] = pc.player_camera_manager.get_class().get_name()
    report["wall_m"] = round((face_wall(world, pc, pawn) or 0) / 100, 1)
    for s in wait(world, 1.0):
        yield s
    for s in shot(world, "01_a_piedi", report):
        yield s
    inv.give(W.BERETTA, 60, True)
    for s in wait(world, 0.8):
        yield s
    for s in shot(world, "02_pistola_in_mano", report):
        yield s
    # Aiming (right mouse held), then a burst while aiming.
    pc.set_aim_held(True)
    for s in wait(world, 0.8):
        yield s
    report["aiming"] = pc.is_aiming()
    for s in shot(world, "03_pistola_mira", report):
        yield s
    for s in side(world, pc, pawn, "03b_pistola_mira_lato", report):
        yield s
    pc.set_fire(True)
    for s in wait(world, 0.8):
        yield s
    pc.set_fire(False)
    for s in shot(world, "04_fori_nel_muro", report):
        yield s
    pc.set_aim_held(False)
    for s in wait(world, 0.6):
        yield s
    # Walking and running with the gun, from the player's camera and from the side.
    yaw = pawn.get_actor_rotation().yaw
    back = unreal.Rotator(0, -10, yaw + 180)
    pc.set_control_rotation(back)

    def walk():
        pawn.add_movement_input(pawn.get_actor_forward_vector() * -1.0, 1.0, False)
    for s in wait(world, 1.2, walk):
        yield s
    for s in shot(world, "05_cammina_armato", report):
        yield s
    for s in side(world, pc, pawn, "05b_cammina_armato_lato", report, walk):
        yield s
    pc.set_character_sprint(True)
    for s in wait(world, 1.0, walk):
        yield s
    for s in shot(world, "06_corre_armato", report):
        yield s
    for s in side(world, pc, pawn, "06b_corre_armato_lato", report, walk):
        yield s
    pc.set_character_sprint(False)
    for s in wait(world, 1.0):
        yield s
    face_wall(world, pc, pawn)
    inv.give(W.LUPARA, 20, True)
    for s in wait(world, 0.6):
        yield s
    pc.set_aim_held(True)
    for s in wait(world, 0.8):
        yield s
    for s in shot(world, "07_lupara_mira", report):
        yield s
    for s in side(world, pc, pawn, "07b_lupara_mira_lato", report):
        yield s
    pc.set_aim_held(False)
    report["aim_point_m"] = round((pc.get_aim_point() - pawn.get_actor_location()).length() / 100, 1)
    (OUT / "combattimento.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "error.txt"))
