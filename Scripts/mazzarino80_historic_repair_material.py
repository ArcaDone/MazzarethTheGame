"""Repair the dampness graph's Clamp input and persist reused module flags."""
import unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir());lib=unreal.MaterialEditingLibrary
parent=unreal.load_asset('/Game/Mazzarino80/Historic/Materials/M80_Umidita')
output=lib.get_material_property_input_node(parent,unreal.MaterialProperty.MP_OPACITY_MASK)
inputs=lib.get_inputs_for_material_expression(parent,output)
clamp=next(n for n in inputs if isinstance(n,unreal.MaterialExpressionClamp))
uv=lib.create_material_expression(parent,unreal.MaterialExpressionTextureCoordinate,-850,1900)
mask=lib.create_material_expression(parent,unreal.MaterialExpressionComponentMask,-650,1900);mask.set_editor_property('r',True)
assert lib.connect_material_expressions(uv,'',mask,'')
scale=lib.create_material_expression(parent,unreal.MaterialExpressionScalarParameter,-650,2100);scale.set_editor_property('parameter_name','Sfuma_umidita_in_altezza');scale.set_editor_property('default_value',7.5)
multiply=lib.create_material_expression(parent,unreal.MaterialExpressionMultiply,-450,1900)
assert lib.connect_material_expressions(mask,'',multiply,'A');assert lib.connect_material_expressions(scale,'',multiply,'B')
subtract=lib.create_material_expression(parent,unreal.MaterialExpressionSubtract,-250,1900);subtract.set_editor_property('const_a',1.)
assert lib.connect_material_expressions(multiply,'',subtract,'B')
assert lib.connect_material_expressions(subtract,'',clamp,'')
lib.recompile_material(parent);assert unreal.EditorAssetLibrary.save_loaded_asset(parent)
houses=[a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)]
for mesh in [houses[0].get_editor_property('pot_mesh'),houses[0].get_editor_property('door_mesh')]:
    for slot in range(mesh.get_num_sections(0)):
        material=mesh.get_material(slot)
        chain=[material]
        while isinstance(material,unreal.MaterialInstance):material=material.parent;chain.append(material)
        material.set_editor_property('used_with_instanced_static_meshes',True);lib.recompile_material(material)
        for m in reversed(chain):assert unreal.EditorAssetLibrary.save_loaded_asset(m,False)
for a in houses:a.rebuild_house()
unreal.log('M80_DAMPNESS_REPAIRED')
