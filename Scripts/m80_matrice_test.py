"""Play test of the new Matrice in the town (Play In Editor): photos from above and from the square in front, the
player walks from the square up to the door and in, then stands in the nave (what floor holds him, how far he got),
photos through the player's camera along the nave both ways.
Positions are given in MatriceDentroFuori.blend's metres and turned into the world with the recovered actor's
transform (M80_Recuperato_Matrice, hidden; the new one stands on the same frame, see m80_matrice_place.py).
Output: Saved/Mazzarino80/Matrice/Gioco/*.png and matrice_test.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_matrice_test.py -ForceLit
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
OUT = ROOT / "Saved/Mazzarino80/Matrice/Gioco"
OLD = "M80_Recuperato_Matrice"
V = unreal.Vector


def shot(world, name, report):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1600x900")
    yield 30
    got = m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1)
    report.setdefault("shots", []).append([name, bool(got)])


def look_rot(eye, at):
    d = at - eye
    return unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))


def floor(world, p, ignore=()):
    """First thing under p (2 m above to 40 m below): (z, actor label) or (None, None)."""
    h = unreal.SystemLibrary.line_trace_single(world, p + V(0, 0, 200), p - V(0, 0, 4000), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                               False, list(ignore), unreal.DrawDebugTrace.NONE, True)
    if not h:
        return None, None
    t = h.to_tuple()
    return round(t[4].z, 1), (t[9].get_actor_label() if t[9] else None)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    report = {}
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 900
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    for atmo in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere):
        atmo.set_editor_property("bAdvanceInGame", False)
        atmo.set_hour(16.5)
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    old = next((a for a in actors if a.get_actor_label() == OLD), None)
    new = [a for a in actors if "M80Matrice" in [str(t) for t in a.tags]]
    report["found"] = {"old": bool(old), "new": [a.get_actor_label() for a in new],
                       "new_hidden": [a.is_hidden() for a in new], "old_hidden": old.is_hidden() if old else None}
    if not old:
        raise RuntimeError("No %s in the game world" % OLD)
    t = old.get_actor_transform()

    def w(bx, by, bz):
        return t.transform_location(V(bx * 100.0, -by * 100.0, bz * 100.0))
    pawn = pc.get_controlled_pawn()
    cam = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(world, unreal.CameraActor, unreal.Transform())
    cam = unreal.GameplayStatics.finish_spawning_actor(cam, unreal.Transform())
    cam.get_editor_property("camera_component").set_editor_property("field_of_view", 75.0)

    def view(name, eye, at):
        cam.set_actor_location_and_rotation(eye, look_rot(eye, at), False, True)
        pc.set_view_target_with_blend(cam, 0.0)
        yield 20
        for s in shot(world, name, report):
            yield s
    centre = w(0.5, 8.0, 10.0)
    for name, dx, dy in (("01_alto_davanti", 0.0, -75.0), ("02_alto_fianco", 70.0, 8.0), ("03_alto_dietro", 0.0, 90.0)):
        for s in view(name, w(0.5 + dx, 8.0 + dy, 55.0), centre):
            yield s
    # The square in front of the facade (Blender -y), at eye height on the ground there.
    sq = w(0.5, -42.0, 0.0)
    gz, glab = floor(world, V(sq.x, sq.y, sq.z + 1500), [pawn])
    report["square_ground"] = [gz, glab]
    if gz is not None:
        eye = V(sq.x, sq.y, gz + 170)
        for s in view("04_piazza_facciata", eye, w(0.5, -14.0, 9.0)):
            yield s
    pc.set_view_target_with_blend(pawn, 0.0)

    # Walk from the square to the door and in (towards Blender +y).
    start = w(0.5, -40.0, 0.0)
    sz, _ = floor(world, V(start.x, start.y, start.z + 1500), [pawn])
    pawn.set_actor_location(V(start.x, start.y, (sz if sz is not None else start.z) + 100), False, True)
    ahead = w(0.5, 30.0, 0.0) - w(0.5, -40.0, 0.0)
    ahead = ahead / ahead.length()
    pc.set_control_rotation(unreal.Rotator(0, -8, math.degrees(math.atan2(ahead.y, ahead.x))))
    yield 30
    track = []
    t0 = unreal.GameplayStatics.get_time_seconds(world)
    took = [False]
    while unreal.GameplayStatics.get_time_seconds(world) - t0 < 14:
        pawn.add_movement_input(ahead, 1.0)
        p = pawn.get_actor_location()
        track.append([round(p.x), round(p.y), round(p.z)])
        if not took[0] and unreal.GameplayStatics.get_time_seconds(world) - t0 > 5:
            took[0] = True
            for s in shot(world, "05_verso_porta", report):
                yield s
        yield 1
    p = pawn.get_actor_location()
    inv = t.inverse_transform_location(p)
    report["walk"] = {"track": track[::15], "end_blender_m": [round(inv.x / 100, 1), round(-inv.y / 100, 1), round(inv.z / 100, 1)],
                      "floor_under_end": floor(world, p, [pawn])}
    for s in shot(world, "06_dopo_cammino", report):
        yield s

    # Standing in the nave.
    for name, at_y, look_y in (("07_navata_verso_altare", 2.0, 40.0), ("08_navata_verso_porta", 36.0, -10.0)):
        spot = w(0.0, at_y, 4.5)
        fz, flab = floor(world, V(spot.x, spot.y, spot.z + 150), [pawn])
        report[name + "_floor"] = [fz, flab, round(spot.z)]
        pawn.set_actor_location(V(spot.x, spot.y, (fz if fz is not None else spot.z) + 100), False, True)
        d = w(0.0, look_y, 4.5) - spot
        pc.set_control_rotation(unreal.Rotator(0, 5, math.degrees(math.atan2(d.y, d.x))))
        yield 60
        q = pawn.get_actor_location()
        report[name + "_stands"] = round(q.z - (fz or 0))
        for s in shot(world, name, report):
            yield s
    (OUT / "matrice_test.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(run(), log_file=str(OUT / "matrice_test_error.txt"))
