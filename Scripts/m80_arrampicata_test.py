"""Climbing test in L_M80_ProvaAzione (Play In Editor): climbing onto the Fiat 126 (mantle), jumping to a high ledge of a
house (a balcony, a terrace, a low roof) and hanging from it, moving along it both ways, climbing up onto it, and
letting go of another one. Photographed from the side and from the player's camera.
Output: Saved/Mazzarino80/Player/Test/arrampicata/*.png and arrampicata.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_arrampicata_test.py -ForceLit
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
MAP = "/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione"
OUT = ROOT / "Saved/Mazzarino80/Player/Test/arrampicata"
V = unreal.Vector


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


def side(world, pc, pawn, name, report, dist=420, up=60):
    cam = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))[0]
    base = pawn.get_actor_location()
    eye = base + pawn.get_actor_right_vector() * dist - pawn.get_actor_forward_vector() * 120 + V(0, 0, up)
    d = base - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    yield 2
    for s in shot(world, name, report):
        yield s
    pc.set_view_target_with_blend(pawn, 0.0)
    yield 2


def trace(world, a, b, ignore):
    h = unreal.SystemLibrary.line_trace_single(world, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore, unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple() if h else None
    return t if t and t[0] else None


def ledge_of(res):
    """FindLedge from Python: (bool, ledge) or the ledge alone."""
    if isinstance(res, tuple):
        return res[1] if res[0] else None
    return res


def place(world, pawn, x, y, yaw):
    """Puts the player there facing yaw (the sample turns the character to the camera: the control rotation too)."""
    g = trace(world, V(x, y, 3000), V(x, y, -500), [pawn])
    if not g:
        return False
    pawn.set_actor_location(V(x, y, g[4].z + 92), False, True)
    pawn.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    unreal.GameplayStatics.get_player_controller(world, 0).set_control_rotation(unreal.Rotator(0, -10, yaw))
    return True


def find_spot(world, pawn, climb, lo, hi, need_room, skip=()):
    """A street spot facing a ledge lo-hi cm high (room on top when need_room)."""
    start = pawn.get_actor_location()
    for r in range(150, 3500, 150):
        for k in range(0, 360, 20):
            a = math.radians(k)
            x, y = start.x + math.cos(a) * r, start.y + math.sin(a) * r
            if any(math.hypot(x - sx, y - sy) < 400 for sx, sy in skip):
                continue
            for yaw in range(0, 360, 45):
                if not place(world, pawn, x, y, yaw):
                    break
                ledge = ledge_of(climb.find_ledge(lo, hi))
                if ledge and (ledge.get_editor_property("bRoomOnTop") or not need_room):
                    return x, y, yaw, ledge
    return None


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 600
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = pc.get_controlled_pawn()
    climb = pc.get_climb()
    report["climb_component"] = bool(climb)

    # 1) Onto the Fiat 126.
    cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car))
    if cars:
        car = cars[0]
        c = car.get_actor_location()
        side_dir = car.get_actor_right_vector()
        x, y = c.x + side_dir.x * 160, c.y + side_dir.y * 160
        yaw = math.degrees(math.atan2(-side_dir.y, -side_dir.x))
        place(world, pawn, x, y, yaw)
        for s in wait(world, 0.5):
            yield s
        ledge = ledge_of(climb.find_ledge(50, 260))
        report["car_ledge_cm"] = round(ledge.get_editor_property("Height")) if ledge else None
        report["car_debug"] = climb.get_editor_property("Debug")
        hit = trace(world, pawn.get_actor_location(), c, [pawn])
        report["car_trace"] = [hit[9].get_name() if hit and hit[9] else None, round((hit[4] - pawn.get_actor_location()).length()) if hit else None]
        report["car_mantle_started"] = climb.jump_pressed()
        track = []

        def follow():
            p = pawn.get_actor_location()
            track.append([round(p.z - 92 - c.z), str(climb.get_state()).split(".")[-1][:8], round((car.get_actor_location() - c).length())])
        for s in wait(world, 0.45, follow):
            yield s
        for s in side(world, pc, pawn, "01_sale_sull_auto_meta", report):
            yield s
        for s in wait(world, 1.4, follow):
            yield s
        report["car_track"] = track[::3]
        report["car_after"] = {"state": str(climb.get_state()), "feet_above_car_cm": round(pawn.get_actor_location().z - 92 - c.z),
                               "car_moved_cm": round((car.get_actor_location() - c).length())}
        for s in side(world, pc, pawn, "02_sopra_l_auto", report):
            yield s
        if os.environ.get("M80_SOLO_AUTO"):
            (OUT / "arrampicata.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
            return

    # 1a) The test blocks: mantle onto 1 m and 2.2 m, jump to the 2.9 m one, hang, climb onto it.
    blocks = {b.get_actor_label(): b for b in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor) if b.get_actor_label().startswith("Prova_")}
    report["blocks"] = sorted(blocks)
    for name in ("Prova_Muretto_1m", "Prova_Muro_2_2m", "Prova_Blocco_2_9m"):
        b = blocks.get(name)
        if not b:
            continue
        o, e = b.get_actor_bounds(False)
        x, y = o.x - e.x - 70, o.y
        place(world, pawn, x, y, 0.0)
        for s in wait(world, 0.4):
            yield s
        row = {"jump": climb.jump_pressed(), "debug": climb.get_editor_property("Debug")}
        trk = []
        for s in wait(world, 0.6, lambda: trk.append([round(pawn.get_actor_location().z - 92), str(climb.get_state())[-12:]])):
            yield s
        for s in side(world, pc, pawn, "00_%s_meta" % name[6:], report):
            yield s
        for s in wait(world, 1.6, lambda: trk.append([round(pawn.get_actor_location().z - 92), str(climb.get_state())[-12:]])):
            yield s
        if "HANGING" in str(climb.get_state()):
            row["hang_then_up"] = climb.jump_pressed()
            for s in wait(world, 1.6, lambda: trk.append([round(pawn.get_actor_location().z - 92), str(climb.get_state())[-12:]])):
                yield s
        row["track"] = trk[::10]
        row["feet_above_ground"] = round(pawn.get_actor_location().z - 92 - (o.z - e.z))
        row["top"] = round(2 * e.z)
        report[name] = row
        for s in side(world, pc, pawn, "00_%s_fine" % name[6:], report):
            yield s

    # 1b) Does LaunchCharacter move the sample character at all?
    z0 = pawn.get_actor_location().z
    pawn.launch_character(V(0, 0, 650), False, True)
    for s in wait(world, 0.3):
        yield s
    report["launch_probe_cm"] = round(pawn.get_actor_location().z - z0)
    for s in wait(world, 1.2):
        yield s

    # 2) A high ledge: jump and hang.
    spot = find_spot(world, pawn, climb, 150, 340, False)
    report["ledge_spot"] = [round(v) for v in spot[:3]] + [round(spot[3].get_editor_property("Height"))] if spot else None
    if spot:
        x, y, yaw, ledge = spot
        place(world, pawn, x, y, yaw)
        # With a gun in hand: it is put away while climbing and comes back after.
        inv = pc.get_inventory()
        inv.give(unreal.M80Weapon.BERETTA, -1, True)
        for s in wait(world, 0.4):
            yield s
        report["jump_to_ledge"] = climb.jump_pressed()
        report["jump_debug"] = climb.get_editor_property("Debug")
        track = []
        for s in wait(world, 1.2, lambda: track.append([round(pawn.get_actor_location().z), str(climb.get_state())[-12:], str(pawn.get_movement_component().movement_mode)[-14:], round(pawn.get_velocity().z), climb.get_editor_property("Debug")])):
            yield s
        report["jump_track"] = track[::6]
        report["after_jump_state"] = str(climb.get_state())
        if str(climb.get_state()).find("HANGING") < 0:
            report["grab_direct"] = climb.grab(ledge)
            for s in wait(world, 0.3):
                yield s
        held = inv.get_held_mesh()
        report["gun_visible_hanging"] = bool(held and held.is_visible())
        for s in side(world, pc, pawn, "03_appeso", report):
            yield s
        for s in side(world, pc, pawn, "03c_appeso_vicino", report, 170, -60):
            yield s
        for s in shot(world, "03b_appeso_camera", report):
            yield s
        report["hang_debug"] = climb.get_editor_property("Debug")
        # The hands on the edge, from close by (the fingers).
        cam = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))[0]
        mesh = pawn.get_component_by_class(unreal.SkeletalMeshComponent)
        hands = (mesh.get_socket_location("hand_l") + mesh.get_socket_location("hand_r")) * 0.5
        eye = hands - pawn.get_actor_forward_vector() * 90 + V(0, 0, 45)
        d = hands - eye
        cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
        pc.set_view_target_with_blend(cam, 0.0)
        yield 2
        for s in shot(world, "03d_mani", report):
            yield s
        pc.set_view_target_with_blend(pawn, 0.0)
        right = pawn.get_actor_right_vector()

        # Along the ledge, right then left (the input as the controller passes it), with the camera behind and turned.
        def shimmy(x, seconds, tag):
            p = pawn.get_actor_location()
            trk = []

            def push():
                climb.force_move_input(right * x, 0.1)
                trk.append([round((pawn.get_actor_location() - p).dot(right)), climb.get_editor_property("Debug")[:60]])
            for s in wait(world, seconds, push):
                yield s
            report["shimmy_" + tag + "_cm"] = round((pawn.get_actor_location() - p).dot(right))
            report["shimmy_" + tag + "_track"] = trk[::10]
            for s in wait(world, 0.8):
                yield s
        for s in shimmy(1.0, 2.4, "right"):
            yield s
        for s in side(world, pc, pawn, "04_spostamento_destra", report):
            yield s
        for s in shimmy(-1.0, 2.4, "left"):
            yield s
        yaw = pawn.get_actor_rotation().yaw
        pc.set_control_rotation(unreal.Rotator(0, -10, yaw + 70))
        for s in shimmy(-1.0, 2.0, "left_camera_side"):
            yield s
        for s in shimmy(1.0, 2.0, "right_camera_side"):
            yield s
        pc.set_control_rotation(unreal.Rotator(0, -10, yaw))
        for s in wait(world, 1.3):
            yield s
        report["state_before_up"] = str(climb.get_state())
        climb.drop()
        for s in wait(world, 1.5):
            yield s
        up = find_spot(world, pawn, climb, 200, 330, True, [(spot[0], spot[1])])
        report["climb_spot"] = [round(v) for v in up[:3]] + [round(up[3].get_editor_property("Height"))] if up else None
        if up:
            spot = up
            ledge = up[3]
            place(world, pawn, up[0], up[1], up[2])
            for s in wait(world, 0.3):
                yield s
            climb.grab(ledge)
            for s in wait(world, 0.4):
                yield s
        report["climb_up"] = climb.jump_pressed()
        ctr = []
        for s in wait(world, 0.55, lambda: ctr.append([round(pawn.get_actor_location().z), str(climb.get_state())[-14:], climb.get_editor_property("Debug")])):
            yield s
        for s in side(world, pc, pawn, "05_sale_sul_bordo_meta", report):
            yield s
        for s in wait(world, 1.2, lambda: ctr.append([round(pawn.get_actor_location().z), str(climb.get_state())[-14:], climb.get_editor_property("Debug")])):
            yield s
        report["climb_track"] = ctr[::5]
        for s in wait(world, 0.5):
            yield s
        held = inv.get_held_mesh()
        report["gun_visible_after_climb"] = bool(held and held.is_visible())
        report["climb_debug"] = climb.get_editor_property("Debug")
        report["after_climb"] = {"state": str(climb.get_state()), "feet_z": round(pawn.get_actor_location().z - 92),
                                 "ledge_z": round(ledge.get_editor_property("Edge").z)}
        for s in side(world, pc, pawn, "06_sopra_il_bordo", report):
            yield s
        for s in shot(world, "06b_sopra_camera", report):
            yield s

    # 3) Another ledge: hang and let go.
    spot2 = find_spot(world, pawn, climb, 200, 330, False, [(spot[0], spot[1])] if spot else [])
    if spot2:
        x, y, yaw, ledge = spot2
        place(world, pawn, x, y, yaw)
        for s in wait(world, 0.3):
            yield s
        climb.grab(ledge)
        for s in wait(world, 0.5):
            yield s
        climb.drop()
        for s in wait(world, 1.5):
            yield s
        report["after_drop"] = {"state": str(climb.get_state()), "falling_or_walking": str(pawn.get_movement_component().movement_mode)}
        for s in side(world, pc, pawn, "07_lasciato", report):
            yield s
    (OUT / "arrampicata.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "error.txt"))
