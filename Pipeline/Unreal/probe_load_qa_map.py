"""Check whether UE's Python commandlet can safely edit the empty QA map."""
from pathlib import Path
import json
import unreal

level = "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_QA"
world = unreal.EditorLoadingAndSavingUtils.load_map(level)
root = Path(__file__).resolve().parents[2]
result = {"world": str(world), "world_name": world.get_name() if world else None,
          "save_methods": [name for name in dir(unreal.EditorLoadingAndSavingUtils)
                           if "save" in name.lower()],
          "actor_subsystem": bool(unreal.get_editor_subsystem(unreal.EditorActorSubsystem))}
(root / "Pipeline/Unreal/probe_load_qa_map.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print("M80_QA_MAP_LOAD", result["world_name"])
