"""Inspect module axes and dimensions before placing them against walls."""
import json
from pathlib import Path
import unreal

names = {
    'ivy': '/Game/Mazzarino80/Library/Comune/Megascans/3D_Plants/English_Ivy_rkEit/S_English_Ivy_rkEit_Var3_lod1',
    'bath': '/Game/City_of_Brass_Enviroment/Meshes/Corridor_A/Corridor_A_Box02_Ex',
    'clothes': '/Game/Megapack/Meshes/MiddleEast/SM_clothes_A_01',
    'tank_platform': '/Game/Megapack/Meshes/MiddleEast/SM_Platform_Water_Tank_01',
    'rusty_tank_a': '/Game/Megascans/3D_Assets/Rusty_Gas_Tank_vizqehw/S_Rusty_Gas_Tank_vizqehw_lod3_Var1',
    'rusty_tank_b': '/Game/Megascans/3D_Assets/Rusty_Gas_Tank_udmkdejqx/S_Rusty_Gas_Tank_udmkdejqx_lod3',
}
report = {}
for key, path in names.items():
    mesh = unreal.load_asset(path)
    if not mesh:
        report[key] = {'missing': path}
        continue
    bounds = mesh.get_bounds()
    report[key] = {'path': mesh.get_path_name(),
                   'origin': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                   'size': [2*bounds.box_extent.x, 2*bounds.box_extent.y, 2*bounds.box_extent.z],
                   'materials': [mesh.get_material(i).get_path_name() if mesh.get_material(i) else None
                                 for i in range(len(mesh.get_editor_property('static_materials')))]}
out = Path(unreal.Paths.project_dir())/'Saved/Mazzarino80/PCG/detail_bounds.json'
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('M80_DETAIL_BOUNDS ' + str(out))
