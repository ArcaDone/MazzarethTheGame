"""Switch the sample between saved cameras and gray/material view.
Set MODE in Saved/Mazzarino80/Historic/view_mode.txt before running in editor.
"""
import unreal,json,math
from pathlib import Path
root=Path(unreal.Paths.project_dir());modefile=root/'Saved/Mazzarino80/Historic/view_mode.txt'
mode=modefile.read_text().strip() if modefile.exists() else 'after'
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_name()!='Mazzarino80_CaseStoriche_Campione':assert level.load_level('/Game/Levels/Mazzarino80_CaseStoriche_Campione')
actors=editor.get_all_level_actors()
houses=[a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)]
assert len(houses)==18
ids={a.get_editor_property('lot_id') for a in houses}
before=mode.startswith('before');gray='gray' in mode
if before and not any(isinstance(a,unreal.MazzarinoBuilding) for a in actors):
    raise RuntimeError('Gli edifici precedenti sono stati rimossi. Per il confronto usare le immagini archiviate o la copia di sicurezza della mappa.')
for a in houses:
    a.set_actor_hidden_in_game(before);a.set_is_temporarily_hidden_in_editor(before);a.set_actor_enable_collision(not before)
    if a.get_editor_property('gray_preview')!=gray:a.set_editor_property('gray_preview',gray);a.rebuild_house()
    for c in a.get_components_by_class(unreal.PrimitiveComponent):c.set_visibility(not before)
for a in actors:
    if isinstance(a,unreal.MazzarinoBuilding) and a.get_editor_property('building_id') in ids:
        a.set_actor_hidden_in_game(not before);a.set_is_temporarily_hidden_in_editor(not before);a.set_actor_enable_collision(before)
        for c in a.get_components_by_class(unreal.PrimitiveComponent):c.set_visibility(before)
name='M80_Camera_Confronto_90'
if 'skyline' in mode:name='M80_Storiche_Panoramica'
elif 'alley' in mode:name='M80_Storiche_Vicolo'
keys=level.get_viewport_config_keys()
for key in keys:level.eject_pilot_level_actor(key)
cam=next((a for a in actors if a.get_actor_label()==name),None)
if cam and name=='M80_Storiche_Vicolo':
    route=json.loads((root/'Saved/Mazzarino80/Historic/routes.json').read_text())
    road=next(r for r in route['roads'] if r['label'].endswith('372573550'))
    pts=[p['position'] for p in road['points'] if p.get('position')]
    idx=min(range(len(pts)),key=lambda i:math.dist(pts[i][:2],[74700,12300]))
    p=pts[idx];q=pts[min(idx+5,len(pts)-1)]
    distance=math.hypot(q[0]-p[0],q[1]-p[1]);assert distance>0
    direction=unreal.Vector((q[0]-p[0])/distance,(q[1]-p[1])/distance,0)
    cam.set_actor_location(unreal.Vector(p[0]+direction.x*300,p[1]+direction.y*300,p[2]+165),False,False)
    cam.set_actor_rotation(unreal.Rotator(pitch=0,yaw=math.degrees(math.atan2(direction.y,direction.x)),roll=0),False)
if not cam:
    if name=='M80_Storiche_Panoramica':loc=(75700,16500,21500);rot=unreal.Rotator(pitch=-29,yaw=-42,roll=0);fov=65
    elif name=='M80_Storiche_Vicolo':
        route=json.loads((root/'Saved/Mazzarino80/Historic/routes.json').read_text())
        road=next(r for r in route['roads'] if r['label'].endswith('372573550'))
        pts=[p['position'] for p in road['points'] if p.get('position')]
        idx=min(range(len(pts)),key=lambda i:math.dist(pts[i][:2],[74700,12300]))
        p=pts[idx];q=pts[min(idx+5,len(pts)-1)]
        loc=(p[0],p[1],p[2]+165);rot=unreal.Rotator(pitch=0,yaw=math.degrees(math.atan2(q[1]-p[1],q[0]-p[0])),roll=0);fov=75
    else:raise RuntimeError(name)
    cam=editor.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(*loc),rot)
    cam.set_actor_label(name);cam.set_folder_path('Mazzarino80/Campione_case_storiche/Verifica')
    cam.camera_component.set_field_of_view(fov);cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
unreal.log('M80_VIEWPORT_KEYS '+str(keys)+' camera '+str(cam.get_actor_rotation()))
for key in keys:
    if str(key).endswith('Viewport0'):level.pilot_level_actor(cam,key)
level.editor_invalidate_viewports()
unreal.log('M80_HISTORIC_VIEW '+mode)
