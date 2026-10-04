import json
from pathlib import Path
import unreal

catalog=unreal.load_asset('/Game/Mazzarino80/PCG/DA_Buildings_Test18')
d=next(x for x in catalog.get_editor_property('buildings') if x.get_editor_property('building_id')=='1249069275')
out={}
for name in ('facade_material','roof_material','roof_mesh'):
    v=d.get_editor_property(name)
    out[name]={'repr':str(v),'type':str(type(v)),
               'path':v.get_path_name() if hasattr(v,'get_path_name') else None}
source=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if isinstance(a,unreal.MazzarinoHistoricBuilding) and a.get_editor_property('lot_id')=='1249069275')
out['source']={name:source.get_editor_property(name).get_path_name()
               for name in ('plaster_material','roof_material','roof_tile_mesh')}
Path(unreal.Paths.project_dir(),'Saved/Mazzarino80/PCG/record_materials.json').write_text(
    json.dumps(out,indent=2),encoding='utf-8')
