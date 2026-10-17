"""Photo test of what the townspeople do in L_M80_ProvaFolla (Play In Editor): hands (holding a bag or a stick, talking),
the old men's walks, a trip and getting up, being run over and getting up, sitting on a chair and standing up, getting
in a parked car, driving it about, getting out, a punch answered (fists up) or run from, a shot scaring the square.
Out: Saved/Mazzarino80/Folla/Azioni/*.png + azioni.json (states over time, distances)
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_azioni.py -ForceLit -TimeoutMinutes 40
Env M80_AZIONI=mani,vecchi,caduta,investito,sedia,auto,pugni,spavento,giocatore,spinta (default: all)
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
OUT = ROOT / "Saved/Mazzarino80/Folla/Azioni"
V = unreal.Vector
DO = [x for x in os.environ.get("M80_AZIONI", "mani,vecchi,vestiti,caduta,investito,sedia,auto,pugni,spavento,giocatore,spinta").split(",") if x]
report = {"shots": [], "log": []}


def now(world):
    # Game time: with 42 MetaHumans the game runs slower than the clock, and the clips play in game time.
    return unreal.GameplayStatics.get_time_seconds(world)


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


def side(world, pc, cam, a, name, dist=300.0, up=20.0, at_up=0.0):
    loc = a.get_actor_location()
    eye = loc + a.get_actor_right_vector() * dist + V(0, 0, up)
    for s in look(world, pc, cam, loc + V(0, 0, at_up), eye, name):
        yield s


def state(a):
    v = a.get_editor_property("stato")
    return getattr(v, "name", str(v))


def log(world, msg):
    report["log"].append([round(now(world), 1), msg])


def save():
    (OUT / "azioni.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


def people(world):
    return list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Pedone))


def find(world, key, moving=None, free=True):
    for a in people(world):
        if not str(a.get_editor_property("personaggio")).startswith(key):
            continue
        if free and state(a) != "LIBERO":
            continue
        if moving is None or (a.get_velocity().length() > 20) == moving:
            return a
    return None


def hand_of(a):
    body = next((c for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body"), None)
    return body.get_socket_location("hand_r") if body else a.get_actor_location()


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
    cam = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor))[0]
    for atmo in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere):
        atmo.set_editor_property("bAdvanceInGame", False)
        atmo.set_hour(16.0)
    # Nobody trips or takes a car by chance: the tests call them.
    for a in people(world):
        a.set_editor_property("cadute_per_minuto", 0.0)
        a.set_editor_property("voglia_di_guidare", 0.0)
    for s in wait(world, 12):
        yield s
    report["people"] = len(people(world))
    report["chairs"] = [[c.get_actor_label(), round(c.get_actor_up_vector().z, 3), c.root_component.is_simulating_physics(),
                         str(c.root_component.mobility), [str(t) for t in c.tags]]
                        for c in unreal.GameplayStatics.get_all_actors_with_tag(world, "M80Sedia")][:6]
    cm = player.get_component_by_class(unreal.CharacterMovementComponent)
    report["player_push"] = [cm.get_editor_property("enable_physics_interaction"), cm.get_editor_property("push_force_factor")] if cm else None
    report["cars"] = [c.get_actor_label() for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car)]
    save()

    if "mani" in DO:
        # Right hand closed on the bag / the stick, close; a chatting pair's hands.
        for key in ("Anziana1", "Donna1", "Anziano1"):
            a = None
            for _ in range(30):
                a = find(world, key, True)
                if a:
                    break
                yield 15
            if a:
                h = hand_of(a)
                eye = h + a.get_actor_right_vector() * 70 + a.get_actor_forward_vector() * 30 + V(0, 0, 10)
                for s in look(world, pc, cam, h, eye, "mano_" + key):
                    yield s
        for _ in range(60):
            talking = [a for a in people(world) if state(a) == "PARLA"]
            if talking:
                for s in wait(world, 2.0):
                    yield s
                a = talking[0]
                h = hand_of(a)
                for s in side(world, pc, cam, a, "mani_chiacchiera", 220.0, 10.0, 20.0):
                    yield s
                eye = h + a.get_actor_forward_vector() * 80 + V(0, 0, 15)
                for s in look(world, pc, cam, h, eye, "mano_chiacchiera"):
                    yield s
                break
            for s in wait(world, 1.0):
                yield s
        save()

    if "vecchi" in DO:
        for key in ("Anziano1", "Anziano2", "Anziana2", "Anziano3"):
            a = None
            for _ in range(40):
                a = find(world, key, True)
                if a:
                    break
                yield 15
            if a:
                report.setdefault("walks", {})[key] = [str(a.get_editor_property("andatura")), round(a.get_velocity().length(), 1)]
                for s in side(world, pc, cam, a, "vecchio_" + key):
                    yield s
                loc = a.get_actor_location()
                eye = loc + a.get_actor_right_vector() * 170 + V(0, 0, -45)
                for s in look(world, pc, cam, loc + V(0, 0, -55), eye, "vecchio_piedi_" + key):
                    yield s
        save()

    if "vestiti" in DO:
        # The old men's clothes close, mid and far (the clothes' LODs change with the distance), walking.
        for key in ("Anziano1", "Anziano3", "Anziana2"):
            a = None
            for _ in range(40):
                a = find(world, key, True)
                if a:
                    break
                yield 15
            if not a:
                continue
            for dist in (160.0, 450.0, 1100.0):
                loc = a.get_actor_location()
                eye = loc + a.get_actor_right_vector() * dist * 0.8 + a.get_actor_forward_vector() * dist * 0.6 + V(0, 0, 10)
                cam.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, loc + V(0, 0, -10)), False, True)
                cam.get_component_by_class(unreal.CameraComponent).set_field_of_view(max(8.0, 60.0 * 160.0 / dist))
                pc.set_view_target_with_blend(cam, 0.0)
                yield 2
                for s in shot(world, "vestiti_%s_%d" % (key, dist)):
                    yield s
            cam.get_component_by_class(unreal.CameraComponent).set_field_of_view(90.0)
        save()

    if "caduta" in DO:
        a = find(world, "Ragazzo1", True) or find(world, "Uomo1")
        if a:
            right = a.get_actor_right_vector()
            start = a.get_actor_location()
            a.inciampa()
            log(world, "trip " + str(a.get_editor_property("personaggio")))
            t0 = now(world)
            for t, name in ((0.8, "caduta_1"), (2.4, "caduta_2_terra"), (6.4, "caduta_3_rialza"), (8.0, "caduta_4_rialza"), (11.0, "caduta_5_in_piedi")):
                while now(world) - t0 < t:
                    yield 1
                loc = a.get_actor_location()
                for s in look(world, pc, cam, loc, loc + right * 380 + V(0, 0, 60), name):
                    yield s
            report["trip"] = {"moved_cm": round((a.get_actor_location() - start).length(), 1), "state_after": state(a)}
        save()

    if "investito" in DO:
        a = find(world, "Uomo1", None) or find(world, "Uomo3", None)
        if a:
            fwd = a.get_actor_forward_vector()
            start = a.get_actor_location()
            a.investi(fwd, 30.0, None)
            log(world, "run over " + str(a.get_editor_property("personaggio")))
            t0 = now(world)
            side_v = a.get_actor_right_vector()
            for t, name in ((0.3, "investito_1"), (0.9, "investito_2"), (2.5, "investito_3_terra"), (5.5, "investito_4_rialza"),
                            (8.0, "investito_5_rialza"), (11.0, "investito_6_in_piedi")):
                while now(world) - t0 < t:
                    yield 1
                loc = a.get_actor_location()
                for s in look(world, pc, cam, loc, loc + side_v * 420 + fwd * 120 + V(0, 0, 80), name):
                    yield s
            report["run_over"] = {"moved_cm": round((a.get_actor_location() - start).length(), 1), "state_after": state(a)}
        save()

    if "sedia" in DO:
        chairs = list(unreal.GameplayStatics.get_all_actors_with_tag(world, "M80Sedia"))
        a = find(world, "Anziana3") or find(world, "Donna2")
        taken = {p.get_sedia() for p in people(world) if p.get_sedia()}
        ok = False
        chair = None
        for c in [c for c in chairs if c not in taken and not c.actor_has_tag("M80Occupata")] if a else []:
            a.set_actor_location(c.get_actor_location() + c.get_actor_forward_vector() * 350 + V(0, 0, 95), False, True)
            ok = a.vai_a_sedere(c)
            if ok:
                chair = c
                break
        if a and chair:
            log(world, "sit %s -> %s %s" % (a.get_editor_property("personaggio"), chair.get_actor_label(), ok))
            t0 = now(world)
            while now(world) - t0 < 20 and state(a) != "SEDUTO":
                yield 2
            report["sit_reached_s"] = round(now(world) - t0, 1)
            fwd = chair.get_actor_forward_vector()
            right = chair.get_actor_right_vector()
            for t, name in ((1.0, "sedia_1_si_siede"), (3.5, "sedia_2_seduta")):
                while now(world) - t0 - report["sit_reached_s"] < t:
                    yield 1
                loc = a.get_actor_location()
                for s in look(world, pc, cam, loc + V(0, 0, -30), loc + fwd * 260 + right * 160 + V(0, 0, 40), name):
                    yield s
            for s in side(world, pc, cam, a, "sedia_3_fianco", 260.0, 0.0, -30.0):
                yield s
            # Waits for it to stand up again.
            t1 = now(world)
            while now(world) - t1 < 50 and state(a) == "SEDUTO":
                yield 5
            report["sit_state_after"] = [state(a), round(now(world) - t1, 1)]
            for s in wait(world, 0.8):
                yield s
            loc = a.get_actor_location()
            for s in look(world, pc, cam, loc, loc + fwd * 300 + right * 150 + V(0, 0, 40), "sedia_4_si_alza"):
                yield s
        save()

    if "auto" in DO:
        cars = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car))
        a = find(world, "Uomo2") or find(world, "Ragazzo2")
        car = next((c for c in cars if "Fiat500" in c.get_actor_label()), cars[0] if cars else None)
        if a and car:
            side_v = car.get_actor_right_vector() * -1.0   # the driver's side (left)
            a.set_actor_location(car.get_actor_location() + side_v * 500 + V(0, 0, 95), False, True)
            ok = a.vai_a_guidare(car, float(os.environ.get("M80_GUIDA_S", "30")))
            log(world, "drive %s -> %s %s" % (a.get_editor_property("personaggio"), car.get_actor_label(), ok))
            t0 = now(world)
            while now(world) - t0 < 20 and state(a) != "IN_AUTO":
                yield 2
            report["car_reached_s"] = round(now(world) - t0, 1)
            for t, name in ((0.6, "auto_1_sale"), (1.6, "auto_2_sale"), (2.8, "auto_3_seduto")):
                t1 = now(world)
                while now(world) - t0 - report["car_reached_s"] < t:
                    yield 1
                c = car.get_actor_location()
                for s in look(world, pc, cam, c + V(0, 0, 80), c + side_v * 420 + car.get_actor_forward_vector() * 150 + V(0, 0, 120), name):
                    yield s
            start = car.get_actor_location()
            for k in range(int(os.environ.get("M80_GUIDA_FOTO", "3"))):
                for s in wait(world, 5.0):
                    yield s
                c = car.get_actor_location()
                for s in look(world, pc, cam, c + V(0, 0, 60), c + car.get_actor_right_vector() * -600 + V(0, 0, 250), "auto_%d_guida" % (4 + k)):
                    yield s
                ctl = car.get_controller()
                log(world, "driving %.0f km/h, %.0f cm from start, state %s; %s" % (car.get_speed_kmh(), (c - start).length(), state(a),
                                                                                  ctl.get_editor_property("diario") if ctl else "no driver"))
            report["car_moved_cm"] = round((car.get_actor_location() - start).length(), 1)
            # Parks after its time and gets out.
            t1 = now(world)
            while now(world) - t1 < 25 and a.get_attach_parent_actor():
                yield 2
            report["car_exit_after_s"] = round(now(world) - t1, 1)
            for t, name in ((0.8, "auto_7_scende"), (2.2, "auto_8_scende"), (4.0, "auto_9_fuori")):
                t2 = now(world)
                while now(world) - t1 - report["car_exit_after_s"] < t:
                    yield 1
                c = car.get_actor_location()
                for s in look(world, pc, cam, c + V(0, 0, 80), c + car.get_actor_right_vector() * -450 + car.get_actor_forward_vector() * 120 + V(0, 0, 120), name):
                    yield s
            report["car_driver_after"] = state(a)
        save()

    if "pugni" in DO:
        # The player hits one who has the nerve (fists up), then one who has not (runs away).
        for nerve, key, tag in ((1.0, "Uomo3", "difende"), (0.0, "Donna3", "scappa")):
            a = find(world, key) or find(world, "Ragazz")
            if not a:
                continue
            a.set_editor_property("coraggio", nerve)
            p = player.get_actor_location()
            fwd = player.get_actor_forward_vector()
            a.set_actor_location(p + fwd * 150 + V(0, 0, 5), False, True)
            a.set_actor_rotation(unreal.MathLibrary.make_rot_from_x(fwd * -1.0), True)
            for s in wait(world, 0.5):
                yield s
            unreal.GameplayStatics.apply_damage(a, 8.0, pc, player, None)
            log(world, "punched %s (nerve %.1f) -> %s" % (a.get_editor_property("personaggio"), nerve, state(a)))
            for t, name in ((0.6, tag + "_1"), (2.0, tag + "_2"), (4.0, tag + "_3")):
                t0 = now(world)
                while now(world) - t0 < (t if name.endswith("_1") else 1.4):
                    yield 1
                loc = a.get_actor_location()
                mid = (loc + player.get_actor_location()) * 0.5
                for s in look(world, pc, cam, mid, mid + fwd.cross(V(0, 0, 1)) * 450 + V(0, 0, 80), name):
                    yield s
            report.setdefault("punch", {})[tag] = {"state": state(a), "dist_cm": round((a.get_actor_location() - player.get_actor_location()).length(), 1)}
            for s in wait(world, 4.0):
                yield s
            report["punch"][tag]["dist_after_8s_cm"] = round((a.get_actor_location() - player.get_actor_location()).length(), 1)
            report["punch"][tag]["state_after_8s"] = state(a)
        vit = player.get_component_by_class(unreal.M80VitalsComponent)
        if vit:
            report["player_health"] = vit.get_editor_property("health")
        save()

    if "spavento" in DO:
        p = player.get_actor_location()
        near = [a for a in people(world) if (a.get_actor_location() - p).length() < 3000]
        unreal.M80Pedone.spaventa(world, p, 3000.0, player)
        for s in wait(world, 2.0):
            yield s
        report["scared"] = {"near": len(near), "running": len([a for a in near if state(a) == "SCAPPA"])}
        cam_eye = p + V(0, 0, 900) + player.get_actor_forward_vector() * -900
        for s in look(world, pc, cam, p, cam_eye, "spavento"):
            yield s
        save()

    if "giocatore" in DO:
        # The player sits on a free chair (E), stands up (E); walks to the Mini, gets in (E), gets out (E).
        chairs = [c for c in unreal.GameplayStatics.get_all_actors_with_tag(world, "M80Sedia")
                  if not c.actor_has_tag("M80Occupata") and c.get_actor_up_vector().z > 0.95]
        report["chairs_upright"] = len(chairs)
        if chairs:
            ch = chairs[-1]
            player.set_actor_location(ch.get_actor_location() + ch.get_actor_forward_vector() * 90 + V(0, 0, 100), False, True)
            for s in wait(world, 0.5):
                yield s
            pc.interact()
            report["player_sit_state"] = str(pc.get_editor_property("state"))
            fwd = ch.get_actor_forward_vector()
            right = ch.get_actor_right_vector()
            for t, name in ((1.0, "giocatore_si_siede"), (3.0, "giocatore_seduto")):
                for s in wait(world, t if name.endswith("siede") else 2.0):
                    yield s
                loc = player.get_actor_location()
                for s in look(world, pc, cam, loc + V(0, 0, -30), loc + fwd * 260 + right * 140 + V(0, 0, 40), name):
                    yield s
            report["chair_held"] = ch.actor_has_tag("M80Occupata")
            pc.interact()
            for s in wait(world, 1.0):
                yield s
            loc = player.get_actor_location()
            for s in look(world, pc, cam, loc, loc + fwd * 300 + right * 150 + V(0, 0, 40), "giocatore_si_alza"):
                yield s
            for s in wait(world, 2.0):
                yield s
            report["player_after_sit"] = str(pc.get_editor_property("state"))
        mini = next((c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car) if "Mini" in c.get_actor_label()), None)
        if mini:
            left = mini.get_actor_right_vector() * -1.0
            player.set_actor_location(mini.get_actor_location() + left * 330 + V(0, 0, 100), False, True)
            for s in wait(world, 0.5):
                yield s
            pc.interact()
            t0 = now(world)
            shots = [(2.5, "giocatore_auto_1"), (3.6, "giocatore_auto_2"), (4.8, "giocatore_auto_3")]
            for t, name in shots:
                while now(world) - t0 < t:
                    yield 1
                c = mini.get_actor_location()
                pc.set_view_target_with_blend(cam, 0.0)
                for s in look(world, pc, cam, c + V(0, 0, 80), c + left * 450 + mini.get_actor_forward_vector() * 150 + V(0, 0, 120), name):
                    yield s
            while now(world) - t0 < 12 and str(pc.get_editor_property("state")).find("DRIVING") < 0:
                yield 2
            report["player_car_state"] = [str(pc.get_editor_property("state")), round(now(world) - t0, 1)]
            pc.interact()
            t0 = now(world)
            for t, name in ((0.8, "giocatore_scende_1"), (2.0, "giocatore_scende_2"), (3.6, "giocatore_scende_3")):
                while now(world) - t0 < t:
                    yield 1
                c = mini.get_actor_location()
                for s in look(world, pc, cam, c + V(0, 0, 80), c + left * 450 + mini.get_actor_forward_vector() * 150 + V(0, 0, 120), name):
                    yield s
            for s in wait(world, 1.0):
                yield s
            report["player_after_car"] = str(pc.get_editor_property("state"))
        save()

    if "spinta" in DO:
        # A car thrown at a chair, the player walking into another: do they move?
        chairs = [c for c in unreal.GameplayStatics.get_all_actors_with_tag(world, "M80Sedia") if not c.actor_has_tag("M80Occupata")]
        golf = next((c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Car) if "Golf" in c.get_actor_label()), None)
        if golf and len(chairs) >= 2:
            ch = chairs[0]
            before = ch.get_actor_location()
            back = golf.get_actor_forward_vector() * -1.0
            golf.set_actor_location_and_rotation(before + back * 700 + V(0, 0, 40), golf.get_actor_rotation(), False, True)
            golf.root_component.set_physics_linear_velocity(golf.get_actor_forward_vector() * 700, False, unreal.Name("None"))
            for s in wait(world, 0.6):
                yield s
            c = golf.get_actor_location()
            for s in look(world, pc, cam, c + V(0, 0, 50), c + golf.get_actor_right_vector() * 600 + V(0, 0, 200), "spinta_auto"):
                yield s
            for s in wait(world, 2.0):
                yield s
            report["chair_moved_by_car_cm"] = round((ch.get_actor_location() - before).length(), 1)
            ch2 = chairs[1]
            before2 = ch2.get_actor_location()
            to = (before2 - player.get_actor_location())
            player.set_actor_location(before2 - ch2.get_actor_forward_vector() * 200 + V(0, 0, 100), False, True)
            dirv = ch2.get_actor_forward_vector()
            t0 = now(world)
            p0 = player.get_actor_location()
            while now(world) - t0 < 2.0:
                player.add_movement_input(dirv, 1.0, True)
                yield 1
            report["player_walked_cm"] = round((player.get_actor_location() - p0).length(), 1)
            report["chair_moved_by_walking_cm"] = round((ch2.get_actor_location() - before2).length(), 1)
        save()

    report["states_end"] = {}
    for a in people(world):
        report["states_end"][state(a)] = report["states_end"].get(state(a), 0) + 1
    save()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    yield 30


m80_seq.Sequencer(steps(), log_file=str(OUT / "azioni_errore.txt"))
