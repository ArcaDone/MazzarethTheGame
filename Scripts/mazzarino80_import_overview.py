"""Open a dedicated overview level from previously imported Unreal meshes."""

import json
from pathlib import Path
import unreal


ROOT = Path(r"D:\UE5Projects\GameAnimationSample")
SOURCE = ROOT / "Research" / "Mazzarino80" / "generated"
REPORT = json.loads((SOURCE / "report.json").read_text(encoding="utf-8"))
LEVEL = "/Game/Levels/Mazzarino80_Panoramica"
imports = {
    "M80_Terreno": "/Game/Mazzarino80/Overview/M80_Terreno1",
    "M80_Strade": "/Game/Mazzarino80/Overview/M80_Strade_Mesh",
    "M80_Edifici": "/Game/Mazzarino80/Overview/M80_Edifici_Mesh",
}
for name, path in imports.items():
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Missing static mesh " + name + ": " + path)

if not unreal.EditorLevelLibrary.new_level(LEVEL):
    raise RuntimeError("Could not create overview level")

placement = unreal.Vector(*REPORT["placement_cm"])
actors = {}
for name, path in imports.items():
    asset = unreal.EditorAssetLibrary.load_asset(path)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(asset, placement)
    actor.set_actor_label(name)
    actor.set_folder_path("Mazzarino80/Panoramica")
    actors[name] = actor

sun = unreal.EditorLevelLibrary.spawn_actor_from_class(
    unreal.DirectionalLight, unreal.Vector(0, 0, 50000),
    unreal.Rotator(roll=0, pitch=-45, yaw=-35))
sun.set_actor_label("M80_Sole")
sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 0))
sky.set_actor_label("M80_Luce_ambiente")

unreal.EditorLevelLibrary.save_current_level()
try:
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    editor.set_level_viewport_camera_info(
        unreal.Vector(placement.x, placement.y, placement.z + 180000),
        unreal.Rotator(roll=0, pitch=-75, yaw=0))
except Exception as exc:
    unreal.log_warning("Viewport camera placement: " + str(exc))

result = {"level": LEVEL, "imports": imports,
          "actor_count": len(unreal.EditorLevelLibrary.get_all_level_actors()),
          "bounds_cm": {name: [[v.x, v.y, v.z] for v in actor.get_actor_bounds(False)]
                        for name, actor in actors.items()}}
(ROOT / "Saved" / "Mazzarino80" / "overview_import.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")
unreal.log("M80_OVERVIEW_DONE " + json.dumps(result))
