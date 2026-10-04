"""Create an isolated UE level for walking around the four imported pilots."""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
LEVEL = "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_QA"
MANIFEST = json.loads((ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export/export_manifest.json").read_text(encoding="utf-8"))
PILOTS = (
    ("STYLE_01", "1249069204"), ("STYLE_02", "1249068307"),
    ("STYLE_03", "1249069200"), ("STYLE_04", "1249069228"),
)
world = unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError("Unable to load QA map: " + LEVEL)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

floor_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")
floor_mat = unreal.EditorAssetLibrary.load_asset(
    "/Game/Mazzarino80/Historic/Materials/M80_Suolo_neutro")
manny_mesh = unreal.EditorAssetLibrary.load_asset(
    "/Game/Characters/UE5_Mannequins/Meshes/SKM_Manny_Simple")
if not all((floor_mesh, floor_mat, manny_mesh)):
    raise RuntimeError("A QA reference asset is missing")

ground = actors.spawn_actor_from_class(
    unreal.StaticMeshActor, unreal.Vector(1450, 100, -25), unreal.Rotator())
ground.set_actor_label("QA Ground - four houses")
ground.static_mesh_component.set_static_mesh(floor_mesh)
ground.set_actor_scale3d(unreal.Vector(42, 19, .5))
ground.static_mesh_component.set_material(0, floor_mat)

records = []
for index, (style, lot) in enumerate(PILOTS):
    x = index * 950
    stages = []
    for record in MANIFEST["pilot_stages"]:
        if record["style"] != style:
            continue
        path = f"/Game/Mazzarino80/ReuseKit/PilotStages/{Path(record['file']).stem}"
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError("Missing pilot stage StaticMesh: " + path)
        actor = actors.spawn_actor_from_class(
            unreal.StaticMeshActor, unreal.Vector(x, 0, 0), unreal.Rotator())
        actor.set_actor_label(f"QA {style} {record['stage']} - lotto {lot}")
        actor.static_mesh_component.set_static_mesh(mesh)
        stages.append(path)
    manny = actors.spawn_actor_from_class(
        unreal.SkeletalMeshActor, unreal.Vector(x - 390, -310, 0), unreal.Rotator(0, 90, 0))
    manny.set_actor_label(f"Manichino 1.8m {style}")
    manny.skeletal_mesh_component.set_skeletal_mesh(manny_mesh)
    records.append({"style": style, "lot": lot, "stages": stages,
                    "world_cm": [x, 0, 0], "mannequin_cm": [x - 390, -310, 0]})

sun = actors.spawn_actor_from_class(
    unreal.DirectionalLight, unreal.Vector(0, 0, 1000), unreal.Rotator(-47, -32, 0))
sun.set_actor_label("QA Sun")
sky = actors.spawn_actor_from_class(
    unreal.SkyLight, unreal.Vector(0, 0, 300), unreal.Rotator())
sky.set_actor_label("QA Sky")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
    raise RuntimeError("Unable to save QA map")

result = {"level": LEVEL, "pilots": records,
          "note": "Isolated visual QA; not the town PCG level."}
(ROOT / "Pipeline/Unreal/reuse_qa_level.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")
print("M80_REUSE_QA_LEVEL", LEVEL, len(records), "pilots")
