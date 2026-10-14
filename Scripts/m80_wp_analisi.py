"""How the town is split for World Partition streaming: for each actor class, how many actors, how many are always
loaded (not spatially loaded), their runtime grids and sizes, and how far they are from the PlayerStart; plus the
map's runtime grids (cell size and loading range) when Python can read them. Nothing is loaded or saved.
Output: Saved/Mazzarino80/Memoria/wp_analisi.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_wp_analisi.py
"""
import collections
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Memoria"


def prop(obj, *names):
    for n in names:
        try:
            return obj.get_editor_property(n)
        except Exception:  # noqa: BLE001
            pass
    return None


def grids(world):
    out = {}
    wp = prop(world.get_world_settings(), "world_partition")
    out["world_partition"] = str(wp)
    if not wp:
        return out
    for name in ("runtime_hash", "runtime_hash_set", "editor_hash"):
        out[name] = str(prop(wp, name))
    rh = prop(wp, "runtime_hash")
    if rh:
        g = prop(rh, "grids")
        if g is not None:
            out["grids"] = [{"name": str(prop(x, "grid_name")), "cell_m": (prop(x, "cell_size") or 0) / 100,
                             "loading_range_m": (prop(x, "loading_range") or 0) / 100} for x in g]
    return out


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    world = m80_seq.editor_world()
    descs = m80_seq.actor_descs()
    report = {"actors": len(descs), "settings": grids(world)}
    if descs:
        report["desc_properties"] = [p for p in dir(descs[0]) if not p.startswith("_")]
    start = next((m80_seq.desc_center(d) for d in descs if m80_seq.desc_class_is(d, "PlayerStart")), None)
    report["player_start"] = [round(start.x), round(start.y), round(start.z)] if start else None
    by = collections.defaultdict(lambda: {"count": 0, "always_loaded": 0, "grids": collections.Counter(),
                                          "size_m": collections.Counter(), "dist_m": collections.Counter()})
    for d in descs:
        cls = d.get_editor_property("native_class")
        r = by[cls.get_name() if cls else "?"]
        r["count"] += 1
        spatial = prop(d, "is_spatially_loaded", "b_is_spatially_loaded", "spatially_loaded")
        if spatial is False:
            r["always_loaded"] += 1
        r["grids"][str(prop(d, "runtime_grid"))] += 1
        b = d.get_editor_property("bounds")
        size = max(b.max.x - b.min.x, b.max.y - b.min.y) / 100
        r["size_m"]["<10" if size < 10 else "<50" if size < 50 else "<200" if size < 200 else "<1000" if size < 1000 else ">=1000"] += 1
        if start:
            c = m80_seq.desc_center(d)
            dist = math.hypot(c.x - start.x, c.y - start.y) / 100
            r["dist_m"]["<128" if dist < 128 else "<256" if dist < 256 else "<512" if dist < 512 else "<1024" if dist < 1024 else ">=1024"] += 1
    report["classes"] = {k: {kk: (dict(vv) if isinstance(vv, collections.Counter) else vv) for kk, vv in v.items()}
                         for k, v in sorted(by.items(), key=lambda kv: -kv[1]["count"])}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wp_analisi.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "wp_analisi_error.txt"))
