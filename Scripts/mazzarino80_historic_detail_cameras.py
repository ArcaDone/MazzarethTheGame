"""Saved close-up cameras framing actual new tile and balcony geometry."""
import unreal,math
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=editor.get_all_level_actors()
houses=[a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)]
def rotate(v,q):
 # Quaternion rotation without scale or a dependency on editor math wrappers.
 u=unreal.Vector(q.x,q.y,q.z)
 cross=lambda a,b:unreal.Vector(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x)
 t=cross(u,v)*2
 return v+t*q.w+cross(u,t)
def camera(name,location,target,fov):
 cam=next((a for a in actors if a.get_actor_label()==name),None)
 if not cam:cam=editor.spawn_actor_from_class(unreal.CameraActor,location,unreal.Rotator())
 cam.set_actor_label(name);cam.set_folder_path('Mazzarino80/Campione_case_storiche/Verifica')
 cam.set_actor_location(location,False,False);cam.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location,target),False)
 cam.camera_component.set_field_of_view(fov);cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
 return cam
roof_house=next(a for a in houses if a.get_editor_property('lot_id')=='1249069275')
tiles=roof_house.get_editor_property('roof_tiles')
points=[tiles.get_instance_transform(i,True).translation for i in range(tiles.get_instance_count())]
center=sum(points,unreal.Vector())/len(points)
# Stay above surrounding three-storey walls instead of looking through one.
camera('M80_Dettaglio_Coppi',center+unreal.Vector(-450,-550,1550),center,35)
balc_house=next(a for a in houses if a.get_editor_property('balcony_modules').get_instance_count()>0)
balcs=balc_house.get_editor_property('balcony_modules');t=balcs.get_instance_transform(0,True)
b=balcs.get_editor_property('static_mesh').get_bounds()
center=t.translation+rotate(b.origin*t.scale3d,t.rotation)
out=rotate(unreal.Vector(0,1,0),t.rotation);along=rotate(unreal.Vector(1,0,0),t.rotation)
camera('M80_Dettaglio_Balcone',center+out*490+along*160+unreal.Vector(0,0,45),center,57)
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
for key in level.get_viewport_config_keys():level.eject_pilot_level_actor(key)
level.editor_invalidate_viewports()
unreal.log('M80_DETAIL_CAMERAS_CREATED')
