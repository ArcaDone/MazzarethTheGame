"""Audit persisted PCG replacement and the edited service splines in the open map."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
baseline = json.loads((root / 'Saved/Mazzarino80/PCG/baseline_18.json').read_text(encoding='utf-8'))
actors = {a.get_actor_label(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
report = {'map': str(unreal.EditorLevelLibrary.get_editor_world()), 'houses': {}, 'errors': []}
for house in baseline['houses']:
    lot = house['id']
    old = actors.get(house['label'])
    new = actors.get('BP_ProceduralBuilding_' + lot)
    if not old or not new:
        report['errors'].append(lot + ': actor missing')
        continue
    footprint = old.get_editor_property('footprint')
    services = [s for s in old.get_components_by_class(unreal.SplineComponent) if s != footprint]
    actual_services = {}
    for service in services:
        actual_services[service.get_name()] = [[round(getattr(v, axis.lower()), 3) for axis in 'XYZ']
            for v in (service.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
                      for i in range(service.get_number_of_spline_points()))]
    expected_services = {s['name']: s['points_world_cm'] for s in house['service_splines']}
    service_errors = []
    for name, expected in expected_services.items():
        actual = actual_services.get(name)
        if actual is None or len(actual) != len(expected):
            service_errors.append(name + ': missing or count changed')
        elif any(abs(a - b) > 0.2 for av, ev in zip(actual, expected) for a, b in zip(av, ev)):
            service_errors.append(name + ': points moved')
    if set(actual_services) != set(expected_services):
        service_errors.append('service names changed')
    originals = old.get_components_by_class(unreal.InstancedStaticMeshComponent)
    surface = old.get_editor_property('surface')
    pcg = new.get_component_by_class(unreal.PCGComponent)
    instances = sum(c.get_instance_count() for c in new.get_components_by_class(unreal.InstancedStaticMeshComponent))
    item = {
        'pcg_visual_replacement': old.get_editor_property('pcg_visual_replacement'),
        'old_surface_visible': surface.is_visible(),
        'old_modules_visible': sum(c.is_visible() for c in originals),
        'old_surface_collision': str(surface.get_collision_enabled()),
        'services_expected': len(expected_services),
        'services_actual': len(actual_services),
        'service_errors': service_errors,
        'pcg_instances': instances,
        'pcg_generated': pcg.generated,
        'pcg_partitioned': pcg.is_component_partitioned,
    }
    report['houses'][lot] = item
    if not item['pcg_visual_replacement'] or item['old_surface_visible'] or item['old_modules_visible'] or service_errors or not instances:
        report['errors'].append(lot + ': ' + str(item))
(root / 'Saved/Mazzarino80/PCG/verify_context.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('M80_PCG_CONTEXT ' + str(len(report['houses'])) + ' houses, ' + str(len(report['errors'])) + ' errors')
