"""The recovered lamps made usable as "Lampione (Mazzarino)" kinds that light up at dusk like the town's own:
copies of /Game/Migrated/Lamp_city and /Game/Migrated/Madonna/Lampione (the originals stay as they are: the Comune's and
the Madonna's wall Blueprints use them) in /Game/Mazzarino80/Kit/Lamps as SM_M80_LampCity and SM_M80_LampioneMadonna,
the glass on M_M80_LampGlass (glows with the "Lampioni" value of MPC_M80_Atmosfera: off by day, on at night; it was an
always-on emissive on Lamp_city and the editor's landscape lighting material on the Lampione), the Lampione's grey
template metal turned into the kit's wrought iron, a box collision (they stand in the street). Each copy is also
exported to OBJ (Saved/Mazzarino80/Lampioni) to measure where its glass is.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_lampioni_migrati.py
Report: Saved/Mazzarino80/Lampioni/migrati.json
"""
import json
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Lampioni"
KIT = "/Game/Mazzarino80/Kit/Lamps"
GLASS = KIT + "/M_M80_LampGlass"
IRON = "/Game/Mazzarino80/Kit/Stairs/MI_M80_Ferro"
# copy name: (original, glass slot, {slot: replacement material})
LAMPS = {"SM_M80_LampCity": ("/Game/Migrated/Lamp_city", 0, {}),
         "SM_M80_LampioneMadonna": ("/Game/Migrated/Madonna/Lampione", 1, {0: IRON})}
EAL = unreal.EditorAssetLibrary
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, (src, glass_slot, other) in LAMPS.items():
        dest = KIT + "/" + name
        mesh = unreal.load_asset(dest) if EAL.does_asset_exist(dest) else EAL.duplicate_asset(src, dest)
        slots = list(mesh.get_editor_property("static_materials"))
        for i, s in enumerate(slots):
            path = GLASS if i == glass_slot else other.get(i)
            if path:
                s.set_editor_property("material_interface", unreal.load_asset(path))
                slots[i] = s
        mesh.set_editor_property("static_materials", slots)
        SUB.remove_collisions(mesh)
        SUB.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        EAL.save_loaded_asset(mesh)
        bb = mesh.get_bounding_box()
        task = unreal.AssetExportTask()
        task.set_editor_property("object", mesh)
        task.set_editor_property("filename", str(OUT / (name + ".obj")))
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_identical", True)
        task.set_editor_property("prompt", False)
        exported = unreal.Exporter.run_asset_export_task(task)
        report[name] = {"source": src, "box": [[round(v, 1) for v in (bb.min.x, bb.min.y, bb.min.z)], [round(v, 1) for v in (bb.max.x, bb.max.y, bb.max.z)]],
                        "slots": [[str(s.get_editor_property("material_slot_name")), s.get_editor_property("material_interface").get_path_name()] for s in slots],
                        "obj": exported}
    (OUT / "migrati.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


try:
    run()
finally:
    unreal.SystemLibrary.quit_editor()
