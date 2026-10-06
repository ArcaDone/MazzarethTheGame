"""HLOD of the town map (L_M80_Paese_WP): what is drawn in place of the unloaded far-away actors.

The World Partition conversion made two layers: HLOD0 "L_M80_Paese_HLODLayer_Instanced" (256 m
cells, shown up to 768 m) and its parent HLOD1 "..._Merged" (the whole town, always loaded). Houses
are unique Nanite meshes, so instancing them saves nothing: HLOD0 becomes a mesh approximation too
(one simplified mesh with baked textures per cell), which is what distant views need. Then build
them with the HLOD builder:
  UnrealEditor-Cmd.exe <project> /Game/Mazzarino80/Houses/Maps/L_M80_Paese_WP
      -run=WorldPartitionBuilderCommandlet -Builder=WorldPartitionHLODsBuilder -AllowCommandletRendering
Report: Saved/Mazzarino80/hlod_setup.json.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
LAYER = "/Game/Mazzarino80/Houses/Maps/L_M80_Paese_HLODLayer_Instanced"
REPORT = ROOT / "Saved/Mazzarino80/hlod_setup.json"


def run():
    yield 5
    layer = unreal.load_asset(LAYER)
    before = str(layer.get_editor_property("layer_type"))
    layer.set_editor_property("layer_type", unreal.HLODLayerType.MESH_APPROXIMATE)
    unreal.EditorAssetLibrary.save_loaded_asset(layer)
    REPORT.write_text(json.dumps({"layer": LAYER, "before": before,
                                  "after": str(layer.get_editor_property("layer_type")),
                                  "settings": str(layer.get_editor_property("hlod_builder_settings"))}, indent=1), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
