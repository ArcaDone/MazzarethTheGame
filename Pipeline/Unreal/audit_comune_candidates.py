"""Read-only asset and dependency audit executed in the Comune UE 5.4 project."""
import json
from pathlib import Path
import unreal

OUT = Path(r"D:\UE5Projects\GameAnimationSample\Pipeline\Unreal\comune_candidate_audit.json")
ROOTS = {
    "clothes_middleeast": ("MiddleEast", ["SM_clothes_A_0", "SM_clothes_B_0"]),
    "clothes_favela": ("Favela/Mannequin", ["SM_Clothes_0"]),
    "stairs": ("MiddleEast", ["SM_stairs_01"]),
    "old_stairs": ("Favela", ["SM_Old_Stair_0"]),
    "pipes_middleeast": ("MiddleEast", ["SM_Water_Pipe_0"]),
    "pipes_favela": ("Favela", ["SM_Rain_Pipe_0"]),
    "awnings": ("MiddleEast", ["SM_awning"]),
    "railings_middleeast": ("MiddleEast", ["SM_balcony_0", "SM_Windows_grill_0", "SM_metal_fence_0"]),
    "railings_favela": ("Favela", ["SM_Metal_Fence_0"]),
    "wood": ("MiddleEast", ["SM_wooden_beams_0"]),
}
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions()
options.include_hard_package_references = True
options.include_soft_package_references = True
options.include_searchable_names = False
options.include_soft_management_references = False
options.include_hard_management_references = False


def describe(group, path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        return {"group": group, "path": path, "loaded": False}
    record = {"group": group, "path": path, "loaded": True,
              "class": asset.get_class().get_name()}
    if isinstance(asset, unreal.StaticMesh):
        extent = asset.get_bounds().box_extent
        record["bounds_cm"] = [round(getattr(extent, a) * 2, 1) for a in ("x", "y", "z")]
        record["materials"] = [slot.material_interface.get_path_name() if slot.material_interface else None
                               for slot in asset.get_editor_property("static_materials")]
        record["lods"] = asset.get_num_lods()
        try:
            record["vertices_lod0"] = asset.get_num_vertices(0)
            record["nanite"] = bool(asset.get_editor_property("nanite_settings").enabled)
        except Exception as error:
            record["mesh_stat_error"] = str(error)
    try:
        record["dependencies"] = [str(dep) for dep in registry.get_dependencies(path, options)
                                  if str(dep).startswith("/Game/")]
    except Exception as error:
        record["dependency_error"] = str(error)
    return record


records = []
for group, (folder, prefixes) in ROOTS.items():
    base = "/Game/Megapack/Meshes/" + folder
    for path in unreal.EditorAssetLibrary.list_assets(base, recursive=False, include_folder=False):
        name = path.rsplit("/", 1)[-1].split(".")[0]
        if any(name.startswith(prefix) for prefix in prefixes):
            records.append(describe(group, path.split(".")[0]))

OUT.write_text(json.dumps({"project": "Comune UE5.4", "candidates": records}, indent=2),
               encoding="utf-8")
print("COMUNE_CANDIDATE_AUDIT", OUT, "count", len(records))
