"""Material usage flags for the packaged game. In the editor a material missing a usage flag is fixed on the fly; in a
cooked game it falls back to the default material (the churches, Palazzo Bartoli, the plants came out grey).
- every base material under /Game/Mazzarino80 (surface domain, opaque or masked) gets "Used with Nanite";
- the ones the packaged game's log named for other usages get those (Terracotta: instanced meshes, the chrome of the
  Ape: skeletal meshes).
Saves only the materials it changed.
Out: Saved/Mazzarino80/Memoria/flag_materiali.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_flag_materiali.py -TimeoutMinutes 60
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Memoria"
ROOTS = ["/Game/Mazzarino80"]
# Material (or instance) path -> usage property names it needs besides Nanite.
EXTRA = {
    "/Game/Mazzarino80/ReuseKit/Materials/MI_M80_Terracotta": ["used_with_instanced_static_meshes"],
    "/Game/StarterContent/Materials/M_Metal_Chrome": ["used_with_skeletal_mesh"],
}
MEL = unreal.MaterialEditingLibrary


def base_of(asset):
    if isinstance(asset, unreal.MaterialInstance):
        return asset.get_base_material()
    return asset


def steps():
    report = {"nanite": [], "extra": [], "skipped": 0, "errors": []}
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    todo = {}
    for root in ROOTS:
        flt = unreal.ARFilter(package_paths=[root], class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "Material")],
                              recursive_paths=True)
        for data in ar.get_assets(flt):
            todo[str(data.package_name)] = set(["used_with_nanite"])
        # Instances here whose base material lives elsewhere (Megapack, Megascans, Starter Content).
        flt = unreal.ARFilter(package_paths=[root], class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "MaterialInstanceConstant")],
                              recursive_paths=True)
        for data in ar.get_assets(flt):
            b = base_of(unreal.load_asset(str(data.package_name)))
            if b:
                todo.setdefault(b.get_outermost().get_name(), set()).add("used_with_nanite")
    yield 5
    for path, props in EXTRA.items():
        a = unreal.load_asset(path)
        b = base_of(a) if a else None
        if b:
            todo.setdefault(b.get_outermost().get_name(), set()).update(props)
        else:
            report["errors"].append("not found: " + path)
    changed = []
    for i, path in enumerate(sorted(todo)):
        if not path.startswith("/Game/"):
            continue   # never the engine's own materials
        m = unreal.load_asset(path)
        if not isinstance(m, unreal.Material):
            continue
        props = set(todo[path])
        if "used_with_nanite" in props and (m.get_editor_property("material_domain") != unreal.MaterialDomain.MD_SURFACE or
                                            m.get_editor_property("blend_mode") not in (unreal.BlendMode.BLEND_OPAQUE,
                                                                                        unreal.BlendMode.BLEND_MASKED)):
            props.discard("used_with_nanite")
        set_now = [p for p in props if not m.get_editor_property(p)]
        if not set_now:
            report["skipped"] += 1
            continue
        for p in set_now:
            m.set_editor_property(p, True)
        MEL.recompile_material(m)
        changed.append(m)
        report["nanite" if set_now == ["used_with_nanite"] else "extra"].append([path, set_now])
        if i % 20 == 0:
            yield 1
    yield 30
    if changed:
        report["saved"] = unreal.EditorLoadingAndSavingUtils.save_packages([m.get_outermost() for m in changed], False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "flag_materiali.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "flag_materiali_errore.txt"))
