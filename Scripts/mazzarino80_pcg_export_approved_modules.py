"""Snapshot approved house geometry as editable, staged PCG module placements."""
import json
import traceback
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / 'Research/Mazzarino80/PCG/BakedSource'
OUT.mkdir(parents=True, exist_ok=True)
TEST_IDS = None
SECTION_STAGE = {0:'Structure',1:'Facades',2:'Roofs',3:'Roofs',4:'Details',5:'Details',
                 6:'Openings',7:'Facades',8:'Structure',9:'Details'}
MODULE_STAGE = {'Pietra_soglie_balconi':'Openings','Ferro_ringhiere':'Details',
                'Legno_portoni_persiane':'Openings','Vetri_incassati':'Openings',
                'Canalette_riparazioni':'Details','Vita_quotidiana':'Details',
                'Portoni_recuperati':'Openings','Vasi_recuperati':'Details',
                'Coppi_tridimensionali':'Roofs','Balconi_completi':'Details'}

def vec(v):
    return [round(v.x,6), round(v.y,6), round(v.z,6)]

def quat(q):
    return [round(q.x,8),round(q.y,8),round(q.z,8),round(q.w,8)]

def path(asset):
    return asset.get_path_name() if asset else ''

def placement(role, stage, transform, mesh, material):
    return {'role':role,'stage':stage,'location_cm':vec(transform.translation),
            'rotation_quat':quat(transform.rotation),'scale':vec(transform.scale3d),
            'mesh':mesh,'material':material}

result={'houses':{},'errors':{}}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if not isinstance(actor,unreal.MazzarinoHistoricBuilding):
        continue
    lot=actor.get_editor_property('lot_id')
    if TEST_IDS is not None and lot not in TEST_IDS:
        continue
    try:
        exported=[str(p) for p in actor.export_pcg_surface_sections(str(OUT))]
        surface=actor.get_editor_property('surface')
        groups={stage:[] for stage in ('Structure','Facades','Openings','Roofs','Details')}
        for section,stage in SECTION_STAGE.items():
            source=OUT/f'Surface_{lot}_S{section}.obj'
            if not source.exists():
                continue
            mesh=f'/Game/Mazzarino80/PCG/ApprovedModules/SM_PCG_Source_{lot}_S{section}.SM_PCG_Source_{lot}_S{section}'
            groups[stage].append(placement(f'surface_section_{section}',stage,surface.get_world_transform(),
                                           mesh,path(surface.get_material(section))))
        component_counts={}
        for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            count=component.get_instance_count()
            if not count:
                continue
            name=component.get_name()
            stage=MODULE_STAGE.get(name,'Details')
            mesh=path(component.get_editor_property('static_mesh'))
            material=path(component.get_material(0))
            for i in range(count):
                transform=component.get_instance_transform(i,world_space=True)
                groups[stage].append(placement(name,stage,transform,mesh,material))
            component_counts[name]=count
        result['houses'][lot]={'label':actor.get_actor_label(),'surface_exports':exported,
                               'component_counts':component_counts,'stage_points':groups}
    except Exception:
        result['errors'][lot]=traceback.format_exc()
(OUT/'approved_modules.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
unreal.log('M80_PCG_APPROVED_MODULES '+str(len(result['houses']))+' houses, '+str(len(result['errors']))+' errors')
