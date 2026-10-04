import json
from pathlib import Path
import unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/Comune')
unreal.log('M80_WP_LIB '+str([x for x in dir(unreal.WorldPartitionBlueprintLibrary) if not x.startswith('_')]))
try:
    descs=unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    unreal.log('M80_DESCS '+str(descs))
    unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in descs])
except Exception as exc: unreal.log_warning('M80_WP_LOAD '+str(exc))
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
result=[]
for actor in editor.get_all_level_actors():
    splines=actor.get_components_by_class(unreal.SplineComponent)
    if not splines: continue
    item={'label':actor.get_actor_label(),'class':actor.get_class().get_path_name(),
          'location':str(actor.get_actor_location()),'splines':[],'meshes':[]}
    for spline in splines:
        item['splines'].append({'name':spline.get_name(),'points':spline.get_number_of_spline_points(),
                               'length_cm':spline.get_spline_length(),
                               'positions':[str(spline.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD)) for i in range(spline.get_number_of_spline_points())]})
    meshes=actor.get_components_by_class(unreal.StaticMeshComponent)
    seen=set()
    for mesh in meshes:
        key=(mesh.static_mesh.get_path_name() if mesh.static_mesh else '',tuple(mesh.get_material(i).get_path_name() if mesh.get_material(i) else '' for i in range(mesh.get_num_materials())))
        if key in seen: continue
        seen.add(key)
        item['meshes'].append({'mesh':key[0],'materials':key[1],'component_class':mesh.get_class().get_name(),'scale':str(mesh.get_editor_property('relative_scale3d')),'start_scale':str(mesh.get_start_scale()) if isinstance(mesh,unreal.SplineMeshComponent) else ''})
    item['available_properties']=[x for x in dir(actor) if not x.startswith('_') and any(y in x.lower() for y in ('mesh','scale','width','construction','spline','material'))]
    result.append(item)
(ROOT/'Research/Mazzarino80/comune_splines_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
unreal.log('M80_COMUNE_AUDIT_DONE '+str(len(result)))
