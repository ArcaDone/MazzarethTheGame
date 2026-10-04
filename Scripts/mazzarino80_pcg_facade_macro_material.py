"""Add an inexpensive world-space color mask to the project facade masters."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
folder='/Game/Mazzarino80/Historic/Materials'
source=root/'Research/Mazzarino80/PCG/Textures/T_M80_FacadeMacroNoise.png'
texture_path=folder+'/T_M80_FacadeMacroNoise'
texture=unreal.load_asset(texture_path)
if not texture:
    task=unreal.AssetImportTask()
    task.filename=str(source)
    task.destination_path=folder
    task.destination_name='T_M80_FacadeMacroNoise'
    task.automated=True
    task.save=True
    task.replace_existing=False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=unreal.load_asset(texture_path)
if not texture:
    raise RuntimeError('Facade macro mask import failed')

lib=unreal.MaterialEditingLibrary
names=['M80_Muratura_locale_0','M80_Muratura_locale_1']+[
    'M80_Calce_consumata_'+str(i) for i in range(6)]
report={}
for name in names:
    material=unreal.load_asset(folder+'/'+name)
    if not material:
        raise RuntimeError('Missing facade master '+name)
    # Rebuild this project-owned master from its known source recipe. This also
    # removes orphaned editor nodes from interrupted graph construction.
    lib.delete_all_material_expressions(material)
    material.set_editor_property('used_with_instanced_static_meshes',True)
    def node(kind,x,y):
        return lib.create_material_expression(material,kind,x,y)
    def link(a,b,pin,output=''):
        if not lib.connect_material_expressions(a,output,b,pin):
            raise RuntimeError('Material graph link failed '+name+' '+pin)
    def scalar(label,value,x,y):
        expression=node(unreal.MaterialExpressionScalarParameter,x,y)
        expression.set_editor_property('parameter_name',label)
        expression.set_editor_property('default_value',value)
        return expression
    stone_family=name.startswith('M80_Muratura')
    stone='/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_'
    stucco='/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Stucco_Facade_wfnjdgl/T_Stucco_Facade_wfnjdgl_2K_'
    damaged='/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Damaged_Brick_Wall_Plaster_vcvodh0/T_Damaged_Brick_Wall_Plaster_vcvodh0_4K_'
    plaster_index=int(name.rsplit('_',1)[-1]) if not stone_family else -1
    # The old painted-concrete scan has a strong blue-grey cast, especially
    # in shade. Keep the sample within Mazzarino's warm lime/brick palette.
    prefix=stone if stone_family else (damaged if plaster_index in (0,2,3,4) else stucco)
    if stone_family:
        tint_value=(.52,.39,.25) if name.endswith('_0') else (.42,.35,.26)
    else:
        palette=[(.54,.49,.40),(.65,.59,.48),(.42,.41,.35),(.60,.46,.33),(.69,.66,.56),(.51,.43,.36)]
        tint_value=palette[int(name.rsplit('_',1)[-1])]
    tint=node(unreal.MaterialExpressionVectorParameter,-1750,-450)
    tint.set_editor_property('parameter_name','Tinta')
    tint.set_editor_property('default_value',unreal.LinearColor(*tint_value,1))
    diffuse=unreal.load_asset(prefix+'D')
    normal_texture=unreal.load_asset(prefix+'N')
    if not diffuse or not normal_texture:
        raise RuntimeError('Original Comune stone maps are missing')
    base_sample=node(unreal.MaterialExpressionTextureSample,-1750,-200)
    base_sample.set_editor_property('texture',diffuse)
    base_sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if diffuse.virtual_texture_streaming else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    base_color=base_sample
    if not stone_family:
        white=node(unreal.MaterialExpressionConstant3Vector,-1740,-20)
        white.set_editor_property('constant',unreal.LinearColor(1,1,1,1))
        mix=node(unreal.MaterialExpressionLinearInterpolate,-1570,-100)
        link(white,mix,'A')
        link(base_sample,mix,'B','RGB')
        link(scalar('Contrasto_superficie',.30,-1730,160),mix,'Alpha')
        base_color=mix
    old=node(unreal.MaterialExpressionMultiply,-1450,-350)
    link(tint,old,'A')
    link(base_color,old,'B','RGB' if stone_family else '')
    normal_sample=node(unreal.MaterialExpressionTextureSample,-1750,0)
    normal_sample.set_editor_property('texture',normal_texture)
    normal_sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if normal_texture.virtual_texture_streaming else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    flat=node(unreal.MaterialExpressionConstant3Vector,-1750,220)
    flat.set_editor_property('constant',unreal.LinearColor(0,0,1,1))
    normal_mix=node(unreal.MaterialExpressionLinearInterpolate,-1450,0)
    link(flat,normal_mix,'A')
    link(normal_sample,normal_mix,'B','RGB')
    link(scalar('Rilievo_superficie',.11 if stone_family else .07,-1740,410),normal_mix,'Alpha')
    lib.connect_material_property(normal_mix,'',unreal.MaterialProperty.MP_NORMAL)
    lib.connect_material_property(scalar('Rugosita',.96 if stone_family else .97,-1450,250),'',unreal.MaterialProperty.MP_ROUGHNESS)
    position=node(unreal.MaterialExpressionWorldPosition,-1300,400)
    xy=node(unreal.MaterialExpressionComponentMask,-1090,390)
    xy.set_editor_property('r',True)
    xy.set_editor_property('g',True)
    xy.set_editor_property('b',False)
    xy.set_editor_property('a',False)
    link(position,xy,'')
    uv=node(unreal.MaterialExpressionMultiply,-220,500)
    link(xy,uv,'A')
    link(scalar('Scala_macro',.00065,-430,940),uv,'B')
    sample=node(unreal.MaterialExpressionTextureSample,0,500)
    sample.set_editor_property('texture',texture)
    sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    link(uv,sample,'UVs')
    channel=node(unreal.MaterialExpressionComponentMask,220,500)
    channel.set_editor_property('r',True)
    channel.set_editor_property('g',False)
    channel.set_editor_property('b',False)
    channel.set_editor_property('a',False)
    link(sample,channel,'','RGB')
    center=node(unreal.MaterialExpressionSubtract,430,500)
    center.set_editor_property('const_b',.5)
    link(channel,center,'A')
    contrast=node(unreal.MaterialExpressionMultiply,640,500)
    link(center,contrast,'A')
    link(scalar('Contrasto_macro',.32,430,760),contrast,'B')
    factor=node(unreal.MaterialExpressionAdd,850,500)
    factor.set_editor_property('const_b',1.0)
    link(contrast,factor,'A')
    # A second projection varies with height. XY alone produces vertical
    # stripes on a facade, regardless of how irregular the mask is.
    xz=node(unreal.MaterialExpressionComponentMask,-1090,700)
    xz.set_editor_property('r',True)
    xz.set_editor_property('g',False)
    xz.set_editor_property('b',True)
    xz.set_editor_property('a',False)
    link(position,xz,'')
    uv_vertical=node(unreal.MaterialExpressionMultiply,-220,1070)
    link(xz,uv_vertical,'A')
    link(scalar('Scala_macro_verticale',.00085,-430,1270),uv_vertical,'B')
    vertical=node(unreal.MaterialExpressionTextureSample,0,1070)
    vertical.set_editor_property('texture',texture)
    vertical.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    link(uv_vertical,vertical,'UVs')
    vertical_red=node(unreal.MaterialExpressionComponentMask,220,1070)
    vertical_red.set_editor_property('r',True)
    vertical_red.set_editor_property('g',False)
    vertical_red.set_editor_property('b',False)
    vertical_red.set_editor_property('a',False)
    link(vertical,vertical_red,'','RGB')
    vertical_center=node(unreal.MaterialExpressionSubtract,430,1070)
    vertical_center.set_editor_property('const_b',.5)
    link(vertical_red,vertical_center,'A')
    vertical_strength=node(unreal.MaterialExpressionMultiply,640,1070)
    link(vertical_center,vertical_strength,'A')
    link(scalar('Contrasto_macro_verticale',.36,430,1280),vertical_strength,'B')
    full_factor=node(unreal.MaterialExpressionAdd,960,690)
    link(factor,full_factor,'A')
    link(vertical_strength,full_factor,'B')
    final=node(unreal.MaterialExpressionMultiply,1060,250)
    link(old,final,'A')
    link(full_factor,final,'B')
    if not lib.connect_material_property(final,'',unreal.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Cannot connect macro color in '+name)
    lib.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError('Cannot save '+name)
    report[name]='world XY+XZ masks added'
out=root/'Saved/Mazzarino80/PCG/facade_macro_material.json'
out.write_text(json.dumps({'texture':texture.get_path_name(),'materials':report},indent=2),encoding='utf-8')
unreal.log('M80_FACADE_MACRO '+str(out))
