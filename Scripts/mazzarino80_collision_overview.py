"""Use mesh triangles for collision, avoiding a town-wide convex collision hull."""

import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
paths = ["/Game/Mazzarino80/Overview/M80_Terreno1",
         "/Game/Mazzarino80/Overview/M80_Strade_Mesh",
         "/Game/Mazzarino80/Overview/M80_Edifici_Mesh"]
result = {}
for path in paths:
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    try:
        unreal.EditorStaticMeshLibrary.remove_collisions(mesh)
        body = mesh.get_editor_property("body_setup")
        body.set_editor_property("collision_trace_flag",
                                 unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        result[path] = "complex_as_simple"
    except Exception as exc:
        result[path] = "ERROR " + str(exc)

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if actor.get_actor_label() == "M80_Sole":
        actor.set_actor_rotation(unreal.Rotator(roll=0, pitch=-45, yaw=-35), False)
    if actor.get_actor_label() == "M80_Luce_ambiente":
        try:
            actor.get_component_by_class(unreal.SkyLightComponent).recapture_sky()
        except Exception:
            pass

unreal.EditorLevelLibrary.save_current_level()
(root / "Saved" / "Mazzarino80" / "overview_collision.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_OVERVIEW_COLLISION " + json.dumps(result))
