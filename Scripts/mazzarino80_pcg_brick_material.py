"""Build project-owned brick materials using the imported Favela PBR textures."""
import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
folder='/Game/Mazzarino80/Historic/Materials'
lib=unreal.MaterialEditingLibrary
asset_tools=unreal.AssetToolsHelpers.get_asset_tools()
macro=unreal.load_asset(folder+'/T_M80_FacadeMacroNoise')
assert macro
configs={
    'M80_Laterizio_rosso_macro':('/Game/Megapack/Textures/Favela/T_Bricks_01_',(.88,.72,.66)),
    'M80_Laterizio_giallo_macro':('/Game/Megapack/Textures/Favela/T_Wall_yellow_01_',(.88,.81,.67)),
}
report={}
for name,(prefix,tint_value) in configs.items():
    m=unreal.load_asset(folder+'/'+name)
    if not m:
        m=asset_tools.create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(m)
    m.set_editor_property('used_with_instanced_static_meshes',True)
    def node(kind,x,y): return lib.create_material_expression(m,kind,x,y)
    def link(a,b,pin='',output=''):
        if not lib.connect_material_expressions(a,output,b,pin):
            raise RuntimeError('Cannot connect '+name+' '+pin)
    def scalar(label,value,x,y):
        e=node(unreal.MaterialExpressionScalarParameter,x,y)
        e.set_editor_property('parameter_name',label)
        e.set_editor_property('default_value',value)
        return e
    def sample(texture,x,y,normal=False,linear=False):
        e=node(unreal.MaterialExpressionTextureSample,x,y)
        e.set_editor_property('texture',texture)
        e.set_editor_property('sampler_type',
            (unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_LINEAR_COLOR if linear else unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR)
            if texture.virtual_texture_streaming else
            (unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if linear else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR))
        return e
    bc=unreal.load_asset(prefix+'BC')
    nm=unreal.load_asset(prefix+'N')
    orm=unreal.load_asset(prefix+'ORM')
    if not all((bc,nm,orm)):
        raise RuntimeError('Incomplete brick texture set '+prefix)
    tint=node(unreal.MaterialExpressionVectorParameter,-800,-500)
    tint.set_editor_property('parameter_name','Tinta')
    tint.set_editor_property('default_value',unreal.LinearColor(*tint_value,1))
    brick=sample(bc,-800,-280)
    base=node(unreal.MaterialExpressionMultiply,-570,-430)
    link(tint,base,'A')
    link(brick,base,'B','RGB')
    normal=sample(nm,-800,-50,True)
    flat=node(unreal.MaterialExpressionConstant3Vector,-800,170)
    flat.set_editor_property('constant',unreal.LinearColor(0,0,1,1))
    normal_mix=node(unreal.MaterialExpressionLinearInterpolate,-560,-50)
    link(flat,normal_mix,'A')
    link(normal,normal_mix,'B','RGB')
    link(scalar('Rilievo_superficie',.25,-800,380),normal_mix,'Alpha')
    lib.connect_material_property(normal_mix,'',unreal.MaterialProperty.MP_NORMAL)
    rough=sample(orm,-560,230,linear=True)
    green=node(unreal.MaterialExpressionComponentMask,-320,230)
    green.set_editor_property('r',False)
    green.set_editor_property('g',True)
    green.set_editor_property('b',False)
    green.set_editor_property('a',False)
    link(rough,green,'','RGB')
    rough_mix=node(unreal.MaterialExpressionLinearInterpolate,-90,220)
    rough_base=node(unreal.MaterialExpressionConstant,-320,510)
    rough_base.set_editor_property('r',.94)
    link(rough_base,rough_mix,'A')
    link(green,rough_mix,'B')
    link(scalar('Rugosita_da_mappa',.15,-310,430),rough_mix,'Alpha')
    lib.connect_material_property(rough_mix,'',unreal.MaterialProperty.MP_ROUGHNESS)
    position=node(unreal.MaterialExpressionWorldPosition,-800,620)
    xy=node(unreal.MaterialExpressionComponentMask,-560,620)
    xy.set_editor_property('r',True)
    xy.set_editor_property('g',True)
    xy.set_editor_property('b',False)
    xy.set_editor_property('a',False)
    link(position,xy)
    uv=node(unreal.MaterialExpressionMultiply,-330,620)
    link(xy,uv,'A')
    link(scalar('Scala_macro',.00065,-550,840),uv,'B')
    noise=sample(macro,-100,620)
    link(uv,noise,'UVs')
    red=node(unreal.MaterialExpressionComponentMask,130,620)
    red.set_editor_property('r',True)
    red.set_editor_property('g',False)
    red.set_editor_property('b',False)
    red.set_editor_property('a',False)
    link(noise,red,'','RGB')
    centered=node(unreal.MaterialExpressionSubtract,340,620)
    centered.set_editor_property('const_b',.5)
    link(red,centered,'A')
    contrast=node(unreal.MaterialExpressionMultiply,550,620)
    link(centered,contrast,'A')
    link(scalar('Contrasto_macro',.75,340,840),contrast,'B')
    factor=node(unreal.MaterialExpressionAdd,760,620)
    factor.set_editor_property('const_b',1.)
    link(contrast,factor,'A')
    xz=node(unreal.MaterialExpressionComponentMask,-560,980)
    xz.set_editor_property('r',True)
    xz.set_editor_property('g',False)
    xz.set_editor_property('b',True)
    xz.set_editor_property('a',False)
    link(position,xz)
    vertical_uv=node(unreal.MaterialExpressionMultiply,-330,980)
    link(xz,vertical_uv,'A')
    link(scalar('Scala_macro_verticale',.00085,-550,1200),vertical_uv,'B')
    vertical=sample(macro,-100,980)
    link(vertical_uv,vertical,'UVs')
    vertical_red=node(unreal.MaterialExpressionComponentMask,130,980)
    vertical_red.set_editor_property('r',True)
    vertical_red.set_editor_property('g',False)
    vertical_red.set_editor_property('b',False)
    vertical_red.set_editor_property('a',False)
    link(vertical,vertical_red,'','RGB')
    vertical_center=node(unreal.MaterialExpressionSubtract,340,980)
    vertical_center.set_editor_property('const_b',.5)
    link(vertical_red,vertical_center,'A')
    vertical_strength=node(unreal.MaterialExpressionMultiply,550,980)
    link(vertical_center,vertical_strength,'A')
    link(scalar('Contrasto_macro_verticale',.85,340,1200),vertical_strength,'B')
    full_factor=node(unreal.MaterialExpressionAdd,900,780)
    link(factor,full_factor,'A')
    link(vertical_strength,full_factor,'B')
    final=node(unreal.MaterialExpressionMultiply,980,-100)
    link(base,final,'A')
    link(full_factor,final,'B')
    assert lib.connect_material_property(final,'',unreal.MaterialProperty.MP_BASE_COLOR)
    lib.recompile_material(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m)
    report[name]={'base':bc.get_path_name(),'normal':nm.get_path_name(),
                  'orm':orm.get_path_name(),'macro':macro.get_path_name()}
out=root/'Saved/Mazzarino80/PCG/brick_materials.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('M80_BRICK_MATERIALS '+str(out))
