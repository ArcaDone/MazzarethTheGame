"""One-off resave after M80Road/M80Sidewalk pieces became instance components and cars stopped being spatially
loaded: every M80Road with pieces and every M80Sidewalk is rebuilt with the ground and the houses around it
loaded (tile by tile, landscape always loaded) and its actor file saved, so Play keeps the editor's geometry
instead of rebuilding it on streaming; every placed car (M80Car*) is resaved so World Partition's actor
descriptor says "not spatially loaded".
Env M80_SOLO=label[,label] limits the roads/sidewalks to those labels (a test).
Out: Saved/Mazzarino80/Risalva/risalva_strade.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_risalva_strade.py -TimeoutMinutes 90
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Risalva"
MARGIN = 4000.0
ONLY = [k for k in os.environ.get("M80_SOLO", "").split(",") if k]


def prop(obj, *names):
    for n in names:
        try:
            return obj.get_editor_property(n)
        except Exception:  # noqa: BLE001
            pass
    return None


def cls_name(d):
    c = d.get_editor_property("native_class")
    return c.get_name() if c else ""


def box(d):
    b = d.get_editor_property("bounds")
    return b.min, b.max


def overlaps(d, lo, hi):
    a, b = box(d)
    return a.x <= hi[0] and b.x >= lo[0] and a.y <= hi[1] and b.y >= lo[1]


def key(d):
    """Object name of the actor of a descriptor (end of its actor path)."""
    return str(prop(d, "actor_path")).rsplit(".", 1)[-1]


def actors_by_name():
    return {a.get_name(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}


def save(actor):
    actor.modify()
    return unreal.EditorLoadingAndSavingUtils.save_packages([actor.get_outermost()], False)


def pieces(actor):
    comps = actor.get_components_by_class(unreal.SplineMeshComponent)
    return len(comps)


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    report = {"cars": [], "tiles": [], "errors": []}
    land = [d for d in descs if "Landscape" in cls_name(d)]
    m80_seq.load(land)
    yield 120

    cars = [d for d in descs if cls_name(d).startswith("M80Car")]
    m80_seq.load(cars)
    yield 30
    by_name = actors_by_name()
    for d in cars:
        a = by_name.get(key(d))
        if not a:
            report["errors"].append("car not loaded: " + str(prop(d, "label")))
            continue
        if prop(a, "is_spatially_loaded"):
            a.set_editor_property("is_spatially_loaded", False)
        report["cars"].append({"label": a.get_actor_label(), "spatially_loaded": bool(prop(a, "is_spatially_loaded")), "saved": save(a)})

    targets = [d for d in descs if cls_name(d) in ("M80Road", "M80Sidewalk")]
    if ONLY:
        targets = [d for d in targets if str(prop(d, "label")) in ONLY]
    report["targets"] = len(targets)
    for group in m80_seq.tiles(targets, 30000.0):
        lo = [min(box(d)[0].x for d in group) - MARGIN, min(box(d)[0].y for d in group) - MARGIN]
        hi = [max(box(d)[1].x for d in group) + MARGIN, max(box(d)[1].y for d in group) + MARGIN]
        context = [d for d in descs if overlaps(d, lo, hi) and "HLOD" not in cls_name(d) and "Landscape" not in cls_name(d)]
        m80_seq.load(context)
        yield 90
        by_name = actors_by_name()
        tile = {"targets": len(group), "context": len(context), "items": []}
        for d in group:
            a = by_name.get(key(d))
            if not a:
                report["errors"].append("not loaded: " + str(prop(d, "label")))
                continue
            before = pieces(a)
            a.rebuild()
            tile["items"].append({"label": a.get_actor_label(), "class": a.get_class().get_name(), "pieces_before": before,
                                  "pieces_after": pieces(a), "saved": save(a)})
        report["tiles"].append(tile)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "risalva_strade.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        m80_seq.unload([d for d in context if not cls_name(d).startswith("M80Car")])
        yield 30
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "risalva_strade.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
