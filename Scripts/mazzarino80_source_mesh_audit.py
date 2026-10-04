import json
from pathlib import Path
import unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
data={}
for name in ['Lavica_curved','LowPoly']:
    mesh=unreal.load_asset('/Game/Mazzarino80/RoadSource/Migrated/'+name)
    bounds=mesh.get_bounding_box()
    data[name]={'min':[bounds.min.x,bounds.min.y,bounds.min.z],'max':[bounds.max.x,bounds.max.y,bounds.max.z]}
bp=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Mazzarino80/RoadSource/Esercitazioni/Spline_StradaLavica')
actor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(bp,unreal.Vector())
meshes=actor.get_components_by_class(unreal.SplineMeshComponent)
data['blueprint']={'mesh_size':str(actor.get_editor_property('MeshSize')),'components':len(meshes),'axis':str(meshes[0].get_forward_axis()) if meshes else '', 'collision':str(meshes[0].get_collision_enabled()) if meshes else ''}
(ROOT/'Research/Mazzarino80/comune_source_mesh_audit.json').write_text(json.dumps(data,indent=2))
unreal.log('M80_MESH_AUDIT '+json.dumps(data))
