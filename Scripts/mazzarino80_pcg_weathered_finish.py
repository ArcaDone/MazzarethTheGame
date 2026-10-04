"""Give all sampled lime facades and shared stone trim a matte, aged finish."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
folder = '/Game/Mazzarino80/Historic/Materials'
lib = unreal.MaterialEditingLibrary
saved = []

facades = json.loads((root / 'Saved/Mazzarino80/Historic/facade_finishes.json').read_text(encoding='utf-8'))
for house in facades:
    material = unreal.load_asset(house['material'])
    assert material, house
    if house['finish'] == 'calce consumata':
        lib.set_material_instance_scalar_parameter_value(material, 'Contrasto_superficie', .43)
        lib.set_material_instance_scalar_parameter_value(material, 'Rilievo_superficie', .07)
        lib.set_material_instance_scalar_parameter_value(material, 'Rugosita', .97)
    else:
        lib.set_material_instance_scalar_parameter_value(material, 'Rilievo_superficie', .11)
        lib.set_material_instance_scalar_parameter_value(material, 'Rugosita', .96)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material)
    saved.append(house['lot'])

damp = unreal.load_asset(folder + '/MI_Umidita_sfumata')
assert damp
lib.set_material_instance_vector_parameter_value(damp, 'Tinta', unreal.LinearColor(.18, .15, .11, 1))
lib.set_material_instance_scalar_parameter_value(damp, 'Rilievo_superficie', .08)
lib.set_material_instance_scalar_parameter_value(damp, 'Rugosita', .97)
assert unreal.EditorAssetLibrary.save_loaded_asset(damp)

material = unreal.load_asset(folder + '/M80_Pietra_modesta')
assert material
lib.delete_all_material_expressions(material)
material.set_editor_property('used_with_instanced_static_meshes', True)
def node(kind, x, y):
    return lib.create_material_expression(material, kind, x, y)
def link(a, b, pin, output=''):
    assert lib.connect_material_expressions(a, output, b, pin)
def scalar(name, value, x, y):
    e = node(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', value)
    return e
prefix = '/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_'
diffuse = unreal.load_asset(prefix + 'D')
normal = unreal.load_asset(prefix + 'N')
assert diffuse and normal
tint = node(unreal.MaterialExpressionVectorParameter, -700, -250)
tint.set_editor_property('parameter_name', 'Tinta')
tint.set_editor_property('default_value', unreal.LinearColor(.42, .32, .21, 1))
albedo = node(unreal.MaterialExpressionTextureSample, -700, 0)
albedo.set_editor_property('texture', diffuse)
albedo.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if diffuse.virtual_texture_streaming else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
white = node(unreal.MaterialExpressionConstant3Vector, -700, 200)
white.set_editor_property('constant', unreal.LinearColor(1, 1, 1, 1))
mix = node(unreal.MaterialExpressionLinearInterpolate, -460, 10)
link(white, mix, 'A')
link(albedo, mix, 'B', 'RGB')
link(scalar('Contrasto_superficie', .92, -700, 390), mix, 'Alpha')
color = node(unreal.MaterialExpressionMultiply, -200, -130)
link(tint, color, 'A')
link(mix, color, 'B')
assert lib.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
normal_sample = node(unreal.MaterialExpressionTextureSample, -700, 560)
normal_sample.set_editor_property('texture', normal)
normal_sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if normal.virtual_texture_streaming else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
flat = node(unreal.MaterialExpressionConstant3Vector, -700, 770)
flat.set_editor_property('constant', unreal.LinearColor(0, 0, 1, 1))
normal_mix = node(unreal.MaterialExpressionLinearInterpolate, -400, 600)
link(flat, normal_mix, 'A')
link(normal_sample, normal_mix, 'B', 'RGB')
link(scalar('Rilievo_superficie', .08, -650, 980), normal_mix, 'Alpha')
assert lib.connect_material_property(normal_mix, '', unreal.MaterialProperty.MP_NORMAL)
assert lib.connect_material_property(scalar('Rugosita', .97, -300, 980), '', unreal.MaterialProperty.MP_ROUGHNESS)
lib.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material)

out = root / 'Saved/Mazzarino80/PCG/weathered_finish.json'
out.write_text(json.dumps({'facade_houses': saved, 'stone_trim': material.get_path_name(),
                           'plaster_contrast': .43, 'normal_strength': .07,
                           'plaster_roughness': .97}, indent=2), encoding='utf-8')
unreal.log('M80_WEATHERED_FINISH ' + str(out))
