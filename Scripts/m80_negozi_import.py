"""Imports the shop and interior packages of D:/Mazzarino80_Sorgenti/Interni_e_Negozi (made on the other PC: Kit Bottega,
Bar Sport, Tabaccheria, Edicola, Cabina SIP) with their own scripts (<package>/unreal/import_pacchetto.py: one shared
material library /Game/Mazzarino/Libreria, meshes in /Game/Mazzarino/<Package>), in the order they need each other, then
lays their reference layouts side by side in a small test map, /Game/Mazzarino80/Negozi/Maps/L_M80_ProvaNegozi (floor,
sun and sky; each package along the X axis, its facade line at its origin), and photographs them.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_negozi_import.py -ForceLit -TimeoutMinutes 90
Env M80_SOLO_MAPPA=1: only the map and photos (packages already imported).
Report: Saved/Mazzarino80/Negozi/negozi.json, photos in Saved/Mazzarino80/Negozi
"""
import json
import os
import runpy
import sys
import traceback
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

SRC = "D:/Mazzarino80_Sorgenti/Interni_e_Negozi"
ORDER = ["Kit_Bottega_Mazzarino", "Bar_Sport_Mazzarino", "Tabaccheria_Mazzarino", "Edicola_Mazzarino", "Cabina_SIP_Mazzarino"]
MAP = "/Game/Mazzarino80/Negozi/Maps/L_M80_ProvaNegozi"
OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Negozi"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector
report = {"import": {}, "layouts": {}, "assets": {}}
SPACING = 2500.0   # cm between the packages' reference layouts


def run_package_script(pkg, name):
    path = os.path.join(SRC, pkg, "unreal", name)
    if not os.path.isfile(path):
        return "missing"
    try:
        runpy.run_path(path, run_name="__main__")
        return "ok"
    except Exception:  # noqa: BLE001 - noted, the next package goes on
        return traceback.format_exc().splitlines()[-1]


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("M80_SOLO_MAPPA"):
        for pkg in ORDER:
            report["import"][pkg] = run_package_script(pkg, "import_pacchetto.py")
            yield 5
        # The phone booth's own skeletal mesh (glass that breaks on its bones).
        report["import"]["Cabina_SIP_sk"] = run_package_script("Cabina_SIP_Mazzarino", "import_cabina_sip.py")
        yield 5
    for pkg in ORDER:
        n = len(unreal.EditorAssetLibrary.list_assets("/Game/Mazzarino/" + pkg.replace("_Mazzarino", ""), True, False)) \
            if unreal.EditorAssetLibrary.does_directory_exist("/Game/Mazzarino/" + pkg.replace("_Mazzarino", "")) else 0
        report["assets"][pkg] = n
    report["assets"]["Libreria"] = len(unreal.EditorAssetLibrary.list_assets("/Game/Mazzarino/Libreria", True, False))
    (OUT / "negozi.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    # Test map: a floor, sun and sky; each package's reference layout at its own origin along X.
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        yield 30
        for a in EAS.get_all_level_actors():
            if a.get_folder_path() and str(a.get_folder_path()).startswith("Mazzarino"):
                EAS.destroy_actor(a)
    else:
        les.new_level(MAP, False)
        yield 20
        floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), V(SPACING * 2, 0, -1))
        floor.set_actor_scale3d(V(160, 60, 1))
        floor.set_actor_label("Pavimento")
        sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 800), unreal.Rotator(0, -40, 130))
        sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
        EAS.spawn_actor_from_class(unreal.SkyAtmosphere, V(0, 0, 0))
        sky = EAS.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 500))
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
        EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V(0, 0, 0))
        yield 10
    for i, pkg in enumerate(ORDER):
        anchor = EAS.spawn_actor_from_class(unreal.TargetPoint, V(i * SPACING, 0, 0))
        anchor.set_actor_label("Origine_" + pkg)
        EAS.set_selected_level_actors([anchor])
        before = len(EAS.get_all_level_actors())
        report["layouts"][pkg] = [run_package_script(pkg, "piazza_riferimento.py")]
        report["layouts"][pkg].append(len(EAS.get_all_level_actors()) - before)
        yield 5
    EAS.set_selected_level_actors([])
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 20
    # Photos: from the street (X is towards the street) and from inside each layout.
    cap = m80_seq.ViewCapture(1280, 720, 70)
    for i, pkg in enumerate(ORDER):
        o = V(i * SPACING, 0, 0)
        for name, eye, at in (("strada", o + V(900, -600, 300), o + V(-200, 0, 150)),
                              ("dentro", o + V(-150, -450, 170), o + V(-450, 200, 100)),
                              ("alto", o + V(600, 0, 1300), o + V(-500, 0, 0))):
            cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, at), str(OUT / ("%s_%s.png" % (pkg, name))))
            yield 5
    cap.destroy()
    (OUT / "negozi.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
