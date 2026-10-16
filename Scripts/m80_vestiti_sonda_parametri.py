"""Probe for "Sandro's light blue shirt renders yellow": what a character's preview instance stores about its outfits
(every property of the instance and of the collection whose name speaks of parameters, overrides or materials,
and the parameters the instance exposes for each selected item), plus the shirt instance's own Tinta.
Env M80_CHI=Key (default Sandro), M80_CAPO=Garment (default CS_CamiciaGiacca).
Out: Saved/Mazzarino80/Folla/Vestiti/Prova/sonda_parametri.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_vestiti_sonda_parametri.py
"""
import json
import os
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Folla/Vestiti/Prova"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
WHO = os.environ.get("M80_CHI", "Sandro")
WHAT = os.environ.get("M80_CAPO", "CS_CamiciaGiacca")
FOLDER = {"Sandro": "Sandro"}
WORDS = ("param", "override", "material", "color", "colour", "tint", "selection", "instance")


def dump(obj):
    out = {}
    for name in dir(obj):
        if name.startswith("_") or not any(w in name.lower() for w in WORDS):
            continue
        try:
            attr = getattr(obj, name)
        except Exception as e:  # noqa: BLE001
            out[name] = "getattr: " + repr(e)
            continue
        if callable(attr):
            out[name] = "(method)"
            continue
        out[name] = str(attr)[:2000]
    for prop in ("slot_selections", "override_instance_parameters", "instance_parameters", "pipeline_parameters"):
        try:
            out["prop:" + prop] = str(obj.get_editor_property(prop))[:4000]
        except Exception as e:  # noqa: BLE001
            out["prop:" + prop] = repr(e)[:200]
    return out


def main():
    report = {}
    c = unreal.load_asset("/Game/Mazzarino80/Personaggi/%s/MHC_%s" % (FOLDER.get(WHO, "Folla"), WHO))
    SUB.try_add_object_to_edit(c)
    coll = SUB.get_preview_collection(c)
    inst = coll.get_editor_property("default_instance")
    report["instance"] = dump(inst)
    report["collection"] = dump(coll)
    report["character"] = dump(c)
    try:
        paths = inst.get_instance_parameter_item_paths()
        report["item_paths"] = [str(x) for x in paths]
        for ip in paths:
            params = inst.get_instance_parameters(ip)
            entry = report.setdefault("params", {}).setdefault(str(ip), [])
            for prm in params:
                row = {"repr": str(prm)[:300]}
                for attr in dir(prm):
                    if attr.startswith("_"):
                        continue
                    try:
                        val = getattr(prm, attr)
                        row[attr] = "(method)" if callable(val) else str(val)[:200]
                    except Exception as e:  # noqa: BLE001
                        row[attr] = repr(e)[:100]
                for getter in ("get_color", "get_float", "get_bool", "get_name", "get_type"):
                    fn = getattr(prm, getter, None)
                    if fn:
                        try:
                            row[getter] = str(fn())[:200]
                        except Exception as e:  # noqa: BLE001
                            row[getter] = repr(e)[:120]
                entry.append(row)
    except Exception as e:  # noqa: BLE001
        report["params_error"] = repr(e)
    try:
        report["slot_selection_data"] = str(inst.get_slot_selection_data())[:4000]
    except Exception as e:  # noqa: BLE001
        report["slot_selection_data"] = repr(e)[:300]
    for method in ("get_all_instance_parameters", "get_slot_selections_data"):
        fn = getattr(inst, method, None)
        if fn:
            try:
                report["call:" + method] = str(fn())[:6000]
            except Exception as e:  # noqa: BLE001
                report["call:" + method] = repr(e)[:300]
    mi = unreal.load_asset("/Game/Mazzarino80/Personaggi/Vestiti/%s/MI_M80_Cotone_Camicia" % WHAT)
    if mi:
        report["mi_vectors"] = {str(p.get_editor_property("parameter_info").get_editor_property("name")):
                                str(p.get_editor_property("parameter_value")) for p in mi.get_editor_property("vector_parameter_values")}
        report["mi_textures"] = {str(p.get_editor_property("parameter_info").get_editor_property("name")):
                                 str(p.get_editor_property("parameter_value").get_path_name() if p.get_editor_property("parameter_value") else None)
                                 for p in mi.get_editor_property("texture_parameter_values")}
    SUB.remove_object_to_edit(c)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda_parametri.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


try:
    main()
finally:
    unreal.SystemLibrary.quit_editor()
