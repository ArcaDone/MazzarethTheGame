"""Assigns the plant meshes (migrated from Comune, moved to Kit/Plants by m80_plants_to_kit.py) to the house styles (houses V3, step 3.2).

Climbers (ivy), ground plants (weeds, cactus) and wall plants (capers-like tufts) go to every
DA_M80Style_*; the generator places and scales them (FM80HouseParams.Vegetation).
Writes the mesh bounds to Saved/Mazzarino80/HousesV2/plants_report.json to tune orientation.
"""
import json
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
STYLES = "/Game/Mazzarino80/Houses/Styles"
CLIMBERS = [
    "/Game/Mazzarino80/Kit/Plants/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var1_lod1",
    "/Game/Mazzarino80/Kit/Plants/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var5_lod1",
]
GROUND = [
    "/Game/Mazzarino80/Kit/Plants/Megapack/Meshes/Favela/Plants/SM_Plant_01",
    "/Game/Mazzarino80/Kit/Plants/Megapack/Meshes/Favela/Plants/SM_Plant_10",
    "/Game/Mazzarino80/Kit/Plants/Megapack/Meshes/Yakohama/SM_Plants_01",
    "/Game/Mazzarino80/Kit/Plants/Megascans/3D_Assets/Cactus_udugcc3fa/S_Cactus_udugcc3fa_lod3_Var1",
]
WALL = [
    "/Game/Mazzarino80/Kit/Plants/Megapack/Meshes/Favela/Plants/SM_Plant_05",
]
POTS = [
    "/Game/Mazzarino80/Kit/Plants/Megapack/Meshes/Yakohama/SM_FlowerPots_01",
    "/Game/Mazzarino80/Kit/Plants/Megapack/Meshes/Yakohama/SM_FlowerPots_04",
    "/Game/Mazzarino80/Kit/Plants/Megapack/Meshes/Yakohama/SM_FlowerPots_07",
]


def load(paths, report):
    meshes = []
    for path in paths:
        mesh = unreal.load_asset(path)
        if not mesh:
            report.setdefault("missing", []).append(path)
            continue
        box = mesh.get_bounding_box()
        report.setdefault("bounds", {})[path.rsplit("/", 1)[-1]] = [
            round(box.min.x), round(box.min.y), round(box.min.z), round(box.max.x), round(box.max.y), round(box.max.z)]
        meshes.append(mesh)
        # Instanced by the houses: the base materials need the ISM usage flag saved, or they
        # only compile it on the fly (invisible plants until the shaders are ready).
        for slot in mesh.get_editor_property("static_materials"):
            mat = slot.get_editor_property("material_interface")
            base = mat.get_base_material() if mat else None
            if base and not base.get_editor_property("used_with_instanced_static_meshes"):
                base.set_editor_property("used_with_instanced_static_meshes", True)
                unreal.EditorAssetLibrary.save_loaded_asset(base, only_if_is_dirty=False)
                report.setdefault("ism_flag", []).append(base.get_path_name())
    return meshes


def run():
    report = {}
    climbers, ground, wall, pots = load(CLIMBERS, report), load(GROUND, report), load(WALL, report), load(POTS, report)
    for data in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(STYLES):
        style = unreal.load_asset(str(data.package_name))
        if not isinstance(style, unreal.M80HouseStyle):
            continue
        style.set_editor_property("climber_meshes", climbers)
        style.set_editor_property("ground_plant_meshes", ground)
        style.set_editor_property("wall_plant_meshes", wall)
        # Ivy strands are flat in the mesh XZ plane: turn them parallel to the wall.
        style.set_editor_property("climber_yaw", -90.0)
        if not style.get_editor_property("prop_meshes"):
            style.set_editor_property("prop_meshes", pots)
        unreal.EditorAssetLibrary.save_loaded_asset(style, only_if_is_dirty=False)
        report.setdefault("styles", []).append(str(data.package_name))
    out = ROOT / "Saved/Mazzarino80/HousesV2/plants_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")


try:
    run()
finally:
    unreal.SystemLibrary.quit_editor()
