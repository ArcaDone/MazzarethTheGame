"""Puts a crowd (AM80Folla, "Folla (Mazzarino)") in L_M80_ProvaFolla, so that Play there fills the square: Quanti people
around the crowd markers, in the outfits of Scripts/m80_folla_build.py. Run again: the crowd actor is replaced.
Env M80_QUANTI=42.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_metti.py -TimeoutMinutes 15
"""
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    for old in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Folla):
        EAS.destroy_actor(old)
    crowd = EAS.spawn_actor_from_class(unreal.M80Folla, unreal.Vector(0, 0, 100))
    crowd.set_actor_label("Folla")
    crowd.set_editor_property("quanti", int(os.environ.get("M80_QUANTI", "42")))
    yield 10
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10


m80_seq.Sequencer(run(), log_file=str(m80_seq.Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Folla/metti_errore.txt"))
