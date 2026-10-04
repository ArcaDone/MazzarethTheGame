"""Read-only check of the four irregular-lot candidate QA map."""
from pathlib import Path
import json
import os

import unreal

ROOT = Path(__file__).resolve().parents[2]
ALL_LOTS = os.environ.get("M80_REUSE_QA_ALL_LOTS") == "1"
TARGET = ("/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_18Lots_QA" if ALL_LOTS
          else "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_4Lots_QA")
PILOTS = (set(json.loads((ROOT / "Pipeline/Unreal/visual_style_map.json").read_text(encoding="utf-8")))
          if ALL_LOTS else {"1249069204", "1249068307", "1249069200", "1249069228"})
world = unreal.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:
    raise RuntimeError("Could not load candidate QA map")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
volumes = []
for actor in actors:
    if isinstance(actor, unreal.PCGVolume):
        volumes.append(actor.get_actor_label())
candidate = {label.split()[-1] for label in volumes if label.startswith("Reuse Candidate ")}
original = {label.split("_")[-1] for label in volumes
            if label.startswith("BP_ProceduralBuilding_")}
other_volumes = [label for label in volumes if not label.startswith("Reuse Candidate ")
                 and not label.startswith("BP_ProceduralBuilding_")]
issues = []
if candidate != PILOTS:
    issues.append("Candidate volume IDs differ from the four pilots")
if len(original) != 18 - len(PILOTS) or original & PILOTS:
    issues.append("The non-candidate lots were not preserved")
out = {"map": TARGET, "candidate_lots": sorted(candidate),
       "unchanged_lots": sorted(original), "volume_count": len(volumes),
       "other_volumes": other_volumes,
       "issues": issues}
(ROOT / ("Pipeline/Unreal/reuse_lots_all_map_audit.json" if ALL_LOTS
         else "Pipeline/Unreal/reuse_lots_pilot_map_audit.json")).write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("M80_REUSE_4_LOTS_AUDIT", len(candidate), len(original), len(issues))
if issues:
    raise RuntimeError("Pilot map audit failed")
