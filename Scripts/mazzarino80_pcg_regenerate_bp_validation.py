"""Regenerate all native building actors in the validation level."""
import json
import traceback
from pathlib import Path
import unreal

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report = {'triggered': [], 'errors': {}, 'cache_flushed': unreal.PCGBlueprintHelpers.flush_pcg_cache()}
for actor in actors:
    if not actor.get_actor_label().startswith('BP_ProceduralBuilding_'):
        continue
    lot = actor.get_actor_label().removeprefix('BP_ProceduralBuilding_')
    try:
        data = actor.get_editor_property('building_data')
        pcg = actor.get_component_by_class(unreal.PCGComponent)
        pcg.cleanup(True)
        pcg.set_editor_property('is_component_partitioned', False)
        pcg.set_graph(data.get_editor_property('building_graph'))
        pcg.generate(True)
        report['triggered'].append(lot)
    except Exception:
        report['errors'][lot] = traceback.format_exc()
Path(unreal.Paths.project_dir(), 'Saved/Mazzarino80/PCG/regenerate_bp_validation.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
