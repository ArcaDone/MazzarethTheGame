"""Palazzo Bartoli into the town (L_M80_Paese_WP): the imported pieces (m80_bartoli_import.py) as static mesh actors at
origin_world_cm, tag M80Bartoli, outliner folder Mazzarino80/PalazzoBartoli; a second run updates them instead of
adding copies. The procedural houses standing on the block (a third of their plan box or more on the footprint raster
of the manifest, as in m80_bartoli_town_views.py) are switched off with their own "Disattiva (sostituita da un edificio
fatto a mano)": hidden, not deleted, one click brings them back.
Saved: only the packages of the actors placed or switched off (no other actor of the map is rewritten).
Then two check views with a temporary daylight that is not saved.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bartoli_place.py -ForceLit
Out: Saved/Mazzarino80/Bartoli/Paese/{report.json, frontale.png, aereo.png}
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Bartoli/Paese"
MANIFEST = ROOT / "Saved/Mazzarino80/Bartoli/Export/M80_Bartoli.json"
DEST = "/Game/Mazzarino80/Buildings/Bartoli"
TAG = "M80Bartoli"
FOLDER = "Mazzarino80/PalazzoBartoli"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# Local metres of the lot: eye, target, horizontal fov.
VIEWS = {
    "frontale": ((13.0, -40.0, 3.0), (2.0, -24.0, 8.5), 90),
    "aereo": ((70.0, -75.0, 55.0), (0.0, -5.0, 6.0), 50),
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


def mesh_names(m):
    names = [g["mesh"] for g in m["groups"].values()] + [d["mesh"] for d in m["details"].values()]
    for key, field in (("roofs", "mesh"), ("roofs", "ridges"), ("volumes", "mesh")):
        if key in m and m[key].get(field):
            names.append(m[key][field])
    return sorted(set(names))


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ox, oy, oz = m["origin_world_cm"]
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    world = m80_seq.editor_world()
    assert world.get_path_name().startswith(m80_seq.TOWN_MAP), world.get_path_name()
    m80_seq.load(m80_seq.near(m80_seq.actor_descs(), ox, oy, 15000))
    yield 200
    report = {"placed": [], "updated": [], "missing_assets": [], "switched_off": [], "touching_kept": []}
    touched = []
    existing = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_with_tag(world, TAG)}
    origin = unreal.Vector(ox, oy, oz)
    for name in mesh_names(m):
        mesh = unreal.load_asset("%s/%s" % (DEST, name))
        if not mesh:
            report["missing_assets"].append(name)
            continue
        label = name.replace("SM_M80_", "")
        a = existing.get(label)
        if a:
            a.static_mesh_component.set_static_mesh(mesh)
            a.set_actor_location_and_rotation(origin, unreal.Rotator(0, 0, 0), False, True)
            report["updated"].append(label)
        else:
            a = EAS.spawn_actor_from_object(mesh, origin)
            a.set_actor_label(label)
            a.set_editor_property("tags", [unreal.Name(TAG)])
            a.set_folder_path(FOLDER)
            report["placed"].append(label)
        touched.append(a)
    fp = m["footprint"]
    for h in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.M80House):
        c, ext = h.get_actor_bounds(False)
        share = covered(fp, ox, oy, (c - ext, c + ext))
        if share >= 0.33:
            if not h.get_editor_property("disabled"):
                h.set_editor_property("disabled", True)
                h.apply_exclusion()
                touched.append(h)
            report["switched_off"].append([h.get_actor_label(), round(share, 2)])
        elif share > 0:
            report["touching_kept"].append([h.get_actor_label(), round(share, 2)])
    yield 30
    packages = [a.get_package() for a in touched]
    unreal.EditorLoadingAndSavingUtils.save_packages(packages, False)
    report["saved_packages"] = [p.get_name() for p in packages]
    (OUT / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    # Check views under a temporary daylight (never saved: the script quits without saving again).
    m80_seq.console("r.TextureStreaming 0")
    daylight()
    yield 300
    for _ in range(2):
        for name, (eye, target, fov) in VIEWS.items():
            e = unreal.Vector(ox + eye[0] * 100, oy - eye[1] * 100, oz + eye[2] * 100)
            t = unreal.Vector(ox + target[0] * 100, oy - target[1] * 100, oz + target[2] * 100)
            cap = m80_seq.ViewCapture(1600, 900, fov)
            cap.capture(e, unreal.MathLibrary.find_look_at_rotation(e, t), OUT / ("%s.png" % name))
            cap.destroy()
            yield 2
        yield 200


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
