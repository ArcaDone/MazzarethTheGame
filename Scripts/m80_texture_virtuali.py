"""Virtual textures plugged into ordinary texture samplers. A material instance can override a texture parameter whose
sampler is not virtual with a texture that streams as a virtual texture: the editor still draws it, the packaged game
draws black (the plastered houses of the town came out black, their plaster textures were virtual).
For every material instance under /Game/Mazzarino80, each overridden texture that is virtual while its base material's
sampler default is not is reported; such a texture stops streaming as virtual when no instance uses it as virtual on
purpose. Saves only the textures it changed. M80_VT_DRY=1 only reports.
Out: Saved/Mazzarino80/Memoria/texture_virtuali.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_texture_virtuali.py -TimeoutMinutes 60
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
DRY = os.environ.get("M80_VT_DRY") == "1"
MEL = unreal.MaterialEditingLibrary


def is_virtual(texture):
    try:
        return bool(texture.get_editor_property("virtual_texture_streaming"))
    except Exception:  # noqa: BLE001 (not a 2D texture)
        return False


def steps():
    report = {"wrong": [], "virtual_on_purpose": [], "changed": [], "errors": []}
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    wrong, wanted = {}, set()
    for root in ROOTS:
        flt = unreal.ARFilter(package_paths=[root], class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "MaterialInstanceConstant")],
                              recursive_paths=True)
        for data in ar.get_assets(flt):
            mi = unreal.load_asset(str(data.package_name))
            base = mi.get_base_material() if mi else None
            if not base:
                continue
            for p in mi.get_editor_property("texture_parameter_values"):
                tex = p.parameter_value
                if not tex or not is_virtual(tex):
                    continue
                name = p.parameter_info.name
                default = MEL.get_material_default_texture_parameter_value(base, name)
                row = {"instance": mi.get_path_name(), "parameter": str(name), "texture": tex.get_path_name(),
                       "sampler_default": default.get_path_name() if default else None}
                if default and not is_virtual(default):
                    wrong.setdefault(tex.get_path_name(), tex)
                    report["wrong"].append(row)
                else:
                    wanted.add(tex.get_path_name())
                    report["virtual_on_purpose"].append(row)
    yield 5
    for path, tex in wrong.items():
        if path in wanted:
            report["errors"].append("also used as virtual, left as it is: " + path)
            continue
        if DRY:
            continue
        tex.set_editor_property("virtual_texture_streaming", False)
        if unreal.EditorAssetLibrary.save_loaded_asset(tex, only_if_is_dirty=False):
            report["changed"].append(path)
        else:
            report["errors"].append("not saved: " + path)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "texture_virtuali.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "texture_virtuali_errore.txt"))
