"""Finish paving only on the seven editable splines supporting the sample."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir());out=root/'Saved/Mazzarino80/Historic'
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name()=='Mazzarino80_CaseStoriche_Campione'
houses=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)]
lib=unreal.MaterialEditingLibrary;assettools=unreal.AssetToolsHelpers.get_asset_tools()
folder='/Game/Mazzarino80/Historic/Materials'
def paving(name,texture,color):
    mat=unreal.load_asset(folder+'/'+name)
    if mat:return mat
    mat=assettools.create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    pos=lib.create_material_expression(mat,unreal.MaterialExpressionWorldPosition,-850,0)
    mask=lib.create_material_expression(mat,unreal.MaterialExpressionComponentMask,-650,0)
    mask.set_editor_property('r',True);mask.set_editor_property('g',True)
    lib.connect_material_expressions(pos,'',mask,'Input')
    scale=lib.create_material_expression(mat,unreal.MaterialExpressionScalarParameter,-650,180)
    scale.set_editor_property('parameter_name','Dimensione_pavimentazione_cm');scale.set_editor_property('default_value',150.)
    div=lib.create_material_expression(mat,unreal.MaterialExpressionDivide,-450,0)
    lib.connect_material_expressions(mask,'',div,'A');lib.connect_material_expressions(scale,'',div,'B')
    tex=unreal.load_asset(texture);assert tex
    sample=lib.create_material_expression(mat,unreal.MaterialExpressionTextureSample,-200,0)
    sample.set_editor_property('texture',tex)
    sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR if tex.virtual_texture_streaming else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    lib.connect_material_expressions(div,'',sample,'Coordinates')
    tint=lib.create_material_expression(mat,unreal.MaterialExpressionVectorParameter,-200,220)
    tint.set_editor_property('parameter_name','Colore_pavimentazione');tint.set_editor_property('default_value',unreal.LinearColor(*color,1))
    mul=lib.create_material_expression(mat,unreal.MaterialExpressionMultiply,0,0)
    lib.connect_material_expressions(sample,'RGB',mul,'A');lib.connect_material_expressions(tint,'',mul,'B')
    lib.connect_material_property(mul,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=lib.create_material_expression(mat,unreal.MaterialExpressionConstant,0,200);rough.set_editor_property('r',.95)
    lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(mat);unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat
stone=paving('M80_Vicolo_pietra_consumata','/Game/Megascans/Surfaces/Rough_Stone_Floor_vixidai/T_Rough_Stone_Floor_vixidai_2K_D',(.62,.59,.50))
repair=paving('M80_Vicolo_riparato','/Game/Megascans/Surfaces/Smooth_Concrete_Floor_vlznaejs/T_Smooth_Concrete_Floor_vlznaejs_4K_D',(.47,.44,.38))
roads=sorted({a.get_editor_property('entrance_road') for a in houses},key=lambda a:a.get_actor_label())
file=out/'paving.json';original=json.loads(file.read_text()) if file.exists() else []
if not original:
    original=[{'label':a.get_actor_label(),'original_material':a.get_editor_property('road_material').get_path_name() if a.get_editor_property('road_material') else None} for a in roads]
    file.write_text(json.dumps(original,indent=2))
for i,a in enumerate(roads):a.set_editor_property('road_material',repair if i==1 else stone);a.rebuild_road()
for a in houses:
    if a.get_editor_property('resolved_family')==unreal.M80HouseFamily.COURTYARD:a.set_editor_property('terrace_material',stone);a.rebuild_house()
for mesh in [houses[0].get_editor_property('pot_mesh'),houses[0].get_editor_property('door_mesh')]:
    if mesh:
        for slot in range(mesh.get_num_sections(0)):
            m=mesh.get_material(slot)
            while isinstance(m,unreal.MaterialInstance):m=m.parent
            if m and not m.get_editor_property('used_with_instanced_static_meshes'):
                m.set_editor_property('used_with_instanced_static_meshes',True);lib.recompile_material(m);unreal.EditorAssetLibrary.save_loaded_asset(m)
unreal.log('M80_HISTORIC_PAVING seven splines finished; original points and widths preserved')
