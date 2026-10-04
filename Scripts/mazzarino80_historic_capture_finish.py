import unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir())
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).set_selected_level_actors([])
exec(compile((root/'Scripts/mazzarino80_historic_capture_details.py').read_text(),'capture_details','exec'),{'M80_CAPTURE_MODES':['after','after_skyline','after_alley','detail_roof']})
