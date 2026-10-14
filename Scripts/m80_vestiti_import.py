"""Imports the 1980s clothes made by Research/Mazzarino80/Blender/m80_vestiti.py (Saved/Mazzarino80/Folla/Vestiti/<Key>/)
as MetaHuman parametric outfits, in /Game/Mazzarino80/Personaggi/Vestiti/<Key>/:

- SM_M80_<Key>{,_LOD1,_LOD2,_LOD3}: the garment's render meshes (no Nanite, no collision), wearing instances of
  Materiali/M_M80_Stoffa (made here if missing): the Cloth shading model (a fuzz that lightens the fabric at grazing
  angles, what tells wool from leather), matt, Epic's MetaHuman micro weave or knit normals, two-sided; the fabric
  (wool, cotton, knit, leather) from the Blender material's name;
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
MASTER = DEST + "/Materiali/M_M80_Stoffa"
MICROS = "/MetaHumanCharacter/Optional/Clothing/Common/Materials/Textures/Clothing/Micros/"
MEL = unreal.MaterialEditingLibrary
# Fabric by the Blender material's name prefix: roughness, specular, fuzz (Cloth pin), fuzz colour as a multiple of the
# cloth's plus a brightening (strong fuzz greys black wool), micro normal, its repeats per texture tile, its strength.
FABRICS = {
    "Lana": (0.92, 0.2, 0.5, 1.3, 0.012, "micro_weave_plain_normal", 24.0, 0.8),
    "Cotone": (0.85, 0.3, 0.4, 1.2, 0.02, "micro_poplin_N", 30.0, 0.6),
    "Maglia": (0.95, 0.2, 0.7, 1.4, 0.02, "micro_knit_front_N", 10.0, 1.0),
    "Seta": (0.6, 0.35, 0.3, 1.2, 0.01, "micro_weave_plain_normal", 40.0, 0.4),
    "Jeans": (0.85, 0.3, 0.5, 1.3, 0.015, "micro_weave_denim_N", 20.0, 0.9),
    "Cuoio": (0.5, 0.4, 0.0, 1.0, 0.0, None, 1.0, 0.0),
    "Oro": (0.25, 1.0, 0.0, 1.0, 0.0, None, 1.0, 0.0),       # the master has no metal: a bright specular instead
}
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
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
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


def master():
    """M_M80_Stoffa: Colore x Tinta for the base colour, Cloth shading with a fuzz of the same colour brightened,
    a micro normal tiled DettaglioScala times per UV unit and blended in by DettaglioForza; two-sided."""
    if EAL.does_asset_exist(MASTER):
        return unreal.load_asset(MASTER)
    folder, name = MASTER.rsplit("/", 1)
    m = TOOLS.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLOTH)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("used_with_skeletal_mesh", True)

    def expr(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def scalar(name, value, x, y):
        return expr(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value)

    colour = expr(unreal.MaterialExpressionTextureSampleParameter2D, -900, -300, parameter_name="Colore",
                  texture=unreal.load_asset("/Engine/EngineResources/WhiteSquareTexture"))
    tint = expr(unreal.MaterialExpressionVectorParameter, -900, -100, parameter_name="Tinta",
                default_value=unreal.LinearColor(1, 1, 1, 1))
    base = expr(unreal.MaterialExpressionMultiply, -600, -250)
    MEL.connect_material_expressions(colour, "RGB", base, "A")
    MEL.connect_material_expressions(tint, "", base, "B")
    MEL.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    # Fuzz: the fibres catch light at grazing angles, a little lighter than the cloth.
    fuzz_mul = expr(unreal.MaterialExpressionMultiply, -400, 0)
    MEL.connect_material_expressions(base, "", fuzz_mul, "A")
    MEL.connect_material_expressions(scalar("FuzzMolt", 1.8, -600, 50), "", fuzz_mul, "B")
    fuzz = expr(unreal.MaterialExpressionAdd, -250, 0)
    MEL.connect_material_expressions(fuzz_mul, "", fuzz, "A")
    MEL.connect_material_expressions(scalar("FuzzAggiunta", 0.06, -400, 100), "", fuzz, "B")
    MEL.connect_material_property(fuzz, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    LIB.connect_material_input(scalar("Fuzz", 1.0, -250, 150), "", "MP_CustomData0")   # the Cloth input
    MEL.connect_material_property(scalar("Ruvidita", 0.9, -250, 220), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(scalar("Specular", 0.25, -250, 290), "", unreal.MaterialProperty.MP_SPECULAR)
    # Micro weave normal.
    uv = expr(unreal.MaterialExpressionTextureCoordinate, -1100, 400)
    tiled = expr(unreal.MaterialExpressionMultiply, -900, 400)
    MEL.connect_material_expressions(uv, "", tiled, "A")
    MEL.connect_material_expressions(scalar("DettaglioScala", 24.0, -1100, 480), "", tiled, "B")
    micro = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, 400, parameter_name="DettaglioNormale",
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
                 texture=unreal.load_asset(MICROS + "micro_weave_plain_normal"))
    MEL.connect_material_expressions(tiled, "", micro, "UVs")
    flat = expr(unreal.MaterialExpressionConstant3Vector, -700, 650, constant=unreal.LinearColor(0, 0, 1, 1))
    blend = expr(unreal.MaterialExpressionLinearInterpolate, -400, 450)
    MEL.connect_material_expressions(flat, "", blend, "A")
    MEL.connect_material_expressions(micro, "RGB", blend, "B")
    MEL.connect_material_expressions(scalar("DettaglioForza", 0.8, -700, 720), "", blend, "Alpha")
    MEL.connect_material_property(blend, "", unreal.MaterialProperty.MP_NORMAL)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def fabric_instance(parent, mat_name, texture, dest):
    kind = next((k for k in FABRICS if mat_name.startswith(k)), "Lana")
    rough, spec, fuzz, fuzz_mul, fuzz_add, micro, scale, strength = FABRICS[kind]
    path = "%s/MI_M80_%s" % (dest, mat_name)
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    mi = TOOLS.create_asset(path.rsplit("/", 1)[1], dest, unreal.MaterialInstanceConstant,
                            unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", parent)
    if texture:
        MEL.set_material_instance_texture_parameter_value(mi, "Colore", texture)
    for name, value in (("Ruvidita", rough), ("Specular", spec), ("Fuzz", fuzz), ("FuzzMolt", fuzz_mul), ("FuzzAggiunta", fuzz_add),
                        ("DettaglioScala", scale), ("DettaglioForza", strength)):
        MEL.set_material_instance_scalar_parameter_value(mi, name, value)
    if micro:
        MEL.set_material_instance_texture_parameter_value(mi, "DettaglioNormale", unreal.load_asset(MICROS + micro))
    EAL.save_loaded_asset(mi, False)
    return mi


def copy_of(src, dest):
    """A copy of Epic's asset, made once: a re-import updates it in place (the characters wearing an outfit keep it;
    M80EditorLibrary releases what the 5.8 engine forgets before rebuilding a loaded outfit)."""
    if EAL.does_asset_exist(dest):
        return unreal.load_asset(dest)
    copy = EAL.duplicate_asset(src, dest)
    if copy is None:
        raise RuntimeError("can't copy %s to %s" % (src, dest))
    return copy


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
        # The fabric texture of each material, T_M80_<Key>_<material> (imported from the PNGs, colour sources as
        # JPEG; the FBX importer skips textures it thinks it has).
        slots = meshes[0].get_editor_property("static_materials")
        names = [str(sl.get_editor_property("material_slot_name")) for sl in slots]
        wanted = {"T_M80_%s_%s" % (key, n) for n in names}     # not the PNGs of materials since renamed
        textures = {}
        for png in sorted(p for p in (SRC / key / "Textures").glob("*.png") if p.stem in wanted):
            t = unreal.AssetImportTask()
            t.set_editor_property("filename", str(png))
            t.set_editor_property("destination_path", dest)
            t.set_editor_property("automated", True)
            t.set_editor_property("replace_existing", True)
            t.set_editor_property("save", False)
            TOOLS.import_asset_tasks([t])
            a = unreal.load_asset("%s/%s" % (dest, png.stem))
            if a:
                LIB.compress_texture_source_jpeg(a, 90)
                textures[a.get_name()] = a
        # Every LOD wears the fabric instances (the FBX import's own Phong instances are left unused).
        parent = master()
        mats = [fabric_instance(parent, n, textures.get("T_M80_%s_%s" % (key, n)), dest) for n in names]
        rep["materials"] = [m.get_name() for m in mats]
        rep["textures"] = sorted(textures)
        for m in meshes:
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
        target = outfit.get_path_name()
        rep["item_set"] = LIB.set_object_property_text(item, "PrincipalAsset",
                                                       '(Asset="%s",AssetIdentifier="%s")' % (target, target))
        rep["item_after"] = LIB.get_object_property_text(item, "PrincipalAsset")
        for a in (graph, cloth, outfit, item, *[m for m in meshes if m]):
            EAL.save_loaded_asset(a, False)
        report[key] = rep
        (SRC / "import_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        yield 5
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    (SRC / "import_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(SRC / "import_error.txt"))
