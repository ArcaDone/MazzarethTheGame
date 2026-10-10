"""Photos of the imported models that have no place in the town yet (m80_oggetti_import.py, the phone booth): each one
spawned for a moment far from the houses in the town map (World Partition opens empty), under a temporary daylight,
seen from three sides and from above. Nothing saved.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_oggetti_foto.py -ForceLit
Out: Saved/Mazzarino80/Oggetti/Foto/<Key>_<view>.png
"""
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Oggetti/Foto"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MESHES = {"Ospedale": "/Game/Mazzarino80/Buildings/Ospedale/SM_M80_Ospedale",
          "Heaven": "/Game/Mazzarino80/Buildings/Heaven/SM_M80_Heaven",
          "Banca": "/Game/Mazzarino80/Buildings/Banca/SM_M80_Banca",
          "Cabina": "/Game/Mazzarino80/Kit/CabinaTelefonica/Meshes/SK_Cabina_Telefonica"}
SPOT = unreal.Vector(-300000, -300000, 60000)


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    m80_seq.console("r.TextureStreaming 0")
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, SPOT + unreal.Vector(0, 0, 5000))
    sun.set_actor_rotation(unreal.Rotator(pitch=-42.0, yaw=-110.0, roll=0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, SPOT + unreal.Vector(0, 0, 3000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), SPOT - unreal.Vector(0, 0, 5))
    floor.set_actor_scale3d(unreal.Vector(400, 400, 1))
    yield 60
    for key, path in MESHES.items():
        asset = unreal.load_asset(path)
        if not asset:
            continue
        a = EAS.spawn_actor_from_object(asset, SPOT)
        yield 120
        c, e = a.get_actor_bounds(False)
        L = max(e.x, e.y, e.z) * 2 + 200
        for name, ang, h in (("tre_quarti", 35, 0.45), ("retro", 215, 0.45), ("aereo", 120, 1.2)):
            t = math.radians(ang)
            eye = c + unreal.Vector(math.cos(t) * L * 0.9, math.sin(t) * L * 0.9, L * h)
            rot = unreal.MathLibrary.find_look_at_rotation(eye, c)
            m80_seq.set_view(eye, rot)
            yield 150
            cap = m80_seq.ViewCapture(1600, 900, 60)
            cap.capture(eye, rot, OUT / ("%s_%s.png" % (key, name)))
            cap.destroy()
            yield 5
        a.destroy_actor()
        yield 10


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
