"""Verify the saved QA level and its shared material assignments."""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
LEVEL = "/Game/Mazzarino80/ReuseKit/Maps/L_ReuseKit_QA"
world = unreal.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError("QA map did not load")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
labels = [actor.get_actor_label() for actor in actors]
stages = [label for label in labels if label.startswith("QA STYLE_")]
mannequins = [label for label in labels if label.startswith("Manichino 1.8m")]
report = {"level": LEVEL, "actor_count": len(actors), "stages": stages,
          "mannequins": mannequins, "missing_assets": [], "empty_material_slots": []}
if len(stages) != 17 or len(mannequins) != 4:
    raise RuntimeError(f"QA map missing stages/mannequins: {len(stages)}, {len(mannequins)}")
for actor in actors:
    if not actor.get_actor_label().startswith("QA STYLE_"):
        continue
    mesh = actor.static_mesh_component.get_editor_property("static_mesh")
    if not isinstance(mesh, unreal.StaticMesh):
        report["missing_assets"].append(actor.get_actor_label())
        continue
    for index, slot in enumerate(mesh.get_editor_property("static_materials")):
        if slot.material_interface is None:
            report["empty_material_slots"].append([actor.get_actor_label(), index])
if report["missing_assets"] or report["empty_material_slots"]:
    raise RuntimeError("QA map has missing assets/materials: " + repr(report))
(ROOT / "Pipeline/Unreal/reuse_qa_audit.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8")
print("M80_REUSE_QA_AUDIT", len(stages), "stages", len(mannequins), "mannequins")
