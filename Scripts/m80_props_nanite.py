"""Turns on Nanite for the detail meshes the houses scatter (Sicilian kit, plants, climbers, laundry...).

Thousands of houses each draw their props as instanced meshes: as Nanite meshes they are drawn by
the GPU in a few passes instead of tens of thousands of draw calls. The meshes are found as the
static meshes referenced by the house styles (Houses/Styles/DA_M80Style_*). Meshes with translucent
materials are left as they are (Nanite does not draw them). Report: Saved/Mazzarino80/props_nanite.json.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
STYLES = "/Game/Mazzarino80/Houses/Styles"
REPORT = ROOT / "Saved/Mazzarino80/props_nanite.json"
EAL = unreal.EditorAssetLibrary
TRANSLUCENT = (unreal.BlendMode.BLEND_TRANSLUCENT, unreal.BlendMode.BLEND_ADDITIVE, unreal.BlendMode.BLEND_MODULATE)


def style_meshes():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True)
    found = set()
    for path in EAL.list_assets(STYLES, recursive=False):
        package = path.split(".")[0]
        for dep in reg.get_dependencies(package, opts) or []:
            dep = str(dep)
            if dep.startswith("/Game/") and EAL.does_asset_exist(dep):
                data = EAL.find_asset_data(dep)
                if str(data.asset_class_path.asset_name) == "StaticMesh":
                    found.add(dep)
    return sorted(found)


def translucent(mesh):
    for slot in mesh.get_editor_property("static_materials"):
        mat = slot.get_editor_property("material_interface")
        base = mat.get_base_material() if mat else None
        if base and base.get_editor_property("blend_mode") in TRANSLUCENT:
            return True
    return False


def run():
    yield 5
    report = {"enabled": [], "already": [], "skipped_translucent": []}
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for path in style_meshes():
        mesh = unreal.load_asset(path)
        settings = mesh.get_editor_property("nanite_settings")
        if settings.get_editor_property("enabled"):
            report["already"].append(path)
            continue
        if translucent(mesh):
            report["skipped_translucent"].append(path)
            continue
        settings.set_editor_property("enabled", True)
        sub.set_nanite_settings(mesh, settings, apply_changes=True)
        EAL.save_loaded_asset(mesh)
        report["enabled"].append(path)
        yield 1
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
