"""Audit the generated meshes for all 18 PCG actors after generation has settled."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
specs = json.loads((root / 'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))['houses']
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report = {'houses': {}, 'missing': [], 'mismatched': [], 'total_expected': 0, 'total_actual': 0,
          'total_roof_tiles': 0, 'total_components': 0}
by_label = {a.get_actor_label(): a for a in actors}
report['extra'] = sorted(label.removeprefix('BP_ProceduralBuilding_') for label in by_label
                         if label.startswith('BP_ProceduralBuilding_') and
                         label.removeprefix('BP_ProceduralBuilding_') not in specs)
for lot, house in specs.items():
    label = 'BP_ProceduralBuilding_' + lot
    actor = by_label.get(label)
    if actor is None:
        report['missing'].append(lot)
        continue
    components = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    actual = sum(c.get_instance_count() for c in components)
    expected = sum(len(points) for points in house['stage_points'].values())
    materials = sorted({str(c.get_material(0).get_path_name()) for c in components if c.get_material(0)})
    item = {'expected': expected, 'actual': actual, 'ism_components': len(components), 'materials': materials,
            'stages': {stage: len(points) for stage, points in house['stage_points'].items()}}
    report['houses'][lot] = item
    report['total_expected'] += expected
    report['total_actual'] += actual
    report['total_components'] += len(components)
    roof_tiles = sum(1 for point in house['stage_points']['Roofs']
                     if str(point['role']).strip().startswith('Coppi_'))
    item['roof_tile_instances'] = roof_tiles
    report['total_roof_tiles'] += roof_tiles
    if expected != actual:
        report['mismatched'].append(lot)
report['saved'] = unreal.EditorLevelLibrary.save_current_level()
(root / 'Saved/Mazzarino80/PCG/verify_18_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('M80_PCG_VERIFY_18 ' + str(report['total_actual']) + '/' + str(report['total_expected']))
