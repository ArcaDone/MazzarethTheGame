"""Preview new materials on generated instances in the copied QA map only.

The headless PCG commandlet schedules regeneration but exits before its async
spawner finishes. This bridge lets the user inspect the proposed surfaces now;
the candidate data/graphs remain the source for eventual live PCG regeneration.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Research/Mazzarino80/PCG/BakedSource/approved_modules.json"
CANDIDATE = ROOT / "Research/Mazzarino80/PCG/Candidates/approved_detail_material_v1.json"
SOURCE_MAP = ROOT / "Content/Levels/Mazzarino80_CaseStoriche_Campione.umap"
MAP = "/Game/Mazzarino80/PCG/DetailMaterialCandidate_v1/L_CaseStoriche_DetailQA"
OUT = ROOT / "Pipeline/Unreal/approved_pcg_surface_preview_result.json"
LOTS = ("1249069204", "1249068307", "1249069200", "1249069228")

old = json.loads(SOURCE.read_text(encoding="utf-8"))["houses"]
new = json.loads(CANDIDATE.read_text(encoding="utf-8"))["houses"]
mapping = {}
for lot in LOTS:
    for stage in old[lot]["stage_points"]:
        for a, b in zip(old[lot]["stage_points"][stage],
                        new[lot]["stage_points"][stage]):
            if a["material"] != b["material"]:
                prior = mapping.setdefault(a["material"], b["material"])
                if prior != b["material"]:
                    raise RuntimeError("Ambiguous material mapping: " + a["material"])

before = sha256(SOURCE_MAP.read_bytes()).hexdigest()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not levels.load_level(MAP):
    raise RuntimeError("Could not load copied QA map")
actors = {a.get_actor_label(): a for a in
          unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
loaded = {}
for old_path, new_path in mapping.items():
    asset = unreal.EditorAssetLibrary.load_asset(new_path)
    if not isinstance(asset, unreal.MaterialInterface):
        raise RuntimeError("Missing candidate material " + new_path)
    loaded[old_path] = asset
counts = Counter()
for lot in LOTS:
    actor = actors.get("BP_ProceduralBuilding_" + lot)
    if actor is None:
        raise RuntimeError("Missing pilot " + lot)
    for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        old_material = comp.get_material(0)
        old_path = old_material.get_path_name() if old_material else ""
        if old_path in loaded:
            comp.set_material(0, loaded[old_path])
            counts[lot] += comp.get_instance_count()
if not levels.save_current_level():
    raise RuntimeError("Could not save copied QA preview")
after = sha256(SOURCE_MAP.read_bytes()).hexdigest()
result = {"qa_map": MAP, "source_map_unchanged": before == after,
          "instances_recolored_by_lot": dict(counts),
          "candidate_materials_loaded": len(loaded),
          "note": "Copied-instance preview. Live PCG graph needs an editor-tick regeneration check."}
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
if before != after:
    raise RuntimeError("Source map changed unexpectedly")
print("M80_SURFACE_PREVIEW", sum(counts.values()))
