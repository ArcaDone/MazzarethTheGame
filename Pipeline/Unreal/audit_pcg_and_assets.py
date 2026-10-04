"""Read-only UE 5.5 editor audit for the Mazzarino sample and existing reuse assets."""
import json
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Pipeline" / "Unreal" / "audit_pcg_and_assets.json"
registry = unreal.AssetRegistryHelpers.get_asset_registry()


def asset_info(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        return {"path": path, "loaded": False}
    data = {"path": path, "loaded": True, "class": asset.get_class().get_name()}
    if isinstance(asset, unreal.StaticMesh):
        bounds = asset.get_bounds()
        data["bounds_cm"] = [round(getattr(bounds.box_extent, axis) * 2, 2)
                             for axis in ("x", "y", "z")]
        data["materials"] = [str(slot.material_interface.get_path_name()) if slot.material_interface else None
                             for slot in asset.get_editor_property("static_materials")]
        data["nanite"] = bool(asset.get_editor_property("nanite_settings").enabled)
        data["lods"] = asset.get_num_lods()
    return data


paths = [
    "/Game/Mazzarino80/PCG/DA_Buildings_Test18",
    "/Game/Mazzarino80/PCG/BP_ProceduralBuilding",
    "/Game/Megapack/Meshes/MiddleEast/SM_metal_gate_01",
    "/Game/Megapack/Meshes/MiddleEast/SM_wooden_gates_01",
    "/Game/Megapack/Meshes/MiddleEast/SM_clothes_A_01",
    "/Game/Migrated/Balcony",
    "/Game/Migrated/Balcony2",
]
report = {"assets": [asset_info(path) for path in paths], "buildings": [], "graphs": []}
catalog = unreal.EditorAssetLibrary.load_asset(paths[0])
if catalog:
    for b in catalog.get_editor_property("buildings"):
        entry = {"id": str(b.get_editor_property("building_id"))}
        for field in ("family", "primary_floors", "floor_height_cm", "roof_type", "facade_type",
                      "character_profile", "variation_seed", "courtyard_gate", "external_bathroom",
                      "facade_flue", "ivy", "cactus"):
            try:
                entry[field] = str(b.get_editor_property(field))
            except Exception:
                pass
        report["buildings"].append(entry)

for data in registry.get_assets_by_path("/Game/Mazzarino80/PCG", recursive=True):
    if "PCGGraph" in str(data.asset_class_path.asset_name):
        report["graphs"].append(str(data.package_name))

OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_AUDIT_WRITTEN", OUT)
