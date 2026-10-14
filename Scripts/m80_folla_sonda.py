"""What the 5.8 MetaHuman Creator gives us for the NPCs, before generating them: for each preset character (Optional
content) whether it is rigged and can be built, its height and body type; the wardrobe items (clothes, hair, beards);
the build parameters and pipelines (normal and MetaHuman Crowd). Nothing is saved.
Output: Saved/Mazzarino80/Personaggi/folla_sonda.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_sonda.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Personaggi"
REG = unreal.AssetRegistryHelpers.get_asset_registry()


def assets(path, cls=None):
    found = REG.get_assets_by_path(path, recursive=True)
    return sorted(str(a.package_name) for a in found if cls is None or str(a.asset_class_path.asset_name) == cls)


def props(obj):
    out = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            value = obj.get_editor_property(name)
        except Exception:  # noqa: BLE001 - dir() also lists methods
            continue
        out[name] = str(value)[:200]
    return out


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    yield 30
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    presets = {}
    for path in assets("/MetaHumanCharacter/Optional/Presets", "MetaHumanCharacter"):
        c = unreal.load_asset(path)
        entry = {"added": subsystem.try_add_object_to_edit(c)}
        entry["can_build"] = subsystem.can_build_meta_human(c, False)
        try:
            for k in subsystem.get_body_constraints(c):
                if str(k.get_editor_property("name")) in ("Height", "Fat", "Masculine/Feminine", "Muscularity"):
                    entry[str(k.get_editor_property("name"))] = round(k.get_editor_property("target_measurement"), 2)
        except Exception as e:  # noqa: BLE001
            entry["constraints_error"] = str(e)
        if not presets:
            entry["props"] = props(c)
        subsystem.remove_object_to_edit(c)
        presets[path.rsplit("/", 1)[1]] = entry
        yield 2
    report["presets"] = presets
    report["wardrobe_items"] = assets("/MetaHumanCharacter/Optional/Clothing", "MetaHumanWardrobeItem") + \
        assets("/MetaHumanCharacter/Optional/Grooms", "MetaHumanWardrobeItem")
    report["outfits"] = assets("/MetaHumanCharacter/Optional/Clothing", "ChaosOutfitAsset")
    report["build_params"] = props(unreal.MetaHumanCharacterEditorBuildParameters())
    report["pipeline_classes"] = [n for n in dir(unreal) if "Pipeline" in n and "MetaHuman" in n]
    report["crowd_content"] = assets("/MetaHumanCrowd")
    report["mh_content_roots"] = sorted({"/".join(p.split("/")[:3]) for p in assets("/MetaHumanCharacter")})
    (OUT / "folla_sonda.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "folla_sonda_error.txt"))
