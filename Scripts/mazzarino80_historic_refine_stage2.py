from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())
for name in ['house_tints','integrity']:
    p=root/'Scripts'/('mazzarino80_historic_'+name+'.py')
    exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),{})
(root/'Saved/Mazzarino80/Historic/view_mode.txt').write_text('after_alley')
p=root/'Scripts/mazzarino80_historic_view.py'
exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),{})
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
