"""Imports the shop and interior packages of D:/Mazzarino80_Sorgenti/Interni_e_Negozi (made on the other PC: Kit Bottega,
Bar Sport, Tabaccheria, Edicola, Cabina SIP) with their own scripts (<package>/unreal/import_pacchetto.py: one shared
material library /Game/Mazzarino/Libreria, meshes in /Game/Mazzarino/<Package>), in the order they need each other, then
lays their reference layouts side by side in a small test map, /Game/Mazzarino80/Negozi/Maps/L_M80_ProvaNegozi (floor,
sun and sky; each package along the X axis, its facade line at its origin), and photographs them.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_negozi_import.py -ForceLit -TimeoutMinutes 90
Env M80_SOLO_MAPPA=1: only the map and photos (packages already imported; with M80_CABINA=1 the booth skeletal too). M80_SOLO_LUCI=1: only the lights' strength
(M80_LUCI_SCALA, default 0.15 of the packages' lumens: at full strength they looked too bright; white lamps made warm) and the photos.
Report: Saved/Mazzarino80/Negozi/negozi.json, photos in Saved/Mazzarino80/Negozi
"""
import json
import os
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


# The phone booth package builds on the original booth's skeleton, clips and materials, which this project keeps
# in /Game/Mazzarino80/Kit/CabinaTelefonica (Scripts/m80_cabina_import.py), not in /Game/CabinaTelefonica.
REMAP = {"/Game/CabinaTelefonica/": "/Game/Mazzarino80/Kit/CabinaTelefonica/"}


def run_package_script(pkg, name):
    path = os.path.join(SRC, pkg, "unreal", name)
    if not os.path.isfile(path):
        return "missing"
    try:
        code = open(path, encoding="utf-8").read()
        for a, b in REMAP.items():
            code = code.replace(a, b)
        exec(compile(code, path, "exec"), {"__name__": "__main__", "__file__": path})
        return "ok"
    except Exception:  # noqa: BLE001 - noted, the next package goes on
        return traceback.format_exc().splitlines()[-1]


def booth_graphics(path):
    """The package's importer sets the graphics' slots on copies of the slot array (Python hands out copies), so the
    sign, instructions, tariff and emergency plate stayed empty (default grid material): each empty M_G_* slot gets its
    MI_G_* of the shared library, the slot put back into the array. Their base material is flagged for skeletal use."""
    sk = unreal.load_asset(path)
    slots = sk.get_editor_property("materials") if sk else []
    done = []
    for i in range(len(slots)):
        s = slots[i]
        name = str(s.get_editor_property("material_slot_name"))
        if s.get_editor_property("material_interface") or not name.startswith("M_G_"):
            continue
        mi = unreal.load_asset("/Game/Mazzarino/Libreria/Materiali/MI_" + name[2:])
        if not mi:
            continue
        base = mi.get_base_material()
        if base and not base.get_editor_property("used_with_skeletal_mesh"):
            base.set_editor_property("used_with_skeletal_mesh", True)
            unreal.MaterialEditingLibrary.recompile_material(base)
            unreal.EditorAssetLibrary.save_loaded_asset(base)
        s.set_editor_property("material_interface", mi)
        slots[i] = s
        done.append(name)
    if done:
        sk.set_editor_property("materials", slots)
        unreal.EditorAssetLibrary.save_loaded_asset(sk)
    return done


SCALE = float(os.environ.get("M80_LUCI_SCALA", "0.15"))
WARM_K = 2800.0    # colour temperature of the white lamps (user: warm, not cold)


def dim_lights():
    """The packages' lights at SCALE of their lumens; the original value kept in a tag, so runs do not add up."""
    n = warm = 0
    for a in EAS.get_all_level_actors():
        comp = a.get_component_by_class(unreal.LocalLightComponent)
        if not comp or not str(a.get_folder_path()).startswith("Mazzarino"):
            continue
        orig = next((float(str(t)[6:]) for t in a.tags if str(t).startswith("M80Lm_")), None)
        if orig is None:
            orig = comp.get_editor_property("intensity")
            a.tags = list(a.tags) + [unreal.Name("M80Lm_%g" % orig)]
        comp.set_editor_property("intensity", orig * SCALE)
        # White or cold lamps made warm (incandescent): only the coloured ones (signs, indicators) keep their colour.
        c = comp.get_editor_property("light_color")
        if max(c.r, c.g, c.b) - min(c.r, c.g, c.b) < 60:
            comp.set_editor_property("light_color", unreal.Color(255, 255, 255, 255))
            comp.set_editor_property("use_temperature", True)
            comp.set_editor_property("temperature", WARM_K)
            warm += 1
        n += 1
    report["lights_scaled"] = [n, SCALE, warm, WARM_K]


def photos():
    cap = m80_seq.ViewCapture(1280, 720, 70)
    for i, pkg in enumerate(ORDER):
        o = V(i * SPACING, 0, 0)
        views = (("strada", o + V(900, -600, 300), o + V(-200, 0, 150)),
                 ("dentro", o + V(-150, -450, 170), o + V(-450, 200, 100)),
                 ("alto", o + V(600, 0, 1300), o + V(-500, 0, 0)))
        if pkg == "Cabina_SIP_Mazzarino":   # a booth of about 1 m: close views (street, phone, roof sign)
            views = (("strada", o + V(260, -170, 190), o + V(0, 0, 120)),
                     ("dentro", o + V(150, 25, 165), o + V(0, 0, 140)),
                     ("alto", o + V(230, -120, 330), o + V(0, 0, 240)))
        for name, eye, at in views:
            cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, at), str(OUT / ("%s_%s.png" % (pkg, name))))
            yield 5
    cap.destroy()


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("M80_SOLO_LUCI"):
        unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        yield 40
        dim_lights()
        unreal.EditorLoadingAndSavingUtils.save_current_level()
        yield 10
        for s in photos():
            yield s
        (OUT / "negozi.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        return
    if not os.environ.get("M80_SOLO_MAPPA"):
        for pkg in ORDER:
            report["import"][pkg] = run_package_script(pkg, "import_pacchetto.py")
            yield 5
    if not os.environ.get("M80_SOLO_MAPPA") or os.environ.get("M80_CABINA"):
        # The phone booth's own skeletal mesh (glass that breaks on its bones), on the original booth's skeleton.
        report["import"]["Cabina_SIP_sk"] = run_package_script("Cabina_SIP_Mazzarino", "import_cabina_sip.py")
        report["import"]["Cabina_SIP_grafiche"] = booth_graphics("/Game/Mazzarino/CabinaSIP/Cabina/SK_CS_Cabina_SIP")
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
        layout = "monta_cabina_sip.py" if pkg == "Cabina_SIP_Mazzarino" else "piazza_riferimento.py"
        report["layouts"][pkg] = [run_package_script(pkg, layout)]
        report["layouts"][pkg].append(len(EAS.get_all_level_actors()) - before)
        yield 5
    EAS.set_selected_level_actors([])
    dim_lights()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 20
    # Photos: from the street (X is towards the street) and from inside each layout.
    for s in photos():
        yield s
    (OUT / "negozi.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
