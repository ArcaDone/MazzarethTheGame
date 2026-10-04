"""What the game really uses: recursive package dependencies (hard and soft) of the official town map,
the test levels and every /Game/ path written in the C++ plugins and Config. Everything else under the
checked folders is a candidate for deletion. Read only: nothing is changed.
Report: Saved/Mazzarino80/Audit/content_audit.json.
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
OUT = ROOT / "Saved/Mazzarino80/Audit/content_audit.json"
ROOTS = [
    "/Game/Mazzarino80/Houses/Maps/L_M80_Paese",
    "/Game/Mazzarino80/Vehicles/L_M80_ProvaGuida",
    "/Game/Mazzarino80/Rooms/L_M80_RoomStudio",
    "/Game/Mazzarino80/Player/BP_M80_Giocatore",
]
CHECK = ["/Game/Levels", "/Game/Mazzarino80/Library", "/Game/Mazzarino80/PCG", "/Game/Mazzarino80/ReuseKit",
         "/Game/Mazzarino80/Houses", "/Game/Mazzarino80/Kit", "/Game/Mazzarino80/RoadSource", "/Game/Mazzarino80/Historic",
         "/Game/Mazzarino80/Overview", "/Game/Migrated", "/Game/Esercitazioni", "/Game/__ExternalActors__", "/Game/Drive"]


def code_paths():
    paths = set()
    for base in (ROOT / "Plugins", ROOT / "Config", ROOT / "Source"):
        for f in base.rglob("*"):
            if f.suffix.lower() in (".cpp", ".h", ".ini") and f.is_file():
                for m in re.findall(r"/Game/[A-Za-z0-9_/]+", f.read_text(encoding="utf-8", errors="ignore")):
                    paths.add(m.split(".")[0])
    return paths


def run():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True,
                                                 include_searchable_names=False, include_soft_management_references=False,
                                                 include_hard_management_references=False)
    roots = list(ROOTS) + sorted(code_paths())
    used = set()
    todo = [r for r in roots]
    while todo:
        p = todo.pop()
        if p in used or not p.startswith("/Game/"):
            continue
        used.add(p)
        deps = reg.get_dependencies(unreal.Name(p), opts) or []
        for d in deps:
            d = str(d)
            if d.startswith("/Game/") and d not in used:
                todo.append(d)
        if len(used) % 2000 == 0:
            yield 1
    report = {"roots": roots, "used_packages": len(used), "folders": {}}
    content = ROOT / "Content"
    for folder in CHECK:
        disk = content / folder[len("/Game/"):]
        if not disk.exists():
            continue
        total = unused = 0
        unused_list = []
        used_list = []
        for f in disk.rglob("*"):
            if f.suffix not in (".uasset", ".umap"):
                continue
            pkg = "/Game/" + str(f.relative_to(content).with_suffix("")).replace("\\", "/")
            size = f.stat().st_size
            total += size
            if pkg in used:
                used_list.append(pkg)
            else:
                unused += size
                if f.suffix == ".umap" or size > 20 * 1024 * 1024:
                    unused_list.append([pkg, round(size / 1048576, 1)])
        report["folders"][folder] = {"total_mb": round(total / 1048576), "unused_mb": round(unused / 1048576),
                                     "used_packages": len(used_list), "big_unused": sorted(unused_list, key=lambda x: -x[1])[:40],
                                     "used_sample": used_list[:15]}
        yield 1
    # Which maps are used by nothing we keep.
    maps = reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "World"))
    report["maps"] = []
    for a in maps:
        pkg = str(a.package_name)
        if not pkg.startswith("/Game/"):
            continue
        f = content / (pkg[len("/Game/"):] + ".umap")
        report["maps"].append([pkg, round(f.stat().st_size / 1048576, 1) if f.exists() else None, pkg in used,
                               [str(x) for x in (reg.get_referencers(unreal.Name(pkg), opts) or [])][:5]])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
