"""Looks at the Matrice standing in the town (L_M80_Paese_WP) before replacing it: the recovered Blueprint
M80_Recuperato_Matrice (/Game/Migrated/Animations/Matrice) with every component (mesh, relative and world transform,
world bounds, the mesh's own box) and photos of it from outside and inside. Nothing is saved.
Output: Saved/Mazzarino80/Matrice/ispeziona.json and Saved/Mazzarino80/Matrice/Prima/*.png
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_matrice_ispeziona.py -ForceLit
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
LABEL = "M80_Recuperato_Matrice"
V = unreal.Vector


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def xf(t):
    r = t.rotation.rotator()
    return {"loc": vec(t.translation), "rot_pyr": [round(r.pitch, 2), round(r.yaw, 2), round(r.roll, 2)], "scale": vec(t.scale3d)}


def views(c, e):
    """Outside: four corners from above and the front at eye height; inside: from the middle at chest height."""
    out = []
    d = max(e.x, e.y) * 2.6
    for name, sx, sy in (("ne", 1, 1), ("no", -1, 1), ("se", 1, -1), ("so", -1, -1)):
        out.append(("fuori_" + name, V(c.x + sx * d, c.y + sy * d, c.z + e.z * 1.2), c))
    for name, sx, sy in (("x+", 1, 0), ("x-", -1, 0), ("y+", 0, 1), ("y-", 0, -1)):
        eye = V(c.x + sx * (e.x + 2500), c.y + sy * (e.y + 2500), c.z - e.z + 170)
        out.append(("strada_" + name, eye, V(c.x, c.y, c.z - e.z + 900)))
    return out


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    world = m80_seq.editor_world()
    descs = m80_seq.actor_descs()
    mine = [d for d in descs if LABEL in str(d.get_editor_property("label"))]
    report = {"descs": [[str(d.get_editor_property("label")), str(d.get_editor_property("native_class").get_name())] for d in mine]}
    if not mine:
        raise RuntimeError("No actor labelled %s" % LABEL)
    c0 = m80_seq.desc_center(mine[0])
    m80_seq.load(m80_seq.near(descs, c0.x, c0.y, 15000))
    yield 400
    actors = [a for a in unreal.EditorLevelLibrary.get_all_level_actors() if LABEL in a.get_actor_label()]
    report["actors"] = []
    main = None
    for a in actors:
        c, e = a.get_actor_bounds(False)
        row = {"label": a.get_actor_label(), "class": a.get_class().get_path_name(), "transform": xf(a.get_actor_transform()),
               "bounds_centre": vec(c), "bounds_extent": vec(e), "hidden_in_game": a.get_editor_property("hidden"),
               "folder": str(a.get_folder_path()), "tags": [str(t) for t in a.tags], "components": []}
        for comp in a.get_components_by_class(unreal.SceneComponent):
            cr = {"name": comp.get_name(), "class": comp.get_class().get_name(), "relative": xf(comp.get_relative_transform()),
                  "world": xf(comp.get_world_transform()), "visible": comp.is_visible()}
            if isinstance(comp, unreal.StaticMeshComponent):
                m = comp.get_editor_property("static_mesh")
                cr["mesh"] = m.get_path_name() if m else None
                if m:
                    bb = m.get_bounding_box()
                    cr["mesh_box"] = [vec(bb.min), vec(bb.max)]
                    cr["collision"] = str(comp.get_collision_enabled())
                if isinstance(comp, unreal.InstancedStaticMeshComponent):
                    cr["instances"] = comp.get_instance_count()
                o, x, _ = unreal.SystemLibrary.get_component_bounds(comp)
                cr["world_bounds"] = [vec(o - x), vec(o + x)]
            row["components"].append(cr)
        report["actors"].append(row)
        if a.get_class().get_name() != "M80ExclusionZone" and (main is None or e.x * e.y > main[2].x * main[2].y):
            main = (a, c, e)
    (OUT / "ispeziona.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if main:
        a, c, e = main
        cap = m80_seq.ViewCapture(1600, 900, 70)
        for name, eye, at in views(c, e):
            rot = unreal.MathLibrary.find_look_at_rotation(eye, at)
            m80_seq.set_view(eye, rot)
            yield 60
            cap.capture(eye, rot, OUT / "Prima" / ("%s.png" % name))
            yield 2
        cap.destroy()


m80_seq.Sequencer(steps(), log_file=str(OUT / "ispeziona_error.txt"))
