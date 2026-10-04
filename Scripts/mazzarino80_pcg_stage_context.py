"""Stage all PCG houses in the copied sample while retaining edited service splines."""
import json
import traceback
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
world=unreal.EditorLevelLibrary.get_editor_world()
if 'L_PCGBuildings_WithContext' not in str(world):
    raise RuntimeError('Open the contextual copy before staging')
baseline=json.loads((root/'Saved/Mazzarino80/PCG/baseline_18.json').read_text(encoding='utf-8'))
catalog=unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
records={d.get_editor_property('building_id'):d for d in catalog.get_editor_property('buildings')}
bp=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Mazzarino80/PCG/BP_ProceduralBuilding')
subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors={a.get_actor_label():a for a in subsystem.get_all_level_actors()}
report={'staged':{},'errors':{},'original_count':len(actors),'cache_flushed':unreal.PCGBlueprintHelpers.flush_pcg_cache()}

for house in baseline['houses']:
    lot=house['id']
    old=actors.get(house['label'])
    data=records.get(lot)
    if not old or not data:
        report['errors'][lot]='Missing original actor or catalog record'
        continue
    try:
        old.set_editor_property('pcg_visual_replacement', True)
        service=[c for c in old.get_components_by_class(unreal.SplineComponent)
                 if c.get_name() != 'Lotto_perimetro']
        points_before=sum(c.get_number_of_spline_points() for c in service)
        hidden=[]
        for comp in old.get_components_by_class(unreal.ActorComponent):
            if isinstance(comp,(unreal.ProceduralMeshComponent,unreal.InstancedStaticMeshComponent,unreal.TextRenderComponent)):
                comp.set_visibility(False)
                comp.set_hidden_in_game(True)
                if isinstance(comp,unreal.PrimitiveComponent):
                    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                hidden.append(comp.get_name())
        poly=[p for p in data.get_editor_property('footprint_world_cm')]
        xmin,xmax=min(p.x for p in poly),max(p.x for p in poly)
        ymin,ymax=min(p.y for p in poly),max(p.y for p in poly)
        base=min(p.z for p in poly)
        height=data.get_editor_property('primary_floors')*data.get_editor_property('floor_height_cm')
        center=unreal.Vector((xmin+xmax)/2,(ymin+ymax)/2,base+height/2)
        label='BP_ProceduralBuilding_'+lot
        new=actors.get(label)
        if new is None:
            new=subsystem.spawn_actor_from_class(bp,center)
            new.set_actor_label(label)
        new.set_actor_hidden_in_game(False)
        new.set_actor_location(center,False,False)
        new.set_actor_scale3d(unreal.Vector(max(2,(xmax-xmin)/1000+1),max(2,(ymax-ymin)/1000+1),2))
        new.set_editor_property('building_data',data)
        pcg=new.get_component_by_class(unreal.PCGComponent)
        pcg.cleanup(True)
        pcg.set_editor_property('is_component_partitioned',False)
        pcg.set_graph(data.get_editor_property('building_graph'))
        pcg.generate(True)
        points_after=sum(c.get_number_of_spline_points() for c in service)
        report['staged'][lot]={'old':old.get_actor_label(),'new':new.get_actor_label(),
                               'hidden_components':hidden,'service_points_before':points_before,
                               'service_points_after':points_after}
    except Exception:
        report['errors'][lot]=traceback.format_exc()

(root/'Saved/Mazzarino80/PCG/stage_context.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
