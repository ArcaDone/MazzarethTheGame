"""Imports the 1980s clothes made by Research/Mazzarino80/Blender/m80_vestiti.py (Saved/Mazzarino80/Folla/Vestiti/<Key>/)
as MetaHuman parametric outfits, in /Game/Mazzarino80/Personaggi/Vestiti/<Key>/:

- SM_M80_<Key>{,_LOD1,_LOD2,_LOD3}: the garment's render meshes (no Nanite, no collision), two-sided cloth materials;
- DF_M80_<Key> + CA_M80_<Key>: a cloth asset made by a copy of the graph of Epic's default garment (one static mesh per
  LOD, skin weights transferred from the source body, no simulation: render mesh only, cheap for a crowd);
- OA_M80_<Key>: a resizable outfit asset (Epic's MakeResizableOutfitTemplate graph) with one size, the cloth asset on
  its source body (the full body m80_vestiti_sonda.py exported), that the Creator fits to any other body;
- WI_M80_<Key>: the wardrobe item the MetaHuman Characters wear it through.
Env M80_VESTITI=Key1,Key2 (default all). Report: Saved/Mazzarino80/Folla/Vestiti/import_report.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_vestiti_import.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Folla/Vestiti"
DEST = "/Game/Mazzarino80/Personaggi/Vestiti"
BODIES = DEST + "/Corpi"
EPIC = "/MetaHumanCharacter/Optional/Clothing/"
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.M80EditorLibrary
LODS = ["", "_LOD1", "_LOD2", "_LOD3"]
# The default garment graph's nodes, LOD by LOD.
IMPORT_NODES = ["StaticMeshImport", "StaticMeshImport_0", "StaticMeshImport_1", "StaticMeshImport_2"]
SKIN_NODES = ["TransferSkinWeights", "TransferSkinWeights_0", "TransferSkinWeights_1", "TransferSkinWeights_2"]


def keys():
    only = [k for k in os.environ.get("M80_VESTITI", "").split(",") if k]
    found = sorted(p.name for p in SRC.iterdir() if (p / ("SM_M80_%s.fbx" % p.name)).exists())
    return [k for k in found if not only or k in only]


def import_mesh(fbx, dest):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", True)
    ui.set_editor_property("import_textures", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    data = ui.static_mesh_import_data
    data.set_editor_property("combine_meshes", True)
    data.set_editor_property("generate_lightmap_u_vs", False)
    data.set_editor_property("auto_generate_collision", False)
    data.set_editor_property("build_nanite", False)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(fbx))
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    t.set_editor_property("options", ui)
    TOOLS.import_asset_tasks([t])
    return unreal.load_asset("%s/%s" % (dest, fbx.stem))


def copy_of(src, dest):
    if EAL.does_asset_exist(dest):
        EAL.delete_asset(dest)
    return EAL.duplicate_asset(src, dest)


def run():
    report = {}
    for key in keys():
        info = json.loads((SRC / key / ("%s.json" % key)).read_text(encoding="utf-8"))
        dest = "%s/%s" % (DEST, key)
        rep = {"body": info["body"]}
        meshes = []
        for suffix in LODS:
            fbx = SRC / key / ("SM_M80_%s%s.fbx" % (key, suffix))
            meshes.append(import_mesh(fbx, dest) if fbx.exists() else None)
            yield 5
        rep["meshes"] = [m.get_path_name() if m else None for m in meshes]
        # Cloth is seen from inside at cuffs and hems: two-sided. Colour sources as JPEG.
        for path in EAL.list_assets(dest, recursive=True):
            a = unreal.load_asset(path)
            if isinstance(a, unreal.Material):
                a.set_editor_property("two_sided", True)
                unreal.MaterialEditingLibrary.recompile_material(a)
            elif isinstance(a, unreal.Texture2D):
                n = a.get_name().lower()
                if "nor" not in n and "nrm" not in n:
                    LIB.compress_texture_source_jpeg(a, 90)
        # The LODs wear LOD0's materials (each FBX made its own copy).
        mats = [m.get_editor_property("material_interface") for m in meshes[0].get_editor_property("static_materials")]
        for m in meshes[1:]:
            if m:
                for i, mat in enumerate(mats[:len(m.get_editor_property("static_materials"))]):
                    m.set_material(i, mat)
        body = unreal.load_asset("%s/MHC_%s_FullBody" % (BODIES, info["body"]))
        rep["source_body"] = body.get_path_name() if body else None

        graph = copy_of(EPIC + "DefaultGarment/ClothAssets/DF_DG_bodyShapeA", "%s/DF_M80_%s" % (dest, key))
        lod_meshes = [m or meshes[0] for m in meshes]
        rep["graph_set"] = [LIB.set_dataflow_node_property(graph, n, "StaticMesh", "StaticMesh'%s'" % m.get_path_name())
                            for n, m in zip(IMPORT_NODES, lod_meshes)]
        rep["graph_set"] += [LIB.set_dataflow_node_property(graph, n, "SkeletalMesh", "SkeletalMesh'%s'" % body.get_path_name())
                             for n in SKIN_NODES]
        cloth = copy_of(EPIC + "DefaultGarment/ClothAssets/CA_DG_bodyShapeA", "%s/CA_M80_%s" % (dest, key))
        rep["cloth_built"] = LIB.rebuild_asset_from_dataflow(cloth, graph, "ClothAssetTerminal")
        yield 10

        outfit = copy_of(EPIC + "OA_DefaultGarment", "%s/OA_M80_%s" % (dest, key))
        rep["outfit_built"] = LIB.set_outfit_sizes(outfit, [cloth], [info["body"]], [body])
        yield 10
        item = copy_of(EPIC + "WI_DefaultGarment", "%s/WI_M80_%s" % (dest, key))
        before = LIB.get_object_property_text(item, "PrincipalAsset")
        rep["item_before"] = before
        old_path = EPIC + "OA_DefaultGarment.OA_DefaultGarment"
        rep["item_set"] = LIB.set_object_property_text(item, "PrincipalAsset",
                                                       before.replace(old_path, outfit.get_path_name()))
        rep["item_after"] = LIB.get_object_property_text(item, "PrincipalAsset")
        for a in (graph, cloth, outfit, item, *[m for m in meshes if m]):
            EAL.save_loaded_asset(a, False)
        report[key] = rep
        (SRC / "import_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        yield 5
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    (SRC / "import_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(SRC / "import_error.txt"))
