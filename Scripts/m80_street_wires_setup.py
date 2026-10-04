"""Places one AM80StreetWires (cables across the streets) in a houses map and saves it (houses V3, step 4.3).

Env: M80_WIRES_MAP (default the 18-house test map). Run after the houses are built.
"""
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

MAP = os.environ.get("M80_WIRES_MAP", "/Game/Mazzarino80/Houses/Maps/L_M80_Houses18_V2")
IRON = "/Game/Mazzarino80/Houses/Materials/MI_M80_Iron"


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Wrong map open: " + world.get_path_name())
    wires = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80StreetWires))
    actor = wires[0] if wires else unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.M80StreetWires, unreal.Vector(0, 0, 0))
    actor.set_actor_label("M80_FiliStrada")
    actor.set_editor_property("wire_material", unreal.load_asset(IRON))
    actor.rebuild()
    unreal.log("M80 wires: " + actor.get_editor_property("build_info"))
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10


m80_seq.Sequencer(run())
