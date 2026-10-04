"""Measure candidate detail meshes before putting them on the eighteen lots."""
import json
from pathlib import Path
import unreal

PATHS = [
    '/Game/City_of_Brass_Enviroment/Meshes/Corridor_A/Corridor_A_Box02_Ex',
    '/Game/Megapack/Meshes/MiddleEast/SM_wooden_gates_01',
    '/Game/Megapack/Meshes/MiddleEast/SM_metal_gate_01',
    '/Game/Megapack/Meshes/Favela/SM_Metal_Gate_01',
    '/Game/Mazzarino80/Library/Comune/Megascans/3D_Assets/Medieval_Iron_Gate_tjykeeofa/S_Medieval_Iron_Gate_tjykeeofa_lod3',
    '/Game/Megascans/3D_Assets/Modular_Building_Gate_ukjsdb1dw/S_Modular_Building_Gate_ukjsdb1dw_lod3_Var1',
    '/Game/Megapack/Meshes/MiddleEast/SM_clothes_A_01',
    '/Game/SoulCity/Environment/Meshes/Building_Slum/SM_Slums_Cloth_01a',
    '/Game/Megascans/3D_Assets/Cactus_udugdfvfa/S_Cactus_udugdfvfa_lod3_Var1',
    '/Game/Megascans/3D_Assets/Cactus_udugcc3fa/S_Cactus_udugcc3fa_lod3_Var1',
    '/Game/Mazzarino80/Library/Comune/Megascans/3D_Assets/Flower_Pot_tmekfduiw/S_Flower_Pot_tmekfduiw_lod3',
    '/Game/Mazzarino80/Library/ComuneDetail/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var3_lod1',
]
report = {}
for path in PATHS:
    asset = unreal.load_asset(path)
    if not asset:
        report[path] = {'exists': False}
        continue
    bounds = asset.get_bounds()
    report[path] = {
        'exists': True,
        'class': asset.get_class().get_name(),
        'origin_cm': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
        'size_cm': [2*bounds.box_extent.x, 2*bounds.box_extent.y, 2*bounds.box_extent.z],
        'materials': [asset.get_material(i).get_path_name() if asset.get_material(i) else ''
                      for i in range(asset.get_num_sections(0))] if False else
                     [slot.material_interface.get_path_name() if slot.material_interface else ''
                      for slot in asset.get_editor_property('static_materials')],
        'lods': asset.get_num_lods(),
        'nanite_enabled': asset.get_editor_property('nanite_settings').enabled,
    }
out = Path(unreal.Paths.project_dir())/'Saved/Mazzarino80/PCG/next_asset_audit.json'
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('M80_NEXT_ASSETS '+str(out))
