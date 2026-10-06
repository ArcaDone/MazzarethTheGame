"""Exclusion zones around the hand-made buildings placed in the town map (L_M80_Paese).

Every blueprint actor whose class lives under /Game/Migrated (scuola, castello, chiese, Agip, ...),
trees excepted, and every static mesh imported from Blender under /Game/Mazzarino80/Buildings, gets "Zone senza case procedurali" shaped as its real footprint (m80_footprints.py: walls and
roofs traced from above, squares, sidewalks and trees left out, one zone per separate block) plus
a 2 m margin; buildings without collision fall back to the convex hull of their meshes. The
procedural houses under a zone disappear (they come back if the zone is switched off or
deleted). Zones are named Zona_<building> in the folder Mazzarino80/Zone_escluse and are recreated on
every run, so moving a building and re-running keeps them in sync; hand-drawn zones are not touched.
Env: M80_ZONES_MAP, M80_ZONES_MARGIN_CM (default 150).
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_footprints  # noqa: E402
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
BUILDINGS = "/Game/Mazzarino80/Buildings/"
MAP = os.environ.get("M80_ZONES_MAP", m80_seq.TOWN_MAP)
MARGIN = float(os.environ.get("M80_ZONES_MARGIN_CM", "150"))
OUT = ROOT / "Saved/Mazzarino80/zones_report.json"
FOLDER = "Mazzarino80/Zone_escluse"
SKIP_CLASSES = ("Tree_C", "NeoClassic_house_C")  # neoclassic palaces replace their own lot (m80_town_props.py)
SKIP_MESH_WORDS = ("Tree", "Pine", "Poplar", "Grass", "Bush", "Plant")


def hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def grow(poly, d):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for x, y in poly:
        l = math.hypot(x - cx, y - cy) or 1.0
        out.append((x + (x - cx) / l * d, y + (y - cy) / l * d))
    return out


def is_imported_building(actor):
    """Buildings modelled in Blender and imported with Scripts/m80_import_blender_assets.py (e.g. the Poste)."""
    if not isinstance(actor, unreal.StaticMeshActor):
        return False
    mesh = actor.static_mesh_component.get_editor_property("static_mesh")
    return bool(mesh) and mesh.get_path_name().startswith(BUILDINGS)


def footprint_points(actor):
    pts = []
    for c in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh = c.static_mesh
        if not mesh or not c.is_visible() or any(w in mesh.get_name() for w in SKIP_MESH_WORDS):
            continue
        b = mesh.get_bounding_box()
        t = c.get_world_transform()
        for x in (b.min.x, b.max.x):
            for y in (b.min.y, b.max.y):
                for z in (b.min.z, b.max.z):
                    w = t.transform_location(unreal.Vector(x, y, z))
                    pts.append((round(w.x, 1), round(w.y, 1)))
    return pts


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected {} open".format(MAP))
    # World Partition: everything but the houses (they apply their zones themselves when they load).
    m80_seq.load([d for d in m80_seq.actor_descs() if not m80_seq.desc_class_is(d, "M80House", "MazzarinoRoadSpline", "DecalActor", "M80Sidewalk")])
    yield 30
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    for a in actors:
        if isinstance(a, unreal.M80ExclusionZone) and str(a.get_folder_path()) == FOLDER:
            a.destroy_actor()
    report = {"zones": {}}
    buildings = [a for a in actors if (a.get_class().get_path_name().startswith("/Game/Migrated/") and a.get_class().get_name() not in SKIP_CLASSES)
                 or is_imported_building(a)]
    houses = [h for h in actors if isinstance(h, unreal.M80House)]
    before = {h.get_name() for h in houses if h.is_excluded()}
    polys = []
    for b in buildings:
        traced = [p for p in m80_footprints.footprints(world, b) if len(p) >= 3]
        if traced:
            polys += [(b, "Zona_{}_{}".format(b.get_actor_label(), k + 1) if len(traced) > 1 else "Zona_" + b.get_actor_label(), p, "traced")
                      for k, p in enumerate(traced)]
            continue
        poly = hull(footprint_points(b))
        if len(poly) >= 3:
            polys.append((b, "Zona_" + b.get_actor_label(), grow(poly, MARGIN), "hull"))
        yield 1
    for b, label, poly, how in polys:
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        z = b.get_actor_location().z
        zone = eas.spawn_actor_from_class(unreal.M80ExclusionZone, unreal.Vector(cx, cy, z))
        zone.set_actor_label(label)
        zone.set_folder_path(FOLDER)
        outline = zone.get_editor_property("outline")
        outline.set_spline_points([unreal.Vector(x, y, z) for x, y in poly], unreal.SplineCoordinateSpace.WORLD, True)
        for i in range(len(poly)):
            outline.set_spline_point_type(i, unreal.SplinePointType.LINEAR, False)
        outline.set_closed_loop(True, True)
        zone.refresh_houses()
        report["zones"][label] = {"points": len(poly), "center": [round(cx), round(cy)], "shape": how}
    yield 10
    for h in houses:
        h.apply_exclusion()
    after = {h.get_name(): h for h in houses if h.is_excluded()}
    report["newly_excluded_houses"] = sorted(set(after) - before)
    report["excluded_total"] = len(after)
    m80_seq.save_all()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
