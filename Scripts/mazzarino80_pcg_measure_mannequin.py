"""Measure the rendered validation mannequin in the live editor."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
actor = next(a for a in actors if a.get_actor_label() == 'Reference_Mannequin_180cm_1249069202')
origin, extent = actor.get_actor_bounds(only_colliding_components=False,
                                        include_from_child_actors=False)
result = {'origin_cm':[origin.x,origin.y,origin.z],
          'extent_cm':[extent.x,extent.y,extent.z],
          'height_cm':extent.z*2,
          'actor_scale':[actor.get_actor_scale3d().x,actor.get_actor_scale3d().y,actor.get_actor_scale3d().z]}
(root/'Saved/Mazzarino80/PCG/mannequin_measure.json').write_text(
    json.dumps(result,indent=2),encoding='utf-8')
unreal.log('M80_MANNEQUIN_MEASURE '+str(result))
