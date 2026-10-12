"""Looks at the recovered lamps /Game/Migrated/Lamp_city and /Game/Migrated/Madonna/Lampione before they get a light:
who uses them (Asset Registry referencers: town actors, Blueprints), their size and material slots. Nothing is saved.
(Where the glass is was measured on the OBJ export of m80_lampioni_migrati.py: Geometry Script is not enabled.)
Output: Saved/Mazzarino80/Lampioni/ispeziona.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_lampioni_ispeziona.py
"""
import json
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Lampioni"
MESHES = ["/Game/Migrated/Lamp_city", "/Game/Migrated/Madonna/Lampione"]


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    report = {}
    for path in MESHES:
        r = {}
        refs = reg.get_referencers(path, unreal.AssetRegistryDependencyOptions())
        r["referencers"] = sorted(str(x) for x in (refs or []))
        mesh = unreal.load_asset(path)
        bb = mesh.get_bounding_box()
        r["box"] = [vec(bb.min), vec(bb.max)]
        r["nanite"] = mesh.get_editor_property("nanite_settings").get_editor_property("enabled")
        r["slots"] = []
        for i, s in enumerate(mesh.get_editor_property("static_materials")):
            m = s.get_editor_property("material_interface")
            r["slots"].append([i, str(s.get_editor_property("material_slot_name")), m.get_path_name() if m else None])
        report[path] = r
    (OUT / "ispeziona.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


try:
    run()
finally:
    unreal.SystemLibrary.quit_editor()
