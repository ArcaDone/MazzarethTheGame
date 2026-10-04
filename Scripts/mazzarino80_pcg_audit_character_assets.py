"""Read-only audit of candidate architectural modules for the 18-house pass."""
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir())
ASSETS = [
    "/Game/City_of_Brass_Enviroment/Meshes/Corridor_A/Corridor_A_Box02_Ex",
    "/Game/Migrated/Balcony",
    "/Game/Migrated/Balcony2",
    "/Game/Mazzarino80/Library/ComuneDetail/Migrated/Balcony",
    "/Game/Mazzarino80/Library/ComuneDetail/Migrated/Balcony2",
    "/Game/Megapack/Meshes/MiddleEast/SM_Platform_Water_Tank_01",
    "/Game/Megascans/3D_Assets/Rusty_Gas_Tank_vizqehw/S_Rusty_Gas_Tank_vizqehw_lod3_Var1",
    "/Game/Megascans/3D_Assets/Rusty_Gas_Tank_udmkdejqx/S_Rusty_Gas_Tank_udmkdejqx_lod3",
    "/Game/OldWestAssets/OldWestVol4/VOL4/Meshes/SM_WaterContainer_01a",
    "/Engine/BasicShapes/Cylinder",
    "/Game/Migrated/Case/building_base_001",
    "/Game/Migrated/Case/building_base_002",
    "/Game/Migrated/Case/building_base_003",
    "/Game/Migrated/Case/building_base_004",
    "/Game/Migrated/Case/building_top_001",
    "/Game/Megapack/Textures/Favela/T_Bricks_01_BC",
    "/Game/Megapack/Textures/Favela/T_Bricks_01_N",
    "/Game/Megapack/Textures/Favela/T_Bricks_01_ORM",
    "/Game/Megapack/Textures/Favela/T_Wall_H",
]


def main():
    result = {}
    for path in ASSETS:
        asset = unreal.load_asset(path)
        item = {"exists": bool(asset), "class": str(asset.get_class().get_name()) if asset else ""}
        if isinstance(asset, unreal.StaticMesh):
            bounds = asset.get_bounds()
            item["size_cm"] = [round(v * 2, 2) for v in (bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z)]
            item["origin_cm"] = [round(v, 2) for v in (bounds.origin.x, bounds.origin.y, bounds.origin.z)]
            item["materials"] = [str(m.material_interface.get_path_name()) if m.material_interface else ""
                                 for m in asset.get_editor_property("static_materials")]
        result[path] = item
    dest = ROOT / "Saved/Mazzarino80/PCG/character_asset_audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    unreal.log("M80_CHARACTER_ASSETS " + str(dest))


main()
