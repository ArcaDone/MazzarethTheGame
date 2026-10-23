"""Fits the town to the terrain as it is now: after the landscape was edited where houses, sidewalks, roads or stairs were
not loaded, they keep the old ground (raised or buried, also in the cooked game, which ships what the editor saved).
Tile by tile (300 m, landscape always loaded, everything within 40 m around), every house is rebuilt and compared with
itself (bottom of the walls every metre): only those that moved are baked again and saved. Then sidewalks, roads and
stairs are rebuilt (they follow the ground and the houses) and saved only if their geometry changed; sidewalks made by
a house's Marciapiedi switch lose the magnet on the way (it turned them onto the next house). Untouched actor
files stay as they are (no needless Git/LFS changes). Afterwards rebuild the HLODs.
Env: M80_ZONA=x,y,radius_m  only around that point (x, y in cm as in the editor's Location; e.g. 72378,8014,150)
     M80_PROVA=1           report only, save nothing
     M80_TOLLERANZA=5      cm a wall bottom may move before the house is redone
     M80_FOTO=6            pictures before/after of the first N houses redone (Saved/Mazzarino80/Terreno/foto)
     M80_DA=28 M80_QUANTI=8  only tiles 28..35, adding to the report of the earlier ones (memory grows tile after
                           tile: the whole town in one editor runs out of it; m80_adatta_terreno_tutto.ps1 restarts it)
Out: Saved/Mazzarino80/Terreno/adatta_terreno.json ("prossimo": the next tile to do, "finito" when all are done)
powershell -File Scripts/m80_adatta_terreno_tutto.ps1
"""
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Terreno"
FOLDER = "/Game/Mazzarino80/Houses/Baked/L_M80_Paese_WP"
MARGIN = 4000.0
TILE = 30000.0
PROVA = os.environ.get("M80_PROVA") == "1"
TOLLERANZA = float(os.environ.get("M80_TOLLERANZA", "5"))
ZONA = [float(v) for v in os.environ.get("M80_ZONA", "").split(",") if v.strip()]
FOTO = int(os.environ.get("M80_FOTO", "0"))
DA = int(os.environ.get("M80_DA", "0"))
QUANTI = int(os.environ.get("M80_QUANTI", "0"))
FOLLOWERS = ("M80Sidewalk", "M80Road", "M80Stairs")
# Sidewalks made by a house's Marciapiedi switch: already on its facades, the magnet only turned them onto a neighbour.
FROM_HOUSE = re.compile(r"^Marciapiede_\d+_\d+$")


def cls_name(d):
    c = d.get_editor_property("native_class")
    return c.get_name() if c else ""


def box(d):
    b = d.get_editor_property("bounds")
    return b.min, b.max


def overlaps(d, lo, hi):
    a, b = box(d)
    return a.x <= hi[0] and b.x >= lo[0] and a.y <= hi[1] and b.y >= lo[1]


def in_zone(d):
    if len(ZONA) != 3:
        return True
    c = m80_seq.desc_center(d)
    return math.hypot(c.x - ZONA[0], c.y - ZONA[1]) <= ZONA[2] * 100.0


def actors_by_name():
    return {a.get_name(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}


def key(d):
    return str(d.get_editor_property("actor_path")).rsplit(".", 1)[-1]


def photo(cap, house, name):
    origin, extent = house.get_actor_bounds(False)
    base = unreal.Vector(origin.x, origin.y, origin.z - extent.z + 150)
    # From high up: in the packed town a low camera ends up inside the next house.
    eye = base + unreal.Vector(-(extent.x + 600), -(extent.y + 600), extent.z * 2 + 2500)
    cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, base), OUT / "foto" / name)


def write(report):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "adatta_terreno.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")


def steps():
    t0 = time.time()
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    land = [d for d in descs if "Landscape" in cls_name(d)]
    m80_seq.load(land)
    yield 120
    targets = [d for d in descs if cls_name(d) in ("M80House",) + FOLLOWERS and in_zone(d)]
    report = {"prova": PROVA, "tolleranza_cm": TOLLERANZA, "zona": ZONA, "da_controllare": len(targets),
              "case_rifatte": [], "case_non_controllate": [], "seguono_rifatti": [], "errori": [], "riquadri": 0,
              "invariati": {"case": 0, "seguono": 0}, "minuti": 0}
    if DA > 0 and (OUT / "adatta_terreno.json").exists():
        report = json.loads((OUT / "adatta_terreno.json").read_text(encoding="utf-8"))
    unchanged = report["invariati"]
    minutes = report.get("minuti", 0)
    groups = m80_seq.tiles(targets, TILE)
    report["riquadri_totali"] = len(groups)
    for index, group in enumerate(groups):
        if index < DA:
            continue
        if QUANTI and index >= DA + QUANTI:
            break
        lo = [min(box(d)[0].x for d in group) - MARGIN, min(box(d)[0].y for d in group) - MARGIN]
        hi = [max(box(d)[1].x for d in group) + MARGIN, max(box(d)[1].y for d in group) + MARGIN]
        context = [d for d in descs if overlaps(d, lo, hi) and "HLOD" not in cls_name(d) and "Landscape" not in cls_name(d)]
        m80_seq.load(context)
        yield 90
        unreal.M80EditorLibrary.finish_all_compilation()
        yield 5
        by_name = actors_by_name()
        cap = m80_seq.ViewCapture(1280, 720, 60.0) if FOTO and len(report["case_rifatte"]) < FOTO else None
        to_save = []
        # Houses first: sidewalks with the magnet follow their facades.
        houses = [d for d in group if cls_name(d) == "M80House"]
        pending = []
        for i, d in enumerate(houses):
            a = by_name.get(key(d))
            if not a:
                report["errori"].append("non caricata: " + str(d.get_editor_property("label")))
                continue
            shot = cap is not None and len(report["case_rifatte"]) < FOTO
            if shot:
                photo(cap, a, "%s_prima.png" % a.get_actor_label())
            result, info = unreal.M80EditorLibrary.fit_house_to_ground(a, FOLDER, TOLLERANZA)
            if shot and result == 1:
                pending.append(a)
            elif shot:
                (OUT / "foto" / ("%s_prima.png" % a.get_actor_label())).unlink(missing_ok=True)
            if result == 1:
                report["case_rifatte"].append({"casa": a.get_actor_label(), "info": info})
                to_save.append(a)
            elif result == 0:
                unchanged["case"] += 1
            else:
                report["case_non_controllate"].append({"casa": a.get_actor_label(), "info": info})
            if i % 10 == 9:
                yield 1
        if pending:
            yield 30  # the rebuilt meshes reach the renderer
            for a in pending:
                photo(cap, a, "%s_dopo.png" % a.get_actor_label())
        for d in group:
            if cls_name(d) not in FOLLOWERS:
                continue
            a = by_name.get(key(d))
            if not a:
                report["errori"].append("non caricato: " + str(d.get_editor_property("label")))
                continue
            if isinstance(a, unreal.M80Sidewalk) and FROM_HOUSE.match(a.get_actor_label()) and a.get_editor_property("snap_to_houses"):
                a.set_editor_property("snap_to_houses", False)
            result = unreal.M80EditorLibrary.rebuild_on_ground(a)
            if result == 1:
                report["seguono_rifatti"].append(a.get_actor_label())
                to_save.append(a)
            elif result == 0:
                unchanged["seguono"] += 1
        if to_save and not PROVA:
            unreal.EditorAssetLibrary.save_directory(FOLDER, only_if_is_dirty=True, recursive=True)
            unreal.EditorLoadingAndSavingUtils.save_packages([a.get_outermost() for a in to_save], True)
        if cap:
            cap.destroy()
        report["riquadri"] += 1
        report["invariati"] = unchanged
        report["minuti"] = round(minutes + (time.time() - t0) / 60, 1)
        report["prossimo"] = index + 1
        write(report)
        m80_seq.unload(context)
        unreal.SystemLibrary.collect_garbage()
        yield 30
    report["finito"] = report.get("prossimo", 0) >= len(groups)
    write(report)
    yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
