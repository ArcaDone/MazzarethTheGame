import json
from pathlib import Path
import unreal

actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
roads=[]
for actor in actors:
    if isinstance(actor,unreal.MazzarinoRoadSpline):
        material=actor.get_editor_property('road_material')
        roads.append({'name':actor.get_actor_label(),'material':material.get_path_name() if material else '',
                      'width':actor.get_editor_property('width_meters')})
out=Path(unreal.Paths.project_saved_dir())/'Mazzarino80/PCG/road_materials.json'
out.write_text(json.dumps(roads,indent=2),encoding='utf-8')
unreal.log('M80_ROADS '+str(out))
