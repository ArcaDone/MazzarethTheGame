"""Photos of the town map details added with m80_town_common.ps1: painted roads, sidewalks, worn signs,
posters, neoclassic palaces, parked cars and the hand-made buildings with their exclusion zones.
Same light as m80_photos.py (not saved). Output: Saved/Mazzarino80/Foto/comune_<n>_<what>.png.
"""
import math
import os
import random
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

HERE = Path(__file__).resolve().parent
_src = (HERE / "m80_photos.py").read_text(encoding="utf-8")
exec(compile(_src[:_src.rindex("m80_seq.Sequencer(")], "m80_photos", "exec"))  # golden_hour, look_at, MAP, OUT

MAX_EACH = int(os.environ.get("M80_CPHOTOS_EACH", "3"))


def by_folder(actors, folder):
    return [a for a in actors if str(a.get_folder_path()) == folder]


def ground_at(world, x, y, z):
    r = unreal.SystemLibrary.line_trace_multi_for_objects(world, unreal.Vector(x, y, z + 5000), unreal.Vector(x, y, z - 5000),
                                                          [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1], True, [], unreal.DrawDebugTrace.NONE, True)
    hits = r[1] if isinstance(r, tuple) else r
    for h in hits or []:
        f = h.to_tuple()
        if isinstance(f[9], unreal.LandscapeProxy):
            return f[5].z
    return z


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)  # noqa: F821
    yield 60
    world = m80_seq.editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    golden_hour(world)  # noqa: F821
    cap = m80_seq.ViewCapture(2560, 1440, 62.0)
    yield 900
    actors = eas.get_all_level_actors()
    rnd = random.Random(3)
    shots = []

    def add(name, eye, target):
        shots.append((name, eye, target))

    # Hand-made buildings seen from above (the procedural houses around them must not overlap).
    for a in actors:
        if a.get_class().get_name() in ("ScuolaMatrice_C", "A_Salesiane_C", "CastelCompleted_C"):
            o, e = a.get_actor_bounds(False)
            r = max(e.x, e.y)
            add("edificio_" + a.get_actor_label(), (o.x - r * 1.6, o.y - r * 1.3, o.z + r * 1.4), (o.x, o.y, o.z))
    # Neoclassic palaces from the street.
    for a in by_folder(actors, "Mazzarino80/Edifici/NeoClassic")[:MAX_EACH + 1]:
        o, e = a.get_actor_bounds(False)
        yaw = math.radians(a.get_actor_rotation().yaw)
        fx, fy = math.sin(yaw), -math.cos(yaw)  # local -Y = main front
        d = max(e.x, e.y) * 1.9
        g = ground_at(world, o.x + fx * d, o.y + fy * d, o.z - e.z)
        add("neoclassico_" + a.get_actor_label(), (o.x + fx * d - fy * d * 0.5, o.y + fy * d + fx * d * 0.5, g + 220), (o.x, o.y, o.z - e.z * 0.2))
    # Posters, close.
    posters = [p for p in by_folder(actors, "Mazzarino80/Manifesti") if p.get_actor_label().startswith("Manifesto") and "sporco" not in p.get_actor_label()]
    rnd.shuffle(posters)
    for p in posters[:MAX_EACH]:
        loc = p.get_actor_location()
        yaw = math.radians(p.get_actor_rotation().yaw)
        fx, fy = -math.cos(yaw), -math.sin(yaw)  # the decal projects along +X into the wall
        add("manifesti", (loc.x + fx * 420 + fy * 150, loc.y + fy * 420 - fx * 150, loc.z), (loc.x, loc.y, loc.z - 20))
    # Sidewalks along the street.
    walks = by_folder(actors, "Mazzarino80/Marciapiedi")
    walks.sort(key=lambda w: -w.get_component_by_class(unreal.SplineComponent).get_spline_length())
    for w in walks[:MAX_EACH]:
        sp = w.get_component_by_class(unreal.SplineComponent)
        L = sp.get_spline_length()
        p0 = sp.get_location_at_distance_along_spline(L * 0.2, unreal.SplineCoordinateSpace.WORLD)
        p1 = sp.get_location_at_distance_along_spline(L * 0.6, unreal.SplineCoordinateSpace.WORLD)
        g0 = ground_at(world, p0.x, p0.y, p0.z)
        g1 = ground_at(world, p1.x, p1.y, p1.z)
        add("marciapiede_strada", (p0.x, p0.y, g0 + 175), (p1.x, p1.y, g1 + 60))
    # Worn signs.
    signs = [s for s in by_folder(actors, "Segnaletica") if s.get_actor_label().startswith("Palo_")]
    rnd.shuffle(signs)
    for s in signs[:2]:
        loc = s.get_actor_location()
        add("cartello", (loc.x + 380, loc.y + 260, loc.z + 230), (loc.x, loc.y, loc.z + 220))
    # Cars.
    cars = by_folder(actors, "Mazzarino80/Auto")
    if cars:
        xs = [c.get_actor_location() for c in cars]
        cx, cy, cz = sum(v.x for v in xs) / len(xs), sum(v.y for v in xs) / len(xs), sum(v.z for v in xs) / len(xs)
        add("auto", (cx + 900, cy + 700, cz + 260), (cx, cy, cz))
    # Painted roads from above.
    for w in walks[:1]:
        p = w.get_actor_location()
        add("strade_dall_alto", (p.x - 6000, p.y - 5000, p.z + 5500), (p.x, p.y, p.z))
    for i, (name, eye, target) in enumerate(shots):
        e, r = look_at(eye, target)  # noqa: F821
        cap.capture(e, r, OUT / "comune_{:02d}_{}.png".format(i, name))  # noqa: F821
        yield 30
    cap.destroy()


m80_seq.Sequencer(run(), log_file=str(OUT / "comune_error.txt"))  # noqa: F821
