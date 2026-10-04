"""Persist non-partitioned PCG generation for the small per-house volumes."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
bp_path = '/Game/Mazzarino80/PCG/BP_ProceduralBuilding'
bp_class = unreal.EditorAssetLibrary.load_blueprint_class(bp_path)
default_actor = unreal.get_default_object(bp_class)
default_pcg = default_actor.get_component_by_class(unreal.PCGComponent)
default_pcg.modify()
default_pcg.set_editor_property('is_component_partitioned', False)
bp = unreal.load_asset(bp_path)
default_saved = unreal.EditorAssetLibrary.save_loaded_asset(bp)

rows = {}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if not actor.get_actor_label().startswith('BP_ProceduralBuilding_'):
        continue
    pcg = actor.get_component_by_class(unreal.PCGComponent)
    actor.modify()
    pcg.modify()
    pcg.set_editor_property('is_component_partitioned', False)
    rows[actor.get_actor_label()] = pcg.is_component_partitioned

saved = unreal.EditorLevelLibrary.save_current_level()
(root / 'Saved/Mazzarino80/PCG/fix_partitioning.json').write_text(
    json.dumps({'default_saved': default_saved, 'map_saved': saved, 'actors': rows}, indent=2),
    encoding='utf-8')
