"""Sandro becomes the player: BP_M80_Giocatore (the sample's MetaHuman Kellan with the tracksuit, Scripts/m80_player_setup.py)
takes the meshes and grooms of the built Sandro (Scripts/m80_sandro_build.py -> /Game/Mazzarino80/Personaggi/Sandro/Build/Sandro):
body, face (with its own face animation blueprint), hair, beard, moustache, eyebrows, eyelashes, and his clothes (the
City Sample shirt-tie-jacket, trousers and oxfords, baked by the optimized pipeline into skeletal meshes) on the
Torso / Legs / Feet slots (the tracksuit's material overrides cleared). Animation (mannequin + retarget), camera and controls stay the player's.
Out: Saved/Mazzarino80/Player/sandro_giocatore.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_sandro_giocatore.py
"""
import json
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Player"
BP = "/Game/Mazzarino80/Player/BP_M80_Giocatore"
SRC = "/Game/Mazzarino80/Personaggi/Sandro/Build/Sandro"
COMMON = "/Game/Mazzarino80/Personaggi/Common"
MESHES = {
    "Body": SRC + "/Body/SKM_MHC_Sandro_BodyMesh",
    "Face": SRC + "/Face/SKM_MHC_Sandro_FaceMesh",
    "Torso": SRC + "/Clothing/MHC_Sandro_Outfits",
    "Legs": SRC + "/Clothing/MHC_Sandro_Outfits_2",
    "Feet": SRC + "/Clothing/MHC_Sandro_Outfits_3",
}
GROOMS = {"Hair": "Hair_L_MessyClumps", "Beard": "Beard_S_Full", "Mustache": "Mustache_S_Full", "Eyebrows": "Eyebrows_M_Dense",
          "Eyelashes": "Eyelashes_S_Sparse", "Fuzz": None}
FACE_ANIM = COMMON + "/Face/ABP_Face"


def templates(bp):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        o = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
        if o:
            out.setdefault(o.get_name().replace("_GEN_VARIABLE", ""), []).append(o)
    return out


def main():
    r = {}
    bp = unreal.load_asset(BP)
    comps = templates(bp)
    r["components"] = sorted(comps)
    for name, path in MESHES.items():
        mesh = unreal.load_asset(path)
        for o in comps.get(name, []):
            o.set_editor_property("skeletal_mesh_asset", mesh)
            o.set_editor_property("override_materials", [])   # the tracksuit's acetate was an override on Torso/Legs
            if name == "Face":
                o.set_editor_property("anim_class", unreal.EditorAssetLibrary.load_blueprint_class(FACE_ANIM))
        r[name] = [path, len(comps.get(name, [])), bool(mesh)]
    for name, groom in GROOMS.items():
        asset = unreal.load_asset("%s/Grooms/%s" % (SRC, groom)) if groom else None
        binding = unreal.load_asset("%s/Grooms/%s_Binding" % (SRC, groom)) if groom else None
        for o in comps.get(name, []):
            o.set_editor_property("groom_asset", asset)
            o.set_editor_property("binding_asset", binding)
        r[name] = [groom, len(comps.get(name, [])), bool(asset), bool(binding)]
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    r["saved"] = unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sandro_giocatore.json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sandro_giocatore_errore.txt").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    unreal.SystemLibrary.quit_editor()
