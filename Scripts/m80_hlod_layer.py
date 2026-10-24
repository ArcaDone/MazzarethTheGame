"""The town's HLOD setup: the World Partition's default HLOD layer and the two layers next to the map
(L_M80_Paese_HLODLayer_Merged / _Instanced) with every editor property of the layer and of its builder settings, and
how many actors use each layer. Read only. Out: Saved/Mazzarino80/Memoria/hlod_layer.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_hlod_layer.py -TimeoutMinutes 20
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
LAYERS = ("/Game/Mazzarino80/Houses/Maps/L_M80_Paese_HLODLayer_Merged", "/Game/Mazzarino80/Houses/Maps/L_M80_Paese_HLODLayer_Instanced")


LAYER_PROPS = ("layer_type", "hlod_builder_class", "hlod_builder_settings", "is_spatially_loaded", "parent_layer",
               "hlod_modifier_class", "cell_size", "loading_range", "runtime_grid")
BUILDER_PROPS = ("hlod_material", "mesh_merge_settings", "mesh_simplify_settings", "mesh_approximation_settings",
                 "batch_instance_material", "disallow_nanite", "reuse_previous_material", "texture_size",
                 "nanite_settings", "use_lowest_lod", "single_instance")


def val(v):
    if isinstance(v, unreal.Object):
        return v.get_path_name()
    if isinstance(v, unreal.StructBase):
        out = {}
        for k in v.__class__.__dict__:
            if k.startswith("_"):
                continue
            try:
                out[k] = val(v.get_editor_property(k))
            except Exception:  # noqa: BLE001
                pass
        return out or str(v)
    return v if isinstance(v, (bool, int, float, str)) or v is None else str(v)


def props(obj, names):
    out = {}
    for n in names:
        try:
            out[n] = val(obj.get_editor_property(n))
        except Exception as e:  # noqa: BLE001
            out[n] = "-"
    return out


def dump(layer):
    if layer is None:
        return None
    out = props(layer, LAYER_PROPS)
    try:
        b = layer.get_editor_property("hlod_builder_settings")
        out["builder"] = {"classe": b.get_class().get_name(), **props(b, BUILDER_PROPS)} if b else None
    except Exception:  # noqa: BLE001
        pass
    return out


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    world = m80_seq.editor_world()
    wp = world.get_world_partition() if hasattr(world, "get_world_partition") else None
    rep = {"world_partition": props(wp, ("default_hlod_layer", "enable_streaming")) if wp else None, "layers": {}}
    for p in LAYERS:
        rep["layers"][p] = dump(unreal.load_asset(p))
    counts = {}
    for d in m80_seq.actor_descs():
        try:
            lay = d.get_editor_property("hlod_layer")
        except Exception:  # noqa: BLE001
            lay = "?"
        counts[str(lay)] = counts.get(str(lay), 0) + 1
    rep["attori_per_layer"] = counts
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hlod_layer.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "hlod_layer_errore.txt"))
