"""Correct only Batch01 FullPCG wall/roof assets after the OBJ Y-axis diagnosis.

Run in the open graphical editor: another UE process cannot save packages while
that editor has them open. Point data, 18 approved houses and source maps stay put.
"""
from hashlib import sha256
from pathlib import Path
import json
import math
import traceback
import unreal

root = Path(unreal.Paths.project_dir())
source = root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/MeshSource"
destination = "/Game/Mazzarino80/PCG/DistrictBatch01_Full/Meshes"
files = sorted(source.glob("SM_PCG_*.obj"))
if len(files) != 134:
    raise RuntimeError("Expected exactly 67 wall and 67 roof OBJ files")
protected = [root / "Content/Levels" / (name + ".umap") for name in (
    "Mazzarino80_Panoramica", "Mazzarino80_CaseStoriche_Campione",
    "Mazzarino80_PCG_Quartieri_Preview", "Mazzarino80_PCG_Quartieri_Batch01")]
before = {p.name: sha256(p.read_bytes()).hexdigest() for p in protected}
report_path = root / "Pipeline/Unreal/first_pcg_batch_alignment_reimport.json"
report = {"source": str(source), "destination": destination,
          "total": len(files), "checked": 0, "corrected": [], "already_correct": [],
          "errors": {}, "source_maps_unchanged": None, "status": "running"}

def save_report():
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

def source_vertices(file, count=8):
    vertices = []
    with file.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("v "):
                x, y, z = (float(x) for x in line.split()[1:4])
                vertices.append((x, -y, z))  # Expected after Unreal OBJ import.
                if len(vertices) >= count:
                    break
    return vertices

def vertex_error(mesh, expected):
    description = mesh.get_static_mesh_description(0)
    if description.get_vertex_count() < len(expected):
        raise RuntimeError("Imported mesh has fewer vertices than source")
    errors = []
    for index, wanted in enumerate(expected):
        actual = description.get_vertex_position(unreal.VertexID(index))
        errors.append(math.dist((actual.x, actual.y, actual.z), wanted))
    return max(errors)

save_report()
for file in files:
    name = file.stem
    try:
        mesh = unreal.load_asset(destination + "/" + name)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError("Missing StaticMesh " + name)
        expected = source_vertices(file)
        old_error = vertex_error(mesh, expected)
        if old_error <= 0.03:
            report["already_correct"].append(name)
        else:
            task = unreal.AssetImportTask()
            task.filename = str(file)
            task.destination_path = destination
            task.destination_name = name
            task.automated = True
            task.save = True
            task.replace_existing = True
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            mesh = unreal.load_asset(destination + "/" + name)
            new_error = vertex_error(mesh, expected)
            if new_error > 0.03:
                raise RuntimeError("Mesh still misaligned after import: %.2f cm" % new_error)
            if not unreal.EditorAssetLibrary.save_loaded_asset(mesh):
                raise RuntimeError("Could not save corrected StaticMesh")
            report["corrected"].append(name)
        report["checked"] += 1
    except Exception:
        report["errors"][name] = traceback.format_exc()
        report["status"] = "failed"
        save_report()
        raise
    if report["checked"] % 10 == 0 or report["checked"] == len(files):
        save_report()

after = {p.name: sha256(p.read_bytes()).hexdigest() for p in protected}
report["source_maps_unchanged"] = before == after
report["status"] = "complete" if before == after else "source_map_changed"
save_report()
if before != after:
    raise RuntimeError("A protected source map changed")
print("M80_ALIGNMENT_REIMPORT", report["checked"], len(report["corrected"]),
      len(report["already_correct"]))
