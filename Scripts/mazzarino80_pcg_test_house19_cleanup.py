"""Remove only the temporary nineteenth actor and keep its reusable test assets."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
subsystem=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors=subsystem.get_all_level_actors()
matches=[a for a in actors if a.get_actor_label()=='BP_ProceduralBuilding_19_TEST']
if len(matches)!=1:
    raise RuntimeError('Expected exactly one temporary actor')
removed=subsystem.destroy_actor(matches[0])
saved=unreal.EditorLevelLibrary.save_current_level()
remaining=sum(a.get_actor_label().startswith('BP_ProceduralBuilding_')
              for a in subsystem.get_all_level_actors())
(root/'Saved/Mazzarino80/PCG/house19_cleanup.json').write_text(
    json.dumps({'removed':removed,'map_saved':saved,'remaining_pcg_houses':remaining},indent=2),
    encoding='utf-8')
