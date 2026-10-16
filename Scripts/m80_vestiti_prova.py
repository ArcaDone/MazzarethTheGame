"""Dresses a few crowd characters with the 1980s outfits (m80_vestiti_import.py) and photographs them in the crowd
square: the outfits' fit on their source body and, resized by the Creator, on other bodies. The characters are not
saved (preview only), unless M80_SALVA=1.
Env M80_CHI=Key1,Key2 (default the cast below). Out: Saved/Mazzarino80/Folla/Vestiti/Prova/<Key>_{fronte,retro,figura}.png
Env M80_FOLLA=1: the whole crowd in its final outfits (CAST_FOLLA).
Env M80_GRUPPO=1: instead, the cast and a few adults side by side in one photo (Gruppo.png), to compare heights.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_vestiti_prova.py -ForceLit
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Folla/Vestiti/Prova"
MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
WEAR = "/Game/Mazzarino80/Personaggi/Vestiti/%s/WI_M80_%s"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
EAL = unreal.EditorAssetLibrary
V = unreal.Vector
SAVE = os.environ.get("M80_SALVA") == "1"
ONLY = [k for k in os.environ.get("M80_CHI", "").split(",") if k]
GROUP = os.environ.get("M80_GRUPPO") == "1"

VECCHIA = ["AbitoNero", "Fazzoletto", "ScarpeDonna"]
VECCHIA_SCIALLE = ["AbitoNero", "Fazzoletto", "Scialle", "ScarpeDonna"]
VECCHIO = ["PantaloniVecchio", "CamiciaVecchio", "GiletVecchio", "GiaccaVecchio", "Coppola", "ScarpeVecchio"]
PASTORE = ["PantaloniVecchio", "CamiciaVecchio", "GiaccaVecchio", "Mantello", "Coppola", "ScarpeVecchio"]
UOMO_QUADRI = ["CamiciaQuadri", "Jeans", "ScarpeGinnastica"]
UOMO_MAGLIONE = ["Maglione", "PantaloniChiari", "Mocassini"]
UOMO_CANOTTIERA = ["Canottiera", "Jeans", "Mocassini"]
TUTA = ["TutaGiacca", "TutaPantaloni", "ScarpeGinnastica"]
DONNA_GONNA = ["Camicetta", "Gonna", "Cardigan", "ScarpeBasse"]
DONNA_FIORI = ["AbitoFiori", "ScarpeBasse"]
DONNA_JEANS = ["Camicetta", "JeansDonna", "ScarpeBasse"]
SANDRO_CLASSICO = ["CamiciaSandro", "CravattaSandro", "GiaccaSandro", "PantaloniSandro", "ScarpeSandro"]
SANDRO_BIANCO = ["CamiciaRosa", "Fondina", "GiaccaBianca", "PantaloniBianchi", "ScarpeChiare", "Orologio"]
SANDRO_FONDINA = ["CamiciaRosa", "Fondina", "PantaloniBianchi", "ScarpeChiare", "Orologio"]
# City Sample garments fitted on our bodies (Research/Mazzarino80/Blender/m80_citysample_vesti.py), for comparison.
SANDRO_CS = ["CS_CamiciaGiacca", "CS_Pantaloni", "CS_Stringate"]
DONNA_CS = ["CS_Camicetta", "CS_Gonna", "CS_Ballerine"]
# key: (folder, garments, hide the hair: the headscarf covers it)
CAST = {
    "Anziana1": ("Folla", VECCHIA_SCIALLE, True),
    "Anziana3": ("Folla", VECCHIA, True),
    "Anziano1": ("Folla", PASTORE, False),
    "Anziano3": ("Folla", VECCHIO, False),
    "Uomo2": ("Folla", UOMO_QUADRI, False),
    "Uomo1": ("Folla", UOMO_MAGLIONE, False),
    "Ragazzo2": ("Folla", UOMO_CANOTTIERA, False),
    "Ragazzo1": ("Folla", TUTA, False),
    "Donna1": ("Folla", DONNA_GONNA, False),
    "Donna2": ("Folla", DONNA_FIORI, False),
    "Ragazza1": ("Folla", DONNA_JEANS, False),
    "Sandro": ("Sandro", SANDRO_CLASSICO, False),
    "SandroBianco": ("Sandro", SANDRO_BIANCO, False),
    "SandroFondina": ("Sandro", SANDRO_FONDINA, False),
    "SandroCS": ("Sandro", SANDRO_CS, False),
    "Donna1CS": ("Folla", DONNA_CS, False),
    # Swapped shirts: is a wrong colour the garment's or the character's?
    "SandroCamicetta": ("Sandro", ["CS_Camicetta"], False),
    "Donna1Camicia": ("Folla", ["CS_CamiciaGiacca"], False),
}
# The whole crowd, final outfits (Env M80_FOLLA=1: dresses these instead of CAST; with M80_SALVA=1 they are saved
# for Scripts/m80_folla_build.py). City Sample garments (CS_*) plus our coppola, cloak, headscarf, shawl, black dress,
# flowered dress and tracksuit.
V_SCARPE, A_SCARPE = "CS_V_Scarpe", "CS_A_Scarpe"
CAST_FOLLA = {
    "Anziano1": ("Folla", ["CS_V_Camicia", "CS_V_PantaloniMarroni", "Mantello", "Coppola", V_SCARPE], False),
    "Anziano2": ("Folla", ["CS_V_Festa", "CS_V_Pantaloni", "Coppola", V_SCARPE], False),
    "Anziano3": ("Folla", ["CS_V_Giacca", "CS_V_PantaloniMarroni", "Coppola", V_SCARPE], False),
    "Anziano4": ("Folla", ["CS_V_Gilet", "CS_V_Pantaloni", "Coppola", V_SCARPE], False),
    "Anziana1": ("Folla", ["AbitoNero", "Fazzoletto", "Scialle", A_SCARPE], True),
    "Anziana2": ("Folla", ["CS_A_Camicia", "CS_A_Gonna", "Scialle", "Fazzoletto", A_SCARPE], True),
    "Anziana3": ("Folla", ["AbitoNero", "Fazzoletto", A_SCARPE], True),
    "Anziana4": ("Folla", ["CS_A_Dolcevita", "CS_A_Gonna", "Scialle", A_SCARPE], False),
    "Uomo1": ("Folla", ["CS_U_Maglione", "CS_U_Pantaloni", "CS_U_Mocassini"], False),
    "Uomo2": ("Folla", ["CS_U_Quadri", "CS_U_Jeans", "CS_U_Mocassini"], False),
    "Uomo3": ("Folla", ["CS_U_Completo", "CS_U_PantaloniGrigi", "CS_U_Stringate"], False),
    "Uomo4": ("Folla", ["CS_U_Dolcevita", "CS_U_PantaloniGrigi", "CS_U_Mocassini"], False),
    "Donna1": ("Folla", ["CS_Camicetta", "CS_Gonna", "CS_Ballerine"], False),
    "Donna2": ("Folla", ["AbitoFiori", "CS_Ballerine"], False),
    "Donna3": ("Folla", ["CS_D_Dolcevita", "CS_D_Pantaloni", "CS_D_Mocassini"], False),
    "Ragazzo1": ("Folla", ["TutaGiacca", "TutaPantaloni", "ScarpeGinnastica"], False),
    "Ragazzo2": ("Folla", ["CS_R_Maglione", "CS_R_Jeans", "ScarpeGinnastica"], False),
    "Ragazzo3": ("Folla", ["CS_R_Camicia", "CS_R_Jeans", "CS_U_Mocassini"], False),
    "Ragazza1": ("Folla", ["CS_RA_Giacchino", "CS_RA_Jeans", "CS_Ballerine"], False),
    "Ragazza2": ("Folla", ["CS_RA_Dolcevita", "CS_RA_Gonna", "CS_Ballerine"], False),
    "Ragazza3": ("Folla", ["CS_RA_Camicia", "CS_RA_Jeans", "CS_RA_Mocassini"], False),
}
if os.environ.get("M80_FOLLA") == "1":
    CAST = CAST_FOLLA
# Photo keys that are another outfit on a character: the character's asset name.
ASSET = {"SandroBianco": "Sandro", "SandroFondina": "Sandro", "SandroCS": "Sandro", "Donna1CS": "Donna1",
         "SandroCamicetta": "Sandro", "Donna1Camicia": "Donna1"}
# Adults beside the old for the group photo, as they are.
ADULTS = {"Uomo2": ("Folla", [], False), "Donna1": ("Folla", [], False)}


def dress(c, garments, no_hair, entry):
    coll = SUB.get_preview_collection(c)
    inst = coll.get_editor_property("default_instance")
    keys = []
    for g in garments:
        wi = unreal.load_asset(WEAR % (g, g))
        if wi is None:
            entry.setdefault("missing", []).append(g)
            continue
        res = coll.try_add_item_from_wardrobe_item("Outfits", wi)
        keys.append(res[1] if isinstance(res, tuple) else res)
    # The first replaces whatever the character wore (the Creator's default garment), the others are added.
    if keys:
        inst.set_single_slot_selection("Outfits", keys[0])
        entry["added"] = []
        for k in keys[1:]:
            sel = unreal.MetaHumanPipelineSlotSelection()
            sel.set_editor_property("slot_name", "Outfits")
            sel.set_editor_property("selected_item", k)
            entry["added"].append(inst.try_add_slot_selection(sel))
    if no_hair:
        inst.set_single_slot_selection("Hair", unreal.MetaHumanPaletteItemKey())
    SUB.on_edit_preview_collection(c)
    SUB.assemble_for_preview(c)


def portrait_lights(head, fwd, right):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for offset, candela in ((fwd * 150.0 + right * 90.0 + V(0, 0, 60), 30.0), (fwd * 150.0 - right * 110.0 + V(0, 0, 10), 10.0),
                            (fwd * -150.0 + V(0, 0, 80), 15.0)):
        light = eas.spawn_actor_from_class(unreal.PointLight, head + offset)
        comp = light.get_component_by_class(unreal.PointLightComponent)
        comp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        comp.set_intensity(candela)
        comp.set_attenuation_radius(700.0)


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP)
    yield 60
    unreal.SystemLibrary.execute_console_command(None, "r.TextureStreaming 0")
    spots = [a.get_actor_location() for a in unreal.GameplayStatics.get_all_actors_with_tag(
        unreal.EditorLevelLibrary.get_editor_world(), "M80Folla_Gioco")]
    spot = V(sum(p.x for p in spots) / len(spots), sum(p.y for p in spots) / len(spots), 0) if spots else V(0, 0, 0)
    yaw = unreal.MathLibrary.radians_to_degrees(unreal.MathLibrary.atan2(-spot.y, -spot.x)) - 90.0 if spots else 0.0
    lit = False
    cast = dict(ADULTS, **CAST) if GROUP else CAST
    group = []
    editing = []
    for key, (folder, garments, no_hair) in cast.items():
        if ONLY and key not in ONLY:
            continue
        entry = report.setdefault(key, {})
        c = unreal.load_asset("/Game/Mazzarino80/Personaggi/%s/MHC_%s" % (folder, ASSET.get(key, key)))
        SUB.try_add_object_to_edit(c)
        try:
            dress(c, garments, no_hair, entry)
        except Exception as e:  # noqa: BLE001 - report and go on with the others
            entry["error"] = repr(e)
        yield 60
        actor = SUB.spawn_meta_human_actor(c, True)
        yield 60
        if actor and GROUP:
            # In a row across the camera, 70 cm apart.
            actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            across = actor.get_actor_forward_vector() * -1.0
            actor.set_actor_location(spot + across * (70.0 * (len(group) - (len(cast) - 1) / 2.0)), False, True)
            group.append((key, actor))
            actor = None
        if actor:
            actor.set_actor_location(spot, False, True)
            actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            fwd, right = actor.get_actor_right_vector(), actor.get_actor_forward_vector() * -1.0
            if not lit:
                portrait_lights(spot + V(0, 0, 150), fwd, right)
                lit = True
            yield 120
            centre = spot + V(0, 0, 85)
            for label, eye, size in (("figura", centre + fwd * 300.0 + V(0, 0, 10), (500, 800)),
                                     ("retro", centre - fwd * 300.0 + V(0, 0, 10), (500, 800)),
                                     ("busto", spot + V(0, 0, 135) + fwd * 110.0 + right * 30.0, (600, 600))):
                target = centre if label != "busto" else spot + V(0, 0, 130)
                cap = m80_seq.ViewCapture(size[0], size[1], 40)
                cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, target), OUT / ("%s_%s.png" % (key, label)))
                cap.destroy()
                yield 5
            actor.destroy_actor()
        if SAVE:
            entry["saved"] = EAL.save_loaded_asset(c, False)
        if GROUP:
            editing.append(c)       # closing the character would empty its actor before the group photo
            continue
        SUB.remove_object_to_edit(c)
        unreal.SystemLibrary.collect_garbage()
        (OUT / "prova.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        yield 5
    if group:
        actor = group[0][1]
        fwd = actor.get_actor_right_vector()
        portrait_lights(spot + V(0, 0, 150), fwd, actor.get_actor_forward_vector() * -1.0)
        yield 120
        eye = spot + V(0, 0, 95) + fwd * 520.0
        cap = m80_seq.ViewCapture(1200, 700, 50)
        cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, spot + V(0, 0, 85)), OUT / "Gruppo.png")
        cap.destroy()
        report["gruppo"] = [k for k, _ in group]
        (OUT / "prova.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        for _, a in group:
            a.destroy_actor()
        for c in editing:
            SUB.remove_object_to_edit(c)
        yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "prova_error.txt"))
