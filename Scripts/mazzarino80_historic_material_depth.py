"""Add mineral, patched and faded facade finishes using the existing Comune library."""
import unreal,random,json
from pathlib import Path
root=Path(unreal.Paths.project_dir());lib=unreal.MaterialEditingLibrary
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
houses=sorted([a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)],key=lambda a:a.get_editor_property('lot_id'))
assert len(houses)==18
folder='/Game/Mazzarino80/Historic/Materials'
original_tints={entry['lot']:entry['tint'] for entry in json.loads((root/'Saved/Mazzarino80/Historic/house_materials.json').read_text())}
stone='/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_'
def create(name,color):
 mat=unreal.load_asset(folder+'/'+name)
 if not mat:mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
 lib.delete_all_material_expressions(mat);mat.set_editor_property('used_with_instanced_static_meshes',True)
 def node(cls):return lib.create_material_expression(mat,cls)
 def link(a,b,pin='',output=''):assert lib.connect_material_expressions(a,output,b,pin)
 tint=node(unreal.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','Tinta');tint.set_editor_property('default_value',unreal.LinearColor(*color,1))
 sample=node(unreal.MaterialExpressionTextureSample);tex=unreal.load_asset(stone+'D');assert tex;sample.set_editor_property('texture',tex);sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if tex.get_editor_property('virtual_texture_streaming') else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
 mul=node(unreal.MaterialExpressionMultiply);link(tint,mul,'A');link(sample,mul,'B','RGB');lib.connect_material_property(mul,'',unreal.MaterialProperty.MP_BASE_COLOR)
 normal=node(unreal.MaterialExpressionTextureSample);tex=unreal.load_asset(stone+'N');normal.set_editor_property('texture',tex);normal.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if tex.get_editor_property('virtual_texture_streaming') else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
 flat=node(unreal.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',unreal.LinearColor(0,0,1,1))
 strength=node(unreal.MaterialExpressionScalarParameter);strength.set_editor_property('parameter_name','Rilievo_superficie');strength.set_editor_property('default_value',.48)
 lerp=node(unreal.MaterialExpressionLinearInterpolate);link(flat,lerp,'A');link(normal,lerp,'B','RGB');link(strength,lerp,'Alpha');lib.connect_material_property(lerp,'',unreal.MaterialProperty.MP_NORMAL)
 rough=node(unreal.MaterialExpressionScalarParameter);rough.set_editor_property('parameter_name','Rugosita');rough.set_editor_property('default_value',.93);lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
 lib.recompile_material(mat);assert unreal.EditorAssetLibrary.save_loaded_asset(mat);return mat
parents=[create('M80_Muratura_locale_0',(.52,.39,.25)),create('M80_Muratura_locale_1',(.42,.35,.26))]
report=[]
for index,a in enumerate(houses):
 lot=a.get_editor_property('lot_id');seed=a.get_editor_property('seed');rng=random.Random(seed)
 # Five modest stone houses; the remaining homes retain individually faded lime.
 masonry=index in [0,3,7,11,15]
 if masonry:
  name=folder+'/Case/MI_Pietra_'+lot;instance=unreal.load_asset(name)
  if not instance:instance=unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_Pietra_'+lot,folder+'/Case',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
  lib.set_material_instance_parent(instance,parents[index%2]);a.set_editor_property('plaster_material',instance)
 else:
  instance=unreal.load_asset(folder+'/Case/MI_Calce_'+lot);assert instance
  old=original_tints[lot]
  factor=.61 if index%4==0 else .72
  lib.set_material_instance_vector_parameter_value(instance,'Tinta',unreal.LinearColor(*(channel*factor for channel in old),1))
  lib.set_material_instance_scalar_parameter_value(instance,'Contrasto_superficie',.38+.22*a.get_editor_property('decay'))
  lib.set_material_instance_scalar_parameter_value(instance,'Rilievo_superficie',.19+.13*a.get_editor_property('decay'))
  a.set_editor_property('plaster_material',instance)
 assert unreal.EditorAssetLibrary.save_loaded_asset(instance)
 a.rebuild_house();report.append({'lot':lot,'finish':'muratura' if masonry else 'calce consumata','material':instance.get_path_name()})
(root/'Saved/Mazzarino80/Historic/facade_finishes.json').write_text(json.dumps(report,indent=2))
unreal.log('M80_FACADE_FINISHES_APPLIED')
