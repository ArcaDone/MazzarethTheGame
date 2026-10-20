"""Imports the 1970s-80s road lamp "a frusta" (D:/Mazzarino80_Sorgenti/Lampioni/M80_LampioneFrusta.fbx, made by
Research/Mazzarino80/Blender/m80_lampione_frusta.py) into /Game/Mazzarino80/Kit/Lamps for the kind "A frusta" of
"Lampione (Mazzarino)":
- SM_M80_Frusta_Palo (the 1 m pole the actor stretches) and SM_M80_Frusta_Testa (bend, arm, luminaire);
- MI_M80_Frusta_Palo (light grey painted steel) and MI_M80_Frusta_Armatura (aluminium), children of the stairs kit's
  colour master M_M80_KitColore;
- MI_M80_Frusta_VetroSodio (orange) and MI_M80_Frusta_VetroMercurio (bluish white), children of the lamps' glass
  M_M80_LampGlass, lit by the "Lampioni" value of MPC_M80_Atmosfera.
Report: Saved/Mazzarino80/lampione_frusta.json.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_lampione_frusta_setup.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
FBX = "D:/Mazzarino80_Sorgenti/Lampioni/M80_LampioneFrusta.fbx"
KIT = "/Game/Mazzarino80/Kit/Lamps"
REPORT = ROOT / "Saved/Mazzarino80/lampione_frusta.json"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
COLOUR_MASTER = "/Game/Mazzarino80/Kit/Stairs/M_M80_KitColore"
GLASS_MASTER = KIT + "/M_M80_LampGlass"
# name -> (colour, roughness, metallic)
PAINT = {"Frusta_Palo": ((0.42, 0.43, 0.42), 0.55, 0.35), "Frusta_Armatura": ((0.5, 0.5, 0.48), 0.4, 0.7)}
# name -> light colour of the glowing bowl
GLASS = {"Frusta_VetroSodio": (1.0, 0.42, 0.1), "Frusta_VetroMercurio": (0.72, 0.88, 1.0)}


def instance(name, parent):
    path = "%s/MI_M80_%s" % (KIT, name)
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        TOOLS.create_asset("MI_M80_" + name, KIT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(parent))
    MEL.clear_all_material_instance_parameters(mi)
    return mi


def import_lamp():
    """Meshes and materials; returns the report."""
    fbx = unreal.FbxImportUI()
    fbx.set_editor_property("import_mesh", True)
    fbx.set_editor_property("import_materials", False)
    fbx.set_editor_property("import_textures", False)
    fbx.set_editor_property("import_as_skeletal", False)
    fbx.static_mesh_import_data.set_editor_property("combine_meshes", False)
    fbx.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", FBX)
    task.set_editor_property("destination_path", KIT)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", fbx)
    TOOLS.import_asset_tasks([task])
    mats = {}
    for name, (rgb, rough, metal) in PAINT.items():
        mi = instance(name, COLOUR_MASTER)
        MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(*rgb, 1))
        MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", rough)
        MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", metal)
        EAL.save_loaded_asset(mi, False)
        mats[name] = mi
    for name, rgb in GLASS.items():
        mi = instance(name, GLASS_MASTER)
        MEL.set_material_instance_vector_parameter_value(mi, "Colore luce", unreal.LinearColor(*rgb, 1))
        EAL.save_loaded_asset(mi, False)
        mats[name] = mi
    slot_mat = {"palo": mats["Frusta_Palo"], "armatura": mats["Frusta_Armatura"], "vetro": mats["Frusta_VetroSodio"]}
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    report = {}
    for mesh_name in ("SM_M80_Frusta_Palo", "SM_M80_Frusta_Testa"):
        mesh = unreal.load_asset("%s/%s" % (KIT, mesh_name))
        if not mesh:
            report[mesh_name] = "not imported"
            continue
        names = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("static_materials")]
        for i, n in enumerate(names):
            mesh.set_material(i, slot_mat.get(n.lower(), mats["Frusta_Palo"]))
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", True)
        sub.set_nanite_settings(mesh, settings, apply_changes=True)
        EAL.save_loaded_asset(mesh, False)
        box = mesh.get_bounding_box()
        report[mesh_name] = {"slots": names, "min": [round(box.min.x), round(box.min.y), round(box.min.z)],
                             "max": [round(box.max.x), round(box.max.y), round(box.max.z)]}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


def steps():
    import_lamp()
    yield 5


if __name__ == "__main__":
    m80_seq.Sequencer(steps(), log_file=str(REPORT.with_suffix(".error.txt")))
