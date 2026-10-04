import json
from pathlib import Path

import unreal


project = Path(unreal.Paths.project_dir())
output = project / "Saved" / "Mazzarino80" / "verify_base.json"
output.parent.mkdir(parents=True, exist_ok=True)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
loaded = bool(level.load_level("/Game/Levels/Mazzarino80_Base"))
descriptors = unreal.WorldPartitionBlueprintLibrary.get_actor_descs() or []
unreal.WorldPartitionBlueprintLibrary.load_actors([desc.guid for desc in descriptors])
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
labels = [actor.get_actor_label() for actor in actors]
result = {
    "loaded": loaded,
    "actor_count": len(actors),
    "descriptor_count": len(descriptors),
    "landscape_proxy_count": sum(
        actor.get_class().get_name() == "LandscapeStreamingProxy" for actor in actors
    ),
    "provisional_cube_count": sum(
        actor.get_class().get_name() == "StaticMeshActor"
        and actor.get_actor_label().startswith("Cube")
        for actor in actors
    ),
    "anchors_present": {
        name: name in labels
        for name in ("ComuneCompleto", "Matrice", "A_SanDomenico")
    },
}
output.write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log("MAZZARINO80_VERIFY " + json.dumps(result))
assert loaded and result["actor_count"] >= 40
assert result["landscape_proxy_count"] == 16
assert result["provisional_cube_count"] == 0
assert all(result["anchors_present"].values())
