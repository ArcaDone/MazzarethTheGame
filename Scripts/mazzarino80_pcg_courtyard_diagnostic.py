"""Inspect the pilot courtyard meshes and source geometry at world scale."""
import json
from pathlib import Path
import unreal

lot='1249069228'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
house=next(a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)
           and a.get_editor_property('lot_id')==lot)
target=next(a for a in actors if a.get_actor_label()=='BP_ProceduralBuilding_'+lot)
rows=[]
for comp in target.get_components_by_class(unreal.InstancedStaticMeshComponent):
    mesh=comp.get_editor_property('static_mesh')
    if not mesh or not any(key in mesh.get_path_name() for key in
                           ('SM_metal_gate_01','Corridor_A_Box02_Ex','/Cube')):
        continue
    bounds=mesh.get_bounds()
    for i in range(comp.get_instance_count()):
        t=comp.get_instance_transform(i,world_space=True)
        p=t.translation
        rows.append({'mesh':mesh.get_path_name(),'location':[p.x,p.y,p.z],
                     'rotation':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
                     'scale':[t.scale3d.x,t.scale3d.y,t.scale3d.z],
                     'mesh_origin_z':bounds.origin.z,
                     'mesh_bottom_z':bounds.origin.z-bounds.box_extent.z,
                     'mesh_size':[bounds.box_extent.x*2,bounds.box_extent.y*2,bounds.box_extent.z*2]})
path=Path(unreal.Paths.project_dir())/'Saved/Mazzarino80/PCG/courtyard_diagnostic.json'
path.write_text(json.dumps(rows,indent=2),encoding='utf-8')
unreal.log('M80_COURTYARD_DIAGNOSTIC '+str(path))
