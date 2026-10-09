"""Imports the noble balcony kit (Research/Mazzarino80/Blender/M80_Balconi.fbx, m80_balcony_kit.py -- moduli).

- /Game/Mazzarino80/Kit/Balconi: slabs with their back plate, consoles, motifs between consoles (Nanite, baked
  textures: colour, normal, ORM; one instance of the baked master M_M80_Lamp each) and the straight and
  goose-breast railings at 180/240/300 cm (rusty painted iron of the stairs kit, MI_M80_Ferro).
- The house builder composes them ("Balcone signorile" in the facade rules); M80_Balconi.json has the sizes.
Collision: slabs a box (to stand on), railings their own bars, consoles and carved panels none (under the slab).
Report: Saved/Mazzarino80/balconies_report.json (bounds of every mesh, to check pivots and orientation).
Env M80_BALCONIES_SETTINGS_ONLY=1: no import, only materials, Nanite and collision of the meshes already there.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_balconies_setup.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
SRC = ROOT / "Research/Mazzarino80/Blender"
KIT = "/Game/Mazzarino80/Kit/Balconi"
MASTER = "/Game/Mazzarino80/Kit/Lamps/M_M80_Lamp"          # baked colour / normal / ORM master
IRON = "/Game/Mazzarino80/Kit/Stairs/MI_M80_Ferro"
REPORT = ROOT / "Saved/Mazzarino80/balconies_report.json"
SETTINGS_ONLY = os.environ.get("M80_BALCONIES_SETTINGS_ONLY", "") == "1"
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary


def import_files(files, options=None):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(f))
        t.set_editor_property("destination_path", KIT)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("automated", True)
        t.set_editor_property("save", False)
        if options:
            t.set_editor_property("options", options)
        tasks.append(t)
    TOOLS.import_asset_tasks(tasks)


def run():
    manifest = json.loads((SRC / "M80_Balconi.json").read_text(encoding="utf-8"))
    report = {}
    fbx = unreal.FbxImportUI()
    fbx.set_editor_property("import_mesh", True)
    fbx.set_editor_property("import_materials", False)
    fbx.set_editor_property("import_textures", False)
    fbx.set_editor_property("import_as_skeletal", False)
    fbx.static_mesh_import_data.set_editor_property("combine_meshes", False)
    fbx.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    if not SETTINGS_ONLY:
        import_files([SRC / "M80_Balconi.fbx"], fbx)
        import_files(sorted((SRC / "Textures/Balconi").glob("T_M80_Balcone_*")))
        yield 10
    master = unreal.load_asset(MASTER)
    iron = unreal.load_asset(IRON)
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    baked = [m["mesh"] for group in ("slabs", "consoles", "decors") for m in manifest[group].values()]
    rails = [m["mesh"] for m in manifest["railings"].values()]
    for name in baked:
        tex = name.replace("SM_", "T_")
        n = unreal.load_asset("%s/%s_N" % (KIT, tex))
        n.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        n.set_editor_property("srgb", False)
        orm = unreal.load_asset("%s/%s_ORM" % (KIT, tex))
        orm.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        orm.set_editor_property("srgb", False)
        for t in (n, orm, unreal.load_asset("%s/%s_D" % (KIT, tex))):
            EAL.save_loaded_asset(t, False)
        mi_name = name.replace("SM_", "MI_")
        mi_path = "%s/%s" % (KIT, mi_name)
        mi = unreal.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else \
            TOOLS.create_asset(mi_name, KIT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, master)
        for param, key in (("Colore", "D"), ("Normali", "N"), ("ORM", "ORM")):
            MEL.set_material_instance_texture_parameter_value(mi, param, unreal.load_asset("%s/%s_%s" % (KIT, tex, key)))
        EAL.save_loaded_asset(mi, False)
    yield 5
    for name in baked + rails:
        mesh = unreal.load_asset("%s/%s" % (KIT, name))
        if not mesh:
            report[name] = "missing"
            continue
        mat = iron if name in rails else unreal.load_asset("%s/%s" % (KIT, name.replace("SM_", "MI_")))
        for i in range(len(mesh.get_editor_property("static_materials"))):
            mesh.set_material(i, mat)
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", True)
        sub.set_nanite_settings(mesh, settings, apply_changes=True)
        # A box to stand on the slab; the railing's own bars (a box would fill the balcony); nothing on
        # the carved parts under the slab.
        sub.remove_collisions(mesh)
        body = mesh.get_editor_property("body_setup")
        if "_Lastra_" in name:
            sub.add_simple_collisions(mesh, unreal.ScriptCollisionShapeType.BOX)
        if body:
            body.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
                                     if name in rails else unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
        EAL.save_loaded_asset(mesh, False)
        box = mesh.get_bounding_box()
        report[name] = {"min": [round(box.min.x, 1), round(box.min.y, 1), round(box.min.z, 1)],
                        "max": [round(box.max.x, 1), round(box.max.y, 1), round(box.max.z, 1)]}
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
