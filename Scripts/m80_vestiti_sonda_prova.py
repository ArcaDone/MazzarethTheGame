"""Probe: what a dressed character wears in the Creator (slot selections, hair) and the materials its garments
render with (cloth asset materials, instance parents and texture parameters) - for test photos that look wrong.
Env M80_CHI=Key[,Key] (default Sandro), M80_CAPO=Garment[,Garment] (default CamiciaSandro).
Out: Saved/Mazzarino80/Folla/Vestiti/Prova/sonda_prova.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_vestiti_sonda_prova.py
"""
import json
import os
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Folla/Vestiti/Prova"
SUB = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
MEL = unreal.MaterialEditingLibrary
WHO = [k for k in os.environ.get("M80_CHI", "Sandro").split(",") if k]
WHAT = [k for k in os.environ.get("M80_CAPO", "CamiciaSandro").split(",") if k]
FOLDER = {"Sandro": "Sandro"}


def material_info(m):
    out = {"name": m.get_path_name() if m else None}
    if isinstance(m, unreal.MaterialInstance):
        parent = m.get_editor_property("parent")
        out["parent"] = parent.get_path_name() if parent else None
        out["textures"] = {str(p.get_editor_property("parameter_info").get_editor_property("name")):
                           (p.get_editor_property("parameter_value").get_path_name()
                            if p.get_editor_property("parameter_value") else None)
                           for p in m.get_editor_property("texture_parameter_values")}
        out["vectors"] = {str(p.get_editor_property("parameter_info").get_editor_property("name")):
                          str(p.get_editor_property("parameter_value"))
                          for p in m.get_editor_property("vector_parameter_values")}
    return out


def main():
    report = {"garments": {}, "characters": {}}
    for g in WHAT:
        base = "/Game/Mazzarino80/Personaggi/Vestiti/%s/" % g
        entry = report["garments"].setdefault(g, {})
        mesh = unreal.load_asset(base + "SM_M80_" + g)
        if mesh:
            entry["mesh"] = [material_info(s.get_editor_property("material_interface"))
                             for s in mesh.get_editor_property("static_materials")]
        cloth = unreal.load_asset(base + "CA_M80_" + g)
        if cloth:
            try:
                entry["cloth"] = [material_info(m.get_editor_property("material_interface"))
                                  for m in cloth.get_editor_property("materials")]
            except Exception as e:  # noqa: BLE001
                entry["cloth"] = repr(e)
    for key in WHO:
        c = unreal.load_asset("/Game/Mazzarino80/Personaggi/%s/MHC_%s" % (FOLDER.get(key, "Folla"), key))
        if c is None:
            continue
        SUB.try_add_object_to_edit(c)
        coll = SUB.get_preview_collection(c)
        inst = coll.get_editor_property("default_instance")
        entry = report["characters"].setdefault(key, {})
        for slot in ("Hair", "Eyebrows", "Beard", "Mustache", "Outfits"):
            try:
                entry[slot] = str(inst.get_slot_selection(slot))
            except Exception as e:  # noqa: BLE001
                try:
                    entry[slot] = str(inst.get_editor_property("slot_selections"))
                except Exception as e2:  # noqa: BLE001
                    entry[slot] = repr(e) + " / " + repr(e2)
        SUB.remove_object_to_edit(c)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sonda_prova.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


try:
    main()
finally:
    unreal.SystemLibrary.quit_editor()
