"""Read-only validation of the four pilots in the separate QA map."""
from collections import Counter
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
MAP = "/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1/L_CaseStoriche_DetailQA"
SOURCE = ROOT / "Research/Mazzarino80/PCG/Candidates/approved_detail_material_v1.json"
OUT = ROOT / "Pipeline/Unreal/approved_pcg_detail_material_qa_verification.json"
LOTS = ("1249069204", "1249068307", "1249069200", "1249069228")

world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
if not world or world.get_name() != "L_CaseStoriche_DetailQA":
    raise RuntimeError("Unable to load independent QA map")
houses = json.loads(SOURCE.read_text(encoding="utf-8"))["houses"]
actors = {a.get_actor_label(): a for a in
          unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
report = {"map": MAP, "lots": {}, "errors": []}
for lot in LOTS:
    house = houses[lot]
    actor = actors.get("BP_ProceduralBuilding_" + lot)
    if actor is None:
        report["errors"].append(lot + ": missing actor")
        continue
    pcg = actor.get_component_by_class(unreal.PCGComponent)
    data = unreal.EditorAssetLibrary.load_asset(
        "/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1/PCGDA_Building_" + lot)
    if pcg is None or data is None:
        report["errors"].append(lot + ": missing component or candidate data asset")
        continue
    first_tagged = data.get_editor_property("data").tagged_data[0]
    first_point = first_tagged.data.get_point(0)
    first_metadata = first_tagged.data.mutable_metadata()
    point_material = first_point.get_soft_object_path_attribute(
        first_metadata, "Material").export_text()
    graph_instance = pcg.get_editor_property("graph_instance")
    assigned_graph = graph_instance.get_editor_property("graph") if graph_instance else None
    expected = Counter((p["mesh"], tuple(round(v, 1) for v in p["location_cm"]))
                       for stage in house["stage_points"].values() for p in stage)
    actual = Counter()
    actual_materials = Counter()
    for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        mesh = comp.get_editor_property("static_mesh")
        material = comp.get_material(0)
        material_path = material.get_path_name() if material else ""
        name = mesh.get_path_name() if mesh else ""
        count = comp.get_instance_count()
        actual_materials[material_path] += count
        for index in range(count):
            v = comp.get_instance_transform(index, world_space=True).translation
            actual[(name, (round(v.x, 1), round(v.y, 1), round(v.z, 1)))] += 1
    missing = sum((expected - actual).values())
    extra = sum((actual - expected).values())
    expected_mats = Counter(p["material"] for stage in house["stage_points"].values()
                            for p in stage)
    absent_mats = sorted(set(expected_mats) - set(actual_materials))
    report["lots"][lot] = {"expected_instances": sum(expected.values()),
                           "actual_instances": sum(actual.values()),
                           "missing": missing, "extra": extra,
                           "generated": bool(pcg.get_editor_property("generated")),
                           "pcg_graph_instance": str(pcg.get_editor_property("graph_instance")),
                           "assigned_graph": assigned_graph.get_path_name() if assigned_graph else None,
                           "data_asset_first_material": point_material,
                           "expected_material_paths": len(expected_mats),
                           "actual_material_paths": len(actual_materials),
                           "expected_materials_not_found": absent_mats,
                           "actual_material_counts": dict(actual_materials)}
    if missing or extra or absent_mats or not pcg.get_editor_property("generated"):
        report["errors"].append(lot + ": instance/material mismatch")
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_APPROVED_DETAIL_QA_VERIFY", len(report["lots"]), len(report["errors"]))
