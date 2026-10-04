"""Checks the exclusion zones on the test map (nothing is saved): a zone over one house hides it,
turning the zone off or deleting it brings the house back. Report in Saved/Mazzarino80/HousesV2/exclusion_test.json.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2"
LOT = "1249069204"
OUT = ROOT / "Saved/Mazzarino80/HousesV2/exclusion_test.json"


def state(house):
    baked = house.get_editor_property("baked")
    shell = house.get_editor_property("shell")
    return {"excluded": house.is_excluded(), "baked_visible": baked.is_visible(), "shell_visible": shell.is_visible(),
            "info": house.get_editor_property("build_info")[:60]}


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    house = next(h for h in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House) if h.get_editor_property("lot_id") == LOT)
    report = {"before": state(house)}
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    zone = actors.spawn_actor_from_class(unreal.M80ExclusionZone, house.get_actor_location())
    zone.refresh_houses()
    report["zone_on"] = state(house)
    zone.set_editor_property("enabled", False)
    zone.refresh_houses()
    report["zone_off"] = state(house)
    zone.set_editor_property("enabled", True)
    zone.refresh_houses()
    zone.destroy_actor()
    yield 2
    report["zone_deleted"] = state(house)
    house.set_editor_property("disabled", True)
    house.apply_exclusion()
    report["house_disabled"] = state(house)
    house.set_editor_property("disabled", False)
    house.apply_exclusion()
    report["house_enabled"] = state(house)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
