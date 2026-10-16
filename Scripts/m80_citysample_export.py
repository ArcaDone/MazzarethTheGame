"""Runs in the City Sample project (UE 5.5), not in ours: exports the crowd garments (normal weight, man and woman)
as FBX, the two bodies they are fitted to (only as the fitting reference for our bodies, not used in the game),
every texture of their materials as TGA, and a report of each garment's material slots (instance, parent,
texture/scalar/vector parameters).
Out: Saved/Mazzarino80/CitySample/{fbx,tex}/ and report.json in our project.
The skeletal mesh FBX export needs the renderer: run the full editor on the empty map (the script quits it):
"D:/UE_5.5/Engine/Binaries/Win64/UnrealEditor.exe" "D:/UE5Projects/CitySample/CitySample.uproject" /Game/NewMap
    -ExecCmds="py D:/UE5Projects/GameAnimationSample/Scripts/m80_citysample_export.py" -nosplash
"""
import json
from pathlib import Path

import unreal

OUT = Path("D:/UE5Projects/GameAnimationSample/Saved/Mazzarino80/CitySample")
SETS = {
    "m": ("/Game/Crowd/Character/Male/NormalWeight/Meshes/", "m_tal_nrw_"),
    "f": ("/Game/Crowd/Character/Female/NormalWeight/Meshes/", "f_tal_nrw_"),
}
SKIP = ("base", "combined")


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:  # noqa: BLE001
        return None


def export(obj, path, options=None):
    task = unreal.AssetExportTask()
    task.object = obj
    task.filename = str(path)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if options:
        task.options = options
    path.parent.mkdir(parents=True, exist_ok=True)
    return unreal.Exporter.run_asset_export_task(task)


def material_info(m, textures):
    out = {"name": m.get_path_name() if m else None}
    chain = m
    while isinstance(chain, unreal.MaterialInstance):
        for p in prop(chain, "texture_parameter_values") or []:
            name = str(p.get_editor_property("parameter_info").get_editor_property("name"))
            tex = p.get_editor_property("parameter_value")
            out.setdefault("textures", {}).setdefault(name, tex.get_path_name() if tex else None)
            if tex:
                textures.add(tex)
        for p in prop(chain, "scalar_parameter_values") or []:
            out.setdefault("scalars", {}).setdefault(str(p.get_editor_property("parameter_info").get_editor_property("name")),
                                                     p.get_editor_property("parameter_value"))
        for p in prop(chain, "vector_parameter_values") or []:
            out.setdefault("vectors", {}).setdefault(str(p.get_editor_property("parameter_info").get_editor_property("name")),
                                                     str(p.get_editor_property("parameter_value")))
        chain = prop(chain, "parent")
        out.setdefault("parents", []).append(chain.get_path_name() if chain else None)
    return out


def main():
    fbx = unreal.FbxExportOption()
    fbx.set_editor_property("ascii", False)
    fbx.set_editor_property("level_of_detail", False)
    fbx.set_editor_property("export_morph_targets", False)
    fbx.set_editor_property("export_preview_mesh", False)
    fbx.set_editor_property("collision", False)
    report = {"meshes": {}, "textures": {}}
    textures = set()
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for key, (folder, prefix) in SETS.items():
        reg.scan_paths_synchronous([folder], True)
        for data in reg.get_assets_by_path(folder, recursive=False):
            name = str(data.asset_name)
            part = name[len(prefix):] if name.startswith(prefix) else name
            if part in SKIP:
                continue
            mesh = data.get_asset()
            if not isinstance(mesh, unreal.SkeletalMesh):
                continue
            entry = {"part": part, "fbx": export(mesh, OUT / "fbx" / (name + ".fbx"), fbx)}
            entry["materials"] = [dict(material_info(s.get_editor_property("material_interface"), textures),
                                       slot=str(s.get_editor_property("material_slot_name")))
                                  for s in mesh.get_editor_property("materials")]
            report["meshes"][name] = entry
    for tex in textures:
        report["textures"][tex.get_path_name()] = export(tex, OUT / "tex" / (tex.get_name() + ".tga"))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


try:
    main()
except Exception:  # noqa: BLE001
    import traceback
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "errore.txt").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    unreal.SystemLibrary.quit_editor()
