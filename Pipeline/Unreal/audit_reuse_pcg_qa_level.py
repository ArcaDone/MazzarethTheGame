"""Read-only check that the isolated PCG map has generated four pilots."""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
MAP = "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_PCG_QA"
LOTS = ("1249069204", "1249068307", "1249069200", "1249069228")
world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
if not world:
    raise RuntimeError("Could not load PCG QA map")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
pcg = []
instances = []
for actor in actors:
    component = actor.get_component_by_class(unreal.PCGComponent)
    if component:
        graph = component.get_editor_property("graph_instance")
        pcg.append({"label": actor.get_actor_label(), "graph": str(graph)})
    for item in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        count = item.get_instance_count()
        if count:
            mesh = item.get_editor_property("static_mesh")
            instances.append({"actor": actor.get_actor_label(),
                              "mesh": mesh.get_path_name() if mesh else None,
                              "count": count})
out = {"map": MAP, "pcg_volumes": pcg, "instanced_mesh_components": instances,
       "total_instances": sum(row["count"] for row in instances),
       "actor_count": len(actors)}
out["data_assets"] = []
for lot in LOTS:
    asset = unreal.EditorAssetLibrary.load_asset(
        "/Game/Mazzarino80/ReuseKit/PCG/PCGDA_ReuseKit_" + lot)
    if asset is None:
        raise RuntimeError("Missing pilot point asset " + lot)
    stages = []
    for tagged in asset.get_editor_property("data").tagged_data:
        metadata = tagged.data.mutable_metadata()
        point = tagged.data.get_point(0)
        stages.append({"stage": next(iter(tagged.tags)),
                       "mesh": point.get_soft_object_path_attribute(metadata, "Mesh").export_text()})
    out["data_assets"].append({"lot": lot, "stages": stages})
(ROOT / "Pipeline/Unreal/reuse_pcg_qa_audit.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("M80_REUSE_PCG_AUDIT", len(pcg), out["total_instances"])
