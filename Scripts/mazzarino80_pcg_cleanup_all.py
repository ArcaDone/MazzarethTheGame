"""Clear old PCG instances before regenerating from approved modules."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
rows=[]
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if actor.get_actor_label().startswith('BP_ProceduralBuilding_'):
        pcg=actor.get_component_by_class(unreal.PCGComponent)
        pcg.cleanup(True)
        rows.append(actor.get_actor_label())
(root/'Saved/Mazzarino80/PCG/cleanup_all.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
