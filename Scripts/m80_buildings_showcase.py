"""Test level for the buildings and street furniture imported from Blender (m80_import_blender_assets.py):
/Game/Mazzarino80/Buildings/L_M80_ProvaEdifici - Comune, its church, Matrice, Castello, the Madonna with every
part where it was in Blender (to be arranged in the town by hand), the bin and the manhole cover next to a
180 cm post for the scale. Renders: Saved/Mazzarino80/Buildings/Render/<view>.png.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_buildings_showcase.py -ForceLit
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Buildings/L_M80_ProvaEdifici"
OUT = ROOT / "Saved/Mazzarino80/Import/out"
RENDER = ROOT / "Saved/Mazzarino80/Buildings/Render"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CUBE = "/Engine/BasicShapes/Cube"

# Key -> (folder, centre of its plot in cm). Plots 200 m apart: the castle site alone is 150 m wide.
PLOTS = {
    "Comune": ("/Game/Mazzarino80/Buildings/Comune", (0, 0)),
    "ChiesaComune": ("/Game/Mazzarino80/Buildings/ChiesaComune", (0, 12000)),
    "Matrice": ("/Game/Mazzarino80/Buildings/Matrice", (20000, 0)),
    "Madonna": ("/Game/Mazzarino80/Buildings/Madonna", (40000, 0)),
    "Castello": ("/Game/Mazzarino80/Buildings/Castello", (20000, 25000)),
}
PROPS = (("SM_M80_Cassonetto", (-1500, -6000)), ("SM_M80_Tombino", (-1200, -6300)))


def spawn(mesh_path, loc, label, folder="Edifici"):
    mesh = unreal.load_asset(mesh_path)
    if not mesh:
        return None
    a = EAS.spawn_actor_from_object(mesh, unreal.Vector(*loc))
    a.set_actor_label(label)
    a.set_folder_path(folder)
    return a


def build_level():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, -35, 140))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    sky.get_component_by_class(unreal.SkyLightComponent).set_intensity(2.0)
    EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    ground = spawn(CUBE, (20000, 12000, -50), "Suolo", "Ambiente")
    ground.set_actor_scale3d(unreal.Vector(800, 600, 1))
    mat = unreal.load_asset("/Game/Mazzarino80/Kit/Stairs/MI_M80_Cemento")
    if mat:
        ground.static_mesh_component.set_material(0, mat)
    placed = {}
    for key, (folder, (x, y)) in PLOTS.items():
        info = json.loads((OUT / (key + ".json")).read_text(encoding="utf-8"))
        # Blender's z = 0 on the ground (the Matrice's walls run 28 m down the hill below the church).
        z = -info.get("blender_zero_cm", 0.0)
        spawn("%s/SM_M80_%s" % (folder, key), (x, y, z), key)
        placed[key] = [key]
        # Pieces where they were in Blender, relative to the main mesh.
        for part, p in info.get("pieces", {}).items():
            o = p["offset_cm"]
            spawn("%s/SM_M80_%s_%s" % (folder, key, part), (x + o[0], y + o[1], z + o[2]), "%s_%s" % (key, part), "Edifici/" + key)
            placed[key].append(part)
    for name, (x, y) in PROPS:
        spawn("/Game/Mazzarino80/Kit/Arredo/" + name, (x, y, 0), name[7:], "Arredo")
    post = spawn(CUBE, (-1800, -6000, 90), "Riferimento_180cm", "Arredo")
    post.set_actor_scale3d(unreal.Vector(0.3, 0.3, 1.8))
    return placed


VIEWS = {
    "comune": ((-6500, -6500, 2500), (0, 0, 800)),
    "chiesa_comune": ((-4500, 7000, 1800), (0, 12000, 700)),
    "matrice": ((12000, -6500, 2500), (20000, 0, 1200)),
    "matrice_interno": ((20000, -1500, 600), (20000, 1500, 500)),
    "madonna": ((32000, -8000, 4500), (40000, 0, 800)),
    "castello": ((8000, 12000, 7000), (20000, 25000, 1500)),
    "arredo": ((-1050, -6700, 180), (-1500, -6050, 50)),
}


def views():
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    for name, (eye, target) in VIEWS.items():
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*eye), unreal.Vector(*target))
        cap.capture(unreal.Vector(*eye), rot, RENDER / ("%s.png" % name))
        yield 2
    cap.destroy()


def steps():
    RENDER.mkdir(parents=True, exist_ok=True)
    placed = build_level()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().startswith(MAP), world.get_path_name()
    (RENDER / "placed.json").write_text(json.dumps(placed, indent=1), encoding="utf-8")
    yield 600
    for _ in views():
        yield 2
    yield 300
    for _ in views():                    # second pass, after everything has streamed in
        yield 2


m80_seq.Sequencer(steps(), log_file=str(RENDER / "error.txt"))
