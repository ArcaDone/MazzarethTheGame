"""Validate selected Comune meshes and their /Game dependencies in UE 5.5."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
PLAN = json.loads((ROOT / "Pipeline/Unreal/comune_migration_plan.json").read_text(encoding="utf-8"))
OUT = ROOT / "Pipeline/Unreal/comune_migration_validation.json"
registry = unreal.AssetRegistryHelpers.get_asset_registry()
options = unreal.AssetRegistryDependencyOptions()
options.include_hard_package_references = True
options.include_soft_package_references = True
options.include_searchable_names = False
options.include_soft_management_references = False
options.include_hard_management_references = False

packages = []
for path in PLAN["packages"]:
    asset = unreal.EditorAssetLibrary.load_asset(path)
    dependencies = [str(dep) for dep in registry.get_dependencies(path, options)
                    if str(dep).startswith("/Game/")]
    missing_dependencies = [dep for dep in dependencies if not unreal.EditorAssetLibrary.does_asset_exist(dep)]
    record = {"path": path, "loaded": bool(asset), "missing_dependencies": missing_dependencies}
    if isinstance(asset, unreal.StaticMesh):
        record["materials"] = [slot.material_interface.get_path_name() if slot.material_interface else None
                               for slot in asset.get_editor_property("static_materials")]
        record["bounds_cm"] = [round(getattr(asset.get_bounds().box_extent, axis) * 2, 1)
                               for axis in ("x", "y", "z")]
    packages.append(record)

report = {"roots": PLAN["roots"], "packages": packages,
          "loaded": sum(x["loaded"] for x in packages),
          "missing": [x["path"] for x in packages if not x["loaded"]],
          "unresolved_references": {x["path"]: x["missing_dependencies"] for x in packages
                                    if x["missing_dependencies"]}}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("COMUNE_MIGRATION_VALIDATION", report["loaded"], len(packages),
      "missing", len(report["missing"]), "unresolved", len(report["unresolved_references"]))
