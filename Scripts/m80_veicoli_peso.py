"""How heavy each drivable vehicle is: triangles and vertices per LOD, materials, bones, from the skeletal meshes.
Out: Saved/Mazzarino80/Veicoli/peso.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_veicoli_peso.py
"""
import json
from pathlib import Path

import unreal

OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Veicoli"
ROOTS = ["/Game/Drive", "/Game/Mazzarino80/Vehicles"]


def main():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    report = {}
    for root in ROOTS:
        for data in reg.get_assets_by_path(root, recursive=True):
            if str(data.asset_class_path.asset_name) != "SkeletalMesh":
                continue
            mesh = data.get_asset()
            entry = {"tags": {t: str(data.get_tag_value(t)) for t in ("Vertices", "Triangles", "LODs", "Bones")}}
            lods = sub.get_lod_count(mesh)
            entry["lods"] = [sub.get_num_verts(mesh, i) for i in range(lods)]
            entry["materials"] = len(mesh.get_editor_property("materials"))
            report[str(data.package_name)] = entry
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "peso.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


try:
    main()
finally:
    unreal.SystemLibrary.quit_editor()
