"""The people of the crowd test and the protagonist, as editable 5.8 MetaHuman Characters (1980s Sicily).

Each one starts from a European-looking preset of the Creator (Optional content) and gets:
- a face of its own: the face model coefficients of two European presets mixed (weights per person);
- Mediterranean skin (olive to sun-tanned) and, for the old, the aged skin textures (wrinkles, spots) of an old preset;
- dark eyes (mostly), height and build (old people short), hair, beard and moustache from the Creator's grooms, grey
  for the old. No children, as in GTA (the Creator has none: 135 cm at least, adult proportions);
- the neck fitted back on the new body (UM80EditorLibrary.ResetMetaHumanNeck).
Faces are only proposals until the user approves them: M80_RIG=1 asks Epic's auto-rigging service for the rig
(cloud, on the user's Epic account; joints and blend shapes for the protagonist, joints only for the crowd).
Env: M80_CHI=Key1,Key2 (default all), M80_RIFAI=1 remakes existing characters from scratch, M80_RIG=1.
Out: /Game/Mazzarino80/Personaggi/{Sandro/MHC_Sandro, Folla/MHC_<Key>}; portraits in
Saved/Mazzarino80/Personaggi/Folla/<Key>_{fronte,figura}.png; report personaggi.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_personaggi.py -ForceLit
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Personaggi/Folla"
MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
PRESETS = "/MetaHumanCharacter/Optional/Presets/"
GROOMS = "/MetaHumanCharacter/Optional/Grooms/Bindings/"
ONLY = [k for k in os.environ.get("M80_CHI", "").split(",") if k]
REMAKE = os.environ.get("M80_RIFAI") == "1"
RIG = os.environ.get("M80_RIG") == "1"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
EAL = unreal.EditorAssetLibrary
V = unreal.Vector

GREY = {"melanin": 0.55, "white": 0.62}     # old people's hair
DARK = {"melanin": 0.92, "white": 0.0}       # most Sicilians'
BROWN = {"melanin": 0.7, "white": 0.0}

# key: faces (preset, weight), skin tone (lightness, redness: 0 light / 0 cool), aged skin from a preset, eyes
# (temperature, brightness), body (masculine/feminine, fat, muscularity 0-1; height cm), grooms per slot, hair colour,
# rig type.
CAST = {
    "Sandro": {"facce": [("Victor", 0.5), ("Orlando", 0.5)], "pelle": (0.56, 0.55), "occhi": (0.9, 0.12),
               "corpo": (0.12, 0.3, 0.6, 180), "rig": "JOINTS_AND_BLEND_SHAPES", "cartella": "Sandro",
               "peli": {"Hair": "Hair/WI_Hair_L_MessyClumps", "Beard": "Beards/WI_Beard_S_Full",
                        "Mustache": "Mustaches/WI_Mustache_S_Full", "Eyebrows": "Eyebrows/WI_Eyebrows_M_Thick"},
               "colore": DARK},
    # Old women: short, heavy-set, hair up (a black headscarf comes with the clothes).
    "Anziana1": {"facce": [("Jelena", 0.6), ("Vivian", 0.4)], "pelle": (0.48, 0.42), "vecchia": "Grace",
                 "corpo": (0.85, 0.7, 0.2, 150), "peli": {"Hair": "Hair/WI_Hair_S_PulledBack"}, "colore": GREY},
    "Anziana2": {"facce": [("Vivian", 0.5), ("Sunita", 0.5)], "pelle": (0.52, 0.4), "vecchia": "Sook-ja",
                 "corpo": (0.85, 0.55, 0.2, 147), "peli": {"Hair": "Hair/WI_Hair_S_UpdoBuns"}, "colore": GREY},
    "Anziana3": {"facce": [("Celeste", 0.5), ("Jelena", 0.5)], "pelle": (0.58, 0.45), "vecchia": "Lani",
                 "corpo": (0.85, 0.8, 0.2, 152), "peli": {"Hair": "Hair/WI_Hair_M_BobSlick"}, "colore": GREY},
    "Anziana4": {"facce": [("Sunita", 0.6), ("Vivian", 0.4)], "pelle": (0.5, 0.38), "vecchia": "Grace",
                 "corpo": (0.85, 0.4, 0.2, 155), "peli": {"Hair": "Hair/WI_Hair_S_LowPonytail"}, "colore": GREY},
    # Old men: short, sun-darkened, thinning hair, moustaches.
    "Anziano1": {"facce": [("Walter", 0.7), ("Lorenzo", 0.3)], "pelle": (0.6, 0.5), "vecchia": "Walter",
                 "corpo": (0.15, 0.5, 0.3, 158), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_HairLoss", "Mustache": "Mustaches/WI_Mustache_S_Full"}},
    "Anziano2": {"facce": [("Lorenzo", 0.6), ("Bruce", 0.4)], "pelle": (0.58, 0.45), "vecchia": "Lorenzo",
                 "corpo": (0.15, 0.3, 0.25, 160), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_RecedeMessy", "Beard": "Beards/WI_Beard_S_Stubble"}},
    "Anziano3": {"facce": [("Bruce", 0.5), ("Walter", 0.5)], "pelle": (0.62, 0.5), "vecchia": "Walter",
                 "corpo": (0.15, 0.7, 0.3, 162), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_BaldingStubble", "Mustache": "Mustaches/WI_Mustache_L_Full"}},
    "Anziano4": {"facce": [("Lorenzo", 0.5), ("Jorge", 0.5)], "pelle": (0.6, 0.48), "vecchia": "Lorenzo",
                 "corpo": (0.15, 0.55, 0.3, 156), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_Clean", "Mustache": "Mustaches/WI_Mustache_S_PencilThin"}},
    # Men, 35-55: big 70s-80s moustaches, slicked or side-parted hair.
    "Uomo1": {"facce": [("Jorge", 0.6), ("Victor", 0.4)], "pelle": (0.55, 0.5), "corpo": (0.12, 0.6, 0.45, 172),
              "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_S_SlickBack", "Mustache": "Mustaches/WI_Mustache_L_Full"}},
    "Uomo2": {"facce": [("Orlando", 0.6), ("Bruce", 0.4)], "pelle": (0.5, 0.48), "corpo": (0.12, 0.4, 0.5, 175),
              "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_S_SideSweptFringe", "Mustache": "Mustaches/WI_Mustache_S_Full"}},
    "Uomo3": {"facce": [("Victor", 0.7), ("Jorge", 0.3)], "pelle": (0.6, 0.5), "corpo": (0.12, 0.45, 0.5, 170),
              "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_S_Casual", "Beard": "Beards/WI_Beard_S_Stubble"}},
    "Uomo4": {"facce": [("Bruce", 0.6), ("Orlando", 0.4)], "pelle": (0.52, 0.45), "corpo": (0.12, 0.3, 0.5, 178),
              "colore": BROWN, "peli": {"Hair": "Hair/WI_Hair_S_RecedeMessy", "Beard": "Beards/WI_Beard_S_Uneven"}},
    # Women, 30-50: permed bobs and layered 80s hair.
    "Donna1": {"facce": [("Jelena", 0.5), ("Sunita", 0.5)], "pelle": (0.45, 0.42), "corpo": (0.85, 0.45, 0.3, 162),
               "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_M_BobCurly"}},
    "Donna2": {"facce": [("Vivian", 0.6), ("Celeste", 0.4)], "pelle": (0.48, 0.45), "corpo": (0.85, 0.55, 0.3, 160),
               "colore": BROWN, "peli": {"Hair": "Hair/WI_Hair_M_Layered"}},
    "Donna3": {"facce": [("Sunita", 0.7), ("Jelena", 0.3)], "pelle": (0.5, 0.4), "corpo": (0.85, 0.35, 0.3, 165),
               "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_L_StraightBangs"}},
    # Young, 16-22.
    "Ragazzo1": {"facce": [("Trey", 0.5), ("Orlando", 0.5)], "pelle": (0.5, 0.5), "corpo": (0.15, 0.25, 0.45, 175),
                 "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_M_Layered"}},
    "Ragazzo2": {"facce": [("Victor", 0.5), ("Trey", 0.5)], "pelle": (0.55, 0.5), "corpo": (0.15, 0.25, 0.4, 172),
                 "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_S_Messy"}},
    "Ragazzo3": {"facce": [("Orlando", 0.7), ("Victor", 0.3)], "pelle": (0.52, 0.48), "corpo": (0.15, 0.2, 0.5, 178),
                 "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_L_MessyClumps", "Peachfuzz": "Peachfuzz/WI_Peachfuzz_M_Thin"}},
    "Ragazza1": {"facce": [("Jelena", 0.7), ("Vivian", 0.3)], "pelle": (0.45, 0.45), "corpo": (0.9, 0.3, 0.3, 163),
                 "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_M_BobCurly"}},
    "Ragazza2": {"facce": [("Jelena", 0.6), ("Sunita", 0.4)], "pelle": (0.5, 0.42), "corpo": (0.9, 0.3, 0.3, 160),
                 "colore": BROWN, "peli": {"Hair": "Hair/WI_Hair_L_Straight"}},
    "Ragazza3": {"facce": [("Vivian", 0.5), ("Jelena", 0.5)], "pelle": (0.47, 0.44), "corpo": (0.9, 0.35, 0.3, 165),
                 "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_S_LowPonytail"}},
}


def asset_path(key, cfg):
    folder = cfg.get("cartella", "Folla")
    return "/Game/Mazzarino80/Personaggi/%s/MHC_%s" % (folder, key)


def coefficients(name, cache):
    if name not in cache:
        p = unreal.load_asset(PRESETS + name)
        SUB.try_add_object_to_edit(p)
        cache[name] = (list(SUB.get_face_model_coefficients(p)), p)
    return cache[name][0]


def set_body(c, mf, fat, muscle, height):
    """As Epic's MetaHuman Generator toolset: 0-1 values mapped onto each constraint's own range."""
    # The loop's items are copies of the returned array's structs: the edited copies are what goes back.
    constraints = list(SUB.get_body_constraints(c, False))
    for k in constraints:
        name = str(k.get_editor_property("name"))
        lo, hi = k.get_editor_property("min_measurement"), k.get_editor_property("max_measurement")
        value = {"Masculine/Feminine": mf, "Fat": fat, "Muscularity": muscle}.get(name)
        if name == "Height":
            k.set_editor_property("is_active", True)
            k.set_editor_property("target_measurement", max(lo, min(hi, height)))
        elif value is not None:
            k.set_editor_property("is_active", True)
            k.set_editor_property("target_measurement", lo + (hi - lo) * value)
    SUB.set_body_constraints(c, constraints)
    SUB.commit_body_state(c)
    after = {str(k.get_editor_property("name")): round(k.get_editor_property("target_measurement"), 2)
             for k in SUB.get_body_constraints(c, False)
             if str(k.get_editor_property("name")) in ("Height", "Fat", "Masculine/Feminine", "Muscularity")}
    return {"neck": unreal.M80EditorLibrary.reset_meta_human_neck(c), "fixed_body_type": c.get_editor_property("fixed_body_type"),
            "after": after}


def set_grooms(c, cfg, entry):
    # Edits go to the preview collection and are handed back to the character (as the Creator's own UI does).
    coll = SUB.get_preview_collection(c)
    inst = coll.get_editor_property("default_instance")
    entry["grooms"] = {}
    for slot, item in cfg.get("peli", {}).items():
        wi = unreal.load_asset(GROOMS + item)
        if wi is None:
            entry["grooms"][slot] = "missing " + item
            continue
        res = coll.try_add_item_from_wardrobe_item(slot, wi)
        key = res[1] if isinstance(res, tuple) else res
        inst.set_single_slot_selection(slot, key)
        entry["grooms"][slot] = item
    # The grooms' parameters exist once the instance is assembled.
    SUB.on_edit_preview_collection(c)
    SUB.assemble_for_preview(c)
    # Hair colour on every groom of the character (hair, brows, beard): melanin and greying.
    colour = cfg.get("colore", DARK)
    entry["hair_params"] = {}
    paths = list(inst.get_instance_parameter_item_paths())
    entry["param_paths"] = [str(p) for p in paths]
    for path in paths:
        for p in inst.get_instance_parameters(path):
            try:
                n = str(p.get_editor_property("name"))
            except Exception:  # noqa: BLE001 - field name unknown: list what the struct has
                entry["param_fields"] = [x for x in dir(p) if not x.startswith("_")]
                continue
            low = n.lower()
            if "melanin" in low and "random" not in low:
                entry["hair_params"][n] = p.set_float(colour["melanin"])
            elif "white" in low or "grey" in low or "gray" in low:
                entry["hair_params"][n] = p.set_float(colour["white"])
    SUB.on_edit_preview_collection(c)
    SUB.assemble_for_preview(c)


def make(key, cfg, cache, report):
    path = asset_path(key, cfg)
    entry = {"path": path}
    if REMAKE and EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    fresh = not EAL.does_asset_exist(path)
    base = cfg["facce"][0][0]
    if fresh:
        EAL.duplicate_asset(PRESETS + base, path)
    c = unreal.load_asset(path)
    entry["added"] = SUB.try_add_object_to_edit(c)
    if fresh:
        # Face: the presets' coefficients mixed by weight.
        mix = None
        for name, w in cfg["facce"]:
            co = coefficients(name, cache)
            mix = [w * x for x in co] if mix is None else [a + w * x for a, x in zip(mix, co)]
        SUB.set_face_model_coefficients(c, mix)

        SUB.commit_face_state(c)
        entry["body"] = set_body(c, *cfg["corpo"])
        skin = c.get_editor_property("skin_settings")
        props = skin.get_editor_property("skin")
        props.set_editor_property("u", cfg["pelle"][0])
        props.set_editor_property("v", cfg["pelle"][1])
        if cfg.get("vecchia"):
            old = unreal.load_asset(PRESETS + cfg["vecchia"]).get_editor_property("skin_settings").get_editor_property("skin")
            props.set_editor_property("face_texture_index", old.get_editor_property("face_texture_index"))
            props.set_editor_property("body_texture_index", old.get_editor_property("body_texture_index"))
        skin.set_editor_property("skin", props)
        SUB.commit_skin_settings(c, skin)
        eyes = c.get_editor_property("eyes_settings")
        t, b = cfg.get("occhi", (0.88, 0.15))
        for side in ("eye_left", "eye_right"):
            iris = eyes.get_editor_property(side).get_editor_property("iris")
            for k in ("primary_color_u", "secondary_color_u"):
                iris.set_editor_property(k, t)
            for k in ("primary_color_v", "secondary_color_v"):
                iris.set_editor_property(k, b)
            e = eyes.get_editor_property(side)
            e.set_editor_property("iris", iris)
            eyes.set_editor_property(side, e)
        SUB.commit_eyes_settings(c, eyes)
        set_grooms(c, cfg, entry)
    if RIG and not SUB.can_build_meta_human(c, False):
        params = unreal.MetaHumanCharacterAutoRiggingRequestParams()
        params.set_editor_property("rig_type", getattr(unreal.MetaHumanRigType, cfg.get("rig", "JOINTS_ONLY")))
        params.set_editor_property("blocking", True)
        params.set_editor_property("report_progress", False)
        SUB.request_auto_rigging(c, params)
    entry["can_build"] = SUB.can_build_meta_human(c, False)
    entry["saved"] = EAL.save_loaded_asset(c, False)
    report[key] = entry
    return c


def portrait_lights(head, fwd, right):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for offset, candela in ((fwd * 120.0 + right * 80.0 + V(0, 0, 60), 25.0), (fwd * 120.0 - right * 100.0 + V(0, 0, 10), 8.0)):
        light = eas.spawn_actor_from_class(unreal.PointLight, head + offset)
        comp = light.get_component_by_class(unreal.PointLightComponent)
        comp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        comp.set_intensity(candela)
        comp.set_attenuation_radius(600.0)


def head_of(actor):
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if comp.does_socket_exist("head"):
            return comp.get_socket_location("head")
    return None


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP)
    yield 60
    unreal.SystemLibrary.execute_console_command(None, "r.TextureStreaming 0")
    cache = {}
    lit = False
    for i, (key, cfg) in enumerate(CAST.items()):
        if ONLY and key not in ONLY:
            continue
        try:
            c = make(key, cfg, cache, report)
        except Exception as e:  # noqa: BLE001 - one broken character must not stop the others
            report[key] = {"error": repr(e)}
            continue
        yield 20
        actor = SUB.spawn_meta_human_actor(c, True)
        yield 30
        if actor:
            actor.set_actor_location(V(0, 0, 0), False, True)
            actor.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
            head = head_of(actor) or V(0, 0, 160)
            fwd, right = actor.get_actor_right_vector(), actor.get_actor_forward_vector() * -1.0
            if not lit:
                portrait_lights(V(0, 0, 160), fwd, right)
                lit = True
            look = head + V(0, 0, 3)
            m80_seq.set_view(look + fwd * 60.0, unreal.MathLibrary.find_look_at_rotation(look + fwd * 60.0, look))
            yield 150
            cap = m80_seq.ViewCapture(700, 700, 28)
            cap.capture(look + fwd * 60.0, unreal.MathLibrary.find_look_at_rotation(look + fwd * 60.0, look), OUT / ("%s_fronte.png" % key))
            cap.destroy()
            eye = head + fwd * 320.0 + V(0, 0, -60)
            cap = m80_seq.ViewCapture(500, 800, 40)
            cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, head + V(0, 0, -80)), OUT / ("%s_figura.png" % key))
            cap.destroy()
            report[key]["height_head_cm"] = round(head.z, 1)
            actor.destroy_actor()
        SUB.remove_object_to_edit(c)
        unreal.SystemLibrary.collect_garbage()
        (OUT / "personaggi.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        yield 5
    for _, p in cache.values():
        SUB.remove_object_to_edit(p)
    (OUT / "personaggi.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "personaggi_error.txt"))
