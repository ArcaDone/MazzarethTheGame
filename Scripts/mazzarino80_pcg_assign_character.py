"""Assign distinct, photo-informed architectural treatments to the 18 study lots.

These are art-direction hypotheses, not claims about the real 1980 buildings.
The source footprints, road frontage, family, floors and seed stay unchanged.
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Research/Mazzarino80/PCG/Buildings_Test18.json"
BRICK_RED = "/Game/Mazzarino80/Historic/Materials/M80_Laterizio_rosso_macro.M80_Laterizio_rosso_macro"
BRICK_YELLOW = "/Game/Mazzarino80/Historic/Materials/M80_Laterizio_giallo_macro.M80_Laterizio_giallo_macro"
TANK = "/Game/Megapack/Meshes/MiddleEast/SM_Platform_Water_Tank_01.SM_Platform_Water_Tank_01"
TANK_VESSEL = "/Engine/BasicShapes/Cylinder.Cylinder"
TANK_VESSEL_MATERIAL = "/Game/Mazzarino80/Historic/Materials/M80_Canaletta_pietra_opaca.M80_Canaletta_pietra_opaca"
ROOFTOP_TANK_LOTS = {"1249069213", "1249069271"}
COURTYARD_GATE_LOTS = {"1249069205", "1249069228"}
EXTERNAL_BATHROOM_LOTS = {"1249069228"}
FACADE_FLUE_LOTS = {"1249069200", "1249069204", "1249069235", "1249069276", "1249069287"}
CACTUS_LOTS = {"1249069205", "1249069275", "1249069286"}
IVY_LOTS = {"1249069205", "1249069228"}

# ID: readable identity, upper-floor construction phase, missing masonry frequency,
# material for the addition. No condition is inferred from an OSM footprint.
CHARACTER = {
    "1249068307": ("palazzetto_pietra_mantenuto", False, .06, BRICK_YELLOW),
    "1249069200": ("casa_ampliata_laterizio", True, .62, BRICK_RED),
    "1249069202": ("corte_muratura_stratificata", True, .80, BRICK_YELLOW),
    "1249069204": ("angolo_pietra_riparata", False, .42, BRICK_YELLOW),
    "1249069205": ("corte_intonaco_consumato", False, .48, BRICK_YELLOW),
    "1249069213": ("casa_stretta_vicolo", False, .22, BRICK_YELLOW),
    "1249069219": ("angolo_sopraelevato", True, .58, BRICK_RED),
    "1249069228": ("corte_addizioni_miste", True, .67, BRICK_YELLOW),
    "1249069229": ("palazzetto_fronte_regolare", False, .03, BRICK_YELLOW),
    "1249069235": ("casa_ampliata_rustica", True, .72, BRICK_RED),
    "1249069237": ("angolo_pietra_irregolare", False, .44, BRICK_YELLOW),
    "1249069246": ("palazzetto_consunto", False, .18, BRICK_YELLOW),
    "1249069247": ("popolare_bassa_riparata", False, .75, BRICK_YELLOW),
    "1249069271": ("casa_stretta_terrazzata", False, .37, BRICK_YELLOW),
    "1249069275": ("popolare_muratura_lacunosa", False, .84, BRICK_YELLOW),
    "1249069276": ("casa_stretta_sopraelevata", True, .49, BRICK_RED),
    "1249069286": ("popolare_degrado_localizzato", False, .69, BRICK_YELLOW),
    "1249069287": ("casa_ampliata_incompiuta", True, .78, BRICK_RED),
}


def main():
    catalog = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = catalog["buildings"]
    assert len(rows) == len(CHARACTER) == 18
    assert {row["building_id"] for row in rows} == set(CHARACTER)
    before = {row["building_id"]: (row["footprint_world_cm"], row["front_edge"],
                                   row["party_wall_edges"], row["primary_floors"])
              for row in rows}
    for row in rows:
        code, upper, loss, material = CHARACTER[row["building_id"]]
        row["character_profile"] = code
        row["upper_brick_floor"] = upper
        row["masonry_loss"] = loss
        row["upper_brick_material"] = material
        row["rooftop_tank"] = row["building_id"] in ROOFTOP_TANK_LOTS
        row["rooftop_tank_mesh"] = TANK if row["rooftop_tank"] else ""
        row["tank_vessel_mesh"] = TANK_VESSEL if row["rooftop_tank"] else ""
        row["tank_vessel_material"] = TANK_VESSEL_MATERIAL if row["rooftop_tank"] else ""
        row["courtyard_gate"] = row["building_id"] in COURTYARD_GATE_LOTS
        row["external_bathroom"] = row["building_id"] in EXTERNAL_BATHROOM_LOTS
        row["facade_flue"] = row["building_id"] in FACADE_FLUE_LOTS
        row["cactus"] = row["building_id"] in CACTUS_LOTS
        row["ivy"] = row["building_id"] in IVY_LOTS
        row["reference_quality"] = "PhotoInformedDesignHypothesis"
    after = {row["building_id"]: (row["footprint_world_cm"], row["front_edge"],
                                  row["party_wall_edges"], row["primary_floors"])
             for row in rows}
    assert before == after
    SOURCE.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Assigned photo-informed character profiles to 18 lots; footprints and floors unchanged")


if __name__ == "__main__":
    main()
