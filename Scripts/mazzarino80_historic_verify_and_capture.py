import unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir())
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
for name in ['mazzarino80_historic_validate_details.py','mazzarino80_historic_validate.py','mazzarino80_historic_integrity.py','mazzarino80_historic_routes.py','mazzarino80_historic_step_passage.py','mazzarino80_historic_detail_cameras.py']:
 unreal.log('M80_VERIFY_START '+name)
 file=root/'Scripts'/name
 exec(compile(file.read_text(),str(file),'exec'),{})
unreal.SystemLibrary.execute_console_command(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),'r.Streaming.PoolSize 2000')
file=root/'Scripts/mazzarino80_historic_capture_details.py'
exec(compile(file.read_text(),str(file),'exec'),globals())
