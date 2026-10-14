"""Probe: the parameters of Epic's MetaHuman clothing materials (Optional/Clothing/Common), to build the 1980s clothes'
fabrics on them, and what the FBX import made of ours.
Out: Saved/Mazzarino80/Folla/Vestiti/materiali.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_vestiti_materiali_sonda.py
"""
import json
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Folla/Vestiti"
MEL = unreal.MaterialEditingLibrary


def params(m):
    out = {}
    for kind, names, get in (
            ("scalar", MEL.get_scalar_parameter_names, MEL.get_material_default_scalar_parameter_value),
            ("vector", MEL.get_vector_parameter_names, MEL.get_material_default_vector_parameter_value),
            ("texture", MEL.get_texture_parameter_names, MEL.get_material_default_texture_parameter_value),
            ("switch", MEL.get_static_switch_parameter_names, MEL.get_material_default_static_switch_parameter_value)):
        try:
            out[kind] = {str(n): str(get(m, n)) for n in names(m)}
        except Exception as e:  # noqa: BLE001
            out[kind] = repr(e)
    return out


def main():
    report = {}
    for path in unreal.EditorAssetLibrary.list_assets("/MetaHumanCharacter/Optional/Clothing", recursive=True):
        a = unreal.load_asset(path)
        if isinstance(a, (unreal.Material, unreal.MaterialInstance)):
            entry = {"class": a.get_class().get_name()}
            if isinstance(a, unreal.MaterialInstance):
                entry["parent"] = a.get_editor_property("parent").get_path_name() if a.get_editor_property("parent") else None
                base = a
                while isinstance(base, unreal.MaterialInstance) and base.get_editor_property("parent"):
                    base = base.get_editor_property("parent")
                entry["params"] = params(base)
            else:
                entry["params"] = params(a)
                entry["two_sided"] = a.get_editor_property("two_sided")
                entry["shading"] = str(a.get_editor_property("shading_model"))
            report[path] = entry
    ours = unreal.load_asset("/Game/Mazzarino80/Personaggi/Vestiti/Fazzoletto/Seta_nera")
    if ours:
        parent = ours.get_editor_property("parent") if isinstance(ours, unreal.MaterialInstance) else None
        report["ours"] = {"class": ours.get_class().get_name(), "parent": parent.get_path_name() if parent else None,
                          "params": params(parent or ours)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "materiali.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


try:
    main()
finally:
    unreal.SystemLibrary.quit_editor()
