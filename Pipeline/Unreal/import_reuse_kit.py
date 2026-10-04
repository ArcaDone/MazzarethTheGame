"""Import the Blender kit into a separate UE5 staging folder for PCG review.

Pilot meshes are QA-only. Reusable source modules stay independent and no
existing PCG graph or building mesh is replaced by this script.
"""
from pathlib import Path
import json

import unreal

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/unreal_export/export_manifest.json"
OUT = ROOT / "Pipeline/Unreal/reuse_import_result.json"
data = json.loads(MANIFEST.read_text(encoding="utf-8"))
BASE = "/Game/Mazzarino80/ReuseKit"
HISTORIC = "/Game/Mazzarino80/Historic/Materials/"
MATERIAL_PATHS = {
    "stone": HISTORIC + "M80_Muratura_locale_0",
    "formal": HISTORIC + "M80_Pietra_modesta",
    "plaster": HISTORIC + "M80_Calce_consumata_2",
    "wood": HISTORIC + "M80_Legno_persiane_1",
    "iron": HISTORIC + "M80_Ferro_ossidato",
    "glass": HISTORIC + "M80_Vetro_ombra",
    "tile": HISTORIC + "M80_Coppi_vecchi",
    "cloth": HISTORIC + "M80_Tessuto_sbiadito",
    "ground": HISTORIC + "M80_Vicolo_pietra_consumata",
    "plant": "/Game/Megapack/Material/Favela/Plants/M_Plant_01",
}


def classify(slot):
    name = str(slot).lower()
    if any(piece in name for piece in ("glass", "vetro", "reflective")):
        return "glass"
    if any(piece in name for piece in ("plant", "leaf", "bark", "moss")):
        return "plant"
    if any(piece in name for piece in ("terracotta", "roof", "tile", "tegole")):
        return "tile"
    if any(piece in name for piece in ("cloth", "tessuto")):
        return "cloth"
    if any(piece in name for piece in ("iron", "metal", "pipe", "shutter", "black", "rust")):
        return "iron"
    if "proxy_mat_grey" in name:
        return "plaster"
    if any(piece in name for piece in ("wood", "marone", "legno")):
        return "wood"
    if any(piece in name for piece in ("plaster", "calce")):
        return "plaster"
    if any(piece in name for piece in ("paving", "soil", "asphalt")):
        return "ground"
    if any(piece in name for piece in ("formal", "marble")):
        return "formal"
    return "stone"


loaded_materials = {key: unreal.EditorAssetLibrary.load_asset(path)
                    for key, path in MATERIAL_PATHS.items()}
missing_materials = [key for key, asset in loaded_materials.items() if asset is None]
if missing_materials:
    raise RuntimeError("Missing shared materials: " + ", ".join(missing_materials))


def import_one(record, folder, force=False):
    file = Path(record["file"])
    if not file.is_file():
        raise FileNotFoundError(file)
    package = f"{BASE}/{folder}/{file.stem}"
    mesh = unreal.EditorAssetLibrary.load_asset(package)
    if mesh is None or force:
        options = unreal.FbxImportUI()
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        mesh_options = options.get_editor_property("static_mesh_import_data")
        mesh_options.set_editor_property("combine_meshes", True)
        mesh_options.set_editor_property("generate_lightmap_u_vs", False)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(file))
        task.set_editor_property("destination_path", f"{BASE}/{folder}")
        task.set_editor_property("destination_name", file.stem)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        task.set_editor_property("replace_existing", force)
        task.set_editor_property("options", options)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = unreal.EditorAssetLibrary.load_asset(package)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("StaticMesh import failed: " + package)

    slots = [str(slot.material_slot_name) for slot in mesh.get_editor_property("static_materials")]
    for index, name in enumerate(slots):
        mesh.set_material(index, loaded_materials[classify(name)])
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Unable to save material assignments: " + package)
    bounds = mesh.get_bounds()
    dimensions = [round(2 * getattr(bounds.box_extent, axis), 2)
                  for axis in ("x", "y", "z")]
    return {"asset": package, "dimensions_cm": dimensions, "slots": slots,
            "material_groups": [classify(slot) for slot in slots],
            "source_file": str(file), "qa_only": folder == "Pilots"}


report = {"source_manifest": str(MANIFEST), "materials": MATERIAL_PATHS,
          "modules": [], "pilots": [], "pilot_stages": []}
for record in data["modules"]:
    report["modules"].append(import_one(record, "Modules"))
for record in data["pilots"]:
    report["pilots"].append(import_one(record, "Pilots"))
for record in data.get("pilot_stages", []):
    report["pilot_stages"].append(import_one(record, "PilotStages"))
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("M80_REUSE_IMPORT", len(report["modules"]), "modules",
      len(report["pilots"]), "pilots", len(report["pilot_stages"]), "stages", OUT)
