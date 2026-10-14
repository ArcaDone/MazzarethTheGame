"""The recovered buildings' Blueprints become Static, so World Partition puts them in the HLODs (movable components are
left out: the Madonna, the Scuola by the Matrice, the Salesiane, Liardo, the Castello, San Domenico and the Matrice
vanished from far away, the Comune, already static, did not). None of them moves anything in game.
In L_M80_Paese_WP the recovered Matrice (now holding the new meshes) is shown again and the separate Matrice_Interno
actor left by m80_matrice_place.py is hidden in game, without collision (kept, not deleted).
Saves the 7 Blueprints, their placed actors and the two Matrice actors; the HLODs then need a rebuild.
Output: Saved/Mazzarino80/Memoria/edifici_static.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_edifici_static.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Memoria"
BLUEPRINTS = ["/Game/Migrated/Arinazzo/A_Liardo", "/Game/Migrated/Madonna/A_Madonna", "/Game/Migrated/Salesiane/A_Salesiane",
              "/Game/Migrated/Castello/CastelCompleted", "/Game/Migrated/SanDomenico/A_SanDomenico",
              "/Game/Migrated/Animations/Matrice", "/Game/Migrated/Matrice/Scuola/ScuolaMatrice"]
SHOW = "M80_Recuperato_Matrice"
HIDE = "Matrice_Interno"
STATIC = unreal.ComponentMobility.STATIC


def make_static(bp):
    """Every scene component of the Blueprint (its own and the inherited ones) Static; count of changed ones."""
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    changed = 0
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        obj = lib.get_object(lib.get_data(h))
        if isinstance(obj, unreal.SceneComponent) and obj.get_editor_property("mobility") != STATIC:
            obj.modify()
            obj.set_editor_property("mobility", STATIC)
            changed += 1
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    return changed


def mobilities(actor):
    out = {}
    for c in actor.get_components_by_class(unreal.SceneComponent):
        k = str(c.get_editor_property("mobility")).split(".")[-1].split(":")[0]
        out[k] = out.get(k, 0) + 1
    return out


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"blueprints": {}}
    for path in BLUEPRINTS:
        bp = unreal.load_asset(path)
        report["blueprints"][path] = make_static(bp)
        unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    yield 10
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 30
    classes = {unreal.load_asset(p).generated_class().get_name() for p in BLUEPRINTS}
    # A desc's native_class is the C++ parent (Actor): pick the Blueprint instances by their actor name (<Class>_<n>).
    descs = [d for d in m80_seq.actor_descs() if str(d.get_editor_property("label")) in (SHOW, HIDE)
             or str(d.get_editor_property("name")).rsplit("_", 1)[0] in classes]
    report["descs"] = sorted(str(d.get_editor_property("label")) for d in descs)
    m80_seq.load(descs)
    yield 120
    world = m80_seq.editor_world()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    packages = []
    report["instances"] = {}
    for a in actors:
        label = a.get_actor_label()
        if a.get_class().get_name() in classes:
            before = mobilities(a)
            # A placed actor may keep its own (movable) copy of a component's mobility: make it follow.
            if before.get("MOVABLE"):
                for c in a.get_components_by_class(unreal.SceneComponent):
                    c.set_mobility(STATIC)
            # Always resaved: its actor desc keeps "not HLOD relevant" from the last save, and the HLOD build
            # reads the descs, not the Blueprint, so an unsaved instance stays out of the HLODs.
            a.modify()
            packages.append(a.get_package())
            report["instances"][label] = {"before": before, "after": mobilities(a)}
        if label in (SHOW, HIDE):
            show = label == SHOW
            a.modify()
            a.set_actor_hidden_in_game(not show)
            a.set_actor_enable_collision(show)
            packages.append(a.get_package())
            report.setdefault("matrice", {})[label] = {"hidden_in_game": not show, "collision": show}
    report["saved_actors"] = unreal.EditorLoadingAndSavingUtils.save_packages(list({p.get_name(): p for p in packages}.values()), False)
    report["saved_packages"] = sorted({p.get_name() for p in packages})
    (OUT / "edifici_static.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "edifici_static_error.txt"))
