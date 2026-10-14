"""Dresses a few crowd characters with the 1980s outfits (m80_vestiti_import.py) and photographs them in the crowd
square: the outfits' fit on their source body and, resized by the Creator, on other bodies. The characters are not
saved (preview only), unless M80_SALVA=1.
Env M80_CHI=Key1,Key2 (default the cast below). Out: Saved/Mazzarino80/Folla/Vestiti/Prova/<Key>_{fronte,retro,figura}.png
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

VECCHIA = ["AbitoNero", "Fazzoletto", "ScarpeDonna"]
VECCHIO = ["PantaloniVecchio", "CamiciaVecchio", "GiletVecchio", "GiaccaVecchio", "ScarpeVecchio"]
# key: (folder, garments, hide the hair: the headscarf covers it)
CAST = {
    "Anziana1": ("Folla", VECCHIA, True),
    "Anziana3": ("Folla", VECCHIA, True),
    "Anziano1": ("Folla", VECCHIO, False),
    "Anziano3": ("Folla", VECCHIO, False),
}


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
    for key, (folder, garments, no_hair) in CAST.items():
        if ONLY and key not in ONLY:
            continue
        entry = report.setdefault(key, {})
        c = unreal.load_asset("/Game/Mazzarino80/Personaggi/%s/MHC_%s" % (folder, key))
        SUB.try_add_object_to_edit(c)
        try:
            dress(c, garments, no_hair, entry)
        except Exception as e:  # noqa: BLE001 - report and go on with the others
            entry["error"] = repr(e)
        yield 60
        actor = SUB.spawn_meta_human_actor(c, True)
        yield 60
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
        SUB.remove_object_to_edit(c)
        unreal.SystemLibrary.collect_garbage()
        (OUT / "prova.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "prova_error.txt"))
