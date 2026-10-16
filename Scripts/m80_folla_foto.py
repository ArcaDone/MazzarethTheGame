"""Photos of the crowd in L_M80_ProvaFolla (Play In Editor, the map's AM80Folla): the walks (old man with the stick,
old man's walk, old woman dragging her feet, old woman with the shopping bag, lady with the handbag, sad walk) from
the side, faces close and far (hair and hats at every LOD), a chatting pair, someone tripping (falling, on the ground,
getting up, standing again), and a townsperson sent straight through the player (do they collide?).
Out: Saved/Mazzarino80/Folla/Foto/*.png + foto.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_foto.py -ForceLit -TimeoutMinutes 30
"""
import json
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
OUT = ROOT / "Saved/Mazzarino80/Folla/Foto"
V = unreal.Vector
WALKS = ["Anziano1", "Anziano2", "Anziana2", "Anziana1", "Donna1", "Uomo4", "Ragazzo2"]
report = {"shots": []}


def now(world):
    return unreal.GameplayStatics.get_real_time_seconds(world)


def wait(world, seconds):
    t0 = now(world)
    while now(world) - t0 < seconds:
        yield 1


def shot(world, name):
    since = time.time()
    unreal.SystemLibrary.execute_console_command(world, "HighResShot 1280x720")
    yield 20
    report["shots"].append([name, bool(m80_seq.collect_screenshot(OUT / (name + ".png"), since - 1))])


def look(world, pc, cam, at, eye, name):
    cam.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, at), False, True)
    pc.set_view_target_with_blend(cam, 0.0)
    yield 2
    for s in shot(world, name):
        yield s


def state(a):
    v = a.get_editor_property("stato")
    return getattr(v, "name", str(v))


def save():
    (OUT / "foto.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


def people(world):
    return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Pedone))


def find(world, key, moving=None):
    for a in people(world):
        if str(a.get_editor_property("personaggio")) != key:
            continue
        if moving is None or (a.get_velocity().length() > 20) == moving:
            return a
    return None


def side(world, pc, cam, a, name, dist=280.0, height=0.0):
    loc = a.get_actor_location()
    eye = loc + a.get_actor_right_vector() * dist + V(0, 0, 20 + height)
    for s in look(world, pc, cam, loc + V(0, 0, height * 0.5), eye, name):
        yield s


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    yield 300
    world = unreal.EditorLevelLibrary.get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    player = pc.get_controlled_pawn()
    cams = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))
    cam = cams[0]
    for atmo in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere):
        atmo.set_editor_property("bAdvanceInGame", False)
        atmo.set_hour(16.0)
    # Nobody falls by chance during the photos: the trip is called below.
    for a in people(world):
        a.set_editor_property("cadute_per_minuto", 0.0)
    for s in wait(world, 15):
        yield s
    report["people"] = len(people(world))
    report["walks"] = {str(a.get_editor_property("personaggio")) + "_" + str(i): [str(a.get_editor_property("andatura")),
                                                                                 str(a.get_editor_property("accessorio"))]
                       for i, a in enumerate(people(world)[:21])}
    # 0) Feet on the ground: over a few seconds, how high the lower foot of each one is above its capsule's bottom
    # (one foot is always down when walking or standing: a few cm is right, more is floating).
    feet = {}
    t0 = now(world)
    while now(world) - t0 < 5.0:
        for a in people(world):
            if state(a) == "CADUTO":
                continue
            body = next((c for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body"), None)
            if not body:
                continue
            floor = a.get_actor_location().z - 90.0
            low = min(body.get_socket_location("ball_l").z, body.get_socket_location("ball_r").z) - floor
            feet.setdefault(str(a.get_editor_property("personaggio")), []).append(low)
        yield 1
    report["piedi_cm"] = {k: {"media": round(sum(v) / len(v), 1), "min": round(min(v), 1), "max": round(max(v), 1)}
                          for k, v in sorted(feet.items())}
    report["passo_scala"] = {str(a.get_editor_property("personaggio")): round(a.get_passo_scala(), 3) for a in people(world)}
    save()
    # 1) The walks, from the side, while walking.
    for key in WALKS:
        a = None
        for _ in range(40):
            a = find(world, key, True)
            if a:
                break
            yield 15
        if a:
            for s in side(world, pc, cam, a, "cammina_" + key):
                yield s
            # Legs and feet, close and low.
            loc = a.get_actor_location()
            eye = loc + a.get_actor_right_vector() * 170 + V(0, 0, -45)
            for s in look(world, pc, cam, loc + V(0, 0, -55), eye, "piedi_" + key):
                yield s
    # 2) Faces close and far (hair, hats).
    for key in ("Anziano2", "Anziana1", "Ragazzo2", "Donna2", "Uomo1"):
        a = find(world, key)
        if not a:
            continue
        loc = a.get_actor_location()
        fwd = a.get_actor_forward_vector()
        for dist, tag in ((130.0, "vicino"), (450.0, "medio"), (1500.0, "lontano")):
            for s in look(world, pc, cam, loc + V(0, 0, 60), loc + fwd * dist + V(0, 0, 70), "%s_%s" % (tag, key)):
                yield s
    # 3) A chat.
    pair = None
    for _ in range(80):
        talking = [a for a in people(world) if state(a) == "PARLA"]
        if talking:
            pair = talking[0]
            break
        for s in wait(world, 1.0):
            yield s
    report["chatting"] = len([a for a in people(world) if state(a) == "PARLA"])
    if pair:
        for s in wait(world, 1.5):
            yield s
        for s in side(world, pc, cam, pair, "chiacchiera", 350.0, 10.0):
            yield s
    # 4) A trip.
    a = find(world, "Ragazzo1", True) or find(world, "Uomo1", True) or find(world, "Uomo2")
    if a:
        report["trip"] = str(a.get_editor_property("personaggio"))
        start = a.get_actor_location()
        right = a.get_actor_right_vector()
        a.inciampa()
        t0 = now(world)
        for t, name in ((0.8, "caduta_1"), (2.6, "caduta_2_terra"), (6.6, "caduta_3_rialza"), (9.5, "caduta_4_in_piedi")):
            while now(world) - t0 < t:
                yield 1
            loc = a.get_actor_location()
            for s in look(world, pc, cam, loc, loc + right * 380 + V(0, 0, 60), name):
                yield s
        report["trip_moved_cm"] = round((a.get_actor_location() - start).length(), 1)
        report["trip_state_after"] = state(a)
    save()
    # 5) Collision: a townsperson sent through the player.
    p = player.get_actor_location()
    fwd = player.get_actor_forward_vector()
    a = next((x for x in people(world) if state(x) == "LIBERO" and str(x.get_editor_property("personaggio")).startswith("Ragazz")),
             people(world)[0])
    a.set_actor_location(p + fwd * 400 + V(0, 0, 5), False, True)
    a.set_actor_rotation(unreal.MathLibrary.make_rot_from_x(fwd * -1.0), True)
    report["collision_who"] = str(a.get_editor_property("personaggio"))
    report["collision_move"] = str(a.get_controller().move_to_location(p - fwd * 400, 20.0, False, False, False, False, None, True))
    closest = 1e9
    t0 = now(world)
    while now(world) - t0 < 12.0:
        yield 1
        d = (a.get_actor_location() - player.get_actor_location())
        closest = min(closest, (d.x ** 2 + d.y ** 2) ** 0.5)
    report["collision_closest_cm"] = round(closest, 1)
    report["collision_end_cm"] = round((a.get_actor_location() - (p + fwd * 400)).length(), 1)
    cap = player.get_component_by_class(unreal.CapsuleComponent)
    report["player_capsule"] = {"object": str(cap.get_collision_object_type()),
                                "vs_pawn": str(cap.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN))}
    save()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(steps(), log_file=str(OUT / "foto_errore.txt"))
