"""Photos of the drivable vehicles and of the Poste building as they are in Unreal (editor, test level).
Output: Saved/Mazzarino80/Import/photos/*.png. The level is not saved (the Poste is placed temporarily).
"""
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Import/photos"
MAP = "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida"


def look(cap, eye, target, name):
    d = target - eye
    rot = unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))
    cap.capture(eye, rot, OUT / (name + ".png"))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 120
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cars = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.M80Car)]
    cap = m80_seq.ViewCapture(1600, 900, 50)
    yield 5
    for c in cars:
        name = c.get_actor_label()
        p = c.get_actor_location()
        f = c.get_actor_forward_vector()
        r = c.get_actor_right_vector()
        size = 520 if "Vespa" not in name else 300
        look(cap, p + f * size * 0.8 - r * size * 0.7 + unreal.Vector(0, 0, 160), p + unreal.Vector(0, 0, 60), name + "_34")
        yield 3
        look(cap, p - f * size * 0.8 + r * size * 0.7 + unreal.Vector(0, 0, 140), p + unreal.Vector(0, 0, 60), name + "_retro")
        yield 3
    # The Poste building with its mast, out in the open (temporary, not saved).
    poste = unreal.load_asset("/Game/Mazzarino80/Buildings/Poste/SM_M80_Poste")
    mast = unreal.load_asset("/Game/Mazzarino80/Buildings/Poste/SM_M80_Poste_Antenna")
    if poste:
        base = unreal.Vector(-9000, 0, 0)
        a = eas.spawn_actor_from_object(poste, base)
        b = eas.spawn_actor_from_object(mast, base + unreal.Vector(-1864.1, -1911.6, 16.5)) if mast else None
        yield 60
        centre = a.get_actor_bounds(False)[0]
        look(cap, centre + unreal.Vector(4500, -3500, 2200), centre, "Poste_34")
        yield 3
        for side, (dx, dy) in {"est": (1, 0), "ovest": (-1, 0), "sud": (0, -1), "nord": (0, 1)}.items():
            look(cap, centre + unreal.Vector(dx * 3800, dy * 3800, 250), centre, "Poste_" + side)
            yield 3
        a.destroy_actor()
        if b:
            b.destroy_actor()
    cap.destroy()
    yield 5


m80_seq.Sequencer(run(), log_file=str(OUT / "photos_error.txt"))
