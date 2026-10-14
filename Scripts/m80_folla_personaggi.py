"""The people of the crowd test and the protagonist, as editable 5.8 MetaHuman Characters (1980s Sicily).

Each one starts from a European-looking preset of the Creator (Optional content) and gets:
- a face of its own: the face model coefficients of two European presets mixed (weights per person);
- Sicilian features region by region, as the Creator's Blend and Move tools (M80EditorLibrary): the nose, jaw or
  eyes of another European preset, a stronger nose, low thick brows, deep-set eyes; sagging cheeks and jaw for the old;
- Mediterranean skin (olive, sun-tanned for the old men; not red) and, for the old, the aged skin textures
  (wrinkles, spots) of an old preset;
- dark eyes (mostly), height and build (old people short), hair, beard and moustache from the Creator's grooms, grey
  for the old. No children, as in GTA (the Creator has none: 135 cm at least, adult proportions);
- the neck fitted back on the new body (UM80EditorLibrary.ResetMetaHumanNeck).
Faces are only proposals until the user approves them: M80_RIG=1 asks Epic's auto-rigging service for the rig
(cloud, on the user's Epic account; joints and blend shapes for the protagonist, joints only for the crowd) and then
the 2k skin textures that building needs, with retries (the service answers 'Busy' to quick requests).
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

GREY = {"melanin": 0.45, "white": 0.78}     # old people's hair
DARK = {"melanin": 0.92, "white": 0.0}       # most Sicilians'
BROWN = {"melanin": 0.7, "white": 0.0}

# The Creator's face regions (blend and move handles, M80EditorLibrary.get_meta_human_face_regions; a left/right
# pair is moved and blended together through its first index). Face space: X sideways, Y forward, Z up (cm).
REGION = {"cranio": 0, "tempie": 1, "nuca": 3, "fronte": 4, "sopracciglia": 5, "occhi": 7, "zigomi": 9,
          "orecchie": 11, "naso": 13, "guance": 14, "bocca": 16, "mento": 17, "sottomento": 18, "mascella": 20}
# Mediterranean touches: a strong nose, low thick brows over deep-set eyes. (dy forward, dz up cm, scale)
NASO = {"naso": (0.5, -0.2, 1.08)}
SICULO = {"naso": (0.5, -0.2, 1.08), "sopracciglia": (0.3, -0.25, 1.0), "occhi": (-0.3, 0, 1.0)}
# Old age: cheeks, jaw and under-chin of the old European presets (sagging), at least partly.
VECCHIAIA = {"guance": [("Walter", 0.5)], "mascella": [("Lorenzo", 0.5)], "sottomento": [("Walter", 0.6)],
             "occhi": [("Lorenzo", 0.35)]}

# key: faces (preset, weight; only European-looking presets: the others read Latin American or Asian), region
# blends (region: [(preset, weight)]), region moves (region: (dy, dz, scale)), skin tone (lightness, redness:
# 0 light / 0 cool; olive = light-medium and not red), aged skin from a preset, eyes (temperature, brightness),
# body (masculine/feminine, fat, muscularity 0-1; height cm), grooms per slot (beard, moustache and fuzz left out
# are emptied), hair colour, rig type.
CAST = {
    "Sandro": {"facce": [("Orlando", 0.6), ("Bruce", 0.4)], "pelle": (0.42, 0.36), "occhi": (0.9, 0.12),
               "regioni": {"naso": [("Lorenzo", 0.5)], "mascella": [("Bruce", 0.5)], "mento": [("Bruce", 0.4)],
                           "zigomi": [("Lorenzo", 0.3)]},
               "ritocchi": {"naso": (0.6, -0.2, 1.1), "sopracciglia": (0.4, -0.35, 1.0), "occhi": (-0.4, 0, 1.0)},
               "corpo": (0.12, 0.3, 0.6, 180), "rig": "JOINTS_AND_BLEND_SHAPES", "cartella": "Sandro",
               "peli": {"Hair": "Hair/WI_Hair_L_MessyClumps", "Beard": "Beards/WI_Beard_S_Full",
                        "Mustache": "Mustaches/WI_Mustache_S_Full", "Eyebrows": "Eyebrows/WI_Eyebrows_M_Dense"},
               "colore": DARK},
    # Old women: short, heavy-set, hair up (a black headscarf comes with the clothes).
    "Anziana1": {"facce": [("Jelena", 0.6), ("Vivian", 0.4)], "pelle": (0.4, 0.34), "vecchia": "Grace",
                 "regioni": VECCHIAIA, "ritocchi": NASO,
                 "corpo": (0.85, 0.7, 0.2, 150), "peli": {"Hair": "Hair/WI_Hair_S_PulledBack"}, "colore": GREY},
    "Anziana2": {"facce": [("Vivian", 0.7), ("Jelena", 0.3)], "pelle": (0.44, 0.36), "vecchia": "Sook-ja",
                 "regioni": VECCHIAIA, "ritocchi": SICULO,
                 "corpo": (0.85, 0.55, 0.2, 147), "peli": {"Hair": "Hair/WI_Hair_S_UpdoBuns"}, "colore": GREY},
    "Anziana3": {"facce": [("Jelena", 0.5), ("Vivian", 0.5)], "pelle": (0.42, 0.36), "vecchia": "Sook-ja",
                 "regioni": dict(VECCHIAIA, naso=[("Lorenzo", 0.4)]),
                 "corpo": (0.85, 0.8, 0.2, 152), "peli": {"Hair": "Hair/WI_Hair_S_Updo"}, "colore": GREY},
    "Anziana4": {"facce": [("Vivian", 0.55), ("Walter", 0.45)], "pelle": (0.46, 0.37), "vecchia": "Grace",
                 "regioni": {"guance": [("Walter", 0.7)], "mascella": [("Lorenzo", 0.7)], "sottomento": [("Walter", 0.8)],
                             "occhi": [("Lorenzo", 0.5)], "bocca": [("Walter", 0.5)]}, "ritocchi": NASO,
                 "corpo": (0.85, 0.4, 0.2, 155), "peli": {"Hair": "Hair/WI_Hair_S_UpdoBraids"}, "colore": GREY},
    # Old men: short, sun-darkened, thinning hair, moustaches.
    "Anziano1": {"facce": [("Walter", 0.7), ("Lorenzo", 0.3)], "pelle": (0.5, 0.4), "vecchia": "Walter",
                 "ritocchi": NASO, "corpo": (0.15, 0.5, 0.3, 158), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_HairLoss", "Mustache": "Mustaches/WI_Mustache_S_Full",
                          "Eyebrows": "Eyebrows/WI_Eyebrows_L_Scraggly"}},
    "Anziano2": {"facce": [("Lorenzo", 0.6), ("Bruce", 0.4)], "pelle": (0.48, 0.38), "vecchia": "Lorenzo",
                 "ritocchi": SICULO, "corpo": (0.15, 0.3, 0.25, 160), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_RecedeMessy", "Beard": "Beards/WI_Beard_S_Stubble",
                          "Eyebrows": "Eyebrows/WI_Eyebrows_M_Unruly"}},
    "Anziano3": {"facce": [("Bruce", 0.5), ("Walter", 0.5)], "pelle": (0.52, 0.42), "vecchia": "Walter",
                 "corpo": (0.15, 0.7, 0.3, 162), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_BaldingStubble", "Mustache": "Mustaches/WI_Mustache_L_Full",
                          "Eyebrows": "Eyebrows/WI_Eyebrows_M_Dense"}},
    "Anziano4": {"facce": [("Lorenzo", 0.5), ("Walter", 0.5)], "pelle": (0.5, 0.4), "vecchia": "Lorenzo",
                 "regioni": {"naso": [("Bruce", 0.5)], "mascella": [("Bruce", 0.4)]}, "ritocchi": SICULO,
                 "corpo": (0.15, 0.55, 0.3, 156), "colore": GREY,
                 "peli": {"Hair": "Hair/WI_Hair_S_Clean", "Mustache": "Mustaches/WI_Mustache_S_Horseshoe",
                          "Eyebrows": "Eyebrows/WI_Eyebrows_L_Scraggly"}},
    # Men, 35-55: big 70s-80s moustaches, slicked or side-parted hair.
    "Uomo1": {"facce": [("Bruce", 0.6), ("Orlando", 0.4)], "pelle": (0.44, 0.38), "corpo": (0.12, 0.6, 0.45, 172),
              "regioni": {"naso": [("Lorenzo", 0.5)]}, "ritocchi": SICULO, "colore": DARK,
              "peli": {"Hair": "Hair/WI_Hair_S_SlickBack", "Mustache": "Mustaches/WI_Mustache_L_Full",
                       "Eyebrows": "Eyebrows/WI_Eyebrows_M_Full"}},
    "Uomo2": {"facce": [("Orlando", 0.6), ("Bruce", 0.4)], "pelle": (0.4, 0.36), "corpo": (0.12, 0.4, 0.5, 175),
              "regioni": {"mascella": [("Bruce", 0.5)]}, "ritocchi": NASO, "colore": DARK,
              "peli": {"Hair": "Hair/WI_Hair_S_SideSweptFringe", "Mustache": "Mustaches/WI_Mustache_S_Full",
                       "Eyebrows": "Eyebrows/WI_Eyebrows_M_Thick"}},
    "Uomo3": {"facce": [("Orlando", 0.5), ("Lorenzo", 0.5)], "pelle": (0.42, 0.36), "corpo": (0.12, 0.45, 0.5, 170),
              "regioni": {"naso": [("Lorenzo", 0.6)], "zigomi": [("Bruce", 0.4)]}, "ritocchi": SICULO, "colore": DARK,
              "peli": {"Hair": "Hair/WI_Hair_S_Casual", "Beard": "Beards/WI_Beard_S_Stubble",
                       "Mustache": "Mustaches/WI_Mustache_S_Stubble", "Eyebrows": "Eyebrows/WI_Eyebrows_M_Dense"}},
    "Uomo4": {"facce": [("Bruce", 0.6), ("Orlando", 0.4)], "pelle": (0.4, 0.36), "corpo": (0.12, 0.3, 0.5, 178),
              "colore": BROWN, "peli": {"Hair": "Hair/WI_Hair_S_RecedeMessy", "Beard": "Beards/WI_Beard_S_Uneven",
                                        "Eyebrows": "Eyebrows/WI_Eyebrows_M_Natural"}},
    # Women, 30-50: permed bobs and layered 80s hair.
    "Donna1": {"facce": [("Jelena", 0.6), ("Vivian", 0.4)], "pelle": (0.38, 0.34), "corpo": (0.85, 0.45, 0.3, 162),
               "regioni": {"naso": [("Lorenzo", 0.25)]}, "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_M_BobCurly"}},
    "Donna2": {"facce": [("Vivian", 0.7), ("Jelena", 0.3)], "pelle": (0.36, 0.34), "corpo": (0.85, 0.55, 0.3, 160),
               "ritocchi": NASO, "colore": BROWN, "peli": {"Hair": "Hair/WI_Hair_M_Layered"}},
    "Donna3": {"facce": [("Jelena", 0.4), ("Vivian", 0.6)], "pelle": (0.4, 0.35), "corpo": (0.85, 0.35, 0.3, 165),
               "regioni": {"naso": [("Bruce", 0.25)]}, "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_M_BobMessy"}},
    # Young, 16-22.
    "Ragazzo1": {"facce": [("Orlando", 0.8), ("Bruce", 0.2)], "pelle": (0.4, 0.36), "corpo": (0.15, 0.25, 0.45, 175),
                 "regioni": {"naso": [("Lorenzo", 0.4)]}, "ritocchi": SICULO, "colore": DARK,
                 "peli": {"Hair": "Hair/WI_Hair_M_Layered", "Eyebrows": "Eyebrows/WI_Eyebrows_M_Thick"}},
    "Ragazzo2": {"facce": [("Orlando", 0.7), ("Lorenzo", 0.3)], "pelle": (0.42, 0.36), "corpo": (0.15, 0.25, 0.4, 172),
                 "regioni": {"mascella": [("Bruce", 0.3)]}, "ritocchi": NASO, "colore": DARK,
                 "peli": {"Hair": "Hair/WI_Hair_S_Messy", "Eyebrows": "Eyebrows/WI_Eyebrows_M_Dense"}},
    "Ragazzo3": {"facce": [("Orlando", 0.9), ("Bruce", 0.1)], "pelle": (0.38, 0.35), "corpo": (0.15, 0.2, 0.5, 178),
                 "regioni": {"naso": [("Walter", 0.4)], "occhi": [("Bruce", 0.3)]}, "colore": DARK,
                 "peli": {"Hair": "Hair/WI_Hair_L_MessyClumps", "Peachfuzz": "Peachfuzz/WI_Peachfuzz_M_Thin",
                          "Eyebrows": "Eyebrows/WI_Eyebrows_M_Natural"}},
    "Ragazza1": {"facce": [("Jelena", 0.7), ("Vivian", 0.3)], "pelle": (0.36, 0.34), "corpo": (0.9, 0.3, 0.3, 163),
                 "colore": DARK, "peli": {"Hair": "Hair/WI_Hair_M_BobCurly"}},
    "Ragazza2": {"facce": [("Jelena", 0.5), ("Vivian", 0.5)], "pelle": (0.38, 0.34), "corpo": (0.9, 0.3, 0.3, 160),
                 "regioni": {"naso": [("Lorenzo", 0.2)]}, "colore": BROWN, "peli": {"Hair": "Hair/WI_Hair_L_Straight"}},
    "Ragazza3": {"facce": [("Vivian", 0.6), ("Jelena", 0.4)], "pelle": (0.4, 0.35), "corpo": (0.9, 0.35, 0.3, 165),
                 "ritocchi": {"sopracciglia": (0.2, -0.2, 1.0)}, "colore": DARK,
                 "peli": {"Hair": "Hair/WI_Hair_S_LowPonytail"}},
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


def shape_regions(c, cfg, cache, entry):
    """Region by region, as the Creator's Blend and Move tools: features of other presets, then small moves."""
    lib = unreal.M80EditorLibrary
    entry["regions"] = {}
    for region, sources in cfg.get("regioni", {}).items():
        for name, _ in sources:
            coefficients(name, cache)
        entry["regions"][region] = lib.blend_meta_human_face_region(
            c, REGION[region], [cache[n][1] for n, _ in sources], [w for _, w in sources], False)
    for region, (dy, dz, scale) in cfg.get("ritocchi", {}).items():
        moved = lib.move_meta_human_face_region(c, REGION[region], V(0, dy, dz), scale)
        entry["regions"]["move_" + region] = [round(moved.x, 2), round(moved.y, 2), round(moved.z, 2)]


def set_grooms(c, cfg, entry):
    # Edits go to the preview collection and are handed back to the character (as the Creator's own UI does).
    coll = SUB.get_preview_collection(c)
    inst = coll.get_editor_property("default_instance")
    entry["grooms"] = {}
    # The duplicated preset may carry a beard or fuzz of its own: those slots are emptied unless the cast fills them.
    for slot in ("Beard", "Mustache", "Peachfuzz"):
        if slot not in cfg.get("peli", {}):
            inst.set_single_slot_selection(slot, unreal.MetaHumanPaletteItemKey())
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
        shape_regions(c, cfg, cache, entry)
        SUB.commit_face_state(c)
        entry["body"] = set_body(c, *cfg["corpo"])
        SUB.commit_face_state(c)
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
    entry["saved"] = EAL.save_loaded_asset(c, False)
    report[key] = entry
    return c


def rig(c, cfg, entry):
    """Epic's cloud services, until the character can be built: the face rig, then the high resolution textures
    (2k, the Creator's default) that assembling needs. The rig service answers 'Busy' to requests too close
    together and the local DNS sometimes fails: each step is retried after a pause (yields = frames to wait)."""
    status = unreal.M80EditorLibrary.get_meta_human_build_status
    entry["tries"] = []
    for attempt in range(6):
        why = status(c)
        entry["tries"].append(why)
        if not why:
            break
        if "not rigged" in why:
            params = unreal.MetaHumanCharacterAutoRiggingRequestParams()
            params.set_editor_property("rig_type", getattr(unreal.MetaHumanRigType, cfg.get("rig", "JOINTS_ONLY")))
            params.set_editor_property("blocking", True)
            params.set_editor_property("report_progress", False)
            SUB.request_auto_rigging(c, params)
        elif "textures" in why.lower():
            params = unreal.MetaHumanCharacterTextureRequestParams()
            params.set_editor_property("blocking", True)
            params.set_editor_property("report_progress", False)
            SUB.request_texture_sources(c, params)
        if status(c) == why:
            yield 300 + 300 * attempt
    entry["build_status"] = status(c) or "ok"
    entry["can_build"] = SUB.can_build_meta_human(c, False)
    entry["saved"] = EAL.save_loaded_asset(c, False)


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
    # Portraits in the free corner of the square (the old children's corner), away from tables and chairs, with the
    # camera on the square's side.
    spots = [a.get_actor_location() for a in unreal.GameplayStatics.get_all_actors_with_tag(
        unreal.EditorLevelLibrary.get_editor_world(), "M80Folla_Gioco")]
    spot = V(sum(p.x for p in spots) / len(spots), sum(p.y for p in spots) / len(spots), 0) if spots else V(0, 0, 0)
    yaw = unreal.MathLibrary.radians_to_degrees(unreal.MathLibrary.atan2(-spot.y, -spot.x)) - 90.0 if spots else 0.0
    for i, (key, cfg) in enumerate(CAST.items()):
        if ONLY and key not in ONLY:
            continue
        try:
            c = make(key, cfg, cache, report)
        except Exception as e:  # noqa: BLE001 - one broken character must not stop the others
            report[key] = {"error": repr(e)}
            continue
        if RIG:
            yield from rig(c, cfg, report[key])
        yield 20
        actor = SUB.spawn_meta_human_actor(c, True)
        yield 30
        if actor:
            actor.set_actor_location(spot, False, True)
            # The face looks along the actor's right vector: turned to the middle of the square.
            actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            head = head_of(actor) or spot + V(0, 0, 160)
            fwd, right = actor.get_actor_right_vector(), actor.get_actor_forward_vector() * -1.0
            if not lit:
                portrait_lights(spot + V(0, 0, 160), fwd, right)
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
