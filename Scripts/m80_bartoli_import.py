"""Imports Palazzo Bartoli (Research/Mazzarino80/Blender/m80_bartoli_bake.py -> Saved/Mazzarino80/Bartoli/Export) into
/Game/Mazzarino80/Buildings/Bartoli.

- SM_M80_Bartoli_<group>: the retopologised facades, staircase, carriage passage, courtyard and gardens, each with its
  baked colour / normal / ORM (Textures/T_Bartoli_<group>_*) on an instance of the baked master M_M80_Lamp. Nanite.
- SM_M80_Bartoli_<group>_Dettagli: shutters, glass, doors, iron, signs, eave tiles. The materials the town already has
  are reused, so they match the procedural houses: iron and roller shutters on the stairs kit iron and the houses' iron,
  shutters on the houses' painted wood, glass on the houses' glass, eave tiles on the houses' coppi; the rest
  (doors, frames, signs, brass) gets an instance of M_M80_Veicolo with the Blender colour. No Nanite (thin slats and bars
  bend), 3 LODs.
- SM_M80_Bartoli_Tetti (+ _Colmi): the houses' tiling coppi; SM_M80_Bartoli_Volumi: dark volumes behind the facades,
  parapets on the houses' plaster and rubble.
Collision: every mesh its own triangles (walk in the courtyard and up the staircase).
Level /Game/Mazzarino80/Buildings/Bartoli/L_M80_PalazzoBartoli: all the pieces at origin_world_cm (where the lot is
in the town), for a first look; the town itself is not touched.
Report: Saved/Mazzarino80/Bartoli/import_report.json

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_bartoli_import.py
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
EXPORT = ROOT / "Saved/Mazzarino80/Bartoli/Export"
TEX_SRC = ROOT / "Research/Mazzarino80/Blender/Textures/Bartoli"
DEST = "/Game/Mazzarino80/Buildings/Bartoli"
TEX = DEST + "/Textures"
MAP = DEST + "/L_M80_PalazzoBartoli"
REPORT = ROOT / "Saved/Mazzarino80/Bartoli/import_report.json"
BAKED = "/Game/Mazzarino80/Kit/Lamps/M_M80_Lamp"
GENERIC = "/Game/Mazzarino80/Vehicles/Materials/M_M80_Veicolo"
HM = "/Game/Mazzarino80/Houses/Materials"
STAIRS = "/Game/Mazzarino80/Kit/Stairs"
# Blender material -> town material (same look as the procedural houses and the kits).
TOWN = {
    "Ferro": STAIRS + "/MI_M80_Ferro",
    "Serranda": HM + "/MI_M80_Iron",
    "Persiane_verdi": HM + "/MI_M80_Wood_Painted",
    "Vetro": HM + "/M_M80_HouseGlass",
    "Coppi": HM + "/MI_M80_Roof_Coppi",
    "Intonaco_crema": HM + "/MI_M80_Wall_Plaster",
    "Pietrame_interno": HM + "/MI_M80_Wall_Rubble",
    "Macerie": HM + "/MI_M80_Wall_Rubble",
}
MANIFEST = os.environ.get("M80_BARTOLI_MANIFEST", "M80_Bartoli.json")
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
SUB = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def import_texture(file, kind):
    name = os.path.splitext(os.path.basename(file))[0]
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", str(file))
    t.set_editor_property("destination_path", TEX)
    t.set_editor_property("destination_name", name)
    t.set_editor_property("automated", True)
    t.set_editor_property("replace_existing", True)
    t.set_editor_property("save", False)
    TOOLS.import_asset_tasks([t])
    tex = unreal.load_asset(TEX + "/" + name)
    if kind == "N":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    elif kind == "ORM":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    if kind != "N":
        unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
    EAL.save_loaded_asset(tex, False)
    return tex


def instance(name, parent):
    path = "%s/%s" % (DEST, name)
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        TOOLS.create_asset(name, DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(parent))
    return mi


def colour_instance(name, info):
    mi = instance("MI_M80_Bartoli_" + name, GENERIC)
    c = info.get("color", [0.5, 0.5, 0.5])
    MEL.set_material_instance_vector_parameter_value(mi, "Colore", unreal.LinearColor(c[0], c[1], c[2], 1))
    MEL.set_material_instance_scalar_parameter_value(mi, "Metallo", info.get("metal", 0.0))
    MEL.set_material_instance_scalar_parameter_value(mi, "Ruvidita", info.get("rough", 0.8))
    e = info.get("emission", 0.0)
    if e:
        MEL.set_material_instance_vector_parameter_value(mi, "Emissivo", unreal.LinearColor(c[0] * e, c[1] * e, c[2] * e, 1))
    EAL.save_loaded_asset(mi, False)
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


def assign(mesh, by_slot):
    missing = []
    for i, sm in enumerate(mesh.get_editor_property("static_materials")):
        slot = str(sm.get_editor_property("material_slot_name"))
        mat = by_slot.get(slot)
        if mat is None and len(by_slot) == 1:
            mat = list(by_slot.values())[0]
        if mat:
            mesh.set_material(i, mat)
        else:
            missing.append(slot)
    return missing


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
    m = json.loads((EXPORT / MANIFEST).read_text(encoding="utf-8"))
    report = {"meshes": {}, "missing_slots": {}}
    import_fbx(EXPORT / m["fbx"])
    yield 10
    colours = {}

    def material_for(slot):
        if slot in TOWN:
            return unreal.load_asset(TOWN[slot])
        if slot not in colours:
            colours[slot] = colour_instance(slot, m.get("materials", {}).get(slot, {}))
        return colours[slot]

    placed = []
    for name, g in m["groups"].items():
        tex = {k: import_texture(TEX_SRC / f, k) for k, f in g["textures"].items()}
        mi = instance("MI_M80_Bartoli_" + name, BAKED)
        for param, key in (("Colore", "D"), ("Normali", "N"), ("ORM", "ORM")):
            MEL.set_material_instance_texture_parameter_value(mi, param, tex[key])
        EAL.save_loaded_asset(mi, False)
        mesh = unreal.load_asset("%s/%s" % (DEST, g["mesh"]))
        report["missing_slots"][g["mesh"]] = assign(mesh, {"": mi})
        settings(mesh, True)
        placed.append(mesh)
        d = m["details"].get(name)
        if d:
            dm = unreal.load_asset("%s/%s" % (DEST, d["mesh"]))
            report["missing_slots"][d["mesh"]] = assign(dm, {s: material_for(s) for s in d["slots"]})
            settings(dm, False)
            placed.append(dm)
        yield 2
    for key in ("roofs", "volumes"):
        if key not in m:
            continue
        info = m[key]
        names = [info["mesh"]] + ([info["ridges"]] if info.get("ridges") else [])
        for n in names:
            mesh = unreal.load_asset("%s/%s" % (DEST, n))
            slots = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("static_materials")]
            report["missing_slots"][n] = assign(mesh, {s: material_for(s if key == "volumes" else "Coppi") for s in slots})
            settings(mesh, key == "roofs" and n == info["mesh"] or key == "volumes")
            placed.append(mesh)
    for mesh in placed:
        b = mesh.get_bounding_box()
        report["meshes"][mesh.get_name()] = {"min": [round(b.min.x), round(b.min.y), round(b.min.z)],
                                             "max": [round(b.max.x), round(b.max.y), round(b.max.z)],
                                             "nanite": mesh.get_editor_property("nanite_settings").get_editor_property("enabled")}
    yield 5
    # A level with the palace where it stands in the town (no landscape: a first look at the pieces).
    if EAL.does_asset_exist(MAP):
        EAL.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    ox, oy, oz = m["origin_world_cm"]
    for mesh in placed:
        a = EAS.spawn_actor_from_object(mesh, unreal.Vector(ox, oy, oz))
        a.set_actor_label(mesh.get_name().replace("SM_M80_", ""))
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(ox, oy, oz + 3000))
    # Sun from the south-east: the Corso fronts face south (+Y in Unreal).
    sun.set_actor_rotation(unreal.Rotator(pitch=-40.0, yaw=-110.0, roll=0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(ox, oy, oz))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(ox, oy, oz + 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
