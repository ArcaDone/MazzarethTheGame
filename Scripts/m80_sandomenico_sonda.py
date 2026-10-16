"""Probe of the area of M80_Recuperato_A_SanDomenico, where the Ape loses the player (the camera stays, the Ape
coasts on alone) and of the road slab 3_Lastra_lavica_secondaria2 that is not seen in Play: every actor within
RADIUS with what can take the player (pawns that auto possess, cameras that auto activate, level sequences,
volumes), and the slab's state (package, spatial loading, data layers, mesh triangles, visibility, collision).
Nothing is saved.
Out: Saved/Mazzarino80/SanDomenico/sonda.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_sandomenico_sonda.py
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/SanDomenico"
RADIUS = 9000.0
CENTER_LABEL = "M80_Recuperato_A_SanDomenico"
SLAB_LABEL = "3_Lastra_lavica_secondaria2"


def prop(obj, *names):
    for n in names:
        try:
            return obj.get_editor_property(n)
        except Exception:  # noqa: BLE001
            pass
    return None


def label(d):
    return str(prop(d, "actor_label", "label") or "")


def xyz(v):
    return [round(v.x), round(v.y), round(v.z)]


def desc_info(d):
    return {"label": label(d), "class": str(prop(d, "native_class").get_name()), "center": xyz(m80_seq.desc_center(d)),
            "package": str(prop(d, "actor_package")), "spatially_loaded": prop(d, "is_spatially_loaded", "spatially_loaded"),
            "runtime_grid": str(prop(d, "runtime_grid")), "data_layers": str(prop(d, "data_layers", "data_layer_instance_names"))}


def actor_info(a):
    e = {"label": a.get_actor_label(), "class": a.get_class().get_path_name(), "location": xyz(a.get_actor_location()),
         "hidden_in_game": bool(prop(a, "hidden"))}
    if isinstance(a, unreal.Pawn):
        e["auto_possess_player"] = str(prop(a, "auto_possess_player"))
        e["auto_possess_ai"] = str(prop(a, "auto_possess_ai"))
    if isinstance(a, unreal.CameraActor):
        e["auto_activate_for_player"] = str(prop(a, "auto_activate_for_player"))
    comps = []
    for c in a.get_components_by_class(unreal.ActorComponent):
        cls = c.get_class().get_name()
        if any(k in cls for k in ("Camera", "Box", "Sphere", "Capsule", "Trigger", "Sequence", "Audio", "Movement", "Child")):
            ce = {"comp": c.get_name(), "class": cls}
            if isinstance(c, unreal.PrimitiveComponent):
                ce["overlap_events"] = bool(prop(c, "generate_overlap_events"))
                ce["profile"] = str(c.get_collision_profile_name())
            comps.append(ce)
    if comps:
        e["components"] = comps
    return e


def slab_info(a):
    e = actor_info(a)
    for n in ("surface", "width", "b_snap_to_ground", "snap_to_ground", "height_above_ground", "collision", "pieces",
              "is_spatially_loaded"):
        v = prop(a, n)
        if v is not None:
            e[n] = str(v)
    for c in a.get_components_by_class(unreal.PrimitiveComponent):
        ce = {"comp": c.get_name(), "class": c.get_class().get_name(), "visible": bool(c.is_visible()),
              "hidden_in_game": bool(prop(c, "hidden_in_game")), "collision": str(c.get_collision_enabled())}
        try:
            origin, extent, _ = unreal.SystemLibrary.get_component_bounds(c)
            ce["center"], ce["extent"] = xyz(origin), xyz(extent)
        except Exception:  # noqa: BLE001
            pass
        if isinstance(c, unreal.DynamicMeshComponent):
            try:
                ce["triangles"] = c.get_dynamic_mesh().get_triangle_count()
            except Exception as ex:  # noqa: BLE001
                ce["triangles"] = repr(ex)
        if isinstance(c, unreal.InstancedStaticMeshComponent):
            ce["instances"] = c.get_instance_count()
        e.setdefault("primitives", []).append(ce)
    return e


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    report = {}
    centre = [d for d in descs if label(d) == CENTER_LABEL]
    slabs = [d for d in descs if SLAB_LABEL.lower() in label(d).lower() or "lastra_lavica_secondaria" in label(d).lower()]
    report["slab_descs"] = [desc_info(d) for d in slabs]
    report["pawns_everywhere"] = [desc_info(d) for d in descs
                                  if any(k in str(prop(d, "native_class").get_name()) for k in ("Pawn", "Character", "Car", "Camera", "Sequence"))]
    if not centre:
        report["error"] = "no " + CENTER_LABEL
    else:
        c = m80_seq.desc_center(centre[0])
        report["centre"] = xyz(c)
        around = m80_seq.near(descs, c.x, c.y, RADIUS)
        report["around_count"] = len(around)
        m80_seq.load(around + slabs)
        yield 150
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        near = []
        for a in actors:
            loc = a.get_actor_location()
            if math.hypot(loc.x - c.x, loc.y - c.y) > RADIUS:
                continue
            cls = a.get_class().get_name()
            if cls in ("M80House", "StaticMeshActor", "M80StreetLight", "MazzarinoRoadSpline"):
                continue
            near.append(actor_info(a))
        report["near"] = near
        report["slabs"] = [slab_info(a) for a in actors if "lastra_lavica_secondaria" in a.get_actor_label().lower()]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
