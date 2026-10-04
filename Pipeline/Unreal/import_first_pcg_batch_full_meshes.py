"""Import 67 irregular wall meshes and 67 roofs for the full PCG batch."""
from pathlib import Path
import json
import traceback
import unreal

root = Path(unreal.Paths.project_dir())
source = root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/MeshSource"
destination = "/Game/Mazzarino80/PCG/DistrictBatch01_Full/Meshes"
files = sorted(source.glob("SM_PCG_*.obj"))
if len(files) != 134:
    raise RuntimeError("Expected 134 generated wall/roof OBJ files")
tasks = []
for file in files:
    path = destination + "/" + file.stem
    if unreal.load_asset(path):
        continue
    task = unreal.AssetImportTask()
    task.filename = str(file)
    task.destination_path = destination
    task.destination_name = file.stem
    task.automated = True
    task.save = True
    task.replace_existing = False
    tasks.append(task)
report = {"source": str(source), "destination": destination,
          "requested": len(tasks), "imported": {}, "errors": {}}
try:
    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
except Exception:
    report["errors"]["batch"] = traceback.format_exc()
for file in files:
    mesh = unreal.load_asset(destination + "/" + file.stem)
    if not isinstance(mesh, unreal.StaticMesh):
        report["errors"][file.stem] = "missing or wrong class"
        continue
    bounds = mesh.get_bounds()
    report["imported"][file.stem] = {
        "path": mesh.get_path_name(),
        "size_cm": [round(bounds.box_extent.x * 2, 2),
                    round(bounds.box_extent.y * 2, 2),
                    round(bounds.box_extent.z * 2, 2)],
    }
dest = root / "Pipeline/Unreal/first_pcg_batch_full_mesh_import.json"
dest.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_FIRST_BATCH_FULL_MESH_IMPORT", len(report["imported"]), len(report["errors"]))
if len(report["imported"]) != 134 or report["errors"]:
    raise RuntimeError("Full PCG mesh import incomplete")
