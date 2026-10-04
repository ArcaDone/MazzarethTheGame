"""Check all approved houses and generated instances in the live Play world."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
expected = json.loads((root / 'Saved/Mazzarino80/PCG/verify_18_validation.json').read_text(
    encoding='utf-8'))['houses']
worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
if len(worlds) != 1:
    raise RuntimeError(f'Expected one Play world, got {len(worlds)}')
actual = {}
for actor in unreal.GameplayStatics.get_all_actors_of_class(worlds[0], unreal.Actor):
    label = actor.get_actor_label()
    if not label.startswith('BP_ProceduralBuilding_'):
        continue
    lot = label.removeprefix('BP_ProceduralBuilding_')
    meshes = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    actual[lot] = {'hidden': actor.get_editor_property('hidden'),
                   'instances': sum(c.get_instance_count() for c in meshes),
                   'components': len(meshes),
                   'visible_components': sum(c.is_visible() and not c.get_editor_property('hidden_in_game')
                                             for c in meshes)}
errors = {}
for lot, data in expected.items():
    runtime = actual.get(lot)
    if not runtime:
        errors[lot] = 'Missing runtime actor'
    elif runtime['hidden'] or runtime['instances'] != data['actual'] or runtime['visible_components'] != runtime['components']:
        errors[lot] = runtime
extra = sorted(set(actual) - set(expected))
report = {'world': worlds[0].get_name(), 'houses': actual,
          'count': len(actual), 'instances': sum(v['instances'] for v in actual.values()),
          'errors': errors, 'extra': extra}
(root / 'Saved/Mazzarino80/PCG/verify_pie_weathered.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
