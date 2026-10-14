"""Probe for the 1980s clothes: how Epic's parametric default garment is made, and the source bodies for Blender.

- the Dataflow graphs of the default garment's cloth assets and outfit asset (M80EditorLibrary.describe_dataflow),
  the wardrobe item's properties and the wardrobe slots (which take more than one item);
- the full bodies (head and body merged, the outfits' source body format) of the characters the clothes are
  modelled on, exported to /Game/Mazzarino80/Personaggi/Vestiti/Corpi and to FBX for Blender.
Out: Saved/Mazzarino80/Folla/Vestiti/sonda.json, sonda_<asset>.txt; Saved/Mazzarino80/Folla/Corpi/<Key>_FullBody.fbx
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_vestiti_sonda.py
"""
import json
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Folla/Vestiti"
BODIES_OUT = ROOT / "Saved/Mazzarino80/Folla/Corpi"
CLOTHING = "/MetaHumanCharacter/Optional/Clothing/"
BODIES = "/Game/Mazzarino80/Personaggi/Vestiti/Corpi"
# Source bodies: an average man and woman, a short heavy old woman, a short old man, the protagonist.
SOURCES = {"Uomo2": "Folla", "Donna1": "Folla", "Anziana1": "Folla", "Anziano1": "Folla", "Sandro": "Sandro"}
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
LIB = unreal.M80EditorLibrary


def props(obj):
    out = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            value = obj.get_editor_property(name)
        except Exception:  # noqa: BLE001 - not a property
            continue
        out[name] = str(value)[:300]
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    BODIES_OUT.mkdir(parents=True, exist_ok=True)
    report = {"graphs": {}, "assets": {}, "bodies": {}}
    for name in ("DefaultGarment/ClothAssets/CA_DG_bodyShapeA", "DefaultGarment/ClothAssets/CA_mtd_archetype",
                 "OA_DefaultGarment", "WI_DefaultGarment"):
        asset = unreal.load_asset(CLOTHING + name)
        key = name.split("/")[-1]
        if asset is None:
            report["assets"][key] = "missing"
            continue
        report["assets"][key] = {"class": asset.get_class().get_name(), "props": props(asset)}
        graph = LIB.get_asset_dataflow(asset)
        if graph:
            report["graphs"][key] = graph.get_path_name()
            (OUT / ("sonda_%s.txt" % key)).write_text(LIB.describe_dataflow(graph), encoding="utf-8")

    # Wardrobe slots: names and whether a slot takes several items.
    preset = unreal.load_asset("/MetaHumanCharacter/Optional/Presets/Bruce")
    SUB.try_add_object_to_edit(preset)
    coll = SUB.get_preview_collection(preset)
    spec = coll.get_pipeline_specification()
    report["specification"] = props(spec)
    SUB.remove_object_to_edit(preset)

    params = unreal.MetaHumanGeometryExportParams()
    params.set_editor_property("project_path", BODIES)
    params.set_editor_property("head_skeletal_mesh", False)
    params.set_editor_property("body_skeletal_mesh", False)
    params.set_editor_property("full_body_skeletal_mesh", True)
    params.set_editor_property("overwrite_existing_assets", True)
    for key, folder in SOURCES.items():
        c = unreal.load_asset("/Game/Mazzarino80/Personaggi/%s/MHC_%s" % (folder, key))
        SUB.try_add_object_to_edit(c)
        unreal.MetaHumanCharacterExportBlueprintLibrary.export_geometry(c, params)
        mesh = unreal.load_asset("%s/MHC_%s_FullBody" % (BODIES, key))
        entry = {"mesh": mesh.get_path_name() if mesh else None}
        if mesh:
            task = unreal.AssetExportTask()
            task.set_editor_property("object", mesh)
            task.set_editor_property("filename", str(BODIES_OUT / ("%s_FullBody.fbx" % key)))
            task.set_editor_property("automated", True)
            task.set_editor_property("prompt", False)
            task.set_editor_property("replace_identical", True)
            opts = unreal.FbxExportOption()
            opts.set_editor_property("collision", False)
            opts.set_editor_property("level_of_detail", False)
            task.set_editor_property("options", opts)
            entry["fbx"] = unreal.Exporter.run_asset_export_task(task)
            entry["bounds"] = str(mesh.get_bounds())
            unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
        report["bodies"][key] = entry
        SUB.remove_object_to_edit(c)
    (OUT / "sonda.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


try:
    main()
finally:
    unreal.SystemLibrary.quit_editor()
