"""Chairs, card tables and cards of L_M80_ProvaFolla as physics objects: pushed by people walking into them and knocked
about by cars; the chairs (tag M80Sedia) can be sat on by the townspeople (AM80Pedone::VaiASedere) and by the player (E
near one), held still while someone sits. Meshes without a simple collision get a box (needed to simulate). Also locks the
root of the clips the player acts out (getting in/out of a car, sitting down, standing up): the player controller moves
the character by their root's travel itself.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_sedie.py -TimeoutMinutes 15
Report: Saved/Mazzarino80/Folla/sedie.json
"""
import json
import os
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
ANIM = "/Game/Mazzarino80/Personaggi/Animazioni/A_M80_Folla_"
REPORT = os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/Folla/sedie.json")
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
# label prefix -> (tag, mass kg)
KINDS = {"Sedia_": ("M80Sedia", 6.0), "Tavolo_carte_": ("M80Tavolo", 22.0), "Carte_": ("M80Carte", 0.1)}
report = {"actors": {}, "meshes_boxed": [], "root_locked": []}


def run():
    for name in ("Sale", "Scende", "Siediti", "Alzati"):
        a = unreal.load_asset(ANIM + name)
        if a:
            a.set_editor_property("force_root_lock", True)
            unreal.EditorAssetLibrary.save_loaded_asset(a, False)
            report["root_locked"].append(name)
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    done_meshes = set()
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
        label = a.get_actor_label()
        kind = next((k for k in KINDS if label.startswith(k)), None)
        if not kind:
            continue
        tag, mass = KINDS[kind]
        comp = a.static_mesh_component
        mesh = comp.static_mesh
        if mesh and mesh.get_path_name() not in done_meshes:
            done_meshes.add(mesh.get_path_name())
            if SUB.get_simple_collision_count(mesh) == 0:
                SUB.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
                unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
                report["meshes_boxed"].append(mesh.get_path_name())
        comp.set_mobility(unreal.ComponentMobility.MOVABLE)
        comp.set_collision_profile_name("PhysicsActor")
        comp.set_simulate_physics(True)
        comp.set_mass_override_in_kg(unreal.Name("None"), mass, True)
        # Asleep until something touches them: a chair pushed into its table would jump at the start.
        bi = comp.get_editor_property("body_instance")
        bi.set_editor_property("start_awake", False)
        # Hard to throw over: weight low, slow to turn and to slide on the stones.
        bi.set_editor_property("com_nudge", unreal.Vector(0, 0, -25 if tag == "M80Sedia" else -30))
        bi.set_editor_property("angular_damping", 4.0)
        bi.set_editor_property("linear_damping", 1.0)
        comp.set_editor_property("body_instance", bi)
        tags = [t for t in a.tags if str(t) != tag]
        a.tags = tags + [unreal.Name(tag)]
        report["actors"][tag] = report["actors"].get(tag, 0) + 1
        yield 1
    # Chairs of the card tables placed into the table's edge: moved back (away from the table they face) until clear,
    # or the first touch would throw them out of it.
    tables = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor)
              if a.get_actor_label().startswith("Tavolo_carte_")]
    report["chairs_moved_back_cm"] = {}
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
        if not a.get_actor_label().startswith("Sedia_tavolo_"):
            continue
        moved = 0
        for _ in range(30):
            o, e = a.get_actor_bounds(False)
            hit = False
            for t in tables:
                to, te = t.get_actor_bounds(False)
                if abs(o.x - to.x) < e.x + te.x and abs(o.y - to.y) < e.y + te.y and abs(o.z - to.z) < e.z + te.z:
                    hit = True
            if not hit:
                break
            a.set_actor_location(a.get_actor_location() - a.get_actor_forward_vector() * 3.0, False, False)
            moved += 3
        report["chairs_moved_back_cm"][a.get_actor_label()] = moved
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)


m80_seq.Sequencer(run(), log_file=REPORT.replace(".json", "_errore.txt"))
