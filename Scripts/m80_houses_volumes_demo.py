"""Forces courtyards, outside stairs and set-back floors on a few houses of the test map (houses V3, step 5).

The same settings are in the house details under "Volumi". Env: M80_VOLUMES_MAP, M80_VOLUMES_LOTS (comma separated).
"""
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

MAP = os.environ.get("M80_VOLUMES_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2")
LOTS = os.environ.get("M80_VOLUMES_LOTS", "1249069213,1249069219,1249069228,1249069246,1249069287").split(",")


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    for house in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House):
        if house.get_editor_property("lot_id") not in LOTS:
            continue
        params = house.get_editor_property("house")
        params.set_editor_property("courtyard_chance", 1.0)
        params.set_editor_property("courtyard_min_depth", 1000.0)
        params.set_editor_property("external_stair_chance", 1.0)
        params.set_editor_property("setback_chance", 0.5)
        house.set_editor_property("house", params)
        house.rebuild()
        unreal.log("M80 volumes: {} ({})".format(house.get_editor_property("lot_id"), house.get_editor_property("build_info")))
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10


m80_seq.Sequencer(run())
