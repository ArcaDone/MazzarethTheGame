import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir())
maps=unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
content=unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
report={'maps':[x.get_name() for x in maps],'content':[x.get_name() for x in content]}
# Content Browser thumbnails may dirty copied assets when loaded. Save only the
# copied resources and authored sample materials; never the archival maps.
packages=[x for x in content if x.get_name().startswith('/Game/Mazzarino80/')]
if packages:assert unreal.EditorLoadingAndSavingUtils.save_packages(packages,True)
if any(x.get_name()=='/Game/Levels/Mazzarino80_CaseStoriche_Campione' for x in maps):assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
report['remaining_maps']=[x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
report['remaining_content']=[x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(root/'Saved/Mazzarino80/Historic/final_save.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_FINAL_SAVE '+json.dumps(report))
