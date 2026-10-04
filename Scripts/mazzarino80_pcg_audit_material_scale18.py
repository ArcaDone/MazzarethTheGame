"""Audit live PCG materials and module sizes against the 18 saved records."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
manifest=json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))['houses']
catalog=unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
records={d.get_editor_property('building_id'):d for d in catalog.get_editor_property('buildings')}
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
report={'houses':{},'errors':{},'warnings':{},'summary':{}}
cache={}
default_markers=('DefaultMaterial','WorldGridMaterial','M_Default','EngineMaterials')

def get_asset(path):
    if path not in cache:
        cache[path]=unreal.load_asset(path) if path else None
    return cache[path]

def display(path):
    return path.rsplit('/',1)[-1].split('.')[0] if path else ''

for lot,house in manifest.items():
    errors=[]
    warnings=[]
    record=records.get(lot)
    actor=actors.get('BP_ProceduralBuilding_'+lot)
    if record is None or actor is None:
        report['errors'][lot]=['Missing record or actor']
        continue
    expected=Counter()
    roles=defaultdict(list)
    for stage,points in house['stage_points'].items():
        for point in points:
            mesh_path=point['mesh']
            material_path=point['material']
            expected[(mesh_path,material_path)]+=1
            mesh=get_asset(mesh_path)
            material=get_asset(material_path)
            if mesh is None:
                errors.append('Missing mesh '+mesh_path)
                continue
            if material is None:
                errors.append('Missing material '+material_path)
                continue
            if any(token in material_path for token in default_markers):
                errors.append('Fallback material '+material_path)
            bounds=mesh.get_bounds()
            scale=point['scale']
            dimensions=[round(2*getattr(bounds.box_extent,axis)*abs(scale[i]),1)
                        for i,axis in enumerate(('x','y','z'))]
            roles[point['role']].append(dimensions)
            if (min(dimensions)<.05 and point['role']!='surface_section_3') or max(dimensions)>20000:
                warnings.append('Extreme '+point['role']+' '+str(dimensions))
    actual=Counter()
    material_paths=[]
    for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
        count=comp.get_instance_count()
        if not count:
            continue
        mesh=comp.get_editor_property('static_mesh')
        material=comp.get_material(0)
        mesh_path=mesh.get_path_name() if mesh else ''
        material_path=material.get_path_name() if material else ''
        actual[(mesh_path,material_path)]+=count
        material_paths.append(material_path)
        if not material or any(token in material_path for token in default_markers):
            errors.append('Live fallback/missing material '+mesh_path+' '+material_path)
    mismatch=expected-actual
    extra=actual-expected
    if mismatch or extra:
        errors.append('Mesh/material instance mismatch missing='+str(sum(mismatch.values()))+
                      ' extra='+str(sum(extra.values())))
    for prop in ('facade_material','roof_material'):
        material=record.get_editor_property(prop)
        if not material:
            errors.append('Missing record '+prop)
    if record.get_editor_property('upper_brick_floor') and not record.get_editor_property('upper_brick_material'):
        errors.append('Upper brick enabled without material')
    for name,lo,hi in (('external_bathroom',180,420),('street_cactus',20,450),
                       ('facade_ivy',30,700)):
        for dims in roles.get(name,[]):
            if max(dims)<lo or max(dims)>hi:
                warnings.append(name+' suspicious size '+str(dims))
    for role,dims_list in roles.items():
        if role.startswith('courtyard_gate_bar'):
            for dims in dims_list:
                if abs(dims[2]-244)>5:
                    errors.append('Gate bar not 244cm '+str(dims))
    role_summary={name:{'count':len(values),
                        'smallest_cm':[min(v[i] for v in values) for i in range(3)],
                        'largest_cm':[max(v[i] for v in values) for i in range(3)]}
                  for name,values in roles.items()}
    row={'family':str(record.get_editor_property('family')),
         'floors':record.get_editor_property('primary_floors'),
         'floor_height_cm':record.get_editor_property('floor_height_cm'),
         'record_facade':record.get_editor_property('facade_material').get_path_name(),
         'expected_instances':sum(expected.values()),'actual_instances':sum(actual.values()),
         'materials':sorted(set(material_paths)),'role_sizes':role_summary,
         'errors':sorted(set(errors)),'warnings':sorted(set(warnings))}
    report['houses'][lot]=row
    if errors:
        report['errors'][lot]=row['errors']
    if warnings:
        report['warnings'][lot]=row['warnings']
report['summary']={'houses':len(report['houses']),
                   'instance_count':sum(h['actual_instances'] for h in report['houses'].values()),
                   'material_errors':len(report['errors']),
                   'scale_warnings':len(report['warnings']),
                   'unique_materials':len({m for h in report['houses'].values() for m in h['materials']})}
out=root/'Saved/Mazzarino80/PCG/audit_material_scale18.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_MATERIAL_SCALE18 '+str(report['summary']))
