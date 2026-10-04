"""Count legacy procedural mesh and module instances to size an exact PCG bake."""
import json
from pathlib import Path
import unreal

rows=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if not isinstance(a, unreal.MazzarinoHistoricBuilding):
        continue
    surface=a.get_editor_property('surface')
    rows.append({'lot':a.get_editor_property('lot_id'),'sections':surface.get_num_sections(),
                 'modules':{c.get_name():c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)}})
Path(unreal.Paths.project_dir(),'Saved/Mazzarino80/PCG/original_module_counts.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
