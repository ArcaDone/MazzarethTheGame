"""Redraws the sidewalks made by the houses' Marciapiedi switch (labels Marciapiede_<lot>_<n>) from their house's
facades: the ones made while the magnet was on had their ends pulled onto the next house. The same actors take the new
lines (their files stay); only the sidewalks whose line moved are saved. A house whose number of lines changed (sides
ticked differently since) is left for the editor: there sidewalks would be deleted and made new.
Env: M80_PROVA=1  report only, save nothing
Out: Saved/Mazzarino80/Marciapiedi/rifai.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_marciapiedi_rifai.py -TimeoutMinutes 60
"""
import json
import os
import re
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Marciapiedi"
PROVA = os.environ.get("M80_PROVA") == "1"
FROM_HOUSE = re.compile(r"^Marciapiede_(\d+)_\d+$")
MARGIN = 4000.0


def cls_name(d):
    c = d.get_editor_property("native_class")
    return c.get_name() if c else ""


def label(d):
    return str(d.get_editor_property("label"))


def points(a):
    path = a.get_editor_property("path")
    return [tuple(round(v) for v in (q.x, q.y, q.z)) for q in
            (path.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD) for i in range(path.get_number_of_spline_points()))]


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    lots = {FROM_HOUSE.match(label(d)).group(1) for d in descs if cls_name(d) == "M80Sidewalk" and FROM_HOUSE.match(label(d))}
    houses = [d for d in descs if cls_name(d) == "M80House" and label(d)[len("Casa_"):] in lots]
    report = {"prova": PROVA, "case": len(houses), "rifatti": [], "invariati": [], "da_fare_a_mano": [], "errori": []}
    m80_seq.load([d for d in descs if "Landscape" in cls_name(d)])
    yield 120
    for group in m80_seq.tiles(houses, 30000.0):
        lo = [min(d.get_editor_property("bounds").min.x for d in group) - MARGIN, min(d.get_editor_property("bounds").min.y for d in group) - MARGIN]
        hi = [max(d.get_editor_property("bounds").max.x for d in group) + MARGIN, max(d.get_editor_property("bounds").max.y for d in group) + MARGIN]
        context = []
        for d in descs:
            b = d.get_editor_property("bounds")
            if b.min.x <= hi[0] and b.max.x >= lo[0] and b.min.y <= hi[1] and b.max.y >= lo[1] \
                    and "HLOD" not in cls_name(d) and "Landscape" not in cls_name(d):
                context.append(d)
        m80_seq.load(context)
        yield 90
        unreal.M80EditorLibrary.finish_all_compilation()
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        by_label = {a.get_actor_label(): a for a in actors}
        to_save = []
        for d in group:
            house = by_label.get(label(d))
            if not house:
                report["errori"].append("non caricata: " + label(d))
                continue
            lot = label(d)[len("Casa_"):]

            def mine():
                return [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                        if isinstance(a, unreal.M80Sidewalk) and FROM_HOUSE.match(a.get_actor_label())
                        and FROM_HOUSE.match(a.get_actor_label()).group(1) == lot]
            made = house.get_editor_property("marciapiedi_creati")
            if len(made) != len(mine()):
                report["da_fare_a_mano"].append({"casa": label(d), "motivo": "marciapiedi non tutti caricati o non suoi"})
                continue
            before = {a.get_actor_label(): points(a) for a in mine()}
            lines = len(before)
            house.rifai_marciapiedi()
            after = {a.get_actor_label(): points(a) for a in mine()}
            if len(after) != lines:
                report["da_fare_a_mano"].append({"casa": label(d), "motivo": "%d linee invece di %d" % (len(after), lines)})
                continue
            changed = [n for n in after if before.get(n) != after[n]]
            if changed:
                report["rifatti"].append({"casa": label(d), "marciapiedi": changed})
                to_save += [a for a in mine() if a.get_actor_label() in changed]
            else:
                report["invariati"].append(label(d))
        if to_save and not PROVA:
            unreal.EditorLoadingAndSavingUtils.save_packages([a.get_outermost() for a in to_save], True)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "rifai.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
        m80_seq.unload(context)
        unreal.SystemLibrary.collect_garbage()
        yield 30
    report["finito"] = True
    (OUT / "rifai.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "rifai_errore.txt"))
