"""Replace validation PCGVolumes with the editable BP_ProceduralBuilding class."""
import json
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
world=unreal.EditorLevelLibrary.get_editor_world()
if 'L_PCGBuildings_Validation' not in str(world):
    raise RuntimeError('Open validation map first')
catalog=unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
records={d.get_editor_property('building_id'):d for d in catalog.get_editor_property('buildings')}
blueprint_class=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Mazzarino80/PCG/BP_ProceduralBuilding')
if not blueprint_class:
    raise RuntimeError('Missing BP_ProceduralBuilding class')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
report={'converted':{},'errors':{},'class':str(blueprint_class),'cache_flushed':unreal.PCGBlueprintHelpers.flush_pcg_cache()}
for lot,data in records.items():
    label='BP_ProceduralBuilding_'+lot
    old=existing.get(label)
    if not old:
        report['errors'][lot]='Old validation actor missing'
        continue
    if old.get_class()==blueprint_class:
        report['converted'][lot]='Already converted'
        continue
    try:
        center=old.get_actor_location()
        scale=old.get_actor_scale3d()
        new=actors.spawn_actor_from_class(blueprint_class,center)
        new.set_actor_scale3d(scale)
        new.set_editor_property('building_data',data)
        new.regenerate_building()
        actors.destroy_actor(old)
        new.set_actor_label(label)
        report['converted'][lot]={'actor':str(new),'data_id':data.get_editor_property('building_id')}
    except Exception:
        report['errors'][lot]=traceback.format_exc()
report['saved']=unreal.EditorLevelLibrary.save_current_level()
(root/'Saved/Mazzarino80/PCG/migrate_validation_to_bp.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
