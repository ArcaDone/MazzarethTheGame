"""Puts the churches imported by m80_chiese_import.py into the town (L_M80_Paese_WP) on their OSM footprints: the model's
plan centre on the footprint's centroid, turned by the manifest's rotation (Unreal yaw = -rotation), standing on the
landscape under the front door. Actors Chiesa_<Key> and Chiesa_<Key>_Dettagli, tags M80Chiesa + M80IgnoreGround, folder
Mazzarino80/Chiese; a second run moves them instead of adding copies. The procedural houses standing on the footprint
(a third of their plan box or more, the stand-in house of the church lot always) are switched off with their own
"Disattiva" flag. Only the packages of the actors placed, moved or switched off are saved.
Env M80_CHIESE=Key1,Key2 (default: every imported church). Report: Saved/Mazzarino80/Chiese/place_report.json

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_chiese_place.py
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
SRC = ROOT / "Saved/Mazzarino80/Chiese"
DEST = "/Game/Mazzarino80/Buildings/Chiese"
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"
TAG = "M80Chiesa"
FOLDER = "Mazzarino80/Chiese"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def keys():
    only = [k for k in os.environ.get("M80_CHIESE", "").split(",") if k]
    found = sorted(p.name for p in SRC.iterdir() if (p / ("SM_M80_%s.fbx" % p.name)).exists())
    return [k for k in found if not only or k in only]


def inside(ring, x, y):
    c = False
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def ground(world, x, y, guess):
    """Landscape height under (x, y): only the landscape counts (houses, roads, HLOD shells skipped)."""
    ignore = []
    for _ in range(24):
        # A trace stops at the first blocking thing: step past whatever is not the landscape.
        h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, guess + 20000), unreal.Vector(x, y, guess - 20000),
                                                   unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
        if not h:
            return None
        t = h.to_tuple()
        if t[9] is None:
            return None
        if isinstance(t[9], unreal.LandscapeProxy):
            return t[4].z
        ignore.append(t[9])
    return None


def steps():
    plan = {str(it["id"]): it for it in json.loads(PLAN.read_text(encoding="utf-8-sig"))}
    ms = {k: json.loads((SRC / k / ("%s.json" % k)).read_text(encoding="utf-8")) for k in keys()}
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    world = m80_seq.editor_world()
    descs = m80_seq.actor_descs()
    near = []
    for m in ms.values():
        cx, cy = m["osm_centroid_world_cm"]
        near += m80_seq.near(descs, cx, cy, 8000)
    m80_seq.load(near + m80_seq.actor_descs("LandscapeStreamingProxy"))
    yield 300
    report = {}
    touched = []
    existing = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)}
    houses = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House)
    for key, m in ms.items():
        rep = {"placed": [], "moved": [], "switched_off": [], "touching_kept": []}
        it = plan[m["osm_id"]]
        cx, cy = m["osm_centroid_world_cm"]
        yaw = -m["rotation_deg"]
        t = math.radians(yaw)
        cos, sin = math.cos(t), math.sin(t)

        def world_xy(px, py):
            # model metres -> Unreal local cm (y flipped) -> turned by the yaw.
            lx, ly = px * 100.0, -py * 100.0
            return lx * cos - ly * sin, lx * sin + ly * cos
        ox, oy = world_xy(*m["plan_centre_m"])
        loc_x, loc_y = cx - ox, cy - oy
        fx, fy = world_xy(*m["front_point_m"])
        z = ground(world, loc_x + fx, loc_y + fy, it["center_cm"][2])
        zc = ground(world, cx, cy, it["center_cm"][2])
        if z is None:
            z = zc if zc is not None else it["center_cm"][2]
        loc = unreal.Vector(loc_x, loc_y, z - m["base_z_m"] * 100.0)
        rot = unreal.Rotator(pitch=0.0, yaw=yaw, roll=0.0)
        rep["location"] = [round(loc.x), round(loc.y), round(loc.z)]
        rep["ground_front_centre_cm"] = [z, zc]
        for name in m["meshes"]:
            mesh = unreal.load_asset("%s/%s/%s" % (DEST, key, name))
            label = name.replace("SM_M80_", "Chiesa_")
            a = existing.get(label)
            if a:
                a.static_mesh_component.set_static_mesh(mesh)
                a.set_actor_location_and_rotation(loc, rot, False, True)
                rep["moved"].append(label)
            else:
                a = EAS.spawn_actor_from_object(mesh, loc, rot)
                a.set_actor_label(label)
                a.set_editor_property("tags", [unreal.Name(TAG), unreal.Name("M80IgnoreGround")])
                a.set_folder_path(FOLDER)
                rep["placed"].append(label)
            touched.append(a)
        ring = it["ring_cm"]
        rs = m.get("plan_raster")

        def on_model(x, y):
            """World cm -> the model's plan raster (the building's real footprint, cloisters and wings included)."""
            if not rs:
                return False
            dx, dy = x - loc_x, y - loc_y
            lx, ly = dx * cos + dy * sin, -dx * sin + dy * cos        # undo the yaw
            px, py = lx / 100.0, -ly / 100.0                            # Unreal local cm -> model metres
            c_ = int((px - rs["x0"]) / rs["cell"])
            r_ = int((py - rs["y0"]) / rs["cell"])
            return 0 <= r_ < rs["h"] and 0 <= c_ < rs["w"] and rs["rows"][r_][c_] == "1"
        for h in houses:
            c, e = h.get_actor_bounds(False)
            if abs(c.x - cx) > 6000 or abs(c.y - cy) > 6000:
                continue
            n = hit = hit_m = 0
            for i in range(8):
                for j in range(8):
                    n += 1
                    x_, y_ = c.x - e.x + 2 * e.x * (i + 0.5) / 8, c.y - e.y + 2 * e.y * (j + 0.5) / 8
                    hit += inside(ring, x_, y_)
                    hit_m += on_model(x_, y_)
            share = max(hit, hit_m) / float(n)
            # Any house standing in the building itself (a tenth of its plan box or more) goes too.
            if hit_m / float(n) >= 0.1:
                share = max(share, 0.33)
            own = h.get_actor_label() == "Casa_" + m["osm_id"]
            if own or share >= 0.33:
                if not h.get_editor_property("disabled"):
                    h.set_editor_property("disabled", True)
                    h.apply_exclusion()
                    touched.append(h)
                rep["switched_off"].append([h.get_actor_label(), round(share, 2)])
            elif share > 0:
                rep["touching_kept"].append([h.get_actor_label(), round(share, 2)])
        report[key] = rep
        yield 5
    packages = list({p.get_name(): p for p in (a.get_package() for a in touched)}.values())
    if packages:
        unreal.EditorLoadingAndSavingUtils.save_packages(packages, False)
    report["saved_packages"] = [p.get_name() for p in packages]
    (SRC / "place_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(SRC / "place_error.txt"))
