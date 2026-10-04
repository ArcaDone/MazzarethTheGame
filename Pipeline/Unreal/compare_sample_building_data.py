"""Compare approved actors with catalog records, without editing either."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
catalog = unreal.load_asset("/Game/Mazzarino80/PCG/DA_Buildings_Test18")
records = {str(d.get_editor_property("building_id")): d for d in
           catalog.get_editor_property("buildings")}
fields = ("family", "visual_style", "primary_floors", "floor_height_cm",
          "roof_type", "roof_rise_cm", "facade_type", "character_profile",
          "variation_seed", "facade_material", "roof_material", "roof_mesh",
          "building_graph")
rows = {}
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if not actor.get_actor_label().startswith("BP_ProceduralBuilding_"):
        continue
    lot = actor.get_actor_label().rsplit("_", 1)[-1]
    original = actor.get_editor_property("building_data")
    catalog_record = records[lot]
    differences = {}
    for field in fields:
        a = str(original.get_editor_property(field))
        b = str(catalog_record.get_editor_property(field))
        if a != b:
            differences[field] = {"actor": a, "catalog": b}
    rows[lot] = differences
(root / "Pipeline/Unreal/sample_building_data_comparison.json").write_text(
    json.dumps(rows, indent=2), encoding="utf-8")
print("M80_SAMPLE_DATA_COMPARISON", sum(bool(x) for x in rows.values()))
