"""Promote the verified 18-house PCG stage to the sample level, retaining an asset backup."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
stage = '/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext'
target = '/Game/Levels/Mazzarino80_CaseStoriche_Campione'
backup = '/Game/Mazzarino80/PCG/Backups/L_CaseStoriche_BeforeWeatheredFinish_20260930'
report_file = root / 'Saved/Mazzarino80/PCG/promote_weathered_sample.json'
report = {'stage': stage, 'target': target, 'backup': backup}

if not unreal.EditorAssetLibrary.does_asset_exist(stage):
    raise RuntimeError('Verified PCG stage is missing')
if not unreal.EditorAssetLibrary.does_asset_exist(target):
    raise RuntimeError('Original sample is missing')

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
pcg_labels = [a.get_actor_label() for a in actors if a.get_actor_label().startswith('BP_ProceduralBuilding_')]
if len(pcg_labels) != 18:
    raise RuntimeError(f'Expected 18 PCG houses in loaded stage, got {len(pcg_labels)}')
report['stage_house_count'] = len(pcg_labels)
report['stage_saved'] = bool(unreal.EditorLevelLibrary.save_current_level())
if not report['stage_saved']:
    raise RuntimeError('Could not save the staged level')

unreal.EditorAssetLibrary.make_directory('/Game/Mazzarino80/PCG/Backups')
if not unreal.EditorAssetLibrary.does_asset_exist(backup):
    report['backup_created'] = bool(unreal.EditorAssetLibrary.duplicate_asset(target, backup))
else:
    report['backup_created'] = False
report['backup_saved'] = bool(unreal.EditorAssetLibrary.save_asset(backup))
if not report['backup_saved'] or not unreal.EditorAssetLibrary.does_asset_exist(backup):
    raise RuntimeError('Original sample backup failed; target was not touched')

report['old_target_deleted'] = bool(unreal.EditorAssetLibrary.delete_asset(target))
if not report['old_target_deleted']:
    raise RuntimeError('Original sample could not be removed; asset backup is safe')
report['new_target_created'] = bool(unreal.EditorAssetLibrary.duplicate_asset(stage, target))
report['new_target_saved'] = bool(unreal.EditorAssetLibrary.save_asset(target)) if report['new_target_created'] else False
report['target_disk_exists'] = (root / 'Content/Levels/Mazzarino80_CaseStoriche_Campione.umap').exists()
report_file.write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('M80_PROMOTE_WEATHERED ' + str(report))
if not (report['new_target_created'] and report['new_target_saved'] and report['target_disk_exists']):
    raise RuntimeError('Promoted sample save failed; restore the backup asset')
