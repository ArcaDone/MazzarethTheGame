"""The castle's hand-made LODs into its meshes (/Game/Migrated/Castello, the pieces of the Blueprint CastelCompleted):
Nanite off (with it the castle turns black from far away), so LOD0 is the mesh's full source; then the LODs of
Research/Mazzarino80/Blender/m80_castello_lod.py (Saved/Mazzarino80/Castello/lod/out/<piece>_LOD<n>.fbx), each copied
into the mesh with the mesh's own materials. Those files start from what Unreal exported, which for a Nanite mesh is
its simplified fallback: when the source is much denser, that file becomes LOD1 and the others follow. The LODs switch
at SCREEN_SIZES. The fallback must sit on the mesh (bounds within TOLERANCE_CM), or that piece only loses Nanite; so does a piece whose slots share one material (the base and the low walls:
the Blueprint gives each slot its own stone, and a LOD's sections could not be told apart). The Blueprint and its overrides are untouched.
Nothing is saved unless M80_SALVA=1. Out: Saved/Mazzarino80/Castello/lod/ue.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_castello_lod.py -TimeoutMinutes 20
"""
import json
import os
import re
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
LOD_DIR = ROOT / "Saved/Mazzarino80/Castello/lod"
FOLDER = "/Game/Migrated/Castello"
TMP = "/Game/M80_Tmp_CastelloLOD"
# LOD0, LOD1...: share of the screen height the mesh's bounds cover when that LOD starts
SCREEN_SIZES = [1.0, 0.5, 0.3, 0.15, 0.06]
# the fallback is simplified, so its box may be a little off the source's
TOLERANCE_CM = 30.0
FULL_VS_FALLBACK = 1.3
SAVE = os.environ.get("M80_SALVA") == "1"
BOXES = {}
SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def import_fbx(path, name):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = TMP
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    data = ui.get_editor_property("static_mesh_import_data")
    data.set_editor_property("combine_meshes", True)
    data.set_editor_property("auto_generate_collision", False)
    data.set_editor_property("build_nanite", False)
    task.options = ui
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return unreal.load_asset("%s/%s" % (TMP, name))


def same_bounds(a, b):
    ba, bb = a.get_bounding_box(), b.get_bounding_box()
    d = max(abs(x - y) for x, y in zip((ba.min.x, ba.min.y, ba.min.z, ba.max.x, ba.max.y, ba.max.z),
                                       (bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z)))
    BOXES[a.get_name()] = [[round(v, 2) for v in (ba.min.x, ba.min.y, ba.min.z, ba.max.x, ba.max.y, ba.max.z)],
                           [round(v, 2) for v in (bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z)],
                           [round(v, 2) for v in (b.get_editor_property("positive_bounds_extension").x, b.get_editor_property("negative_bounds_extension").x)]]
    return d, d <= TOLERANCE_CM


def base(name):
    """A material name as the FBX round trip left it (WorldGridMaterial.003 -> WorldGridMaterial)."""
    return re.sub(r"(\.\d+|_\d+)$", "", name)


def give_materials(tmp, dest):
    """The temporary mesh's slots get the destination's materials (matched by name, else in order), so the LOD copy
    reuses the destination's slots instead of adding new ones."""
    dmats = [m.get_editor_property("material_interface") for m in dest.get_editor_property("static_materials")]
    for i, slot in enumerate(tmp.get_editor_property("static_materials")):
        mi = slot.get_editor_property("material_interface")
        name = base(str(slot.get_editor_property("material_slot_name")) or (mi.get_name() if mi else ""))
        match = next((d for d in dmats if d and d.get_name() == name), None)
        tmp.set_material(i, match or dmats[min(i, len(dmats) - 1)])


def steps():
    lods = json.loads((LOD_DIR / "out/lod.json").read_text(encoding="utf-8"))
    rep = {"salvato": SAVE, "pezzi": {}}
    for piece, counts in sorted(lods.items()):
        dest = unreal.load_asset("%s/%s" % (FOLDER, piece))
        entry = rep["pezzi"].setdefault(piece, {"lod_file": counts})
        # Nanite off first: the mesh is then drawn from its full source, not from Nanite's simplified fallback
        ns = SMS.get_nanite_settings(dest)
        ns.set_editor_property("enabled", False)
        SMS.set_nanite_settings(dest, ns, True)
        # LODs from an earlier run go (only LOD0 is kept)
        SMS.remove_lods(dest)
        yield 2
        full = dest.get_num_triangles(0)
        ref = import_fbx(LOD_DIR / "out" / ("%s_LOD0.fbx" % piece), piece + "_LOD0")
        yield 2
        dist, ok = same_bounds(ref, dest)
        entry["scarto_lod0_cm"] = round(dist, 2)
        entry["triangoli_sorgente"] = full
        if not ok:
            entry["nota"] = "il LOD0 del file non combacia con la mesh: solo Nanite spento"
            continue
        dmats = [m.get_editor_property("material_interface") for m in dest.get_editor_property("static_materials")]
        if len(set(dmats)) < len(dmats):
            # slots sharing a material (the Blueprint gives each its own): a LOD's sections can't be told apart
            entry["nota"] = "slot con lo stesso materiale: solo Nanite spento"
            continue
        # the file's LOD0 is the fallback Unreal exported: when the source is much denser it becomes LOD1
        first = 1 if full > FULL_VS_FALLBACK * counts["LOD0"] else 0
        files = ["%s_LOD%d" % (piece, k) for k in range(len(counts))][1 - first:]
        slots_before = len(dest.get_editor_property("static_materials"))
        for n, name in enumerate(files, start=1):
            tmp = ref if name.endswith("_LOD0") else import_fbx(LOD_DIR / "out" / (name + ".fbx"), name)
            yield 2
            give_materials(tmp, dest)
            entry.setdefault("copiati", []).append([name, SMS.set_lod_from_static_mesh(dest, n, tmp, 0, True)])
        SMS.set_lod_screen_sizes(dest, SCREEN_SIZES[:dest.get_num_lods()])
        entry["lod"] = dest.get_num_lods()
        entry["triangoli"] = [dest.get_num_triangles(i) for i in range(dest.get_num_lods())]
        entry["schermo"] = [round(v, 3) for v in SMS.get_lod_screen_sizes(dest)]
        entry["slot_sezioni"] = [[SMS.get_lod_material_slot(dest, i, k) for k in range(dest.get_num_sections(i))]
                                 for i in range(dest.get_num_lods())]
        entry["slot_prima_dopo"] = [slots_before, len(dest.get_editor_property("static_materials"))]
        entry["nanite"] = bool(SMS.get_nanite_settings(dest).get_editor_property("enabled"))
        yield 2
    unreal.EditorAssetLibrary.delete_directory(TMP)
    yield 2
    if SAVE:
        for piece in rep["pezzi"]:
            unreal.EditorAssetLibrary.save_asset("%s/%s" % (FOLDER, piece), only_if_is_dirty=False)
    rep["box_file_mesh_estensioni"] = BOXES
    (LOD_DIR / "ue.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(LOD_DIR / "errore.txt"))
