"""Moves the plant and pot meshes used by the house styles, with their materials and textures, from the
gitignored Megascans/Megapack folders into the versioned /Game/Mazzarino80/Kit/Plants (houses V3).

Textures are reduced to 1K with a JPEG source. Redirectors stay in the old (ignored) folders, so other
content that used the same assets keeps working. Run m80_houses_plants.py afterwards (new paths).
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
KIT = "/Game/Mazzarino80/Kit/Plants"
SOURCES = ("/Game/Megascans/", "/Game/Megapack/")
REPORT = ROOT / "Saved/Mazzarino80/HousesV2/plants_kit_report.json"
OLD_MESHES = [
    "/Game/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var1_lod1",
    "/Game/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var5_lod1",
    "/Game/Megapack/Meshes/Favela/Plants/SM_Plant_01",
    "/Game/Megapack/Meshes/Favela/Plants/SM_Plant_10",
    "/Game/Megapack/Meshes/Yakohama/SM_Plants_01",
    "/Game/Megascans/3D_Assets/Cactus_udugcc3fa/S_Cactus_udugcc3fa_lod3_Var1",
    "/Game/Megapack/Meshes/Favela/Plants/SM_Plant_05",
    "/Game/Megapack/Meshes/Yakohama/SM_FlowerPots_01",
    "/Game/Megapack/Meshes/Yakohama/SM_FlowerPots_04",
    "/Game/Megapack/Meshes/Yakohama/SM_FlowerPots_07",
]


def new_path(old):
    for src in SOURCES:
        if old.startswith(src):
            return KIT + "/" + old[len("/Game/"):]
    return None


def run():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True)
    todo, seen = list(OLD_MESHES), []
    while todo:
        pkg = todo.pop()
        if pkg in seen or not new_path(pkg):
            continue
        seen.append(pkg)
        for dep in registry.get_dependencies(pkg, options) or []:
            todo.append(str(dep))
    report = {"moved": [], "textures": []}
    for pkg in seen:
        dst = new_path(pkg)
        if unreal.EditorAssetLibrary.does_asset_exist(dst):
            continue
        if not unreal.EditorAssetLibrary.does_asset_exist(pkg):
            continue
        if unreal.EditorAssetLibrary.rename_asset(pkg, dst):
            report["moved"].append(dst)
    yield 10
    for path in unreal.EditorAssetLibrary.list_assets(KIT, recursive=True):
        asset = unreal.load_asset(path)
        if isinstance(asset, unreal.Texture2D):
            changed = unreal.M80EditorLibrary.downsize_texture_source(asset, 1024)
            changed = unreal.M80EditorLibrary.compress_texture_source_jpeg(asset, 88) or changed
            if changed:
                report["textures"].append(path)
            unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
            unreal.SystemLibrary.collect_garbage()
            yield 1
    unreal.EditorAssetLibrary.save_directory(KIT, only_if_is_dirty=False, recursive=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
