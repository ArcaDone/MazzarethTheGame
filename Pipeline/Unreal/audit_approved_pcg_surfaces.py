"""Read-only inventory of materials actually referenced by approved PCG points."""
from collections import Counter, defaultdict
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Research/Mazzarino80/PCG/BakedSource/approved_modules.json"
OUT = ROOT / "Pipeline/Unreal/approved_pcg_surface_audit.json"
data = json.loads(SOURCE.read_text(encoding="utf-8"))["houses"]
uses = Counter()
roles = defaultdict(Counter)
for house in data.values():
    for points in house["stage_points"].values():
        for point in points:
            path = point.get("material", "")
            uses[path] += 1
            roles[path][point.get("role", "")] += 1


def params(asset, property_name):
    try:
        values = asset.get_editor_property(property_name)
    except Exception:
        return []
    rows = []
    for value in values:
        row = {}
        for field in ("parameter_info", "parameter_name", "parameter_value"):
            try:
                item = value.get_editor_property(field)
                row[field] = item.get_path_name() if hasattr(item, "get_path_name") else str(item)
            except Exception:
                pass
        rows.append(row)
    return rows


materials = []
for path, count in uses.most_common():
    asset = unreal.EditorAssetLibrary.load_asset(path)
    row = {"path": path, "point_count": count,
           "roles": dict(roles[path]),
           "class": asset.get_class().get_name() if asset else None}
    if asset is None:
        row["missing"] = True
    elif isinstance(asset, unreal.MaterialInstanceConstant):
        parent = asset.get_editor_property("parent")
        row["parent"] = parent.get_path_name() if parent else None
        for name in ("scalar_parameter_values", "vector_parameter_values",
                     "texture_parameter_values"):
            row[name] = params(asset, name)
    elif isinstance(asset, unreal.Material):
        try:
            row["expression_classes"] = [expr.get_class().get_name()
                                         for expr in asset.get_editor_property("expressions")]
        except Exception:
            pass
    materials.append(row)

report = {"source": str(SOURCE), "houses": len(data), "point_count": sum(uses.values()),
          "unique_material_paths": len(uses), "materials": materials}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_APPROVED_PCG_SURFACES", len(data), len(uses), sum(uses.values()))
