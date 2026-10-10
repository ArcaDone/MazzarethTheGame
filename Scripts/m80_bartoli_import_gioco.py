"""Imports the game version of Palazzo Bartoli (Research/Mazzarino80/Blender/m80_bartoli_gioco.py ->
Saved/Mazzarino80/Bartoli/Gioco) into /Game/Mazzarino80/Buildings/Bartoli (it replaced the first, baked version): the
meshes keep their names (SM_M80_Bartoli_<group>, _Dettagli, Tetti, Tetti_Colmi, Volumi), so the actors already placed in
the town take the new geometry.

- Master Materiali/M_M80_BartoliTile: colour, normal and ORM of a tiling set laid in metres (UV0 x ScalaU, ScalaV =
  1/period), colour x Tinta x occlusion x Sporco (the facade's dirt map on UV1, white elsewhere), roughness and metal from
  ORM. Its default textures match the sampler types (colour, normal, masks), so it compiles.
- Textures (TexGioco/T_<set>_{D,N,ORM}, <facade>_sporco): normals with the green channel flipped (Blender writes OpenGL
  normals), ORM and dirt as masks; colour, ORM and dirt sources stored as JPEG.
- One instance per material slot (Materiali/MI_M80_BG_<slot>); glass on the houses' glass, brass, water and the dark
  plates behind the openings on colour instances of M_M80_Veicolo.
- Meshes: Nanite, except the fittings (_Dettagli: thin slats and bars) and the ridge rows, which get 3 LODs; collision
  from their own triangles.
Report: Saved/Mazzarino80/Bartoli/Gioco/import_report.json

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bartoli_import_gioco.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
EXPORT = ROOT / "Saved/Mazzarino80/Bartoli/Gioco"
TEX_SRC = ROOT / "Research/Mazzarino80/Blender/Textures/BartoliGioco"
DEST = "/Game/Mazzarino80/Buildings/Bartoli"
TEX = DEST + "/TexGioco"
MATS = DEST + "/Materiali"
MASTER = MATS + "/M_M80_BartoliTile"
WHITE = TEX + "/T_M80_BiancoLineare"
REPORT = EXPORT / "import_report.json"
GENERIC = "/Game/Mazzarino80/Vehicles/Materials/M_M80_Veicolo"
GLASS = "/Game/Mazzarino80/Houses/Materials/M_M80_HouseGlass"
# Flat materials of the model: colour, metal, roughness.
FLAT = {"G_Ottone": ((0.55, 0.42, 0.18), 1.0, 0.35), "G_Interno_buio": ((0.03, 0.025, 0.02), 0.0, 0.9),
        "G_Acqua": ((0.05, 0.08, 0.09), 0.0, 0.1)}
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
MP = unreal.MaterialProperty


def import_file(file, dest, name):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", dest)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    TOOLS.import_asset_tasks([t])
    return unreal.load_asset("%s/%s" % (dest, name))


def texture(file, kind):
    """kind: D (colour), N (OpenGL normal), M (masks: ORM, dirt)."""
    name = os.path.splitext(os.path.basename(file))[0]
    tex = import_file(file, TEX, name)
    if kind == "N":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("flip_green_channel", True)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif kind == "M":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    if kind != "N":
        unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
    EAL.save_loaded_asset(tex, False)
    return tex


def white_texture():
    if EAL.does_asset_exist(WHITE):
        return unreal.load_asset(WHITE)
    png = EXPORT / "T_M80_BiancoLineare.png"
    # 4x4 white PNG, written by hand (no imaging library in the editor's Python).
    import struct
    import zlib
    raw = b"".join(b"\x00" + b"\xff\xff\xff" * 4 for _ in range(4))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)) +
                    chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    tex = import_file(png, TEX, "T_M80_BiancoLineare")
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    EAL.save_loaded_asset(tex, False)
    return tex


def master():
    if EAL.does_asset_exist(MASTER):
        return unreal.load_asset(MASTER)
    white = white_texture()
    m = TOOLS.create_asset("M_M80_BartoliTile", MATS, unreal.Material, unreal.MaterialFactoryNew())

    def expr(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e
    uv0 = expr(unreal.MaterialExpressionTextureCoordinate, -1400, 0)
    su = expr(unreal.MaterialExpressionScalarParameter, -1400, 120, parameter_name="ScalaU", default_value=0.5)
    sv = expr(unreal.MaterialExpressionScalarParameter, -1400, 220, parameter_name="ScalaV", default_value=0.5)
    scale = expr(unreal.MaterialExpressionAppendVector, -1200, 160)
    MEL.connect_material_expressions(su, "", scale, "A")
    MEL.connect_material_expressions(sv, "", scale, "B")
    uv = expr(unreal.MaterialExpressionMultiply, -1000, 60)
    MEL.connect_material_expressions(uv0, "", uv, "A")
    MEL.connect_material_expressions(scale, "", uv, "B")
    st = unreal.MaterialSamplerType
    col = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, -200, parameter_name="TexColore",
               sampler_type=st.SAMPLERTYPE_COLOR, texture=unreal.load_asset("/Engine/EngineResources/DefaultTexture"))
    nor = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, 150, parameter_name="TexNormali",
               sampler_type=st.SAMPLERTYPE_NORMAL, texture=unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"))
    orm = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, 450, parameter_name="TexORM",
               sampler_type=st.SAMPLERTYPE_MASKS, texture=white)
    for t in (col, nor, orm):
        MEL.connect_material_expressions(uv, "", t, "UVs")
    uv1 = expr(unreal.MaterialExpressionTextureCoordinate, -1000, 750, coordinate_index=1)
    dirt = expr(unreal.MaterialExpressionTextureSampleParameter2D, -700, 750, parameter_name="Sporco",
                sampler_type=st.SAMPLERTYPE_MASKS, texture=white)
    MEL.connect_material_expressions(uv1, "", dirt, "UVs")
    tint = expr(unreal.MaterialExpressionVectorParameter, -700, -420, parameter_name="Tinta",
                default_value=unreal.LinearColor(1, 1, 1, 1))
    a = expr(unreal.MaterialExpressionMultiply, -350, -250)
    MEL.connect_material_expressions(col, "RGB", a, "A")
    MEL.connect_material_expressions(tint, "", a, "B")
    b = expr(unreal.MaterialExpressionMultiply, -200, -150)
    MEL.connect_material_expressions(a, "", b, "A")
    MEL.connect_material_expressions(orm, "R", b, "B")
    c = expr(unreal.MaterialExpressionMultiply, -50, -50)
    MEL.connect_material_expressions(b, "", c, "A")
    MEL.connect_material_expressions(dirt, "RGB", c, "B")
    MEL.connect_material_property(c, "", MP.MP_BASE_COLOR)
    MEL.connect_material_property(orm, "G", MP.MP_ROUGHNESS)
    MEL.connect_material_property(orm, "B", MP.MP_METALLIC)
    MEL.connect_material_property(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(nor, "RGB", MP.MP_NORMAL)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def instance(name, parent):
    path = "%s/%s" % (MATS, name)
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        TOOLS.create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    return mi


def import_fbx(file):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    data = ui.static_mesh_import_data
    data.set_editor_property("combine_meshes", False)
    data.set_editor_property("generate_lightmap_u_vs", False)
    data.set_editor_property("auto_generate_collision", False)
    data.set_editor_property("build_nanite", True)
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", DEST)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    t.set_editor_property("options", ui)
    TOOLS.import_asset_tasks([t])


def settings(mesh, nanite):
    st = mesh.get_editor_property("nanite_settings")
    st.set_editor_property("enabled", nanite)
    SUB.set_nanite_settings(mesh, st, apply_changes=True)
    if not nanite:
        opts = unreal.StaticMeshReductionOptions()
        opts.set_editor_property("auto_compute_lod_screen_size", True)
        opts.set_editor_property("reduction_settings", [unreal.StaticMeshReductionSettings(p, 0.0) for p in (1.0, 0.5, 0.25)])
        SUB.set_lods(mesh, opts)
    SUB.remove_collisions(mesh)
    body = mesh.get_editor_property("body_setup")
    if body:
        body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    EAL.save_loaded_asset(mesh, False)


def run():
    m = json.loads((EXPORT / "M80_Bartoli_Gioco.json").read_text(encoding="utf-8"))
    report = {"meshes": {}, "missing_slots": {}, "instances": []}
    import_fbx(EXPORT / m["fbx"])
    yield 10
    base = master()
    sets = {}

    def tset(record):
        name = os.path.splitext(record["files"]["D"])[0][2:-2]
        if name not in sets:
            sets[name] = {k: texture(TEX_SRC / f, {"D": "D", "N": "N", "ORM": "M"}[k]) for k, f in record["files"].items()}
        return sets[name]
    terra = m["sets"].get("Terra")
    mats = {}

    def material_for(slot):
        if slot in mats:
            return mats[slot]
        rec = m["materials"].get(slot)
        if slot == "G_Vetro":
            mi = unreal.load_asset(GLASS)
        elif rec is None:
            colour, metal, rough = FLAT.get(slot, ((0.5, 0.5, 0.5), 0.0, 0.8))
            mi = instance("MI_M80_BG_" + slot[2:], unreal.load_asset(GENERIC))
            MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(*colour, 1))
            MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", metal)
            MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", rough)
            EAL.save_loaded_asset(mi, False)
        else:
            # Flower beds came out on the plaster set (their own small high-poly patch): they are soil.
            record = terra if "aiuola" in slot and terra else rec["set"]
            tint = None if "aiuola" in slot else rec.get("tint")
            tex = tset(record)
            mi = instance("MI_M80_BG_" + slot[2:], base)
            MEL.set_material_instance_texture_parameter_value(mi, "TexColore", tex["D"])
            MEL.set_material_instance_texture_parameter_value(mi, "TexNormali", tex["N"])
            MEL.set_material_instance_texture_parameter_value(mi, "TexORM", tex["ORM"])
            MEL.set_material_instance_scalar_parameter_value(mi, "ScalaU", 1.0 / record["period"][0])
            MEL.set_material_instance_scalar_parameter_value(mi, "ScalaV", 1.0 / record["period"][1])
            if tint:
                MEL.set_material_instance_vector_parameter_value(mi, "Tinta", unreal.LinearColor(*tint, 1))
            if slot.startswith("G_Muro_"):
                dirt = TEX_SRC / ("%s_sporco.png" % slot[len("G_Muro_"):])
                if dirt.exists():
                    MEL.set_material_instance_texture_parameter_value(mi, "Sporco", texture(dirt, "M"))
            EAL.save_loaded_asset(mi, False)
            report["instances"].append(mi.get_name())
        mats[slot] = mi
        return mi
    for name, info in m["meshes"].items():
        mesh = unreal.load_asset("%s/%s" % (DEST, name))
        if not mesh:
            report["missing_slots"][name] = ["<mesh not imported>"]
            continue
        missing = []
        for i, sm in enumerate(mesh.get_editor_property("static_materials")):
            slot = str(sm.get_editor_property("material_slot_name"))
            if slot in m["materials"] or slot == "G_Vetro" or slot in FLAT:
                mesh.set_material(i, material_for(slot))
            else:
                missing.append(slot)
        report["missing_slots"][name] = missing
        settings(mesh, not (name.endswith("_Dettagli") or name.endswith("_Colmi")))
        b = mesh.get_bounding_box()
        report["meshes"][name] = {"min": [round(b.min.x), round(b.min.y), round(b.min.z)], "max": [round(b.max.x), round(b.max.y), round(b.max.z)],
                                  "triangles": info["triangles"]}
        yield 1
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
