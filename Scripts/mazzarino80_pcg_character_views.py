"""Capture repeatable street and roof checks for the character pass."""
import json
import math
import time
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = ROOT/'Saved/Mazzarino80/PCG/CharacterViews'
DEST.mkdir(parents=True,exist_ok=True)
REPORT = DEST/'capture.json'
JOBS = [('1249069213','Roof'),('1249069271','Roof'),
        ('1249069200','Street'),('1249069275','Street')]
state = {'jobs':list(JOBS),'task':None,'handle':None,'elapsed':0.0,'path':None,
         'report':{'completed':{},'errors':{}}}


def write():
    REPORT.write_text(json.dumps(state['report'],indent=2),encoding='utf-8')


def start(job):
    lot,kind = job
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    source = next(a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)
                  and a.get_editor_property('lot_id')==lot)
    spline=source.get_editor_property('footprint')
    p=[spline.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD)
       for i in range(spline.get_number_of_spline_points())]
    front=source.get_editor_property('front_edge')
    a,b=p[front],p[(front+1)%len(p)]
    dx,dy=b.x-a.x,b.y-a.y
    length=math.hypot(dx,dy)
    signed=sum(q.x*p[(i+1)%len(p)].y-p[(i+1)%len(p)].x*q.y for i,q in enumerate(p))
    ox,oy=((dy/length,-dx/length) if signed>0 else (-dy/length,dx/length))
    mx,my=(a.x+b.x)/2,(a.y+b.y)/2
    record=next(v for v in unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18').get_editor_property('buildings')
                if v.get_editor_property('building_id')==lot)
    height=record.get_editor_property('primary_floors')*record.get_editor_property('floor_height_cm')
    if kind=='Roof':
        target_actor=next(v for v in actors if v.get_actor_label()=='BP_ProceduralBuilding_'+lot)
        tank=next(c for c in target_actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
                  if c.get_instance_count()==1 and c.get_editor_property('static_mesh')
                  and 'SM_Platform_Water_Tank_01' in c.get_editor_property('static_mesh').get_path_name())
        p=tank.get_instance_transform(0,world_space=True).translation
        location=unreal.Vector(p.x+450,p.y-500,p.z+550)
        target=unreal.Vector(p.x,p.y,p.z+40)
    else:
        location=unreal.Vector(mx+ox*1100,my+oy*1100,a.z+175)
        target=unreal.Vector(mx,my,a.z+height*.45)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        location,unreal.MathLibrary.find_look_at_rotation(location,target))
    path=DEST/(kind+'_'+lot+'.png')
    state['path']=path
    state['task']=unreal.AutomationLibrary.take_high_res_screenshot(
        1600,900,str(path),delay=.6,force_game_view=True)
    if not state['task'].is_valid_task():
        raise RuntimeError('Screenshot task unavailable')
    state['elapsed']=0.0
    state['started_wall']=time.time()


def tick(delta):
    try:
        state['elapsed']+=delta
        if state['task'] is not None:
            if (state['path'].exists() and state['path'].stat().st_size>10000
                    and state['path'].stat().st_mtime>=state['started_wall']-1):
                job=state['current']
                path=state['path']
                if not path.exists() or path.stat().st_size<10000:
                    raise RuntimeError('Empty screenshot: '+str(path))
                state['report']['completed']['_'.join(job)]={'path':str(path),'bytes':path.stat().st_size}
                state['task']=None
                write()
            elif state['elapsed']>60:
                raise RuntimeError('Screenshot timeout')
            return
        if not state['jobs']:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            return
        state['current']=state['jobs'].pop(0)
        start(state['current'])
    except Exception as exc:
        state['report']['errors']['_'.join(state.get('current',('setup',)))]=str(exc)
        write()
        unreal.unregister_slate_post_tick_callback(state['handle'])


write()
state['handle']=unreal.register_slate_post_tick_callback(tick)
