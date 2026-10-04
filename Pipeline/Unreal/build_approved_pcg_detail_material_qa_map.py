"""Duplicate the approved map and test four candidate PCG graphs in the copy."""
from hashlib import sha256
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "/Game/Levels/Mazzarino80_CaseStoriche_Campione"
DEST = "/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1/L_CaseStoriche_DetailQA"
BASE = "/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1"
OUT = ROOT / "Pipeline/Unreal/approved_pcg_detail_material_qa_map_result.json"
SOURCE_FILE = ROOT / "Content/Levels/Mazzarino80_CaseStoriche_Campione.umap"
PILOTS = ("1249069204", "1249068307", "1249069200", "1249069228")

before = sha256(SOURCE_FILE.read_bytes()).hexdigest()
if not unreal.EditorAssetLibrary.does_asset_exist(DEST):
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST):
        raise RuntimeError("Could not duplicate sample map")
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(DEST):
    raise RuntimeError("Could not load QA map")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_name() != "L_CaseStoriche_DetailQA":
    raise RuntimeError("Unexpected open map: " + world.get_name())
actors = {a.get_actor_label(): a for a in
          unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
result = {"source": SOURCE, "source_sha256_before": before,
          "qa_map": DEST, "pilot_lots": {}, "errors": []}
for lot in PILOTS:
    actor = actors.get("BP_ProceduralBuilding_" + lot)
    graph = unreal.EditorAssetLibrary.load_asset(BASE + "/PCG_Building_" + lot)
    if actor is None or not isinstance(graph, unreal.PCGGraph):
        result["errors"].append(lot + ": actor or candidate graph missing")
        continue
    component = actor.get_component_by_class(unreal.PCGComponent)
    if component is None:
        result["errors"].append(lot + ": no PCG component")
        continue
    component.cleanup(True)
    component.set_graph(graph)
    component.set_editor_property("is_component_partitioned", False)
    component.generate(True)
    result["pilot_lots"][lot] = {"actor": actor.get_actor_label(),
                                 "graph": graph.get_path_name(),
                                 "generated": bool(component.get_editor_property("generated"))}
if result["errors"]:
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    raise RuntimeError("QA map has missing pilot actors/graphs")
if not levels.save_current_level():
    raise RuntimeError("Could not save separate QA map")
after = sha256(SOURCE_FILE.read_bytes()).hexdigest()
result["source_sha256_after"] = after
result["source_unchanged"] = before == after
if not result["source_unchanged"]:
    raise RuntimeError("Source map changed unexpectedly")
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_APPROVED_DETAIL_QA_MAP", len(result["pilot_lots"]), DEST)
