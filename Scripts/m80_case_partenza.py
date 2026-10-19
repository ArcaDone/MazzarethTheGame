"""The buildings around where Vito starts in the town (L_M80_Paese_WP), to compare with the packaged game: for each
actor within RADIUS of the player start, its class, label, distance, and what draws it (baked static mesh with Nanite
or not, the live dynamic mesh's triangles, materials, per-lot custom data). Nothing is saved.
Out: Saved/Mazzarino80/Cotto/case_partenza.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_case_partenza.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Cotto"
RADIUS = 9000.0


def mesh_info(c):
    m = c.get_editor_property("static_mesh") if isinstance(c, unreal.StaticMeshComponent) else None
    info = {"comp": c.get_name(), "class": c.get_class().get_name(), "visible": c.is_visible()}
    if m:
        info["mesh"] = m.get_path_name()
        try:
            info["nanite"] = m.get_editor_property("nanite_settings").enabled
        except Exception:  # noqa: BLE001
            pass
        info["materials"] = [x.get_path_name().rsplit("/", 1)[-1] if x else None for x in c.get_materials()][:6]
    if isinstance(c, unreal.DynamicMeshComponent):
        info["triangles"] = c.get_dynamic_mesh().get_triangle_count()
        info["materials"] = [x.get_path_name().rsplit("/", 1)[-1] if x else None for x in c.get_materials()][:6]
    try:
        info["cpd"] = [round(v, 3) for v in c.get_editor_property("custom_primitive_data").get_editor_property("data")][:8]
    except Exception:  # noqa: BLE001
        pass
    return info


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    starts = m80_seq.actor_descs("PlayerStart")
    m80_seq.load(starts)
    yield 10
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    start = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.PlayerStart)][0]
    p = start.get_actor_location()
    m80_seq.load(m80_seq.near(m80_seq.actor_descs(), p.x, p.y, RADIUS))
    yield 120
    rows = []
    for a in eas.get_all_level_actors():
        d = (a.get_actor_location() - p).length()
        if d > RADIUS or a.get_class().get_name() in ("LandscapeStreamingProxy", "WorldPartitionHLOD"):
            continue
        comps = [c for c in a.get_components_by_class(unreal.PrimitiveComponent)
                 if isinstance(c, (unreal.StaticMeshComponent, unreal.DynamicMeshComponent))]
        if not comps:
            continue
        rows.append({"label": a.get_actor_label(), "class": a.get_class().get_name(), "dist_m": round(d / 100),
                     "at": [round(a.get_actor_location().x), round(a.get_actor_location().y), round(a.get_actor_location().z)],
                     "comps": [mesh_info(c) for c in comps if c.is_visible()][:5]})
    rows.sort(key=lambda r: r["dist_m"])
    (OUT / "case_partenza.json").write_text(json.dumps({"start": [p.x, p.y, p.z], "yaw": start.get_actor_rotation().yaw,
                                                        "actors": rows}, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "case_partenza_errore.txt"))
