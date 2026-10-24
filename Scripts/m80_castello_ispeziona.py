"""The castle in the town: which actors use the old Blueprint /Game/Migrated/Castello/CastelCompleted or the imported
SM_M80_Castello, and for every static mesh component its mesh, triangles, Nanite, LODs, scale and materials (with blend
mode). Used to plan the castle's hand-made LODs (with Nanite it turns black from far away). Read only.
Out: Saved/Mazzarino80/Castello/ispeziona.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_castello_ispeziona.py -TimeoutMinutes 20
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Castello"
NAMES = ("castel", "castello")


def vec(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def tris(sm, lod):
    try:
        return sm.get_num_triangles(lod)
    except AttributeError:
        return None


def mesh_info(sm):
    nanite = sm.get_editor_property("nanite_settings")
    mats = []
    for i, m in enumerate(sm.get_editor_property("static_materials")):
        mi = m.get_editor_property("material_interface")
        base = mi.get_base_material() if mi else None
        mats.append({"slot": str(m.get_editor_property("material_slot_name")), "mat": mi.get_path_name() if mi else None,
                     "blend": str(base.get_editor_property("blend_mode")) if base else None,
                     "two_sided": bool(base.get_editor_property("two_sided")) if base else None})
    box = sm.get_bounding_box()
    return {"path": sm.get_path_name(), "nanite": bool(nanite.get_editor_property("enabled")),
            "fallback_pct": nanite.get_editor_property("fallback_percent_triangles"),
            "lods": sm.get_num_lods(), "tris": [tris(sm, l) for l in range(sm.get_num_lods())],
            "size_cm": vec(box.max - box.min), "materials": mats}


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = []
    for d in m80_seq.actor_descs():
        label = str(d.get_editor_property("label")).lower()
        if any(n in label for n in NAMES):
            descs.append(d)
    m80_seq.load(descs)
    yield 90
    rep = {"attori": [], "mesh": {}}
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        cls = a.get_class().get_path_name()
        comps = a.get_components_by_class(unreal.StaticMeshComponent)
        uses = [c for c in comps if c.get_editor_property("static_mesh") and
                ("Castello" in c.get_editor_property("static_mesh").get_path_name())]
        if "Castel" not in cls and not uses:
            continue
        entry = {"label": a.get_actor_label(), "classe": cls, "loc": vec(a.get_actor_location()),
                 "scala": vec(a.get_actor_scale3d()), "rot": [a.get_actor_rotation().roll, a.get_actor_rotation().pitch,
                                                               a.get_actor_rotation().yaw], "componenti": []}
        for c in comps:
            sm = c.get_editor_property("static_mesh")
            if not sm:
                continue
            t = c.get_world_transform()
            entry["componenti"].append({"nome": c.get_name(), "mesh": sm.get_path_name(), "scala": vec(t.scale3d),
                                        "loc": vec(t.translation), "visibile": bool(c.is_visible()),
                                        "override": [m.get_path_name() if m else None for m in c.get_editor_property("override_materials")]})
            if sm.get_path_name() not in rep["mesh"]:
                rep["mesh"][sm.get_path_name()] = mesh_info(sm)
        rep["attori"].append(entry)
    for p in ("/Game/Mazzarino80/Buildings/Castello/SM_M80_Castello",):
        sm = unreal.load_asset(p)
        if sm and sm.get_path_name() not in rep["mesh"]:
            rep["mesh"][sm.get_path_name()] = mesh_info(sm)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ispeziona.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
