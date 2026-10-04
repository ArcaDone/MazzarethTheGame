"""Capture real editor renders with a reentrancy guard and restore after mode."""
import unreal,time,json
from pathlib import Path
capture_root=Path(unreal.Paths.project_dir())
capture_output=capture_root/'Saved/Mazzarino80/Preview/Historic/Refined'
capture_output.mkdir(parents=True,exist_ok=True)
capture_script=(capture_root/'Scripts/mazzarino80_historic_view.py').read_text()
capture_modes=['after','after_gray','after_skyline','after_gray_skyline','after_alley','after_gray_alley']
capture_state={'index':0,'at':0.,'started':False,'busy':False,'files':[],'mtime':0.}
def capture_tick(dt):
    if capture_state['busy']:return
    capture_state['busy']=True
    try:
        i=capture_state['index']
        if capture_state['started']:
            file=capture_output/f'{capture_modes[i]}.png'
            if time.monotonic()-capture_state['at']<8 or not file.exists() or file.stat().st_mtime<=capture_state['mtime']:return
            capture_state['files'].append(str(file));capture_state['index']+=1;capture_state['started']=False
            unreal.log('M80_CAPTURE_DONE '+str(file));return
        if i>=len(capture_modes):
            unreal.unregister_slate_post_tick_callback(capture_callback)
            (capture_root/'Saved/Mazzarino80/Historic/view_mode.txt').write_text('after_alley')
            exec(compile(capture_script,'historic_view','exec'),{})
            (capture_root/'Saved/Mazzarino80/Historic/captures_refined.json').write_text(json.dumps(capture_state['files'],indent=2))
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
            unreal.log('M80_CAPTURE_SET_FINISHED');return
        mode=capture_modes[i]
        (capture_root/'Saved/Mazzarino80/Historic/view_mode.txt').write_text(mode)
        ns={};exec(compile(capture_script,'historic_view','exec'),ns)
        file=capture_output/f'{mode}.png'
        capture_state['mtime']=file.stat().st_mtime if file.exists() else 0.
        capture_state['at']=time.monotonic();capture_state['started']=True
        capture_state['task']=unreal.AutomationLibrary.take_high_res_screenshot(1600,1000,str(file),camera=ns['cam'],delay=2.0,force_game_view=True)
    except Exception:
        unreal.unregister_slate_post_tick_callback(capture_callback)
        (capture_root/'Saved/Mazzarino80/Historic/view_mode.txt').write_text('after_alley')
        exec(compile(capture_script,'historic_view','exec'),{})
        raise
    finally:capture_state['busy']=False
capture_callback=unreal.register_slate_post_tick_callback(capture_tick)
unreal.log('M80_CAPTURE_SET_STARTED')



