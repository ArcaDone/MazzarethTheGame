"""Read a few imported mesh vertices to detect axis conversion on OBJ import."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
asset = unreal.load_asset(
    "/Game/Mazzarino80/PCG/DistrictBatch01_Full/Meshes/SM_PCG_Walls_1249054419")
if not isinstance(asset, unreal.StaticMesh):
    raise RuntimeError("Wall asset missing")
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
report = {"asset_methods": [x for x in dir(asset) if "mesh_description" in x.lower()],
          "subsystem_methods": [x for x in dir(subsystem)
                                if "mesh_description" in x.lower() or "vertex" in x.lower()]}
report["geometry_script_types"] = [x for x in dir(unreal) if "GeometryScript" in x][:40]
report["mesh_exporter_types"] = [x for x in dir(unreal) if "StaticMeshExporter" in x]
description = asset.get_static_mesh_description(0)
report["description_type"] = str(type(description))
report["description_methods"] = [x for x in dir(description)
                                 if "vertex" in x.lower() or "position" in x.lower()]
for accessor in ("get_vertices", "get_vertex_positions"):
    try:
        report[accessor] = [str(v) for v in list(getattr(description, accessor)())[:8]]
    except Exception as exc:
        report[accessor + "_error"] = repr(exc)
try:
    report["first_positions"] = [str(description.get_vertex_position(unreal.VertexID(i)))
                                  for i in range(min(8, description.get_vertex_count()))]
except Exception as exc:
    report["first_positions_error"] = repr(exc)
(root / "Pipeline/Unreal/first_pcg_mesh_vertices.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8")
print("M80_MESH_VERTEX_INSPECTION", report)
