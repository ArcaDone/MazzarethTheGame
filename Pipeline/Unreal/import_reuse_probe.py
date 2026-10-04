"""Import two Blender FBX files and report their UE5 centimetre bounds."""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export"
DEST = "/Game/Mazzarino80/ReuseKit/ScaleProbe"
FILES = (
    EXPORT / "modules/SM_M80_B80__Ground_002.fbx",
    EXPORT / "pilots/SM_M80_QA_STYLE_01_1249069204.fbx",
)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
report = []

for file in FILES:
    existing = unreal.EditorAssetLibrary.load_asset(DEST + "/" + file.stem)
    if existing:
        paths = [existing.get_path_name()]
    else:
        options = unreal.FbxImportUI()
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        mesh_options = options.get_editor_property("static_mesh_import_data")
        mesh_options.set_editor_property("combine_meshes", True)
        mesh_options.set_editor_property("generate_lightmap_u_vs", False)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(file))
        task.set_editor_property("destination_path", DEST)
        task.set_editor_property("destination_name", file.stem)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("options", options)
        asset_tools.import_asset_tasks([task])
        paths = list(task.get_editor_property("imported_object_paths"))
    if len(paths) != 1:
        raise RuntimeError(f"Unexpected import paths for {file}: {paths}")
    mesh = unreal.EditorAssetLibrary.load_asset(paths[0])
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Not a StaticMesh: {paths[0]}")
    bounds = mesh.get_bounds()
    size = [round(getattr(bounds.box_extent, axis) * 2, 2) for axis in ("x", "y", "z")]
    report.append({"file": str(file), "asset": paths[0], "bounds_cm": size,
                   "lods": mesh.get_num_lods(),
                   "materials": [str(slot.material_slot_name) for slot in mesh.get_editor_property("static_materials")]})

result = {"assets": report}
(ROOT / "Pipeline/Unreal/reuse_scale_probe.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_REUSE_SCALE_PROBE", json.dumps(result))
