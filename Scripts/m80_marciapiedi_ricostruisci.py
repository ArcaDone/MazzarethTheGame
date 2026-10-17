"""Rebuilds every sidewalk (AM80Sidewalk) of the town map L_M80_Paese_WP with the current code (2026-10-17: the slab
is one mesh laid on the ground every 50 cm at both edges, lava-stone sides, instead of 3 m stretched boxes) and saves
their actor files. World Partition: region by region (300 m tiles), the sidewalks are loaded with the landscape and
the other actors around them (the slab is laid on whatever ground is there), rebuilt, saved, unloaded.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_marciapiedi_ricostruisci.py -TimeoutMinutes 120
Report: Saved/Mazzarino80/marciapiedi_ricostruiti.json
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/marciapiedi_ricostruiti.json"
report = {"tiles": 0, "rebuilt": 0, "skipped": []}


def gid(g):
    return unreal.GuidLibrary.conv_guid_to_string(g)


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 120
    every = m80_seq.actor_descs()
    walks = [d for d in every if m80_seq.desc_class_is(d, "M80Sidewalk")]
    report["sidewalks"] = len(walks)
    for tile in m80_seq.tiles(walks, 30000.0):
        xs = [m80_seq.desc_center(d).x for d in tile]
        ys = [m80_seq.desc_center(d).y for d in tile]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        radius = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 6000.0
        # The ground the slabs are laid on: everything around, except the HLOD shells.
        around = [d for d in m80_seq.near(every, cx, cy, radius) if not m80_seq.desc_class_is(d, "WorldPartitionHLOD")]
        m80_seq.load(around)
        yield 30
        world = m80_seq.editor_world()
        guids = {gid(d.get_editor_property("guid")) for d in tile}
        for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Sidewalk):
            # Only this tile's: a neighbour's at the edge of what is loaded could miss part of its ground.
            if gid(a.get_editor_property("actor_guid")) not in guids:
                continue
            try:
                a.rebuild()
                report["rebuilt"] += 1
            except Exception as e:  # noqa: BLE001
                report["skipped"].append([a.get_actor_label(), str(e)])
        yield 5
        m80_seq.save_all()
        yield 10
        m80_seq.unload(around)
        yield 10
        report["tiles"] += 1
        OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT.with_suffix(".errore.txt")))
