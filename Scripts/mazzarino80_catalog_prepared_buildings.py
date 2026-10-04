import unreal,json
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
LEVEL='/Game/Levels/Mazzarino80_Catalogo'
if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(LEVEL)
    assert len(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())<3,'Catalogue exists: preserve user work.'
else:assert unreal.EditorLevelLibrary.new_level(LEVEL)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
inventory=json.loads((ROOT/'Research/Mazzarino80/prepared_buildings_inventory.json').read_text())
rows=[]
for i,item in enumerate(sorted(inventory,key=lambda x:x['label'])):
    rot=item['transform']['rotation'];cls=unreal.load_class(None,item['class']);assert cls
    a=actors.spawn_actor_from_class(cls,unreal.Vector((i%5)*40000,(i//5)*40000,0),unreal.Rotator(pitch=rot[0],yaw=rot[1],roll=rot[2]))
    a.set_actor_label(item['label']);a.set_folder_path('Strutture_personali/'+item['label'])
    center,extent=a.get_actor_bounds(False);a.set_actor_location(a.get_actor_location()+unreal.Vector(0,0,extent.z-center.z+50),False,False)
    a.tags=['M80_PreparedCatalogue','Da_posizionare_in_citta' if item['label'] not in ('ComuneCompleto','Matrice','A_SanDomenico') else 'Gia_posato_in_Panoramica']
    label=actors.spawn_actor_from_class(unreal.TextRenderActor,unreal.Vector((i%5)*40000,(i//5)*40000-10000,3000))
    c=label.get_component_by_class(unreal.TextRenderComponent);c.set_text(item['label']);c.set_world_size(200);label.set_folder_path('Etichette')
    rows.append({'label':item['label'],'class':item['class'],'position':list(a.get_actor_location().to_tuple())})
cube=unreal.load_asset('/Engine/BasicShapes/Cube')
ground=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(80000,20000,-100));ground.static_mesh_component.set_static_mesh(cube);ground.set_actor_scale3d(unreal.Vector(2100,950,1));ground.set_actor_label('Piano_catalogo')
sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,50000),unreal.Rotator(pitch=-50,yaw=-30));sun.set_actor_label('Sole')
sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,0));sky.set_actor_label('Luce_ambiente')
assert unreal.EditorLevelLibrary.save_current_level()
(ROOT/'Research/Mazzarino80/prepared_buildings_catalog.json').write_text(json.dumps({'level':LEVEL,'structures':rows},indent=2))
unreal.log('M80_PREPARED_CATALOG_DONE '+str(len(rows)))
