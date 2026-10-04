"""Find an unobstructed street-level camera around crowded lot 1249069228."""
import json
import math
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
h=next(h for h in json.loads((root/'Saved/Mazzarino80/PCG/baseline_18.json').read_text(
    encoding='utf-8'))['houses'] if h['id']=='1249069228')
p=h['footprint_world_cm']
area=sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1]
         for i in range(len(p)))
edges=[1,6,7,10,11,12]
views=[]
for edge in edges:
    a,b=p[edge],p[(edge+1)%len(p)]
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    outward=(dy/length,-dx/length) if area>0 else (-dy/length,dx/length)
    mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
    for distance in (300,700):
        loc=unreal.Vector(mid[0]+outward[0]*distance,
                          mid[1]+outward[1]*distance,a[2]+180)
        target=unreal.Vector(mid[0],mid[1],a[2]+250)
        views.append((edge,distance,loc,unreal.MathLibrary.find_look_at_rotation(loc,target)))

folder=root/'Saved/Mazzarino80/PCG/Views'
state={'i':0,'task':None,'handle':None,'done':[],'error':None,'elapsed':0.0}
output=root/'Saved/Mazzarino80/PCG/capture_9228_alternates.json'
viewport=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)

def save():
    output.write_text(json.dumps({'completed':len(state['done']),'total':len(views),
                                   'files':state['done'],'error':state['error']},indent=2),
                      encoding='utf-8')

def tick(dt):
    try:
        state['elapsed']+=dt
        if state['task']:
            if state['task'].is_task_done():
                edge,distance,_,_=views[state['i']]
                path=folder/f'StreetAlt_1249069228_E{edge}_D{distance}.png'
                if not path.exists():
                    raise RuntimeError('Missing '+str(path))
                state['done'].append(str(path))
                state['i']+=1
                state['task']=None
                state['elapsed']=0.0
                save()
            elif state['elapsed']>30:
                raise RuntimeError('Timed out')
            return
        if state['i']>=len(views):
            unreal.unregister_slate_post_tick_callback(state['handle'])
            return
        edge,distance,loc,rot=views[state['i']]
        viewport.set_level_viewport_camera_info(loc,rot)
        path=folder/f'StreetAlt_1249069228_E{edge}_D{distance}.png'
        state['task']=unreal.AutomationLibrary.take_high_res_screenshot(
            960,540,str(path),delay=.2,force_game_view=False)
        state['elapsed']=0.0
    except Exception as exc:
        state['error']=str(exc)
        save()
        unreal.unregister_slate_post_tick_callback(state['handle'])

save()
state['handle']=unreal.register_slate_post_tick_callback(tick)
