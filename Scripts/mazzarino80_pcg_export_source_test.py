"""Test exporting a single approved legacy house surface and instance transform."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
actor=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
           if isinstance(a,unreal.MazzarinoHistoricBuilding))
out=root/'Research/Mazzarino80/PCG/BakedSourceTest'
out.mkdir(parents=True,exist_ok=True)
paths=actor.export_pcg_surface_sections(str(out))
module=next(c for c in actor.get_components_by_class(unreal.InstancedStaticMeshComponent) if c.get_instance_count())
transform=module.get_instance_transform(0,world_space=True)
report={'lot':actor.get_editor_property('lot_id'),'paths':[str(p) for p in paths],'module':module.get_name(),
        'transform':str(transform),'translation':str(transform.translation),
        'rotation':str(transform.rotation),'scale3d':str(transform.scale3d),
        'transform_methods':[x for x in dir(transform) if 'rotat' in x or 'trans' in x]}
(root/'Saved/Mazzarino80/PCG/export_source_test.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
