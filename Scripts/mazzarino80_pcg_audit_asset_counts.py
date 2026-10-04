"""Read persisted point counts from the eighteen PCG data assets."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
houses=json.loads((root/'Research/Mazzarino80/PCG/Buildings_Test18_PCGPoints.json').read_text(encoding='utf-8'))['houses']
report={}
for house in houses:
    lot=house['building_id']
    asset=unreal.load_asset('/Game/Mazzarino80/PCG/Buildings/PCGDA_Building_'+lot)
    tagged=asset.get_editor_property('data').tagged_data
    report[lot]={'expected':sum(len(v) for v in house['stage_points'].values()),
                 'actual':sum(t.data.get_num_points() for t in tagged),
                 'stages':{next(iter(t.tags)):t.data.get_num_points() for t in tagged}}
(root/'Saved/Mazzarino80/PCG/audit_asset_counts.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
