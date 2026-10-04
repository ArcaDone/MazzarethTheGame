"""Compute transitive /Game package dependencies for the selected Comune meshes."""
import json
from pathlib import Path
import unreal

OUT = Path(r"D:\UE5Projects\GameAnimationSample\Pipeline\Unreal\comune_migration_plan.json")
roots = [
    "/Game/Megapack/Meshes/Favela/Mannequin/SM_Clothes_01",
    "/Game/Megapack/Meshes/Favela/Mannequin/SM_Clothes_03",
    "/Game/Megapack/Meshes/Favela/SM_Old_Stair_01",
    "/Game/Megapack/Meshes/Favela/SM_Rain_Pipe_01",
    "/Game/Megapack/Meshes/MiddleEast/SM_awning_01",
]
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions()
options.include_hard_package_references = True
options.include_soft_package_references = True
options.include_searchable_names = False
options.include_soft_management_references = False
options.include_hard_management_references = False

queued = list(roots)
seen = set()
edges = {}
while queued:
    package = queued.pop()
    if package in seen:
        continue
    seen.add(package)
    dependencies = sorted(str(item) for item in registry.get_dependencies(package, options)
                          if str(item).startswith("/Game/"))
    edges[package] = dependencies
    queued.extend(dep for dep in dependencies if dep not in seen)

OUT.write_text(json.dumps({"roots": roots, "packages": sorted(seen),
                           "dependencies": edges}, indent=2), encoding="utf-8")
print("COMUNE_MIGRATION_PLAN", OUT, "roots", len(roots), "packages", len(seen))
