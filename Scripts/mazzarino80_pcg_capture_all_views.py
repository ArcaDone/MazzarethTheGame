"""Capture top and street views for every approved PCG house in the open map."""
import json
import math
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
houses=json.loads((root/'Saved/Mazzarino80/PCG/baseline_18.json').read_text(encoding='utf-8'))['houses']
folder=root/'Saved/Mazzarino80/PCG/Views'
folder.mkdir(parents=True,exist_ok=True)
viewport=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
views=[]
for h in houses:
    points=h['footprint_world_cm']
    xs=[p[0] for p in points]
    ys=[p[1] for p in points]
    z=points[0][2]
    cx=(min(xs)+max(xs))/2
    cy=(min(ys)+max(ys))/2
    span=max(max(xs)-min(xs),max(ys)-min(ys))
    altitude=max(1700,span*1.1)
    views.append({'id':h['id'],'kind':'Top',
                  'location':unreal.Vector(cx,cy,z+altitude),
                  'rotation':unreal.Rotator(pitch=-90,yaw=0,roll=0)})
    edge=int(h['properties']['front_edge'])
    a=points[edge]
    b=points[(edge+1)%len(points)]
    dx=b[0]-a[0]
    dy=b[1]-a[1]
    length=math.hypot(dx,dy)
    if length<1:
        raise RuntimeError('Front edge too short for '+h['id'])
    signed=sum(points[i][0]*points[(i+1)%len(points)][1]
               -points[(i+1)%len(points)][0]*points[i][1]
               for i in range(len(points)))
    outward=(dy/length,-dx/length) if signed>0 else (-dy/length,dx/length)
    middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
    distance=300
    location=unreal.Vector(middle[0]+outward[0]*distance,
                           middle[1]+outward[1]*distance,z+180)
    target=unreal.Vector(middle[0],middle[1],z+250)
    views.append({'id':h['id'],'kind':'Street','location':location,
                  'rotation':unreal.MathLibrary.find_look_at_rotation(location,target)})

state={'index':0,'task':None,'elapsed':0.0,'results':[],'error':None,'handle':None}
report_path=root/'Saved/Mazzarino80/PCG/capture_all_views.json'

def write_report():
    report_path.write_text(json.dumps({'total':len(views),'completed':len(state['results']),
                                       'results':state['results'],'error':state['error']},indent=2),
                           encoding='utf-8')

def tick(delta):
    try:
        state['elapsed']+=delta
        if state['task'] is not None:
            if state['task'].is_task_done():
                view=views[state['index']]
                path=folder/(view['kind']+'_'+view['id']+'.png')
                if not path.exists() or path.stat().st_size<10000:
                    raise RuntimeError('Screenshot missing: '+str(path))
                state['results'].append({'id':view['id'],'view':view['kind'],
                                         'file':str(path),'bytes':path.stat().st_size})
                state['index']+=1
                state['task']=None
                state['elapsed']=0.0
                write_report()
            elif state['elapsed']>30:
                raise RuntimeError('Screenshot task timed out at '+str(state['index']))
            return
        if state['index']>=len(views):
            unreal.unregister_slate_post_tick_callback(state['handle'])
            return
        view=views[state['index']]
        viewport.set_level_viewport_camera_info(view['location'],view['rotation'])
        path=folder/(view['kind']+'_'+view['id']+'.png')
        if path.exists():
            path.unlink()
        state['task']=unreal.AutomationLibrary.take_high_res_screenshot(
            960,540,str(path),delay=.2,force_game_view=False)
        state['elapsed']=0.0
        if not state['task'].is_valid_task():
            raise RuntimeError('Screenshot task invalid for '+view['id']+' '+view['kind'])
    except Exception as exc:
        state['error']=str(exc)
        write_report()
        unreal.unregister_slate_post_tick_callback(state['handle'])
        unreal.log_error('M80_CAPTURE_ALL '+str(exc))

write_report()
state['handle']=unreal.register_slate_post_tick_callback(tick)
unreal.log('M80_CAPTURE_ALL started '+str(len(views))+' views')
