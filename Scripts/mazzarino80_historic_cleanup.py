"""Remove obsolete generated actors only from the dedicated sample map."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir())
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()!='Mazzarino80_CaseStoriche_Campione':
    assert levels.load_level('/Game/Levels/Mazzarino80_CaseStoriche_Campione')
actors=editor.get_all_level_actors()
houses=[a for a in actors if isinstance(a,unreal.MazzarinoHistoricBuilding)]
old=[a for a in actors if isinstance(a,unreal.MazzarinoBuilding)]
assert len(houses)==18
archive=root/'Saved/Mazzarino80/Historic/previous_lots.json'
if old and not archive.exists():
    rows={}
    for a in old:
        s=a.get_editor_property('footprint')
        rows[a.get_editor_property('building_id')]={'label':a.get_actor_label(),'points':[list(s.get_location_at_spline_point(i,unreal.SplineCoordinateSpace.WORLD).to_tuple()) for i in range(s.get_number_of_spline_points())]}
    archive.write_text(json.dumps(rows,indent=2))
for i,a in enumerate(old):
    assert editor.destroy_actor(a),a.get_actor_label()
    if i%500==0:unreal.log('M80_CLEANUP_PROGRESS '+str(i)+'/'+str(len(old)))
remaining=editor.get_all_level_actors()
assert not any(isinstance(a,unreal.MazzarinoBuilding) for a in remaining)
assert len([a for a in remaining if isinstance(a,unreal.MazzarinoHistoricBuilding)])==18
(root/'Saved/Mazzarino80/Historic/cleanup.json').write_text(json.dumps({'removed_previous_buildings':len(old),'remaining_historic_buildings':18,'map':'/Game/Levels/Mazzarino80_CaseStoriche_Campione','backup':'Saved/Mazzarino80/Backups/Before_sample_cleanup_2026-09-28/Mazzarino80_CaseStoriche_Campione.umap'},indent=2))
unreal.log('M80_CLEANUP_FINISHED '+str(len(old)))
