"""Generate each approved house after the previous cleanup has completed."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
rows=[]
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if actor.get_actor_label().startswith('BP_ProceduralBuilding_'):
        pcg=actor.get_component_by_class(unreal.PCGComponent)
        pcg.set_editor_property('is_component_partitioned',False)
        pcg.generate(True)
        rows.append(actor.get_actor_label())
(root/'Saved/Mazzarino80/PCG/generate_all.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
