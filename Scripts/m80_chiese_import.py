"""Imports the churches made ready by Research/Mazzarino80/Blender/m80_chiese_gioco.py (Saved/Mazzarino80/Chiese/<Key>/)
into /Game/Mazzarino80/Buildings/Chiese/<Key>.

- Meshes SM_M80_<Key> (Nanite) and SM_M80_<Key>_Dettagli (iron, glass, bells, gilding: 3 LODs), collision from their
  own triangles.
- Materials: one instance per slot (MI_M80_<Key>_<slot>) on Palazzo Bartoli's tiling master M_M80_BartoliTile with the
  shared tiling sets: Bartoli's (Buildings/Bartoli/TexGioco) when the set exists there, new ones (majolica, cotto,
  bricks) imported once into /Game/Mazzarino80/Materiali/Ripetibili; the church's dirt map (T_M80_<Key>_Sporco) on the
  walls; bronze and gold on colour instances of M_M80_Veicolo, glass on the houses' glass.
Env M80_CHIESE=Key1,Key2 (default: every church with a manifest). Report: Saved/Mazzarino80/Chiese/import_report.json

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_chiese_import.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Saved/Mazzarino80/Chiese"
BLENDER = ROOT / "Research/Mazzarino80/Blender"
SET_SRC = BLENDER / "Textures/BartoliGioco"
DEST = "/Game/Mazzarino80/Buildings/Chiese"
BARTOLI_TEX = "/Game/Mazzarino80/Buildings/Bartoli/TexGioco"
SHARED_TEX = "/Game/Mazzarino80/Materiali/Ripetibili"
MASTER = "/Game/Mazzarino80/Buildings/Bartoli/Materiali/M_M80_BartoliTile"
GENERIC = "/Game/Mazzarino80/Vehicles/Materials/M_M80_Veicolo"
GLASS = "/Game/Mazzarino80/Houses/Materials/M_M80_HouseGlass"
REPORT = SRC / "import_report.json"
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


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


def texture(file, dest, kind):
    """kind: D (colour), N (OpenGL normal), M (masks: ORM, dirt)."""
    name = os.path.splitext(os.path.basename(file))[0]
    tex = import_file(file, dest, name)
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


def tiling_set(name, record):
    """The three textures of a tiling set: Bartoli's if there, else the shared folder (imported the first time)."""
    out = {}
    for key, kind in (("D", "D"), ("N", "N"), ("ORM", "M")):
        asset = "T_%s_%s" % (name, key)
        for folder in (BARTOLI_TEX, SHARED_TEX):
            if EAL.does_asset_exist("%s/%s" % (folder, asset)):
                out[key] = unreal.load_asset("%s/%s" % (folder, asset))
                break
        else:
            out[key] = texture(SET_SRC / record["files"][key], SHARED_TEX, kind)
    return out


def instance(path, parent):
    folder, name = path.rsplit("/", 1)
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        TOOLS.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    return mi


def import_fbx(file, dest):
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
    t.set_editor_property("destination_path", dest)
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


def keys():
    only = [k for k in os.environ.get("M80_CHIESE", "").split(",") if k]
    found = sorted(p.name for p in SRC.iterdir() if (p / ("SM_M80_%s.fbx" % p.name)).exists())
    return [k for k in found if not only or k in only]


def run():
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
    base = unreal.load_asset(MASTER)
    for key in keys():
        m = json.loads((SRC / key / ("%s.json" % key)).read_text(encoding="utf-8"))
        dest = "%s/%s" % (DEST, key)
        import_fbx(SRC / key / m["fbx"], dest)
        yield 10
        dirt = texture(BLENDER / m["dirt_dir"] / m["dirt"], dest, "M")
        rep = {"meshes": {}, "missing_slots": {}}
        mats = {}

        def material_for(slot, walls):
            k = (slot, walls)
            if k in mats:
                return mats[k]
            info = m["materials"][slot]
            name = "MI_M80_%s_%s%s" % (key, slot, "" if walls else "_d")
            if info["kind"] == "glass":
                mi = unreal.load_asset(GLASS)
            elif info["kind"] == "flat":
                mi = instance("%s/%s" % (dest, name), unreal.load_asset(GENERIC))
                MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(*info["color"], 1))
                MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", info["metal"])
                MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", info["rough"])
                EAL.save_loaded_asset(mi, False)
            else:
                record = m["sets"][info["set"]]
                tex = tiling_set(info["set"], record)
                mi = instance("%s/%s" % (dest, name), base)
                MEL.set_material_instance_texture_parameter_value(mi, "TexColore", tex["D"])
                MEL.set_material_instance_texture_parameter_value(mi, "TexNormali", tex["N"])
                MEL.set_material_instance_texture_parameter_value(mi, "TexORM", tex["ORM"])
                MEL.set_material_instance_scalar_parameter_value(mi, "ScalaU", 1.0 / record["period"][0])
                MEL.set_material_instance_scalar_parameter_value(mi, "ScalaV", 1.0 / record["period"][1])
                if info.get("tint"):
                    MEL.set_material_instance_vector_parameter_value(mi, "Tinta", unreal.LinearColor(*info["tint"], 1))
                if walls:
                    MEL.set_material_instance_texture_parameter_value(mi, "Sporco", dirt)
                EAL.save_loaded_asset(mi, False)
            mats[k] = mi
            return mi
        for name, info in m["meshes"].items():
            mesh = unreal.load_asset("%s/%s" % (dest, name))
            if not mesh:
                rep["missing_slots"][name] = ["<mesh not imported>"]
                continue
            missing = []
            for i, sm in enumerate(mesh.get_editor_property("static_materials")):
                slot = str(sm.get_editor_property("material_slot_name"))
                s = slot.replace("GM_%s_" % key, "")
                if s in m["materials"]:
                    mesh.set_material(i, material_for(s, info["nanite"]))
                else:
                    missing.append(slot)
            rep["missing_slots"][name] = missing
            settings(mesh, info["nanite"])
            b = mesh.get_bounding_box()
            rep["meshes"][name] = {"min": [round(b.min.x), round(b.min.y), round(b.min.z)],
                                   "max": [round(b.max.x), round(b.max.y), round(b.max.z)], "triangles": info["triangles"]}
            yield 1
        report[key] = rep
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
        yield 5
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(SRC / "import_error.txt"))
