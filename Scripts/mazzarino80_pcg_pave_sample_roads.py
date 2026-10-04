"""Give the seven access streets of the 18-house sample an existing 2K paving finish."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
rows=json.loads((root/'Saved/Mazzarino80/PCG/sample_roads.json').read_text(encoding='utf-8'))
names={row['road'] for row in rows}
folder='/Game/Mazzarino80/Historic/Materials'
material=unreal.load_asset(folder+'/M80_Pavimentazione_campione')
if not material:
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'M80_Pavimentazione_campione',folder,unreal.Material,unreal.MaterialFactoryNew())
assert material
lib=unreal.MaterialEditingLibrary
lib.delete_all_material_expressions(material)
material.set_editor_property('used_with_spline_meshes',True)
texture=unreal.load_asset('/Game/Mazzarino80/Library/Comune/Megascans_2K/Surface/01_Cobblestone_Floor_2x2_M_tctoehat/tctoehat_2K_Albedo')
assert texture
position=lib.create_material_expression(material,unreal.MaterialExpressionWorldPosition,-800,0)
xy=lib.create_material_expression(material,unreal.MaterialExpressionComponentMask,-600,0)
xy.set_editor_property('r',True)
xy.set_editor_property('g',True)
xy.set_editor_property('b',False)
xy.set_editor_property('a',False)
assert lib.connect_material_expressions(position,'',xy,'')
scale=lib.create_material_expression(material,unreal.MaterialExpressionMultiply,-400,0)
scale.set_editor_property('const_b',.005)
assert lib.connect_material_expressions(xy,'',scale,'A')
sample=lib.create_material_expression(material,unreal.MaterialExpressionTextureSample,-200,0)
sample.set_editor_property('texture',texture)
sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if texture.virtual_texture_streaming else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
assert lib.connect_material_expressions(scale,'',sample,'UVs')
tint=lib.create_material_expression(material,unreal.MaterialExpressionConstant3Vector,-200,200)
tint.set_editor_property('constant',unreal.LinearColor(.64,.56,.44,1))
color=lib.create_material_expression(material,unreal.MaterialExpressionMultiply,0,0)
assert lib.connect_material_expressions(sample,'RGB',color,'A')
assert lib.connect_material_expressions(tint,'',color,'B')
assert lib.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
rough=lib.create_material_expression(material,unreal.MaterialExpressionConstant,0,200)
rough.set_editor_property('r',.96)
assert lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
lib.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material)
changed=[]
for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if isinstance(actor,unreal.MazzarinoRoadSpline) and actor.get_actor_label() in names:
        actor.modify()
        actor.set_editor_property('road_material',material)
        actor.rebuild_road()
        changed.append(actor.get_actor_label())
assert len(changed)==len(names),(changed,names)
saved=bool(unreal.EditorLevelLibrary.save_current_level())
out=root/'Saved/Mazzarino80/PCG/paved_sample_roads.json'
out.write_text(json.dumps({'roads':changed,'material':material.get_path_name(),'saved':saved},indent=2),encoding='utf-8')
unreal.log('M80_PAVED_SAMPLE_ROADS '+str(out))
