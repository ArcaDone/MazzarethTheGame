"""Audit source houses and protected surroundings in the contextual copy."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
baseline=json.loads((root/'Saved/Mazzarino80/PCG/baseline_18.json').read_text(encoding='utf-8'))
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
by_label={a.get_actor_label():a for a in actors}
original={h['id']:str(by_label.get(h['label'])) for h in baseline['houses']}
report={'world':str(unreal.EditorLevelLibrary.get_editor_world()),'actors':len(actors),
        'original_houses':original,
        'missing_original':[lot for lot,val in original.items() if val=='None'],
        'pcg_houses':[a.get_actor_label() for a in actors if a.get_actor_label().startswith('BP_ProceduralBuilding_')],
        'road_splines':sum('MazzarinoRoadSpline' in a.get_class().get_name() for a in actors),
        'service_splines':sum('Service' in a.get_class().get_name() or 'Impiant' in a.get_actor_label() for a in actors)}
(root/'Saved/Mazzarino80/PCG/audit_context.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
