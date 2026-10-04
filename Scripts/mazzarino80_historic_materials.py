"""Surface aging uses masked material variation, without adding structural rubble."""
import unreal
from pathlib import Path
lib=unreal.MaterialEditingLibrary
base='/Game/Mazzarino80/Historic/Materials/'
for name in ['M80_Umidita','M80_Rappezzo']:
    mat=unreal.load_asset(base+name);assert mat,name
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value',.45)
    noise=lib.create_material_expression(mat,unreal.MaterialExpressionNoise,-600,800)
    noise.set_editor_property('scale',.028);noise.set_editor_property('quality',1);noise.set_editor_property('levels',2)
    noise.set_editor_property('output_min',0.0);noise.set_editor_property('output_max',1.0)
    lib.connect_material_property(noise,'',unreal.MaterialProperty.MP_OPACITY_MASK)
    lib.recompile_material(mat);assert unreal.EditorAssetLibrary.save_loaded_asset(mat)
unreal.log('M80_HISTORIC_AGING_MATERIALS_SAVED')
