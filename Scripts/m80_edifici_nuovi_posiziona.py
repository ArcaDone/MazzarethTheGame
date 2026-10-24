"""Puts a building made in Blender and imported by m80_import_blender_assets.py into L_M80_Paese_WP, switches off the
procedural houses standing on its lots, puts it on the hand-made buildings' HLOD layer and takes pictures of it under a
temporary daylight (as m80_edificio_foto.py).
- SantaMariaGesu: the church, the old hospital and the convent ruins were drawn in the town's own frame
  (m80_santa_maria_gesu.py), so each mesh goes where its pivot was in the .blend; off: the OSM houses of the church
  (372575840), of the hospital (372575833) and of the ruins (372575839).
- Bar24Ore: the 24 Ore bar on its OSM lot (way 1249072050, Via Caltanissetta), the long side along the lot's,
  standing on the ground at its centre; M80_YAW overrides the yaw (the model's door side faces the actor's -Y at 0).
Env M80_EDIFICIO=SantaMariaGesu|Bar24Ore (required), M80_SALVA=1 saves the new actors and the switched-off houses.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_edifici_nuovi_posiziona.py -ForceLit -TimeoutMinutes 40
Out: Saved/Mazzarino80/Edifici/<key>_posiziona/ (pictures, posiziona.json)
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
KEY = os.environ.get("M80_EDIFICIO", "")
SAVE = os.environ.get("M80_SALVA") == "1"
OUT = ROOT / ("Saved/Mazzarino80/Edifici/%s_posiziona" % KEY)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LAYER = "/Game/Mazzarino80/Houses/Maps/L_M80_Paese_HLODLayer_Edifici"
FOLDER = "Mazzarino80/Edifici"
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"
CONFIG = {
    "SantaMariaGesu": {"houses_off": ["372575840", "372575833", "372575839"]},
    "Bar24Ore": {"houses_off": ["1249072050"], "lot": "1249072050"},
}


def ground_z(world, x, y, ignore):
    hits = unreal.SystemLibrary.line_trace_multi(world, unreal.Vector(x, y, 30000), unreal.Vector(x, y, 5000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    hits = hits[1] if isinstance(hits, tuple) and len(hits) == 2 and isinstance(hits[1], (list, tuple)) else hits
    for h in hits or []:
        return h.to_tuple()[5].z
    return None


def is_ground(a):
    n = a.get_class().get_name()
    return "Landscape" in n or "RoadSpline" in n


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


def mesh_actor(label, mesh_path, loc, yaw, layer):
    a = next((x for x in EAS.get_all_level_actors() if x.get_actor_label() == label), None)
    if not a:
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, yaw))
        a.set_actor_label(label)
    a.set_actor_location(loc, False, False)
    a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), False)
    a.set_folder_path(FOLDER)
    smc = a.get_component_by_class(unreal.StaticMeshComponent)
    smc.set_editor_property("static_mesh", unreal.load_asset(mesh_path))
    smc.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    a.set_editor_property("hlod_layer", layer)
    return a


def steps():
    cfg = CONFIG[KEY]
    info = json.loads((ROOT / ("Saved/Mazzarino80/Import/out/%s.json" % KEY)).read_text(encoding="utf-8"))
    px, py, pz = info["pivot_blender_m"]
    plan = {str(b["id"]): b for b in json.loads(PLAN.read_text(encoding="utf-8-sig"))}
    if "lot" in cfg:
        ring = plan[cfg["lot"]]["ring_cm"]
        cx, cy = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    else:
        cx, cy = px * 100, -py * 100
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    m80_seq.load([d for d in m80_seq.near(descs, cx, cy, 9000) if "HLOD" not in str(d.get_editor_property("native_class"))]
                 + m80_seq.actor_descs("LandscapeStreamingProxy"))
    yield 200
    world = m80_seq.editor_world()
    layer = unreal.load_asset(LAYER)
    actors = EAS.get_all_level_actors()
    ignore = [a for a in actors if not is_ground(a)]
    dest = "/Game/Mazzarino80/Buildings/%s/SM_M80_%s" % (KEY, KEY)
    rep = {"salvato": SAVE, "attori": {}, "case_spente": []}
    placed = []
    if "lot" in cfg:
        # the long side of the lot gives the yaw
        best = max(range(len(ring)), key=lambda i: math.dist(ring[i], ring[(i + 1) % len(ring)]))
        a, b = ring[best], ring[(best + 1) % len(ring)]
        yaw = float(os.environ.get("M80_YAW", math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))))
        bx = info["box_cm"]
        cos, sin = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        zs = []
        for lx, ly in ((bx[0], bx[1]), (bx[3], bx[1]), (bx[3], bx[4]), (bx[0], bx[4]), (0, 0)):
            z = ground_z(world, cx + lx * cos - ly * sin, cy + lx * sin + ly * cos, ignore)
            if z is not None:
                zs.append(z)
        # the ground at the lot's centre (the town's landscape can drop metres at a lot's edge)
        loc = unreal.Vector(cx, cy, zs[-1] - 5 if zs else plan[cfg["lot"]]["center_cm"][2])
        placed.append(mesh_actor("M80_" + KEY, dest, loc, yaw, layer))
        rep["terreno_angoli"] = [round(z, 1) for z in zs]
    else:
        main = unreal.Vector(px * 100, -py * 100, pz * 100)
        placed.append(mesh_actor("M80_" + KEY, dest, main, 0.0, layer))
        for part, off in info["pieces"].items():
            o = off["offset_cm"]
            placed.append(mesh_actor("M80_%s_%s" % (KEY, part), "%s_%s" % (dest, part),
                                     main + unreal.Vector(o[0], -o[1], o[2]), 0.0, layer))
    for a in placed:
        l = a.get_actor_location()
        rep["attori"][a.get_actor_label()] = {"loc": [round(l.x, 1), round(l.y, 1), round(l.z, 1)],
                                             "yaw": round(a.get_actor_rotation().yaw, 2)}
    touched = []
    off_labels = {"Casa_" + i for i in cfg["houses_off"]}
    for h in actors:
        if isinstance(h, unreal.M80House) and h.get_actor_label() in off_labels:
            if not h.get_editor_property("disabled"):
                h.set_editor_property("disabled", True)
                h.apply_exclusion()
                touched.append(h)
            rep["case_spente"].append(h.get_actor_label())
    yield 5
    if SAVE:
        unreal.EditorLoadingAndSavingUtils.save_packages([a.get_package() for a in placed + touched], False)
        yield 30
    # pictures
    OUT.mkdir(parents=True, exist_ok=True)
    lo = hi = None
    for a in placed:
        o, e = a.get_actor_bounds(False)
        lo = o - e if lo is None else unreal.Vector(min(lo.x, o.x - e.x), min(lo.y, o.y - e.y), min(lo.z, o.z - e.z))
        hi = o + e if hi is None else unreal.Vector(max(hi.x, o.x + e.x), max(hi.y, o.y + e.y), max(hi.z, o.z + e.z))
    c = (lo + hi) * 0.5
    size = hi - lo
    r = max(size.x, size.y) * 0.5
    m80_seq.console("r.TextureStreaming 0")
    m80_seq.console("wp.Editor.HLOD.AllowShowingHLODsInEditor 0")
    daylight()
    yield 120
    views = {}
    for k in range(8):
        ang = math.radians(k * 45)
        d = r + 1500
        views["giro_%d" % (k * 45)] = ((c.x + math.cos(ang) * d, c.y + math.sin(ang) * d, lo.z + size.z * 0.5 + 300),
                                        (c.x, c.y, lo.z + size.z * 0.4), 70)
    views["aereo"] = ((c.x + r * 1.4, c.y - r * 1.4, hi.z + r * 1.3), (c.x, c.y, lo.z), 60)
    views["alto"] = ((c.x + 1, c.y, hi.z + r * 2.5), (c.x, c.y, lo.z), 60)
    for name, (e, t, fov) in views.items():
        e, t = unreal.Vector(*e), unreal.Vector(*t)
        rot = unreal.MathLibrary.find_look_at_rotation(e, t)
        m80_seq.set_view(e, rot)
        yield 200
        cap = m80_seq.ViewCapture(1600, 900, fov)
        cap.capture(e, rot, OUT / ("%s.png" % name))
        cap.destroy()
        yield 5
    (OUT / "posiziona.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT.parent / ("%s_posiziona_errore.txt" % KEY)))
