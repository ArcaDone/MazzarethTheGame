"""Vito becomes an in-engine MetaHuman Character (UE 5.8 MetaHuman Creator), editable like the NPCs.
His face comes from the DNA of the legacy MetaHuman made with the online Creator, read straight from the Comune
project (Content/MetaHumans/Vito/SourceAssets/Vito.dna, the project is not opened): the face state is fitted to it,
so the character stays editable (skin, eyes, hair and clothes are set afterwards in the Creator).
Also lists what the Creator offers (body constraints, optional content: presets, clothing, grooms) and the
MetaHuman Crowd classes, for the NPC test.
Output: /Game/Mazzarino80/Personaggi/Vito/MHC_Vito, Saved/Mazzarino80/Personaggi/vito_crea.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_vito_crea.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Personaggi"
DNA = "D:/UE5Projects/Comune/Content/MetaHumans/Vito/SourceAssets/Vito.dna"
FOLDER = "/Game/Mazzarino80/Personaggi/Vito"
NAME = "MHC_Vito"


def api_names(obj, words=None):
    return sorted(n for n in dir(obj) if not n.startswith("_") and (not words or any(w in n.lower() for w in words)))


def asset_paths(path):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    found = reg.get_assets_by_path(path, recursive=True)
    return sorted("%s [%s]" % (a.package_name, a.asset_class_path.asset_name) for a in found)


def steps():
    report = {"dna": DNA}
    OUT.mkdir(parents=True, exist_ok=True)
    yield 30
    report["classes"] = [n for n in dir(unreal) if "MetaHuman" in n]
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    report["subsystem_api"] = api_names(subsystem)
    report["dna_params"] = api_names(unreal.ImportFromDNAParams())

    path = FOLDER + "/" + NAME
    character = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if character is None:
        character = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, FOLDER, unreal.MetaHumanCharacter,
                                                                            unreal.MetaHumanCharacterFactoryNew())
    report["created"] = character.get_path_name() if character else None
    yield 30
    report["added_for_edit"] = subsystem.try_add_object_to_edit(character)
    yield 30
    params = unreal.ImportFromDNAParams()
    params.set_editor_property("import_whole_rig", False)
    report["import"] = str(subsystem.import_from_face_dna(character, DNA, params))
    yield 30
    if "SUCCESS" not in report["import"]:
        # Legacy DNA (online Creator 1.3): its rig fails the archetype check, but the meshes have the MetaHuman
        # topology, so the face is fitted to its head, eyes and teeth vertices instead.
        info, head, left, right, teeth = unreal.M80EditorLibrary.read_face_dna_vertices(DNA)
        report["dna_meshes"] = info.splitlines()
        fit = unreal.MetaHumanCharacterFitToVerticesParams()
        fit.set_editor_property("head_vertices", head)
        fit.set_editor_property("left_eye_vertices", left)
        fit.set_editor_property("right_eye_vertices", right)
        fit.set_editor_property("teeth_vertices", teeth)
        report["fit_counts"] = [len(head), len(left), len(right), len(teeth)]
        report["fit"] = subsystem.fit_state_to_target_vertices(character, fit)
        yield 30
        subsystem.commit_face_state(character)
    yield 60
    report["can_build"] = subsystem.can_build_meta_human(character, True)
    try:
        report["body_constraints"] = [
            {"name": str(c.get_editor_property("name")), "active": c.get_editor_property("is_active"),
             "range": [c.get_editor_property("target_measurement"), c.get_editor_property("min_measurement"),
                       c.get_editor_property("max_measurement")]}
            for c in subsystem.get_body_constraints(character)]
    except Exception as e:  # noqa: BLE001 - the struct field names are only a guess, keep the rest of the report
        report["body_constraints_error"] = str(e)
    report["character_api"] = api_names(character)
    report["saved"] = unreal.EditorAssetLibrary.save_loaded_asset(character, False)

    # A look at the face (unrigged preview), front and three-quarter, to compare with the original Vito.
    try:
        actor = subsystem.spawn_meta_human_actor(character, True)
        yield 120
        report["preview_actor"] = actor.get_class().get_name() if actor else None
        if actor:
            loc = actor.get_actor_location()
            head = unreal.Vector(loc.x, loc.y, loc.z + 165)
            for name, off in (("fronte", unreal.Vector(0, 55, 0)), ("tre_quarti", unreal.Vector(40, 40, 0))):
                eye = head + off
                rot = unreal.MathLibrary.find_look_at_rotation(eye, head)
                cap = m80_seq.ViewCapture(900, 900, 30)
                cap.capture(eye, rot, OUT / ("vito_%s.png" % name))
                cap.destroy()
                yield 5
            actor.destroy_actor()
    except Exception as e:  # noqa: BLE001 - the photos are only a check, the asset is already saved
        report["preview_error"] = str(e)

    for folder in ("Presets", "Clothing", "Grooms", "Body"):
        items = asset_paths("/MetaHumanCharacter/Optional/" + folder)
        report["optional_" + folder] = {"count": len(items), "first": items[:60]}
    report["crowd_classes"] = [n for n in dir(unreal) if "Crowd" in n or "Mass" in n[:4]]
    (OUT / "vito_crea.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "vito_crea_error.txt"))
