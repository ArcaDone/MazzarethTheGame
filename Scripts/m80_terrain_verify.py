"""Compares the Landscape height with the original terrain heights recorded in the OSM plan.

For a sample of lots, traces the landscape at the lot centre and compares it with center_cm.z
(sampled from the old terrain mesh). Writes Saved/Mazzarino80/Terrain/verify.json.
"""
import json
import os
import random
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
MAP = "/Game/Mazzarino80/Houses/Maps/L_M80_Paese_WP"
PLAN = ROOT / "Research/Mazzarino80/building_footprint_plan.json"
OUT = ROOT / "Saved/Mazzarino80/Terrain/verify.json"


def run():
    unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    yield 60
    world = m80_seq.editor_world()
    landscapes = list(unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Landscape))
    info = {"landscapes": [l.get_actor_label() for l in landscapes]}
    if landscapes:
        l = landscapes[0]
        info["landscape_location"] = l.get_actor_location().to_tuple()
        info["landscape_scale"] = l.get_actor_scale3d().to_tuple()
        origin, extent = l.get_actor_bounds(False)
        info["landscape_bounds"] = [origin.to_tuple(), extent.to_tuple()]
    # Old terrain mesh, collision re-enabled in memory only (the map is not saved).
    terrain = None
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
        mesh = actor.static_mesh_component.get_editor_property("static_mesh")
        if mesh and "M80_Terreno" in mesh.get_name():
            terrain = actor
    if terrain:
        terrain.set_actor_enable_collision(True)
        terrain.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    yield 5
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    rng = random.Random(3)
    rows = []
    for lot in rng.sample(plan, 40):
        x, y, z = lot["center_cm"]
        result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z + 50000), unreal.Vector(x, y, z - 50000),
                                                        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        hit = result[1] if isinstance(result, tuple) else result
        fields = hit.to_tuple() if hit else None
        if fields and fields[0]:
            actor = fields[9] if len(fields) > 9 else None
            impact = fields[5]  # impact_point
            hz = impact.z if impact else None
            mesh_z = None
            if terrain:
                r2 = terrain.static_mesh_component.line_trace_component(unreal.Vector(x, y, z + 50000), unreal.Vector(x, y, z - 50000), True, False, False)
                if r2 and r2[0]:
                    mesh_z = round(r2[1].z)
            rows.append({"lot": lot["id"], "mesh_z": mesh_z, "mesh_delta": round(hz - mesh_z) if (mesh_z is not None and hz is not None) else None,
                         "plan_z": round(z), "hit_z": round(hz) if hz is not None else None,
                         "delta": round(hz - z) if hz is not None else None, "actor": str(actor.get_actor_label()) if actor else None})
        else:
            rows.append({"lot": lot["id"], "plan_z": round(z), "hit": None})
    info["samples"] = rows
    md = [r["mesh_delta"] for r in rows if r.get("mesh_delta") is not None]
    if md:
        info["mesh_delta_mean_cm"] = round(sum(md) / len(md))
        info["mesh_delta_min_max_cm"] = [min(md), max(md)]
    deltas = [r["delta"] for r in rows if r.get("delta") is not None]
    if deltas:
        info["delta_mean_cm"] = round(sum(deltas) / len(deltas))
        info["delta_min_max_cm"] = [min(deltas), max(deltas)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(OUT.with_suffix(".error.txt")))
