"""Reimport one wall/roof pair and verify the OBJ inverse-Y correction."""
from pathlib import Path
import json
import math
import unreal

root = Path(unreal.Paths.project_dir())
source = root / "Research/Mazzarino80/PCG/DistrictBatch01_Full/MeshSource"
destination = "/Game/Mazzarino80/PCG/DistrictBatch01_Full/Meshes"
lot = "1249054419"
report = {"lot": lot, "assets": {}}
for role in ("Walls", "Roof"):
    name = f"SM_PCG_{role}_{lot}"
    file = source / (name + ".obj")
    original = unreal.load_asset(destination + "/" + name)
    if not isinstance(original, unreal.StaticMesh):
        raise RuntimeError("Existing mesh missing " + name)
    task = unreal.AssetImportTask()
    task.filename = str(file)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(destination + "/" + name)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Reimported mesh missing " + name)
    description = mesh.get_static_mesh_description(0)
    vertices = [description.get_vertex_position(unreal.VertexID(i)) for i in range(3)]
    with file.open("r", encoding="utf-8") as stream:
        source_vertices = []
        for line in stream:
            if line.startswith("v "):
                source_vertices.append([float(x) for x in line.split()[1:4]])
                if len(source_vertices) == 3:
                    break
    actual = [[v.x, v.y, v.z] for v in vertices]
    expected = [[v[0], -v[1], v[2]] for v in source_vertices]
    errors = [math.dist(a, b) for a, b in zip(actual, expected)]
    report["assets"][name] = {"path": mesh.get_path_name(),
                              "first_source_vertices": source_vertices,
                              "first_imported_vertices": actual,
                              "max_vertex_error_cm": max(errors)}
    if max(errors) > 0.02:
        raise RuntimeError("OBJ import did not align " + name)

out = root / "Pipeline/Unreal/first_pcg_alignment_sample_result.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_ALIGNMENT_SAMPLE", report)
