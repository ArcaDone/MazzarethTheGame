"""Traffic test map /Game/Mazzarino80/Traffico/Maps/L_M80_ProvaMatrice (classic level): the Matrice and what is around it,
cut out of the town L_M80_Paese_WP, with cars driven about by townspeople, parked cars and people on foot.

From the town (made again from scratch each run, so it follows the town's edits):
- every actor within M80_RAGGIO cm (default 150 m) of the Matrice square: houses, Palazzo Bartoli, the Matrice, roads,
  sidewalks, steps, lamps, signs, carts, the parked cars; the light (sun, sky, fog);
- the ground: the town's landscape heights there (UM80EditorLibrary.SampleLandscapeHeights), made again as a landscape
  with the town's material and the "Strada" layer painted along the roads.
Then the traffic:
- AM80StradeNav (the roadway is dear in the people's navigation: they keep to the houses and cross where they must) and
  the navigation;
- parking places (AM80Parcheggio) by the right edge of the wide roads where there is room, some with a parked car the
  townspeople take for a drive (tag M80Folla_Auto);
- cars on the lanes (tag M80Traffico) that get a townsperson at the wheel at the start;
- the crowd (AM80Folla) and the player's start in the square.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_prova_matrice.py -ForceLit -TimeoutMinutes 90
Env M80_SOLO_TRAFFICO=1: only the parking places and the cars again, on the map already made.
Env M80_SOLO_NEGOZI=1: only the shops (one of each kind on houses around the square, Scripts/m80_negozi_prototipi.py),
photographed from the street and from inside.
Report: Saved/Mazzarino80/ProvaMatrice/prova_matrice.json, photos there.
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
MAP = "/Game/Mazzarino80/Traffico/Maps/L_M80_ProvaMatrice"
OUT = ROOT / "Saved/Mazzarino80/ProvaMatrice"
HEIGHTS = OUT / "terreno.bin"
MATRICE = "M80_Recuperato_Matrice"
RAGGIO = float(os.environ.get("M80_RAGGIO", "15000"))
LANDSCAPE_MAT = "/Game/Mazzarino80/Terrain/Materials/M_M80_Landscape"
STRADA_LAYER = "/Game/Mazzarino80/Terrain/Layers/LI_M80_Strada"
# Not copied: the town's own machinery (HLOD shells, landscape tiles, far horizon, cameras, the player's start).
SKIP = {"WorldPartitionHLOD", "LandscapeStreamingProxy", "Landscape", "LandscapeProxy", "M80Horizon", "CameraActor", "PlayerStart",
        "WorldDataLayers", "WorldPartitionMiniMap", "NavMeshBoundsVolume", "RecastNavMesh", "AbstractNavData", "WorldSettings",
        "Brush", "DefaultPhysicsVolume", "GameplayDebuggerCategoryReplicator", "M80Folla", "M80Pedone"}
# The light of the town, wherever it stands.
LIGHTS = {"DirectionalLight", "SkyLight", "SkyAtmosphere", "ExponentialHeightFog", "VolumetricCloud", "PostProcessVolume", "M80Atmosphere"}
CARS = [unreal.M80CarFiat500, unreal.M80CarMini, unreal.M80CarMaggiolino, unreal.M80CarGolf, unreal.M80CarM3]
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector
report = {"raggio": RAGGIO}


def classname(a):
    return a.get_class().get_name()


def ground(world, at):
    """Height of the ground (the landscape) under at, or None."""
    hits = unreal.SystemLibrary.line_trace_multi_for_objects(world, at + V(0, 0, 3000), at - V(0, 0, 3000),
                                                             [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1], False, [],
                                                             unreal.DrawDebugTrace.NONE, True)
    for h in hits or []:
        t = h.to_tuple()
        if isinstance(t[9], unreal.Landscape) or isinstance(t[9], unreal.LandscapeProxy):
            return t[4].z
    return None


def surface(world, at):
    """Height of whatever a car stands on under at (road slabs, paving, the landscape), or None."""
    hit = unreal.SystemLibrary.line_trace_single_for_objects(world, at + V(0, 0, 3000), at - V(0, 0, 3000),
                                                            [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1], False, [],
                                                            unreal.DrawDebugTrace.NONE, True)
    return hit.to_tuple()[4].z if hit else None


def clear(world, at, rot, half=V(240, 105, 70)):
    """Nothing standing in a car's room at at, turned by rot (houses, walls, kerbs, lamps, steps, other cars)."""
    types = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2,
             unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY5, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY6]
    c = at + V(0, 0, half.z + 40)
    hits = unreal.SystemLibrary.box_trace_multi_for_objects(world, c, c + V(0, 0, 1), half, rot, types, False, [],
                                                            unreal.DrawDebugTrace.NONE, True) or []
    for h in hits:
        a = h.to_tuple()[9]
        if a and not isinstance(a, (unreal.Landscape, unreal.LandscapeProxy)) and                 classname(a) not in ("MazzarinoRoadSpline", "M80Road", "M80StradeNav", "M80Parcheggio"):
            return False
    return True


def place_traffic(world):
    """Lanes, parking places (some with a parked car), cars on the lanes; those placed before are replaced."""
    old = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80Parcheggio))
    old += list(unreal.GameplayStatics.get_all_actors_with_tag(world, "M80Traffico"))
    old += [c for c in unreal.GameplayStatics.get_all_actors_with_tag(world, "M80Folla_Auto") if c.get_actor_label().startswith("Parcheggiata_")]
    for a in old:
        EAS.destroy_actor(a)
    yield 5
    traffic = unreal.M80Traffico.trova(world)
    traffic.ricostruisci()
    report["lanes"] = traffic.descrivi()
    spots = []
    for t in traffic.posti_parcheggio(float(os.environ.get("M80_PARCHEGGIO_MIN", "650"))):
        p = t.translation
        z = surface(world, p)
        if z is None or any((p - s.translation).length() < 650 for s in spots):
            continue
        if clear(world, V(p.x, p.y, z), t.rotation.rotator()):
            spots.append(unreal.Transform(V(p.x, p.y, z), t.rotation.rotator()))
        if len(spots) >= 16:
            break
    report["spots"] = len(spots)
    parked = 0
    for i, t in enumerate(spots):
        spot = EAS.spawn_actor_from_class(unreal.M80Parcheggio, t.translation + V(0, 0, 80), t.rotation.rotator())
        spot.set_actor_label("Parcheggio_%02d" % i)
        if i % 2 == 0:
            car = EAS.spawn_actor_from_class(CARS[parked % len(CARS)], t.translation + V(0, 0, 40), t.rotation.rotator())
            if car:
                car.tags = [unreal.Name("M80Folla_Auto")]
                car.set_actor_label("Parcheggiata_%s_%02d" % (CARS[parked % len(CARS)].__name__.replace("M80Car", ""), i))
                parked += 1
    report["parked"] = parked
    driving = 0
    for t in traffic.posti_su_corsie(8, 3500.0):
        p = t.translation
        z = surface(world, p)
        if z is None or not clear(world, V(p.x, p.y, z), t.rotation.rotator(), V(260, 110, 60)):
            continue
        cls = CARS[(driving + 2) % len(CARS)]
        car = EAS.spawn_actor_from_class(cls, V(p.x, p.y, z + 40), t.rotation.rotator())
        if car:
            car.tags = [unreal.Name("M80Traffico")]
            car.set_actor_label("Traffico_%s_%d" % (cls.__name__.replace("M80Car", ""), driving))
            driving += 1
        if driving >= 6:
            break
    report["driving"] = driving
    traffic.ricostruisci()   # the parking places on their lanes
    report["lanes_after"] = traffic.descrivi()



def traffic_only():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected %s open" % MAP)
    for s_ in place_traffic(world):
        yield s_
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10
    (OUT / "prova_matrice_traffico.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


SHOPS = ["Bar_Sport", "Negozio_Alimentari", "Tabaccheria", "Negozio_Frutta", "Negozio_Ferramenta", "Edicola_Negozio"]


def inside(poly, x, y):
    c = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a.y > y) != (b.y > y) and x < (b.x - a.x) * (y - a.y) / (b.y - a.y) + a.x:
            c = not c
    return c


def place_shops(world):
    """A shop on the street side of some houses around the square (one of each kind), rebuilt, photographed outside and in."""
    sq = None
    start = unreal.GameplayStatics.get_actor_of_class(world, unreal.PlayerStart)
    if start:
        sq = start.get_actor_location()
    roads = []
    for r in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if classname(r) == "MazzarinoRoadSpline" and float(r.get_editor_property("width_meters")) >= 4.0:
            sp = r.get_editor_property("spline")
            n = max(1, int(sp.get_spline_length() / 200))
            roads += [sp.get_location_at_distance_along_spline(sp.get_spline_length() * i / n, unreal.SplineCoordinateSpace.WORLD) for i in range(n + 1)]
    houses = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House))
    for h in houses:
        if list(h.get_editor_property("negozi")):
            h.set_editor_property("negozi", [])
            h.rebuild()
    cands = []
    for h in houses:
        if h.is_excluded():
            continue
        poly = h.get_footprint_world2d()
        if len(poly) < 3:
            continue
        for e in range(len(poly)):
            a, b = poly[e], poly[(e + 1) % len(poly)]
            ln = math.hypot(b.x - a.x, b.y - a.y)
            if ln < 650:
                continue
            mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
            ux, uy = (b.x - a.x) / ln, (b.y - a.y) / ln
            ox, oy = uy, -ux
            if inside(poly, mx + ox * 50, my + oy * 50):
                ox, oy = -ox, -oy
            # The street in front: a road's centre line within 5 m of the side, outside the house.
            near = min((math.hypot(p.x - (mx + ox * 300), p.y - (my + oy * 300)) for p in roads), default=1e9)
            d = math.hypot(mx - sq.x, my - sq.y) if sq else 0
            # Deep enough for a shop room behind this side (about the area over the side's length).
            area = abs(sum(poly[i].x * poly[(i + 1) % len(poly)].y - poly[(i + 1) % len(poly)].x * poly[i].y for i in range(len(poly)))) / 2
            if near < 350 and 1200 < d < 9000 and area / ln > 450:
                cands.append((d, h, e, (mx, my), (ox, oy), ln))
    cands.sort(key=lambda c: c[0])
    chosen = []
    for c in cands:
        if any(c[1] == o[1] or math.hypot(c[3][0] - o[3][0], c[3][1] - o[3][1]) < 1800 for o in chosen):
            continue
        chosen.append(c)
        if len(chosen) >= len(SHOPS):
            break
    report["shops"] = []
    for (d, h, e, mid, out, ln), name in zip(chosen, SHOPS):
        proto = unreal.load_asset("/Game/Mazzarino/Prototipi/DA_Negozio_" + name)
        n = unreal.M80NegozioScelto()
        n.set_editor_property("lato", e)
        n.set_editor_property("prototipo", proto)
        n.set_editor_property("posizione", 0.5)
        h.set_editor_property("negozi", [n])
        h.rebuild()
        report["shops"].append({"negozio": name, "casa": h.get_actor_label(), "lato": e, "lungo_cm": round(ln),
                                "costruito": [str(x) for x in h.get_editor_property("negozi_costruiti")], "mid": mid, "out": out})
    yield 30
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 10
    # Photos: from the street, and from just inside towards the back.
    m80_seq.console("r.TextureStreaming 0")
    cap = m80_seq.ViewCapture(1600, 900, 75)
    for i, sh in enumerate(report["shops"]):
        (mx, my), (ox, oy) = sh["mid"], sh["out"]
        z = ground(world, V(mx + ox * 400, my + oy * 400, sq.z if sq else 0)) or (sq.z if sq else 0)
        views = {"strada": (V(mx + ox * 450, my + oy * 450, z + 170), V(mx, my, z + 140)),
                 "dentro": (V(mx - ox * 50, my - oy * 50, z + 160), V(mx - ox * 400, my - oy * 400, z + 110))}
        for name, (eye, at) in views.items():
            rot = unreal.MathLibrary.find_look_at_rotation(eye, at)
            m80_seq.set_view(eye, rot)
            yield 200
            cap.capture(eye, rot, str(OUT / ("negozio_%d_%s_%s.png" % (i, sh["negozio"], name))))
            yield 5
    cap.destroy()


def shops_only():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected %s open" % MAP)
    for s_ in place_shops(world):
        yield s_
    (OUT / "prova_matrice_negozi.json").write_text(json.dumps(report, indent=1), encoding="utf-8")



def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    if os.environ.get("M80_SOLO_TRAFFICO"):
        for s in traffic_only():
            yield s
        return
    if os.environ.get("M80_SOLO_NEGOZI"):
        for s in shops_only():
            yield s
        return
    # 1) The town: where the square is.
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    m80_seq.load([d for d in descs if str(d.get_editor_property("label")) == MATRICE])
    yield 30
    world = m80_seq.editor_world()
    mat = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if a.get_actor_label() == MATRICE)
    sq = mat.get_actor_transform().transform_location(V(50.0, 4000.0, 0.0))
    report["square"] = [sq.x, sq.y, sq.z]

    # 2) The ground first, with only the landscape loaded (nothing standing on it can be mistaken for it).
    proxies = [d for d in descs if m80_seq.desc_class_is(d, "LandscapeStreamingProxy")]
    m80_seq.load(proxies)
    yield 120
    report["heights"] = unreal.M80EditorLibrary.sample_landscape_heights(unreal.Vector2D(sq.x, sq.y), 100.0, 3, 3, str(HEIGHTS))
    if not report["heights"]:
        raise RuntimeError("No landscape under the square")

    # 3) Everything around the square, copied.
    near = [d for d in m80_seq.near(descs, sq.x, sq.y, RAGGIO) if not m80_seq.desc_class_is(d, *SKIP)]
    m80_seq.load(near)
    yield 240
    copy = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        cls = classname(a)
        if cls in LIGHTS:
            copy.append(a)
        elif cls not in SKIP and not isinstance(a, (unreal.Landscape, unreal.LandscapeProxy, unreal.Brush)):
            p = a.get_actor_location()
            if math.hypot(p.x - sq.x, p.y - sq.y) <= RAGGIO and a.get_actor_label():
                copy.append(a)
    report["copied"] = len(copy)
    report["copied_classes"] = {}
    for a in copy:
        report["copied_classes"][classname(a)] = report["copied_classes"].get(classname(a), 0) + 1
    EAS.set_selected_level_actors(copy)
    yield 5
    unreal.SystemLibrary.execute_console_command(world, "EDIT COPY")
    yield 10
    EAS.set_selected_level_actors([])

    # 4) The test map, new each time.
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level(MAP, False)
    yield 30
    world = m80_seq.editor_world()
    if not world.get_path_name().startswith(MAP):
        raise RuntimeError("Expected %s open, got %s" % (MAP, world.get_path_name()))
    unreal.SystemLibrary.execute_console_command(world, "EDIT PASTE")
    yield 120
    pasted = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor) if classname(a) not in ("WorldSettings", "Brush")]
    report["pasted"] = len(pasted)
    EAS.set_selected_level_actors([])

    # 5) The ground again, and the roads painted on it.
    land = unreal.M80EditorLibrary.create_landscape_from_heights_file(unreal.Vector2D(sq.x, sq.y), 100.0, str(HEIGHTS), unreal.load_asset(LANDSCAPE_MAT))
    if not land:
        raise RuntimeError("Landscape not made")
    yield 30
    layer = unreal.M80EditorLibrary.ensure_landscape_layer(land, "Strada", STRADA_LAYER, True)
    roads = [a for a in pasted if classname(a) == "MazzarinoRoadSpline"]
    report["roads"] = len(roads)
    report["painted"] = unreal.M80EditorLibrary.paint_landscape_layer_along_splines(
        land, layer, [r.get_component_by_class(unreal.SplineComponent) for r in roads],
        [float(r.get_editor_property("width_meters")) * 50.0 for r in roads], 70.0, True)
    yield 30
    # Sidewalks and steps sit again on this ground.
    for a in pasted:
        if classname(a) in ("M80Sidewalk", "M80Stairs", "M80Road"):
            try:
                a.rebuild()
            except Exception:  # noqa: BLE001
                pass
    yield 30

    # 6) The people's navigation, with the roadway dear.
    nav = EAS.spawn_actor_from_class(unreal.M80StradeNav, sq)
    nav.set_actor_label("Strade_Navigazione")
    vol = EAS.spawn_actor_from_class(unreal.NavMeshBoundsVolume, V(sq.x, sq.y, sq.z))
    vol.set_actor_scale3d(V(RAGGIO / 100.0 + 5, RAGGIO / 100.0 + 5, 60))
    vol.set_actor_label("Navigazione")
    unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")
    yield 60
    for _ in range(120):
        if not unreal.NavigationSystemV1.is_navigation_being_built(world):
            break
        yield 30

    for s_ in place_traffic(world):
        yield s_

    # 8) The crowd, the player's start, the game mode.
    crowd = EAS.spawn_actor_from_class(unreal.M80Folla, V(sq.x, sq.y, sq.z + 100))
    crowd.set_actor_label("Folla")
    crowd.set_editor_property("quanti", int(os.environ.get("M80_QUANTI", "40")))
    crowd.set_editor_property("raggio", RAGGIO * 0.6)
    crowd.set_editor_property("usa_segnaposto", False)
    start = EAS.spawn_actor_from_class(unreal.PlayerStart, V(sq.x, sq.y, (ground(world, sq) or sq.z) + 120))
    start.set_actor_label("Inizio")
    world.get_world_settings().set_editor_property("default_game_mode", unreal.M80GameMode.static_class())
    yield 10
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 20

    # 9) Photos: from high over the square, along the Corso, the square.
    m80_seq.console("r.TextureStreaming 0")
    cap = m80_seq.ViewCapture(1600, 900, 70)
    views = {"alto": (sq + V(-9000, -9000, 9000), sq), "piazza": (sq + V(-2500, 1500, 600), sq + V(0, 0, 300)),
             "piazza2": (sq + V(2000, -2500, 500), sq + V(0, 0, 300))}
    for name, (eye, at) in views.items():
        rot = unreal.MathLibrary.find_look_at_rotation(eye, at)
        m80_seq.set_view(eye, rot)
        yield 240
        cap.capture(eye, rot, str(OUT / ("%s.png" % name)))
        yield 5
    cap.destroy()
    (OUT / "prova_matrice.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
