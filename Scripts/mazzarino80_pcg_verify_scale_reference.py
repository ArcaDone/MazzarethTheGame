"""Verify that the scale reference survives a save/reopen cycle."""
import json
import traceback
from pathlib import Path

import unreal

LEVEL = "/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext"
LOT = "1249069202"
OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/PCG/scale_reference_reopen.json"


def main():
    result = {"level": LEVEL}
    try:
        result["saved"] = bool(unreal.EditorLevelLibrary.save_current_level())
        result["reopened"] = bool(unreal.EditorLevelLibrary.load_level(LEVEL))
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        by_label = {actor.get_actor_label(): actor for actor in actors}
        man = by_label["Reference_Mannequin_180cm_" + LOT]
        ruler = by_label["Reference_ExactHeight_180cm_" + LOT]
        mesh = man.get_component_by_class(unreal.SkeletalMeshComponent).get_editor_property("skeletal_mesh_asset")
        bounds_origin, bounds_extent = man.get_actor_bounds(False)
        ruler_mesh = ruler.get_component_by_class(unreal.StaticMeshComponent).get_editor_property("static_mesh")
        ruler_height = 2.0 * ruler_mesh.get_bounds().box_extent.z * ruler.get_actor_scale3d().z
        result.update({
            "mannequin_asset": mesh.get_path_name(),
            "mannequin_scale": [man.get_actor_scale3d().x, man.get_actor_scale3d().y,
                                man.get_actor_scale3d().z],
            "mannequin_height_cm": 2.0 * bounds_extent.z,
            "ruler_height_cm": ruler_height,
            "reference_count": sum(actor.get_actor_label().startswith("Reference_") for actor in actors),
            "pcg_actor_count": sum(actor.get_actor_label().startswith("BP_ProceduralBuilding_") for actor in actors),
        })
    except Exception:
        result["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    unreal.log("M80_SCALE_REOPEN " + str(OUT))


main()
