"""Automatic weapons test in the town (Play In Editor): pickups on the streets, holding and aiming a
pistol, firing at a wall (holes), the lupara, a bat blow, picking up and dropping.
Output: Saved/Mazzarino80/Player/Test/armi/*.png and weapons_test.json.
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
MAP = os.environ.get("M80_PLAY_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese")
OUT = ROOT / "Saved/Mazzarino80/Player/Test/armi"
W = unreal.M80Weapon


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "shot showui")
    yield 30
    got = m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    report.setdefault("shots", []).append([name, bool(got)])


def wait(world, seconds, each=None):
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < seconds:
        if each:
            each()
        yield 1


def look(cam, pc, eye, target):
    d = target - eye
    cam.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, True)
    pc.set_view_target_with_blend(cam, 0.0)


def inv_state(inv):
    s = inv.get_slot(inv.get_current_slot())
    return {"weapon": str(inv.get_current_weapon()), "clip": s.get_editor_property("InClip"), "reserve": s.get_editor_property("Reserve")}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {}
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 900
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world:
        raise RuntimeError("PIE did not start")
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = pc.get_controlled_pawn()
    inv = pc.get_inventory()
    report["inventory"] = bool(inv)
    picks = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80WeaponPickup))
    report["pickups"] = [[str(p.get_editor_property("weapon")), round((p.get_actor_location() - pawn.get_actor_location()).length() / 100, 1)] for p in picks]
    overlay = [c for c in pawn.get_components_by_class(unreal.SkeletalMeshComponent) if c.component_has_tag("M80Overlay")]
    report["overlay_installed"] = bool(overlay)
    cam = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))[0]

    # 1) The nearest pickup, from close.
    if picks:
        p = min(picks, key=lambda a: (a.get_actor_location() - pawn.get_actor_location()).length())
        loc = p.get_actor_location()
        look(cam, pc, loc + unreal.Vector(-220, -120, 90), loc)
        yield 30
        for s in shot(world, "01_arma_a_terra", report):
            yield s
        # Walk onto it: picked up.
        pawn.set_actor_location(loc + unreal.Vector(0, 0, 40), False, True)
        for s in wait(world, 1.0):
            yield s
        report["picked_up"] = inv_state(inv)
        pc.set_view_target_with_blend(pawn, 0.0)

    # 2) Beretta held (not aiming) and aimed, seen from the side and from behind.
    inv.give(W.BERETTA, 45, True)
    for s in wait(world, 0.8):
        yield s
    fwd = pawn.get_actor_forward_vector()
    right = pawn.get_actor_right_vector()
    base = pawn.get_actor_location()
    look(cam, pc, base + right * 230 + fwd * 60 + unreal.Vector(0, 0, 40), base + unreal.Vector(0, 0, 30))
    yield 20
    for s in shot(world, "02_pistola_in_mano", report):
        yield s
    pc.set_view_target_with_blend(pawn, 0.0)
    yield 5
    pc.set_fire(True)
    for s in wait(world, 0.3):
        yield s
    # Where the right hand is on the animation mesh, on the overlay copy and on the visible body.
    hands = {}
    for comp in pawn.get_components_by_class(unreal.SkeletalMeshComponent):
        if comp.does_socket_exist("hand_r"):
            l = pawn.get_actor_transform().inverse_transform_location(comp.get_socket_location("hand_r"))
            hands[comp.get_name()] = [round(l.x), round(l.y), round(l.z), comp.get_attach_parent().get_name() if comp.get_attach_parent() else None]
    report["hands_while_aiming"] = hands
    report["aiming"] = pc.is_aiming()
    fwd = pawn.get_actor_forward_vector()
    right = pawn.get_actor_right_vector()
    base = pawn.get_actor_location()
    look(cam, pc, base + right * 230 + fwd * 120 + unreal.Vector(0, 0, 50), base + fwd * 30 + unreal.Vector(0, 0, 50))
    yield 2
    for s in shot(world, "03_pistola_mira_lato", report):
        yield s
    pc.set_fire(False)
    pc.set_view_target_with_blend(pawn, 0.0)
    # 3) Firing a burst from the player camera at what is in front (walls get holes).
    shots0 = inv_state(inv)
    pc.set_fire(True)
    for s in wait(world, 1.2):
        yield s
    pc.set_fire(False)
    report["beretta_before_after"] = [shots0, inv_state(inv)]
    report["aim_point_dist_m"] = round((pc.get_aim_point() - pawn.get_actor_location()).length() / 100, 1)
    for s in shot(world, "04_spari_muro", report):
        yield s
    decals = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.DecalActor))
    report["decal_actors"] = len(decals)

    # 4) Lupara, aimed (trigger held during the photo, as for the pistol).
    inv.give(W.LUPARA, 16, True)
    for s in wait(world, 0.5):
        yield s
    pc.set_fire(True)
    for s in wait(world, 0.3):
        yield s
    base = pawn.get_actor_location()
    fwd = pawn.get_actor_forward_vector()
    right = pawn.get_actor_right_vector()
    held = [c for c in pawn.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == "M80Arma"]
    if held:
        h = held[0]
        l = pawn.get_actor_transform().inverse_transform_location(h.get_world_location())
        report["lupara_held"] = {"mesh": h.static_mesh.get_name() if h.static_mesh else None, "visible": h.is_visible(), "local": [round(l.x), round(l.y), round(l.z)]}
    look(cam, pc, base + right * 240 + fwd * 120 + unreal.Vector(0, 0, 50), base + fwd * 30 + unreal.Vector(0, 0, 50))
    yield 2
    for s in shot(world, "05_lupara", report):
        yield s
    pc.set_fire(False)
    report["lupara"] = inv_state(inv)
    pc.set_view_target_with_blend(pawn, 0.0)

    # 5) Bat blow, caught mid-swing.
    inv.give(W.MAZZA, 0, True)
    for s in wait(world, 0.5):
        yield s
    base = pawn.get_actor_location()
    fwd = pawn.get_actor_forward_vector()
    right = pawn.get_actor_right_vector()
    look(cam, pc, base + fwd * 260 + right * 80 + unreal.Vector(0, 0, 50), base + unreal.Vector(0, 0, 40))
    yield 3
    inv.try_fire(pc.get_aim_point())
    for s in wait(world, 0.22):
        yield s
    for s in shot(world, "06_mazza", report):
        yield s
    pc.set_view_target_with_blend(pawn, 0.0)

    # 6) Fists: a punch.
    inv.select_slot(0)
    for s in wait(world, 0.4):
        yield s
    look(cam, pc, base + fwd * 260 + right * 80 + unreal.Vector(0, 0, 50), base + unreal.Vector(0, 0, 40))
    yield 3
    inv.try_fire(pc.get_aim_point())
    for s in wait(world, 0.15):
        yield s
    for s in shot(world, "07_pugno", report):
        yield s
    pc.set_view_target_with_blend(pawn, 0.0)

    # 7) Drop the bat.
    inv.select_slot(1)
    yield 5
    n0 = len(list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80WeaponPickup)))
    inv.drop_current()
    yield 10
    n1 = len(list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80WeaponPickup)))
    report["drop"] = {"pickups_before_after": [n0, n1], "now": inv_state(inv)}
    for s in shot(world, "08_lasciata", report):
        yield s
    (OUT / "weapons_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "weapons_test_error.txt"))
