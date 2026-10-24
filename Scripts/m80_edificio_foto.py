"""Photos of one hand-made building of the town under a temporary daylight (nothing saved): the actors whose label starts
with M80_LABEL (e.g. Chiesa_SantIgnazio), the town around them and the landscape loaded, then eight views around it from
over the houses, two from the air and one looking up from close by. The editor viewport goes to each view first so Nanite
streams it in. Also lists the building's actors, meshes, Nanite and materials.
Env M80_LABEL (required), M80_NOME (output name, default the label), M80_HLOD=1 (HLODs shown, else hidden).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_edificio_foto.py -ForceLit -TimeoutMinutes 40
Out: Saved/Mazzarino80/Edifici/<nome>/<view>.png, attori.json
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
LABEL = os.environ.get("M80_LABEL", "")
OUT = ROOT / "Saved/Mazzarino80/Edifici" / os.environ.get("M80_NOME", LABEL)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def daylight():
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 30000))
    sun.set_actor_rotation(unreal.Rotator(pitch=-42.0, yaw=-110.0, roll=0.0), False)
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("atmosphere_sun_light", True)
    c.set_intensity(7.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 20000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight) and a != sun:
            a.get_component_by_class(unreal.DirectionalLightComponent).set_visibility(False)


def describe(actors):
    out = []
    for a in actors:
        comps = []
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            if not sm:
                continue
            comps.append({"mesh": sm.get_path_name(), "nanite": bool(sm.get_editor_property("nanite_settings").get_editor_property("enabled")),
                          "lods": sm.get_num_lods(), "tris0": sm.get_num_triangles(0),
                          "materiali": [m.get_path_name() if m else None for m in c.get_materials()]})
        out.append({"label": a.get_actor_label(), "classe": a.get_class().get_name(),
                    "loc": [round(v, 1) for v in (a.get_actor_location().x, a.get_actor_location().y, a.get_actor_location().z)],
                    "rot_yaw": round(a.get_actor_rotation().yaw, 2), "scala": a.get_actor_scale3d().x, "mesh": comps})
    return out


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    mine = [d for d in descs if str(d.get_editor_property("label")).startswith(LABEL)]
    if not mine:
        raise RuntimeError("nessun attore che inizia con " + LABEL)
    cx = sum(m80_seq.desc_center(d).x for d in mine) / len(mine)
    cy = sum(m80_seq.desc_center(d).y for d in mine) / len(mine)
    m80_seq.load(m80_seq.near(descs, cx, cy, 12000) + m80_seq.actor_descs("LandscapeStreamingProxy"))
    yield 300
    actors = [a for a in EAS.get_all_level_actors() if a.get_actor_label().startswith(LABEL)]
    lo = hi = None
    for a in actors:
        o, e = a.get_actor_bounds(False)
        a_lo, a_hi = o - e, o + e
        lo = a_lo if lo is None else unreal.Vector(min(lo.x, a_lo.x), min(lo.y, a_lo.y), min(lo.z, a_lo.z))
        hi = a_hi if hi is None else unreal.Vector(max(hi.x, a_hi.x), max(hi.y, a_hi.y), max(hi.z, a_hi.z))
    (OUT / "attori.json").write_text(json.dumps({"attori": describe(actors), "box": [[lo.x, lo.y, lo.z], [hi.x, hi.y, hi.z]]},
                                                indent=1), encoding="utf-8")
    c = (lo + hi) * 0.5
    size = hi - lo
    r = max(size.x, size.y) * 0.5
    m80_seq.console("r.TextureStreaming 0")
    if os.environ.get("M80_HLOD") != "1":
        # the editor draws HLODs over loaded regions too: hidden, only the real meshes are seen
        m80_seq.console("wp.Editor.HLOD.AllowShowingHLODsInEditor 0")
    daylight()
    yield 120
    views = {}
    for k in range(8):
        a = math.radians(k * 45)
        d = r + 2500
        views["giro_%d" % (k * 45)] = ((c.x + math.cos(a) * d, c.y + math.sin(a) * d, lo.z + size.z * 0.6 + 600),
                                        (c.x, c.y, lo.z + size.z * 0.4), 70)
    views["aereo_a"] = ((c.x + r * 1.6, c.y - r * 1.6, hi.z + r * 1.4), (c.x, c.y, lo.z), 60)
    views["aereo_b"] = ((c.x - r * 1.6, c.y + r * 1.6, hi.z + r * 1.4), (c.x, c.y, lo.z), 60)
    views["dal_basso"] = ((c.x - r - 600, c.y - 200, lo.z + 170), (c.x, c.y, lo.z + size.z * 0.8), 80)
    for name, (e, t, fov) in views.items():
        e, t = unreal.Vector(*e), unreal.Vector(*t)
        rot = unreal.MathLibrary.find_look_at_rotation(e, t)
        m80_seq.set_view(e, rot)
        yield 240
        cap = m80_seq.ViewCapture(1600, 900, fov)
        cap.capture(e, rot, OUT / ("%s.png" % name))
        cap.destroy()
        yield 5


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
