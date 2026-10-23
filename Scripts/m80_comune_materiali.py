"""What the Comune (and its church) in the town are made of: for every actor of L_M80_Paese_WP whose label has
"Comune" or "Chiesa" (or the words in M80_CERCA, comma separated), its class, transform, and per component the mesh,
the mesh's size and the materials it renders with (overrides on the placed actor included). Read only.
Out: Saved/Mazzarino80/Comune/materiali.json (M80_CERCA: Saved/Mazzarino80/Comune/cerca.json)
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_comune_materiali.py -TimeoutMinutes 20
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Comune"
WORDS = [w for w in os.environ.get("M80_CERCA", "").split(",") if w] or ["Comune", "Chiesa", "comune", "chiesa"]
NAME = "cerca.json" if os.environ.get("M80_CERCA") else "materiali.json"


def path_of(o):
    return o.get_path_name() if o else None


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    mine = [d for d in descs if any(k.lower() in str(d.get_editor_property("label")).lower() for k in WORDS)]
    m80_seq.load(mine)
    yield 60
    rep = {"attori": []}
    labels = {str(d.get_editor_property("label")) for d in mine}
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() not in labels:
            continue
        t = a.get_actor_transform()
        ent = {"label": a.get_actor_label(), "classe": a.get_class().get_path_name(),
               "posizione": [round(v, 1) for v in (t.translation.x, t.translation.y, t.translation.z)],
               "rotazione": [round(v, 2) for v in (t.rotation.rotator().roll, t.rotation.rotator().pitch, t.rotation.rotator().yaw)],
               "scala": [round(v, 4) for v in (t.scale3d.x, t.scale3d.y, t.scale3d.z)], "componenti": []}
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            slots = []
            names = sm.get_editor_property("static_materials") if sm else []
            for i in range(c.get_num_materials()):
                slots.append({"slot": str(names[i].material_slot_name) if i < len(names) else str(i),
                              "materiale": path_of(c.get_material(i)),
                              "del_mesh": path_of(names[i].material_interface) if i < len(names) else None})
            box = sm.get_bounding_box() if sm else None
            ent["componenti"].append({"nome": c.get_name(), "mesh": path_of(sm), "slot": slots,
                                      "mesh_cm": [round(box.max.x - box.min.x), round(box.max.y - box.min.y), round(box.max.z - box.min.z)] if box else None,
                                      "scala_mondo": [round(v, 4) for v in (c.get_world_scale().x, c.get_world_scale().y, c.get_world_scale().z)]})
        rep["attori"].append(ent)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / NAME).write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
