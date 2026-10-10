"""Palazzo Bartoli in the town, nothing saved: loads L_M80_Paese_WP around the lot, takes the reference-photo views with
the procedural houses as they are ("prima"), then hides the houses standing on the block, places the imported
pieces (m80_bartoli_import_gioco.py) at origin_world_cm and takes the same views ("dopo"), so the palace is seen next to the
town materials under the same light. The map is closed without saving (temporary daylight, hidden houses).

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bartoli_town_views.py
Out: Saved/Mazzarino80/Bartoli/Citta/{prima,dopo}_<view>.png, views.json
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
OUT = ROOT / "Saved/Mazzarino80/Bartoli/Citta"
MANIFEST = ROOT / "Saved/Mazzarino80/Bartoli/Export/M80_Bartoli.json"
DEST = "/Game/Mazzarino80/Buildings/Bartoli"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# Reference-photo views of the Blender model (m80_palazzo_bartoli.photo_views): local metres, eye height above the
# ground for the street views (None = absolute height), target, horizontal fov.
VIEWS = {
    "frontale_bartoli": ((-1.1, -46.5, 1.6), (-2.0, -29.4, 7.1), 62, True),
    "corso_222": ((13.0, -38.0, 1.6), (6.0, -24.0, 8.5), 95, True),
    "angolo_farmacia": ((53.0, -25.0, 1.6), (40.0, -11.5, 9.0), 100, True),
    "corso_ovest_b": ((-36.0, -41.5, 1.6), (-14.0, -33.0, 5.5), 80, True),
    "salita_teatro": ((-37.5, -31.0, 1.6), (-44.0, -9.0, 9.0), 90, True),
    "cortile_scalone": ((5.5, -9.5, 2.7), (-2.6, 6.5, 6.0), 95, False),
    "via_butera": ((43.5, 37.0, 1.6), (28.0, 33.5, 9.5), 85, True),
    "aereo_sudest": ((70.0, -75.0, 55.0), (0.0, -5.0, 6.0), 50, False),
}


def covered(fp, ox, oy, box):
    """Share of a house's plan box (world cm) that falls on the block's footprint raster (local metres)."""
    lo, hi = box
    n = hit = 0
    steps = 8
    for i in range(steps):
        for j in range(steps):
            x = lo.x + (hi.x - lo.x) * (i + 0.5) / steps
            y = lo.y + (hi.y - lo.y) * (j + 0.5) / steps
            c = int(((x - ox) / 100.0 - fp["x0"]) / fp["cell"])
            r = int((-(y - oy) / 100.0 - fp["y0"]) / fp["cell"])
            n += 1
            if 0 <= r < fp["h"] and 0 <= c < fp["w"] and fp["rows"][r][c] == "1":
                hit += 1
    return hit / float(n)


def ground_z(world, x, y, guess):
    hits = unreal.SystemLibrary.line_trace_multi(world, unreal.Vector(x, y, guess + 20000), unreal.Vector(x, y, guess - 20000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    for h in hits or []:
        t = h.to_tuple()
        actor = t[9] if len(t) > 9 else None
        if actor and isinstance(actor, unreal.LandscapeProxy):
            return t[4].z
    return guess


def daylight():
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 30000))
    # From the south-east, as in L_M80_PalazzoBartoli: the Corso fronts face south (+Y in Unreal).
    sun.set_actor_rotation(unreal.Rotator(pitch=-40.0, yaw=-110.0, roll=0.0), False)
    c = sun.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_editor_property("atmosphere_sun_light", True)
    c.set_editor_property("atmosphere_sun_light_index", 0)
    c.set_intensity(7.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 20000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    # Any other sun of the map off (the town may be set at night).
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight) and a != sun:
            a.get_component_by_class(unreal.DirectionalLightComponent).set_visibility(False)


def capture_all(world, m, tag):
    ox, oy, oz = m["origin_world_cm"]
    rec = {}
    for name, (eye, target, fov, on_ground) in VIEWS.items():
        ex, ey = ox + eye[0] * 100, oy - eye[1] * 100
        ez = ground_z(world, ex, ey, oz) + eye[2] * 100 if on_ground else oz + eye[2] * 100
        e = unreal.Vector(ex, ey, ez)
        t = unreal.Vector(ox + target[0] * 100, oy - target[1] * 100, oz + target[2] * 100)
        cap = m80_seq.ViewCapture(1600, 900, fov)
        cap.capture(e, unreal.MathLibrary.find_look_at_rotation(e, t), OUT / ("%s_%s.png" % (tag, name)))
        cap.destroy()
        rec[name] = [round(ex), round(ey), round(ez)]
        yield 2
    (OUT / ("views_%s.json" % tag)).write_text(json.dumps(rec, indent=1), encoding="utf-8")


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ox, oy, oz = m["origin_world_cm"]
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    # Scene captures do not drive texture streaming: load every mip so the baked detail shows.
    m80_seq.console("r.TextureStreaming 0")
    yield 60
    world = m80_seq.editor_world()
    # The landscape whole: sidewalks and stairs drape their paving on it when they rebuild at load; a tile left unloaded
    # (centres are far apart) puts them on the HLOD shells of the houses instead, metres up.
    m80_seq.load(m80_seq.near(m80_seq.actor_descs(), ox, oy, 15000) + m80_seq.actor_descs("LandscapeStreamingProxy"))
    yield 200
    daylight()
    yield 300
    for _ in capture_all(world, m, "prima"):
        yield 2
    # Houses standing on the block (a third of their plan box or more on the footprint raster) go; the palace comes in.
    fp = m["footprint"]
    hidden, kept = [], []
    for h in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House):
        c, ext = h.get_actor_bounds(False)
        share = covered(fp, ox, oy, (c - ext, c + ext))
        if 0 < share < 0.33:
            kept.append([h.get_actor_label(), round(share, 2)])
        if share >= 0.33:
            h.set_is_temporarily_hidden_in_editor(True)
            h.set_actor_hidden_in_game(True)
            for comp in h.get_components_by_class(unreal.PrimitiveComponent):
                comp.set_visibility(False)
            hidden.append([h.get_actor_label(), round(share, 2)])
    gioco = ROOT / "Saved/Mazzarino80/Bartoli/Gioco/M80_Bartoli_Gioco.json"
    for name in sorted(json.loads(gioco.read_text(encoding="utf-8"))["meshes"]):
        mesh = unreal.load_asset("%s/%s" % (DEST, name))
        if mesh:
            EAS.spawn_actor_from_object(mesh, unreal.Vector(ox, oy, oz))
    (OUT / "nascoste.json").write_text(json.dumps({"nascoste": hidden, "toccano_ma_restano": kept}, indent=1), encoding="utf-8")
    yield 400
    for _ in capture_all(world, m, "dopo"):
        yield 2
    yield 200
    for _ in capture_all(world, m, "dopo"):
        yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
