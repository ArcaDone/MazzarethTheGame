"""Builds (assembles) the crowd's MetaHuman Characters for the game, as Scripts/m80_sandro_build.py does for Sandro:
optimized pipeline (clothes baked into skeletal meshes, hair as cards), MEDIUM quality (lighter textures than the
player's), each into /Game/Mazzarino80/Personaggi/Folla/Build/<Name>/BP_<Name>, the shared assets in
/Game/Mazzarino80/Personaggi/Common. AM80Pedone (MazzarinoGameplay) wears these Blueprints.
Dress and save them first: M80_FOLLA=1 M80_SALVA=1 Scripts/m80_vestiti_prova.py.
Env M80_CHI=Key1,Key2 (default all 21), M80_QUALITA=LOW|MEDIUM|HIGH.
Out: Saved/Mazzarino80/Folla/build.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_build.py -TimeoutMinutes 240
"""
import json
import os
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Folla"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
EAL = unreal.EditorAssetLibrary
BUILD = "/Game/Mazzarino80/Personaggi/Folla/Build"
COMMON = "/Game/Mazzarino80/Personaggi/Common"
CAST = ["Anziano1", "Anziano2", "Anziano3", "Anziano4", "Anziana1", "Anziana2", "Anziana3", "Anziana4",
        "Uomo1", "Uomo2", "Uomo3", "Uomo4", "Donna1", "Donna2", "Donna3",
        "Ragazzo1", "Ragazzo2", "Ragazzo3", "Ragazza1", "Ragazza2", "Ragazza3"]
ONLY = [k for k in os.environ.get("M80_CHI", "").split(",") if k]
QUALITY = os.environ.get("M80_QUALITA", "MEDIUM")


def build(key):
    entry = {}
    c = unreal.load_asset("/Game/Mazzarino80/Personaggi/Folla/MHC_%s" % key)
    if not c:
        return {"error": "missing"}
    SUB.try_add_object_to_edit(c)
    entry["status"] = unreal.M80EditorLibrary.get_meta_human_build_status(c) or "ok"
    entry["can_build"] = SUB.can_build_meta_human(c, False)
    if entry["can_build"]:
        p = unreal.MetaHumanCharacterEditorBuildParameters()
        p.set_editor_property("absolute_build_path", BUILD)
        p.set_editor_property("common_folder_path", COMMON)
        p.set_editor_property("name_override", key)
        p.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.OPTIMIZED)
        p.set_editor_property("pipeline_quality", getattr(unreal.MetaHumanQualityLevel, QUALITY))
        # Copying the face control rigs to COMMON logs "Cannot break link ... RerouteNode" errors, raised by Python
        # after the call: the build has gone on (see m80_sandro_build.py).
        try:
            SUB.build_meta_human(c, p)
            entry["built"] = "ok"
        except Exception as e:  # noqa: BLE001
            entry["built"] = "errors: " + str(e)[:400]
        folder = "%s/%s" % (BUILD, key)
        entry["bp"] = EAL.does_asset_exist("%s/BP_%s" % (folder, key))
        entry["saved"] = EAL.save_directory(folder, False, True) if EAL.does_directory_exist(folder) else False
    SUB.remove_object_to_edit(c)
    unreal.SystemLibrary.collect_garbage()
    return entry


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "build.json"
    report = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for key in CAST:
        if ONLY and key not in ONLY:
            continue
        report[key] = build(key)
        path.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    if EAL.does_directory_exist(COMMON):
        EAL.save_directory(COMMON, False, True)


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "build_errore.txt").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    unreal.SystemLibrary.quit_editor()
