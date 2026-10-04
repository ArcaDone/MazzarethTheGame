"""Import the larger overview meshes without assuming synchronous Interchange tasks."""

import unreal

root = r"D:/UE5Projects/GameAnimationSample/Research/Mazzarino80/generated/"
dest = "/Game/Mazzarino80/Overview"
for name in ("M80_Strade", "M80_Edifici"):
    task = unreal.AssetImportTask()
    task.filename = root + name + ".obj"
    task.destination_path = dest
    task.destination_name = name + "_Mesh"
    task.automated = True
    task.save = True
    task.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    unreal.log("M80_IMPORT_SUBMITTED " + name + " " + str(task.imported_object_paths))
