"""Puts the new Matrice (SM_M80_Matrice + SM_M80_Matrice_Interno from MatriceDentroFuori.blend, imported by
m80_import_blender_assets.py) in the town where the recovered one stands (M80_Recuperato_Matrice,
/Game/Migrated/Animations/Matrice) and hides that one (hidden in game, no collision; not deleted).

The recovered Blueprint's church meshes are in Blender's coordinates (Unreal x, -y, z in cm, origin at Blender's 0),
while the new meshes are centred: SM_M80_Matrice on its plan centre at its lowest point (MAIN_MID, Blender metres),
the interior on its own (MAIN_MID + the piece's offset). Placed with the recovered actor's transform (its fit to the OSM
footprint, scale 0.8 in plan and 0.7 in height), so it stands exactly where the old one did.
Actors Matrice and Matrice_Interno, folder Mazzarino80/Edifici/Matrice, tags M80Matrice + M80IgnoreGround; a second
run moves them. Photos from outside (as m80_matrice_ispeziona.py) and inside to Saved/Mazzarino80/Matrice/Dopo.
Env M80_MATRICE_VECCHIA=1 shows the recovered one again and hides the new one (going back).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_matrice_place.py -ForceLit
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Matrice"
INFO = ROOT / "Saved/Mazzarino80/Import/out/Matrice.json"
OLD = "M80_Recuperato_Matrice"
DEST = "/Game/Mazzarino80/Buildings/Matrice"
TAG = "M80Matrice"
FOLDER = "Mazzarino80/Edifici/Matrice"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector
BACK = os.environ.get("M80_MATRICE_VECCHIA") == "1"
# Inside (Blender metres): the nave runs along y; floor at z 4.4.
INSIDE = (("dentro_navata_avanti", (0.0, -8.0, 6.1), (0.0, 40.0, 7.0)),
          ("dentro_navata_indietro", (0.0, 38.0, 6.1), (0.0, -10.0, 7.0)),
          ("dentro_alto", (6.0, 0.0, 12.0), (-4.0, 30.0, 5.0)))


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def xf(t):
    r = t.rotation.rotator()
    return {"loc": vec(t.translation), "rot_pyr": [round(r.pitch, 2), round(r.yaw, 2), round(r.roll, 2)], "scale": vec(t.scale3d)}


def views(c, e):
    """Outside: four corners from above and the street at eye height on each side (as m80_matrice_ispeziona.py)."""
    out = []
    d = max(e.x, e.y) * 2.6
    for name, sx, sy in (("ne", 1, 1), ("no", -1, 1), ("se", 1, -1), ("so", -1, -1)):
        out.append(("fuori_" + name, V(c.x + sx * d, c.y + sy * d, c.z + e.z * 1.2), c))
    for name, sx, sy in (("x+", 1, 0), ("x-", -1, 0), ("y+", 0, 1), ("y-", 0, -1)):
        eye = V(c.x + sx * (e.x + 2500), c.y + sy * (e.y + 2500), c.z - e.z + 170)
        out.append(("strada_" + name, eye, V(c.x, c.y, c.z - e.z + 900)))
    return out


def old_frame(p):
    """Blender metres -> the recovered actor's local cm."""
    return V(p[0] * 100.0, -p[1] * 100.0, p[2] * 100.0)


def steps():
    info = json.loads(INFO.read_text(encoding="utf-8"))
    b = info["box_cm"]
    # Plan centre and lowest point of the main mesh in Blender metres (the json keeps the box after centring).
    # x and y from the export's world box (Export + Export2): x -22.90..24.00, y -35.26..51.90; z from blender_zero_cm.
    main_mid = (0.55, 8.32, -info["blender_zero_cm"] / 100.0)
    assert abs((b[3] - b[0]) / 100.0 - 46.90) < 0.05 and abs((b[4] - b[1]) / 100.0 - 87.16) < 0.05, b
    pieces = {"": main_mid}
    for part, d in info.get("pieces", {}).items():
        o = d["offset_cm"]
        pieces["_" + part] = (main_mid[0] + o[0] / 100.0, main_mid[1] + o[1] / 100.0, main_mid[2] + o[2] / 100.0)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    world = m80_seq.editor_world()
    descs = m80_seq.actor_descs()
    mine = [d for d in descs if str(d.get_editor_property("label")) == OLD]
    if not mine:
        raise RuntimeError("No actor labelled %s" % OLD)
    c0 = m80_seq.desc_center(mine[0])
    m80_seq.load(m80_seq.near(descs, c0.x, c0.y, 15000))
    yield 400
    level = unreal.EditorLevelLibrary.get_all_level_actors()
    old = next(a for a in level if a.get_actor_label() == OLD)
    t = old.get_actor_transform()
    existing = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)}
    report = {"old_transform": xf(t), "placed": [], "moved": []}
    new = []
    for suffix, mid in pieces.items():
        mesh = unreal.load_asset("%s/SM_M80_Matrice%s" % (DEST, suffix))
        loc = t.transform_location(old_frame(mid))
        label = "Matrice" + suffix
        a = existing.get(label)
        if a:
            a.static_mesh_component.set_static_mesh(mesh)
            report["moved"].append(label)
        else:
            a = EAS.spawn_actor_from_object(mesh, loc, t.rotation.rotator())
            a.set_actor_label(label)
            a.set_editor_property("tags", [unreal.Name(TAG), unreal.Name("M80IgnoreGround")])
            a.set_folder_path(FOLDER)
            report["placed"].append(label)
        a.set_actor_transform(unreal.Transform(loc, t.rotation.rotator(), t.scale3d), False, False)
        new.append(a)
    # One shown, the other hidden in game and without collision (kept, to go back).
    for a, show in [(old, BACK)] + [(n, not BACK) for n in new]:
        a.set_actor_hidden_in_game(not show)
        a.set_actor_enable_collision(show)
        a.set_is_temporarily_hidden_in_editor(not show)
    report["shown"] = "vecchia" if BACK else "nuova"
    packages = list({p.get_name(): p for p in (a.get_package() for a in new + [old])}.values())
    unreal.EditorLoadingAndSavingUtils.save_packages(packages, False)
    report["saved_packages"] = [p.get_name() for p in packages]
    report["new"] = [{"label": a.get_actor_label(), "transform": xf(a.get_actor_transform())} for a in new]
    (OUT / "place_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 30
    shown = old if BACK else new[0]
    c, e = shown.get_actor_bounds(False)
    report["bounds_centre"], report["bounds_extent"] = vec(c), vec(e)
    folder = OUT / ("Prima" if BACK else "Dopo")
    cap = m80_seq.ViewCapture(1600, 900, 70)
    shots = views(c, e) + [(n, t.transform_location(old_frame(eye)), t.transform_location(old_frame(at))) for n, eye, at in INSIDE]
    for name, eye, at in shots:
        rot = unreal.MathLibrary.find_look_at_rotation(eye, at)
        m80_seq.set_view(eye, rot)
        yield 60
        cap.capture(eye, rot, folder / ("%s.png" % name))
        yield 2
    cap.destroy()
    (OUT / "place_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "place_error.txt"))
