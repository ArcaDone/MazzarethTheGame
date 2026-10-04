"""Clay colour, individual replacement tiles and mineral weathering, reusable on 3D coppi."""
import unreal
lib=unreal.MaterialEditingLibrary
tilemat=unreal.load_asset('/Game/Mazzarino80/Historic/Materials/M80_Coppi_terracotta_3D');assert tilemat
lib.delete_all_material_expressions(tilemat)
tilemat.set_editor_property('used_with_instanced_static_meshes',True)
def node(cls):return lib.create_material_expression(tilemat,cls)
def link(a,b,pin='',output=''):assert lib.connect_material_expressions(a,output,b,pin)
def vector(name,color):
 n=node(unreal.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',unreal.LinearColor(*color,1));return n
def scalar(name,value):
 n=node(unreal.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
instance=node(unreal.MaterialExpressionPerInstanceRandom)
mix=node(unreal.MaterialExpressionLinearInterpolate)
link(vector('Argilla_scura',(.085,.028,.012)),mix,'A');link(vector('Argilla_chiara',(.22,.125,.058)),mix,'B');link(instance,mix,'Alpha')
weather=node(unreal.MaterialExpressionNoise);weather.set_editor_property('scale',.035);weather.set_editor_property('levels',3);weather.set_editor_property('output_min',0.);weather.set_editor_property('output_max',1.)
bounded=node(unreal.MaterialExpressionClamp);link(weather,bounded,'')
power=node(unreal.MaterialExpressionPower);power.set_editor_property('const_exponent',2.5);link(bounded,power,'Base')
amount=node(unreal.MaterialExpressionMultiply);link(power,amount,'A');link(scalar('Depositi_minerali',.75),amount,'B')
aged=node(unreal.MaterialExpressionLinearInterpolate);link(mix,aged,'A');link(vector('Depositi_grigi',(.075,.068,.053)),aged,'B');link(amount,aged,'Alpha')
grain=node(unreal.MaterialExpressionNoise);grain.set_editor_property('scale',.8);grain.set_editor_property('levels',2);grain.set_editor_property('output_min',.78);grain.set_editor_property('output_max',1.08)
result=node(unreal.MaterialExpressionMultiply);link(aged,result,'A');link(grain,result,'B')
moss_selection=node(unreal.MaterialExpressionPower);moss_selection.set_editor_property('const_exponent',8.);link(instance,moss_selection,'Base')
moss_patch=node(unreal.MaterialExpressionMultiply);link(moss_selection,moss_patch,'A');link(bounded,moss_patch,'B')
moss_amount=node(unreal.MaterialExpressionMultiply);link(moss_patch,moss_amount,'A');link(scalar('Muschio_rado',.9),moss_amount,'B')
moss=node(unreal.MaterialExpressionLinearInterpolate);link(result,moss,'A');link(vector('Patina_muschio',(.045,.085,.032)),moss,'B');link(moss_amount,moss,'Alpha')
lib.connect_material_property(moss,'',unreal.MaterialProperty.MP_BASE_COLOR)
lib.connect_material_property(scalar('Rugosita',.94),'',unreal.MaterialProperty.MP_ROUGHNESS)
# Dense plaster grain adds pores without imprinting a second tile grid on the curved geometry.
tex=unreal.load_asset('/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Stucco_Facade_wfnjdgl/T_Stucco_Facade_wfnjdgl_2K_N');assert tex
normal=node(unreal.MaterialExpressionTextureSample);normal.set_editor_property('texture',tex);normal.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL if tex.virtual_texture_streaming else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
uv=node(unreal.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',2.);uv.set_editor_property('v_tiling',2.);link(uv,normal,'')
flat=node(unreal.MaterialExpressionConstant3Vector);flat.set_editor_property('constant',unreal.LinearColor(0,0,1,1))
relief=node(unreal.MaterialExpressionLinearInterpolate);link(flat,relief,'A');link(normal,relief,'B','RGB');link(scalar('Porosita',.03),relief,'Alpha');lib.connect_material_property(relief,'',unreal.MaterialProperty.MP_NORMAL)
lib.recompile_material(tilemat);assert unreal.EditorAssetLibrary.save_loaded_asset(tilemat)
unreal.log('M80_TILE_FINISH_APPLIED')
