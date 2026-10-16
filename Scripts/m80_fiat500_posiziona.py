"""Puts the Fiat 500 where the heavy cars stood, before their classes are removed: in the town (L_M80_Paese_WP) and in
the action test map (L_M80_ProvaAzione) every placed M80CarPanda / Fiat127 / FiatUno / Golf / Fiat126 becomes an
M80CarFiat500 with the same transform (labelled Auto_Fiat500), and the old actor is deleted.
Out: Saved/Mazzarino80/Veicoli/posiziona_500.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_fiat500_posiziona.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Veicoli"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OLD = ("M80CarPanda", "M80CarFiat127", "M80CarFiatUno", "M80CarGolf", "M80CarFiat126")
ACTION_MAP = "/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione"


def replace(actors, report, save_each):
    for old in actors:
        t = old.get_actor_transform()
        loc = t.translation + unreal.Vector(0, 0, 10)
        new = EAS.spawn_actor_from_class(unreal.M80CarFiat500, loc, t.rotation.rotator())
        new.set_actor_label("Auto_Fiat500")
        folder = old.get_folder_path()
        if folder:
            new.set_folder_path(folder)
        row = {"old": old.get_actor_label(), "class": old.get_class().get_name(), "at": [round(loc.x), round(loc.y), round(loc.z)]}
        pkg = old.get_outermost()
        EAS.destroy_actor(old)
        if save_each:
            row["saved_new"] = unreal.EditorLoadingAndSavingUtils.save_packages([new.get_outermost()], False)
            row["saved_old"] = unreal.EditorLoadingAndSavingUtils.save_packages([pkg], False)
            row["old_package"] = pkg.get_name()
        report.append(row)


def steps():
    report = {"town": [], "action": []}
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    m80_seq.load([d for d in descs if "Landscape" in (d.get_editor_property("native_class").get_name()
                                                      if d.get_editor_property("native_class") else "")])
    yield 60
    m80_seq.load(m80_seq.actor_descs(*OLD))
    yield 30
    replace([a for a in EAS.get_all_level_actors() if a.get_class().get_name() in OLD], report["town"], True)
    yield 10

    unreal.EditorLoadingAndSavingUtils.load_map(ACTION_MAP)
    yield 30
    replace([a for a in EAS.get_all_level_actors() if a.get_class().get_name() in OLD], report["action"], False)
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 5
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "posiziona_500.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "posiziona_500_errore.txt"))
