"""Why some hand-made buildings of L_M80_Paese_WP are missing (or half there) in the HLODs: for every big actor that is
not a procedural one (houses, roads, lamps...), its HLOD layer, whether it is hidden in game or always loaded, and per
mesh component whether it may go into HLODs, its mesh, Nanite and materials; the HLOD layers' settings; and which HLOD
actors hold each building's meshes. Nothing is saved.
Output: Saved/Mazzarino80/Memoria/hlod_ispeziona.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_hlod_ispeziona.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Memoria"
PROCEDURAL = {"M80House", "MazzarinoRoadSpline", "M80StreetLight", "DecalActor", "M80ExclusionZone", "M80Sidewalk",
              "LandscapeStreamingProxy", "Landscape", "WorldPartitionHLOD", "M80Bougainvillea", "M80Road", "M80Stairs",
              "M80StreetWires", "M80Horizon", "M80Atmosphere", "WorldDataLayers", "WorldPartitionMiniMap",
              "InstancedFoliageActor", "PlayerStart", "CameraActor"}
MIN_SIZE_M = 12.0


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:  # noqa: BLE001
        return "?"


def name(obj):
    return obj.get_path_name() if isinstance(obj, unreal.Object) else (str(obj) if obj else None)


def layer_info(layer):
    if not isinstance(layer, unreal.Object):
        return str(layer) if layer else None
    info = {"path": name(layer)}
    for p in ("layer_type", "is_spatially_loaded", "parent_layer", "hlod_builder_class", "hlod_builder_settings"):
        v = prop(layer, p)
        info[p] = name(v) if isinstance(v, unreal.Object) else str(v)
    settings = prop(layer, "hlod_builder_settings")
    if isinstance(settings, unreal.Object):
        for p in ("hlod_material", "mesh_merge_settings", "mesh_approximation_settings", "mesh_simplify_settings"):
            v = prop(settings, p)
            if v != "?":
                info["settings." + p] = name(v) if isinstance(v, unreal.Object) else str(v)[:300]
    return info


def describe(actor):
    out = {"label": actor.get_actor_label(), "class": actor.get_class().get_name(),
           "hidden_in_game": prop(actor, "hidden"), "spatially_loaded": prop(actor, "is_spatially_loaded"),
           "actor_auto_lod": prop(actor, "enable_auto_lod_generation"),
           "hlod_layer": name(prop(actor, "hlod_layer")) if isinstance(prop(actor, "hlod_layer"), unreal.Object) else str(prop(actor, "hlod_layer")),
           "location": [round(c) for c in actor.get_actor_location().to_tuple()], "components": []}
    for c in actor.get_components_by_class(unreal.PrimitiveComponent):
        comp = {"name": c.get_name(), "class": c.get_class().get_name(), "visible": prop(c, "visible"),
                "hidden_in_game": prop(c, "hidden_in_game"), "auto_lod": prop(c, "enable_auto_lod_generation"),
                "mobility": str(prop(c, "mobility"))}
        if isinstance(c, unreal.StaticMeshComponent):
            mesh = c.get_editor_property("static_mesh")
            comp["mesh"] = name(mesh)
            if mesh:
                nanite = prop(mesh, "nanite_settings")
                comp["nanite"] = prop(nanite, "enabled") if nanite != "?" else "?"
                b = mesh.get_bounding_box()
                comp["mesh_size_m"] = [round((b.max.x - b.min.x) / 100, 1), round((b.max.y - b.min.y) / 100, 1), round((b.max.z - b.min.z) / 100, 1)]
            comp["materials"] = [name(m) for m in c.get_materials()][:8]
            if isinstance(c, unreal.InstancedStaticMeshComponent):
                comp["instances"] = c.get_instance_count()
        out["components"].append(comp)
    return out


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 30
    world = m80_seq.editor_world()
    report = {"default_hlod_layer": layer_info(prop(world.get_world_settings(), "default_hlod_layer"))}
    descs = m80_seq.actor_descs()
    big = []
    for d in descs:
        cls = d.get_editor_property("native_class")
        if cls and cls.get_name() in PROCEDURAL:
            continue
        b = d.get_editor_property("bounds")
        if max(b.max.x - b.min.x, b.max.y - b.min.y) / 100 >= MIN_SIZE_M:
            big.append(d)
    hlods = m80_seq.actor_descs("WorldPartitionHLOD")
    m80_seq.load(big + hlods)
    yield 120
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    labels = {str(d.get_editor_property("label")) for d in big}
    buildings = [a for a in actors if a.get_actor_label() in labels and a.get_class().get_name() != "WorldPartitionHLOD"]
    report["big_descs"] = len(big)
    layers = {}
    report["buildings"] = []
    for a in sorted(buildings, key=lambda x: x.get_actor_label()):
        info = describe(a)
        report["buildings"].append(info)
        lay = prop(a, "hlod_layer")
        if isinstance(lay, unreal.Object):
            layers[name(lay)] = layer_info(lay)
    report["layers"] = layers
    # Which HLOD actors hold each building's meshes (instanced HLODs keep the source meshes).
    meshes = {}
    for info in report["buildings"]:
        for c in info["components"]:
            if c.get("mesh"):
                meshes.setdefault(c["mesh"], set()).add(info["label"])
    held = {}
    hlod_actors = [a for a in actors if a.get_class().get_name() == "WorldPartitionHLOD"]
    report["hlod_actors_loaded"] = len(hlod_actors)
    for h in hlod_actors:
        for c in h.get_components_by_class(unreal.StaticMeshComponent):
            m = name(c.get_editor_property("static_mesh"))
            if m in meshes:
                held.setdefault(m, []).append(h.get_actor_label())
    report["meshes_in_hlods"] = {m: {"buildings": sorted(meshes[m]), "hlod_actors": held.get(m, [])} for m in sorted(meshes)}
    (OUT / "hlod_ispeziona.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "hlod_ispeziona_error.txt"))
