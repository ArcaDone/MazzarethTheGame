"""Read-only pivots and bounds for proposed district detail assets."""
import json
from pathlib import Path
import unreal

paths = {
    "rain_pipe": "/Game/Megapack/Meshes/Favela/SM_Rain_Pipe_01",
    "ivy": "/Game/Mazzarino80/Library/Comune/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var3_lod1",
    "pot": "/Game/Mazzarino80/Library/Comune/Megascans/3D_Assets/Flower_Pot_tmekfduiw/S_Flower_Pot_tmekfduiw_lod3",
    "door": "/Game/Mazzarino80/Library/Comune/OldWestAssets/OldWestVol6/VOL6/Meshes/SM_Door_06c",
    "awning": "/Game/Megapack/Meshes/MiddleEast/SM_awning_01",
    "clothes": "/Game/Megapack/Meshes/Favela/Mannequin/SM_Clothes_01",
}
out = {}
for role, path in paths.items():
    mesh = unreal.load_asset(path)
    if not mesh:
        out[role] = {"path": path, "missing": True}
        continue
    bounds = mesh.get_bounds()
    b = mesh.get_bounding_box()
    out[role] = {
        "path": mesh.get_path_name(),
        "origin": [bounds.origin.x, bounds.origin.y, bounds.origin.z],
        "box_extent": [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
        "box_min": [b.min.x, b.min.y, b.min.z],
        "box_max": [b.max.x, b.max.y, b.max.z],
        "materials": [slot.material_interface.get_path_name() if slot.material_interface else None
                      for slot in mesh.get_editor_property("static_materials")],
    }
dest = Path(unreal.Paths.project_dir()) / "Pipeline/Unreal/first_batch_detail_mesh_audit.json"
dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_DETAIL_MESHES", len(out))
