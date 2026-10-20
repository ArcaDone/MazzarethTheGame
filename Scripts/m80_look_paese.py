"""The realistic look chosen with test A (m80_look_realistico.py) applied to the town L_M80_Paese_WP: on its Atmosfera
"Colore naturale" and "Camera a mano" (the weather, hour and wetness stay as they are), and the lens volume "Look
realistico" (unbound, always loaded) with the same settings and MI_M80_Obiettivo. Saves only those two actors.
Out: Saved/Mazzarino80/Look/look_paese.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_look_paese.py
"""
import json
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402
import m80_look_realistico as look  # noqa: E402

VOLUME = "Look realistico"


def steps():
    report = {"map": m80_seq.TOWN_MAP}
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(m80_seq.TOWN_MAP + "."):
        raise RuntimeError("wrong map open: " + world.get_path_name())
    atmos = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Atmosphere))
    if len(atmos) != 1:
        raise RuntimeError("expected one Atmosfera in the town, found %d" % len(atmos))
    atmo = atmos[0]
    atmo.modify()
    atmo.set_editor_property("natural_colour", True)
    atmo.set_editor_property("handheld_camera", True)
    atmo.apply()
    volume = look.look_volume(world, unreal.load_asset(look.LOOK + "/MI_M80_Obiettivo"), VOLUME)
    volume.set_editor_property("is_spatially_loaded", False)   # World Partition: wherever the player is
    report["atmosfera"] = {k: str(atmo.get_editor_property(k)) for k in ("weather", "hour", "wetness", "natural_colour", "handheld_camera")}
    report["pp_skipped"] = look.SKIPPED
    yield 5
    packages = [atmo.get_package(), volume.get_package()]
    report["saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_packages(packages, False))
    report["packages"] = [p.get_name() for p in packages]
    look.OUT.mkdir(parents=True, exist_ok=True)
    (look.OUT / "look_paese.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(look.OUT / "look_paese_errore.txt"))
