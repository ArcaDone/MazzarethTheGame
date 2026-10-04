"""Build the editable PCG source catalog from a captured Unreal baseline."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Saved/Mazzarino80/PCG/baseline_18.json"
DEST = ROOT / "Research/Mazzarino80/PCG"
DEST.mkdir(parents=True, exist_ok=True)
baseline = json.loads(SOURCE.read_text(encoding="utf-8"))
assert len(baseline["houses"]) == 18

family_names = {
    "POPULAR": "Casa bassa popolare",
    "NARROW": "Casa stretta su più piani",
    "CORNER": "Casa d'angolo",
    "COURTYARD": "Casa con piccolo cortile",
    "EXTENDED": "Casa ampliata",
    "PALAZZETTO": "Piccolo palazzetto",
}
material_fields = (
    "plaster_material", "stone_material", "roof_material", "terrace_material",
    "iron_material", "wood_material", "glass_material", "damp_material",
    "repair_material", "exposed_stone_material", "drain_material", "tile_material",
)
module_fields = (
    "roof_tile_mesh", "cable_mesh", "balcony_module_mesh", "door_mesh", "pot_mesh",
)
rows = []
for house in baseline["houses"]:
    properties = house["properties"]
    family = str(properties["family"]).split(".")[1].split(":")[0]
    floors = properties["floors_override"] or {"POPULAR": 1, "NARROW": 3}.get(family, 2)
    roof_type = "Terrace" if family in {"NARROW", "PALAZZETTO"} else "PitchedOrMixed"
    rows.append({
        "building_id": house["id"],
        "family": family,
        "family_label": family_names[family],
        "position_world_cm": house["location_cm"],
        "footprint_world_cm": house["footprint_world_cm"],
        "front_edge": properties["front_edge"],
        "party_wall_edges": properties["party_wall_edges"],
        "entrance_road_path": properties["entrance_road"],
        "ground_actor_path": properties["ground_actor"],
        "primary_floors": floors,
        "floor_height_cm": round(properties["floor_height"] * 100, 3),
        "wall_thickness_cm": round(properties["wall_thickness"] * 100, 3),
        "roof_type": roof_type,
        "roof_rise_cm": round(properties["roof_rise"] * 100, 3),
        "roof_direction": "FrontEdgeDerived",
        "facade_type": "ExposedStone" if "MI_Pietra_" in properties["plaster_material"] else "Plaster",
        "window_pattern": "FamilyRule",
        "door_type": "ExistingModuleOrProcedural",
        "balcony_type": "FamilyRule",
        "ground_relationship": "RoadEntranceAndTerrainFoundations",
        "importance": "Secondary",
        "reference_quality": "CurrentGeneratedStudy",
        "variation_seed": properties["seed"],
        "facade_irregularity": properties["facade_irregularity"],
        "balcony_density": properties["balcony_density"],
        "decay": properties["decay"],
        "materials": {key: properties[key] for key in material_fields},
        "modules": {key: properties[key] for key in module_fields},
        "source_actor_label": house["label"],
    })

ids = [row["building_id"] for row in rows]
assert len(ids) == len(set(ids)) == 18
(DEST / "Buildings_Test18.json").write_text(
    json.dumps({"schema_version": 1, "coordinate_frame": "reflected_world_y_2026-09-28", "buildings": rows}, indent=2),
    encoding="utf-8",
)

lines = [
    "# Test delle 18 case — stato PCG",
    "",
    "Fonte: attori della mappa campione salvata il 29 settembre 2026. I valori edilizi sono quelli della proposta procedurale attuale, non misure storiche certificate. La geometria dei lotti è in coordinate mondo già riflesse su Y.",
    "",
    "| ID lotto | Famiglia | Piani principali | Seed | Punti lotto |",
    "|---|---|---:|---:|---:|",
]
for row in rows:
    lines.append(f"| {row['building_id']} | {row['family_label']} | {row['primary_floors']} | {row['variation_seed']} | {len(row['footprint_world_cm'])} |")
lines += [
    "",
    "## Stato",
    "",
    "- Catalogo iniziale acquisito dall'editor e sei famiglie censite.",
    "- Il generatore PCG non è ancora validato su alcuna casa.",
    "- La mappa campione rimane sul generatore attuale fino al superamento delle verifiche.",
    "",
    "## Vincoli di validazione",
    "",
    "Conservare i 18 ID, le impronte XY, le case verticali su Z, le strade, il terreno, le strutture personali e i percorsi manuali degli impianti. Confrontare volume, silhouette, aperture e materiali con le stesse camere prima di sostituire il campione.",
    "",
]
(DEST / "TEST18.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {len(rows)} buildings to {DEST}")
