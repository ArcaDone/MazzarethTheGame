"""The hand-made buildings of L_M80_Paese_WP (churches, castle, Matrice, Comune, Bartoli, the recovered Blueprints...)
get their own HLOD layer, L_M80_Paese_HLODLayer_Edifici: Instancing, so from far away they are drawn with their own
meshes at their lowest LOD (Nanite or the hand-made LODs) and their own materials. The town's HLOD0 is a mesh
approximation (voxels and a captured texture per 256 m cell): right and cheap for the thousands of houses, but it
turned these buildings into blotchy blobs with black patches (thin walls, columns, ruins). Instancing bakes nothing:
no extra textures, no build time, a few draws for some twenty buildings. The layer has no parent (these buildings stay
out of the town's merged HLOD1) and a loading range wider than the town, so they are seen from anywhere.
A building is an actor whose class is a Blueprint under /Game/Migrated (but trees and the neoclassic houses and
palaces, which stand for houses) or a static mesh actor whose mesh lives under /Game/Mazzarino80/Buildings.
Nothing is saved unless M80_SALVA=1 (then the layer and the changed actors; the HLODs need a rebuild).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_hlod_edifici.py -TimeoutMinutes 30
Out: Saved/Mazzarino80/Memoria/hlod_edifici.json
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Memoria"
SOURCE_LAYER = "/Game/Mazzarino80/Houses/Maps/L_M80_Paese_HLODLayer_Instanced"
LAYER = "/Game/Mazzarino80/Houses/Maps/L_M80_Paese_HLODLayer_Edifici"
BUILDINGS = "/Game/Mazzarino80/Buildings/"
SKIP_CLASSES = ("Tree_C", "NeoClassic_house_C")
# the neoclassic palaces are dozens and stand for houses: they stay in the cheaper approximation
SKIP_CLASS_PREFIXES = ("NeoclassicBuilding_",)
LABELS = ("Chiesa_", "Bartoli_", "M80_Recuperato_", "ScuolaMatrice", "CastelCompleted", "A_", "NeoClassic_",
          "M80_ChiesaComune", "M80_", "Ospedale", "Banca", "Poste")
SAVE = os.environ.get("M80_SALVA") == "1"


def layer():
    if not unreal.EditorAssetLibrary.does_asset_exist(LAYER):
        unreal.EditorAssetLibrary.duplicate_asset(SOURCE_LAYER, LAYER)
    lay = unreal.load_asset(LAYER)
    lay.set_editor_property("layer_type", unreal.HLODLayerType.INSTANCING)
    lay.set_editor_property("parent_layer", None)
    lay.set_editor_property("is_spatially_loaded", True)
    lay.set_editor_property("cell_size", 25600)
    lay.set_editor_property("loading_range", 409600.0)
    return lay


def is_building(a):
    cls = a.get_class()
    if cls.get_name().startswith(SKIP_CLASS_PREFIXES):
        return False
    if cls.get_path_name().startswith("/Game/Migrated/") and cls.get_name() not in SKIP_CLASSES:
        return True
    if isinstance(a, unreal.StaticMeshActor):
        mesh = a.static_mesh_component.get_editor_property("static_mesh")
        return bool(mesh) and mesh.get_path_name().startswith(BUILDINGS)
    return False


def steps():
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = [d for d in m80_seq.actor_descs() if str(d.get_editor_property("label")).startswith(LABELS)]
    m80_seq.load(descs)
    yield 120
    lay = layer()
    rep = {"salvato": SAVE, "layer": {"tipo": str(lay.get_editor_property("layer_type")),
                                      "builder": str(lay.get_editor_property("hlod_builder_settings"))}, "edifici": {}}
    changed = []
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if not is_building(a):
            continue
        before = a.get_editor_property("hlod_layer")
        rep["edifici"][a.get_actor_label()] = {"classe": a.get_class().get_name(),
                                               "prima": before.get_name() if before else None}
        if before != lay:
            a.modify()
            a.set_editor_property("hlod_layer", lay)
            changed.append(a)
    rep["cambiati"] = len(changed)
    yield 2
    if SAVE:
        unreal.EditorAssetLibrary.save_loaded_asset(lay, False)
        # World Partition keeps each actor in its own package: only those of the changed actors are saved
        unreal.EditorLoadingAndSavingUtils.save_packages([a.get_outermost() for a in changed], True)
        yield 30
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hlod_edifici.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "hlod_edifici_errore.txt"))
