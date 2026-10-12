"""Test map for the soapbox carts: /Game/Mazzarino80/Vehicles/Maps/L_M80_ProvaCarretti (classic level, made again from
scratch each run). A stone floor 160 x 100 m, at one end a 3 m platform with a 30 m ramp down at 10% (the steepness of
Mazzarino's streets), a slalom of posts, the four carts parked in a row by the player start, the town's atmosphere on a
summer afternoon and the town game mode (E gets on a cart, W pushes, S brakes and goes back, A / D steer).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_carretti_prova_setup.py -ForceLit
Report and photos: Saved/Mazzarino80/Carretti/prova_setup.json, Saved/Mazzarino80/Carretti/*.png
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Vehicles/Maps/L_M80_ProvaCarretti"
OUT = ROOT / "Saved/Mazzarino80/Carretti"
FLOOR_MATERIAL = "/Game/Mazzarino80/Kit/Stairs/MI_M80_Lavica_secondaria"
CUBE = "/Engine/BasicShapes/Cube"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
V = unreal.Vector
CARTS = [unreal.M80CarrettoCuscinetti, unreal.M80CarrettoTriangolo, unreal.M80CarrettoCassetta, unreal.M80CarrettoPersiana]
# Ramp: from the platform's edge (x = RAMP_TOP_X, 3 m up) down to the floor at x = 0.
RAMP_TOP_X, RAMP_H = -3000.0, 300.0


def box(label, centre, size_cm, folder, yaw=0.0, pitch=0.0, material=None):
    a = EAS.spawn_actor_from_object(unreal.load_asset(CUBE), centre)
    a.set_actor_scale3d(V(size_cm[0] / 100.0, size_cm[1] / 100.0, size_cm[2] / 100.0))
    a.set_actor_rotation(unreal.Rotator(0, pitch, yaw), False)
    a.set_actor_label(label)
    a.set_folder_path(folder)
    if material:
        a.static_mesh_component.set_material(0, material)
    return a


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
        yield 5
    LES.new_level(MAP)
    yield 10
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected %s to be open, got %s" % (MAP, world.get_path_name()))
    world.get_world_settings().set_editor_property("default_game_mode", unreal.M80GameMode.static_class())
    stone = unreal.load_asset(FLOOR_MATERIAL)

    # Floor (top at z = 0), the platform and the ramp down from it.
    floor = box("Pavimento", V(3500, 0, -5), (16000, 10000, 10), "Pista", material=stone)
    floor.tags = ["M80Ground"]
    box("Piattaforma", V(RAMP_TOP_X - 600, 0, RAMP_H / 2), (1200, 800, RAMP_H), "Pista", material=stone)
    length = math.hypot(-RAMP_TOP_X, RAMP_H)
    angle = math.degrees(math.atan2(RAMP_H, -RAMP_TOP_X))
    thick = 40.0
    mid = V(RAMP_TOP_X / 2, 0, RAMP_H / 2 - thick / 2 / math.cos(math.radians(angle)))
    box("Discesa_10pc", mid, (length + 20, 800, thick), "Pista", pitch=-angle, material=stone)
    # Low kerbs along the ramp so a cart going wrong stays on it.
    for side in (-1, 1):
        box("Cordolo_%d" % side, V(RAMP_TOP_X / 2, side * 420, RAMP_H / 2 + 5), (length, 40, 40), "Pista", pitch=-angle, material=stone)
    # Slalom on the flat after the ramp.
    posts = []
    for i in range(6):
        x, y = 1800 + i * 700, (250 if i % 2 else -250)
        box("Birillo_%d" % i, V(x, y, 45), (30, 30, 90), "Slalom")
        posts.append([x, y])
    atmo = EAS.spawn_actor_from_class(unreal.M80Atmosphere, V(0, 0, 0))
    atmo.set_actor_label("Atmosfera")
    atmo.set_editor_property("hour", 17.0)
    # The carts side by side on the flat beside the ramp's foot, facing down the track (nothing in front of them);
    # the player start behind them.
    start = EAS.spawn_actor_from_class(unreal.PlayerStart, V(-450, -1800, 100))
    start.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    placed = []
    for i, cls in enumerate(CARTS):
        x, y = 0, -900 - i * 600
        c = EAS.spawn_actor_from_class(cls, V(x, y, 15), unreal.Rotator(0, 0, 0))
        c.set_actor_label(cls.__name__.replace("M80", ""))
        c.set_folder_path("Carretti")
        placed.append([c.get_actor_label(), x, y])
    cam = EAS.spawn_actor_from_class(unreal.CameraActor, V(0, -2500, 400))
    cam.set_actor_label("CameraTest")
    yield 5
    LES.save_current_level()
    for name, eye, target, fov in (("carretti_parcheggiati", V(700, -3300, 380), V(0, -1800, 20), 60),
                                   ("pista", V(-4500, -1800, 900), V(1500, 0, 0), 70)):
        rot = unreal.MathLibrary.find_look_at_rotation(eye, target)
        m80_seq.set_view(eye, rot)
        yield 150
        cap = m80_seq.ViewCapture(1600, 900, fov)
        cap.capture(eye, rot, OUT / ("%s.png" % name))
        cap.destroy()
        yield 3
    (OUT / "prova_setup.json").write_text(json.dumps({"map": MAP, "carts": placed, "posts": posts,
                                                      "ramp": {"top_x": RAMP_TOP_X, "height": RAMP_H, "slope_deg": round(angle, 2)}},
                                                     indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "prova_setup_error.txt"))
