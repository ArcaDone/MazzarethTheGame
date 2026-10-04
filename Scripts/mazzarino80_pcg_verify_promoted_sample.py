"""Reopen the saved main sample and verify its 18 generated houses."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
target = '/Game/Levels/Mazzarino80_CaseStoriche_Campione'
loaded = bool(unreal.EditorLevelLibrary.load_level(target))
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
houses = [a for a in actors if a.get_actor_label().startswith('BP_ProceduralBuilding_')]
report = {
    'target': target,
    'loaded': loaded,
    'actor_count': len(actors),
    'house_count': len(houses),
    'house_labels': sorted(a.get_actor_label() for a in houses),
    'ism_instances': sum(c.get_instance_count() for a in houses for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent)),
    'spline_actor_count': sum(1 for a in actors if a.get_components_by_class(unreal.SplineComponent)),
    'target_file_bytes': (root/'Content/Levels/Mazzarino80_CaseStoriche_Campione.umap').stat().st_size,
}
report['passed'] = loaded and report['house_count'] == 18 and report['ism_instances'] == 37109 and report['spline_actor_count'] > 0
(root/'Saved/Mazzarino80/PCG/verify_promoted_sample.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('M80_VERIFY_PROMOTED ' + str(report))
if not report['passed']:
    raise RuntimeError('The reopened sample failed verification')
