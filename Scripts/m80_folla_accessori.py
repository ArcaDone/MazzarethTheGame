"""Imports the crowd's accessories (Research/Mazzarino80/Blender/m80_accessori_folla.py: walking stick, shopping bag,
handbag) as static meshes in /Game/Mazzarino80/Personaggi/Accessori, each material slot an instance of the vehicles'
generic master (M_M80_Veicolo: Colore, Ruvidita, Metallo) with the colour from accessori.json.
Report: Saved/Mazzarino80/Folla/accessori.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_folla_accessori.py
"""
import json
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Folla/Accessori"
DEST = "/Game/Mazzarino80/Personaggi/Accessori"
MASTER = "/Game/Mazzarino80/Vehicles/Materials/M_M80_Veicolo"
NAMES = ["SM_M80_Bastone", "SM_M80_BorsaSpesa", "SM_M80_Borsetta"]
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def import_mesh(name):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.static_mesh_import_data.set_editor_property("combine_meshes", True)
    ui.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(SRC / (name + ".fbx")))
    t.set_editor_property("destination_path", DEST)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", True)
    t.set_editor_property("options", ui)
    TOOLS.import_asset_tasks([t])
    return unreal.load_asset(DEST + "/" + name)


def instance(slot, spec):
    path = "%s/Materiali/MI_M80_Acc_%s" % (DEST, slot)
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "MI_M80_Acc_" + slot, DEST + "/Materiali", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(MASTER))
    c = spec["color"]
    MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(c[0], c[1], c[2], 1))
    MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", spec.get("roughness", 0.5))
    MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", spec.get("metallic", 0.0))
    EAL.save_loaded_asset(mi, False)
    return mi


def main():
    specs = json.loads((SRC / "accessori.json").read_text(encoding="utf-8"))
    report = {}
    for name in NAMES:
        mesh = import_mesh(name)
        if not mesh:
            report[name] = "not imported"
            continue
        slots = []
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(sm.get_editor_property("material_slot_name"))
            key = next((k for k in specs if slot.startswith(k)), None)
            if key:
                mesh.set_material(i, instance(key, specs[key]))
            slots.append([slot, key])
        EAL.save_loaded_asset(mesh, False)
        box = mesh.get_bounding_box()
        report[name] = {"slots": slots, "min": str(box.min), "max": str(box.max)}
    (ROOT / "Saved/Mazzarino80/Folla/accessori.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    (ROOT / "Saved/Mazzarino80/Folla/accessori_errore.txt").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    unreal.SystemLibrary.quit_editor()
