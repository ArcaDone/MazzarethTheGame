"""Face photos of the 5.8 MetaHuman Creator presets (Optional content), front and three-quarter, in the crowd test
square's afternoon light: to choose the faces the protagonist and the townspeople start from. Also lists how a
character's wardrobe is reached from Python (internal collection, slots, default instance). Nothing is saved.
Out: Saved/Mazzarino80/Personaggi/Preset/<Name>_{fronte,tre_quarti}.png, preset_foto.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_preset_foto.py -ForceLit
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Personaggi/Preset"
MAP = "/Game/Mazzarino80/Personaggi/Maps/L_M80_ProvaFolla"
PRESETS = "/MetaHumanCharacter/Optional/Presets"
ONLY = [k for k in os.environ.get("M80_PRESET", "").split(",") if k]
V = unreal.Vector


def head_of(actor):
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if comp.does_socket_exist("head"):
            return comp.get_socket_location("head")
    return None


def portrait_lights(head, fwd, right):
    """A key light high on one side of the face and a weaker fill on the other: the square is in shade at 15:00."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    out = []
    for offset, candela in ((fwd * 120.0 + right * 80.0 + V(0, 0, 60), 25.0), (fwd * 120.0 - right * 100.0 + V(0, 0, 10), 8.0)):
        light = eas.spawn_actor_from_class(unreal.PointLight, head + offset)
        comp = light.get_component_by_class(unreal.PointLightComponent)
        comp.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        comp.set_intensity(candela)
        comp.set_attenuation_radius(600.0)
        out.append(light)
    return out


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"presets": {}}
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP)
    yield 60
    unreal.SystemLibrary.execute_console_command(None, "r.TextureStreaming 0")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    names = sorted(str(a.asset_name) for a in reg.get_assets_by_path(PRESETS, recursive=False)
                   if str(a.asset_class_path.asset_name) == "MetaHumanCharacter")
    lights = None
    for i, name in enumerate(names):
        if ONLY and name not in ONLY:
            continue
        c = unreal.load_asset(PRESETS + "/" + name)
        entry = {"added": subsystem.try_add_object_to_edit(c)}
        if i == 0:
            coll = c.get_editor_property("internal_collection")
            entry["collection_api"] = [n for n in dir(coll) if not n.startswith("_")]
            try:
                entry["slots"] = [str(s) for s in unreal.MetaHumanCollectionBlueprintLibrary.get_slot_names(coll)]
            except Exception as e:  # noqa: BLE001
                entry["slots_error"] = str(e)
        actor = subsystem.spawn_meta_human_actor(c, True)
        yield 30
        if not actor:
            entry["error"] = "no actor"
            report["presets"][name] = entry
            continue
        actor.set_actor_location(V(0, 0, 0), False, True)
        actor.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
        # Shaders of a new face compile on first sight: look at it a while before the photo.
        head = head_of(actor) or V(0, 0, 165)
        # The MetaHuman meshes face the actor's +Y (its right vector), not its forward.
        fwd = actor.get_actor_right_vector()
        right = actor.get_actor_forward_vector() * -1.0
        if lights is None:
            lights = portrait_lights(head, fwd, right)
        entry["head"] = [head.x, head.y, head.z]
        entry["components"] = [comp.get_name() for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent)]
        look = head + V(0, 0, 3)
        eye = look + fwd * 60.0
        m80_seq.set_view(eye, unreal.MathLibrary.find_look_at_rotation(eye, look))
        yield 240 if i == 0 else 90
        for shot, offset in (("fronte", fwd * 60.0), ("tre_quarti", fwd * 45.0 + right * 40.0)):
            eye = look + offset
            cap = m80_seq.ViewCapture(700, 700, 28)
            cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, look), OUT / ("%s_%s.png" % (name, shot)))
            cap.destroy()
            yield 3
        # Whole figure, to see height and build.
        eye = head + fwd * 320.0 + V(0, 0, -60)
        cap = m80_seq.ViewCapture(500, 800, 40)
        cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, head + V(0, 0, -80)), OUT / ("%s_figura.png" % name))
        cap.destroy()
        actor.destroy_actor()
        subsystem.remove_object_to_edit(c)
        report["presets"][name] = entry
        unreal.SystemLibrary.collect_garbage()
        yield 5
    (OUT / "preset_foto.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "preset_foto_error.txt"))
