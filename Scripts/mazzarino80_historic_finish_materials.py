"""Refine the sample's lime, wood, limestone and moisture materials."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir())
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()=='Mazzarino80_CaseStoriche_Campione'
lib=unreal.MaterialEditingLibrary;assets=unreal.AssetToolsHelpers.get_asset_tools()
folder='/Game/Mazzarino80/Historic/Materials'
def node(m,cls,x=0,y=0):return lib.create_material_expression(m,cls,x,y)
def scalar(m,name,value,x=0,y=0):
    n=node(m,unreal.MaterialExpressionScalarParameter,x,y);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def vector(m,name,color,x=0,y=0):
    n=node(m,unreal.MaterialExpressionVectorParameter,x,y);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',unreal.LinearColor(*color,1));return n
def link(a,b,pin,output=''):lib.connect_material_expressions(a,output,b,pin)
def build(name,color,texpath=None,normalpath=None,strength=.18,contrast=.35,rough=.94):
    m=unreal.load_asset(folder+'/'+name)
    if not m:m=assets.create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    else:lib.delete_all_material_expressions(m)
    m.set_editor_property('used_with_instanced_static_meshes',True)
    tint=vector(m,'Tinta',color,-550,-100);result=tint
    def sample(path,y,normal=False):
        tex=unreal.load_asset(path);assert tex,path
        n=node(m,unreal.MaterialExpressionTextureSample,-850,y);n.set_editor_property('texture',tex)
        n.set_editor_property('sampler_type', (unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR) if tex.virtual_texture_streaming else (unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR))
        return n
    if texpath:
        tex=sample(texpath,100)
        white=node(m,unreal.MaterialExpressionConstant3Vector,-850,-100);white.set_editor_property('constant',unreal.LinearColor(1,1,1,1))
        lerp=node(m,unreal.MaterialExpressionLinearInterpolate,-450,100)
        link(white,lerp,'A');link(tex,lerp,'B','RGB');link(scalar(m,'Contrasto_superficie',contrast,-700,300),lerp,'Alpha')
        mul=node(m,unreal.MaterialExpressionMultiply,-150,0);link(tint,mul,'A');link(lerp,mul,'B');result=mul
    lib.connect_material_property(result,'',unreal.MaterialProperty.MP_BASE_COLOR)
    if normalpath:
        n=sample(normalpath,500,True)
        flat=node(m,unreal.MaterialExpressionConstant3Vector,-800,700);flat.set_editor_property('constant',unreal.LinearColor(0,0,1,1))
        lerp=node(m,unreal.MaterialExpressionLinearInterpolate,-350,500)
        link(flat,lerp,'A');link(n,lerp,'B','RGB');link(scalar(m,'Rilievo_superficie',strength,-650,850),lerp,'Alpha')
        lib.connect_material_property(lerp,'',unreal.MaterialProperty.MP_NORMAL)
    lib.connect_material_property(scalar(m,'Rugosita',rough,-200,950),'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m
stucco='/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Stucco_Facade_wfnjdgl/T_Stucco_Facade_wfnjdgl_2K_'
stone='/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_'
wood='/Game/Megascans/Surfaces/Flaked_Paint_Wooden_Panel_tlsmbafdy/T_Flaked_Paint_Wooden_Panel_tlsmbafdy_4K_'
palette=[(.54,.49,.40),(.65,.59,.48),(.42,.41,.35),(.60,.46,.33),(.69,.66,.56),(.51,.43,.36)]
for i,c in enumerate(palette):build('M80_Calce_consumata_'+str(i),c,stucco+'D',stucco+'N',strength=.18,contrast=.30)
build('M80_Pietra_modesta',(.49,.44,.34),normalpath=stone+'N',strength=.13)
for i,c in enumerate([(.14,.21,.17),(.30,.24,.17),(.29,.30,.26)]):build('M80_Legno_persiane_'+str(i),c,wood+'D',wood+'N',strength=.22,contrast=.60,rough=.87)
build('M80_Terrazza_calce',(.42,.39,.32),stucco+'D',stucco+'N',strength=.12,contrast=.25)
# Height-dependent dampness follows the authored vertical strip UV.
for name,color,fade in [('M80_Umidita',(.29,.28,.23),True),('M80_Rappezzo',(.55,.51,.42),False),('M80_Pietra_esposta',(.47,.41,.31),False)]:
    m=build(name,color,stone+'D' if name.endswith('esposta') else stucco+'D',stone+'N' if name.endswith('esposta') else stucco+'N',strength=.16,contrast=.58 if name.endswith('esposta') else .30)
    m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED);m.set_editor_property('opacity_mask_clip_value',.20 if fade else .27)
    noise=node(m,unreal.MaterialExpressionNoise,-850,1150);noise.set_editor_property('scale',.012 if fade else .025);noise.set_editor_property('quality',2);noise.set_editor_property('levels',4);noise.set_editor_property('output_min',.10);noise.set_editor_property('output_max',1.)
    opacity=noise
    if fade:
        uv=node(m,unreal.MaterialExpressionTextureCoordinate,-850,1450)
        mask=node(m,unreal.MaterialExpressionComponentMask,-650,1450);mask.set_editor_property('r',True);assert lib.connect_material_expressions(uv,'',mask,'')
        multiply=node(m,unreal.MaterialExpressionMultiply,-450,1450);link(mask,multiply,'A');link(scalar(m,'Sfuma_umidita_in_altezza',2.8,-700,1650),multiply,'B')
        subtract=node(m,unreal.MaterialExpressionSubtract,-250,1450);subtract.set_editor_property('const_a',1.);link(multiply,subtract,'B')
        clamp=node(m,unreal.MaterialExpressionClamp,-50,1450);assert lib.connect_material_expressions(subtract,'',clamp,'')
        opacity=node(m,unreal.MaterialExpressionMultiply,150,1150);link(noise,opacity,'A');link(clamp,opacity,'B')
    lib.connect_material_property(opacity,'',unreal.MaterialProperty.MP_OPACITY_MASK);lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m)
# Replace green placeholder margins with a neutral, editable surface in this map.
groundmat=unreal.load_asset(folder+'/M80_Suolo_neutro')
if not groundmat:groundmat=unreal.EditorAssetLibrary.duplicate_asset(folder+'/M80_Vicolo_riparato',folder+'/M80_Suolo_neutro')
assert groundmat
for expression in lib.get_material_expressions(groundmat) if hasattr(lib,'get_material_expressions') else []:
    if isinstance(expression,unreal.MaterialExpressionVectorParameter):expression.set_editor_property('default_value',unreal.LinearColor(.43,.40,.34,1))
# The cloned paving graph's tint is replaced explicitly, keeping world UVs intact.
oldbase=lib.get_material_property_input_node(groundmat,unreal.MaterialProperty.MP_BASE_COLOR)
newtint=vector(groundmat,'Tinta_margini',(.43,.40,.34),-100,1300)
if isinstance(oldbase,unreal.MaterialExpressionMultiply):link(newtint,oldbase,'B')
lib.recompile_material(groundmat);assert unreal.EditorAssetLibrary.save_loaded_asset(groundmat)
ground=next(a for a in editor.get_all_level_actors() if a.get_actor_label()=='M80_Terreno')
component=ground.get_component_by_class(unreal.StaticMeshComponent)
for i in range(component.get_num_materials()):component.set_material(i,groundmat)
houses=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)]
for a in houses:a.set_editor_property('gray_preview',False);a.rebuild_house()
(root/'Saved/Mazzarino80/Historic/material_refinement.json').write_text(json.dumps({'houses':len(houses),'changes':['Lime normal strength 0.18, contrast 0.30','Painted wood textures replace stucco on shutters','Warm mineral stone details','Dampness fades with height','Neutral ground margins'],'material_parameters':['Tinta','Contrasto_superficie','Rilievo_superficie','Rugosita','Sfuma_umidita_in_altezza','Tinta_margini']},indent=2))
unreal.log('M80_MATERIAL_REFINEMENT_FINISHED')
