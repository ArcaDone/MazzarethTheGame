"""Find the original house components that hold modified service splines."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
baseline=json.loads((root/'Saved/Mazzarino80/PCG/baseline_18.json').read_text(encoding='utf-8'))
labels={h['label'] for h in baseline['houses']}
report={}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    label=actor.get_actor_label()
    if label not in labels:
        continue
    report[label]=[]
    for comp in actor.get_components_by_class(unreal.ActorComponent):
        row={'name':comp.get_name(),'class':comp.get_class().get_name()}
        if isinstance(comp,unreal.SceneComponent):
            row['visible']=comp.is_visible()
        if isinstance(comp,unreal.SplineComponent):
            row['points']=comp.get_number_of_spline_points()
        if isinstance(comp,unreal.InstancedStaticMeshComponent):
            row['instances']=comp.get_instance_count()
        report[label].append(row)
(root/'Saved/Mazzarino80/PCG/audit_original_components.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
