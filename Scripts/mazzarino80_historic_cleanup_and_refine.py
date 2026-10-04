from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())
for name in ['cleanup','finish_materials','integrity','routes','step_passage']:
    script=root/'Scripts'/('mazzarino80_historic_'+name+'.py')
    exec(compile(script.read_text(encoding='utf-8-sig'),str(script),'exec'),{})
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log('M80_CLEAN_SAMPLE_SAVED')
