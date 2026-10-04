import json
from pathlib import Path
import unreal

actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
rows=[]
for actor in actors:
    if isinstance(actor,unreal.MazzarinoHistoricBuilding):
        lot=actor.get_editor_property('lot_id')
        road=actor.get_editor_property('entrance_road')
        if lot and road:
            rows.append({'lot':lot,'road':road.get_actor_label(),
                         'spline_length_cm':road.get_editor_property('spline').get_spline_length()})
out=Path(unreal.Paths.project_saved_dir())/'Mazzarino80/PCG/sample_roads.json'
out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
unreal.log('M80_SAMPLE_ROADS '+str(out))
