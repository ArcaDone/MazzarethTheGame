"""Update only the sample, with reusable resources and surface aging."""
import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir());editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_name()!='Mazzarino80_CaseStoriche_Campione':assert levels.load_level('/Game/Levels/Mazzarino80_CaseStoriche_Campione')
lib=unreal.MaterialEditingLibrary
path='/Game/Mazzarino80/Historic/Materials/'
stone=unreal.load_asset(path+'M80_Pietra_modesta')
exposed=unreal.load_asset(path+'M80_Pietra_esposta')
if not exposed:exposed=unreal.EditorAssetLibrary.duplicate_asset(path+'M80_Pietra_modesta',path+'M80_Pietra_esposta')
assert exposed
# Fine stone details use a restrained mineral color; brick photos stretched on
# narrow instanced cubes looked like wooden strips in the previous generator.
color=lib.create_material_expression(stone,unreal.MaterialExpressionConstant3Vector,-350,-100)
color.set_editor_property('constant',unreal.LinearColor(.38,.36,.29,1))
lib.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR)
lib.recompile_material(stone);assert unreal.EditorAssetLibrary.save_loaded_asset(stone)
for name in ['M80_Umidita','M80_Rappezzo','M80_Pietra_esposta']:
    mat=unreal.load_asset(path+name);mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED);mat.set_editor_property('opacity_mask_clip_value',.45)
    if not lib.get_material_property_input_node(mat,unreal.MaterialProperty.MP_OPACITY_MASK):
        noise=lib.create_material_expression(mat,unreal.MaterialExpressionNoise,-600,800)
        noise.set_editor_property('scale',.028);noise.set_editor_property('quality',1);noise.set_editor_property('levels',2)
        noise.set_editor_property('output_min',0.0);noise.set_editor_property('output_max',1.0)
        lib.connect_material_property(noise,'',unreal.MaterialProperty.MP_OPACITY_MASK)
    lib.recompile_material(mat);assert unreal.EditorAssetLibrary.save_loaded_asset(mat)
LIB='/Game/Mazzarino80/Library/Comune'
door=unreal.load_asset(LIB+'/OldWestAssets/OldWestVol6/VOL6/Meshes/SM_Door_06c')
pot=unreal.load_asset(LIB+'/Megascans/3D_Assets/Flower_Pot_tmekfduiw/S_Flower_Pot_tmekfduiw_lod3')
assert door and pot
houses=[a for a in editor.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)]
for a in houses:
    a.set_editor_property('door_mesh',door);a.set_editor_property('pot_mesh',pot);a.set_editor_property('exposed_stone_material',exposed)
    a.set_editor_property('gray_preview',False);a.update_support();a.rebuild_house()
assert len(houses)==18
assert levels.save_current_level()
unreal.log('M80_HISTORIC_REFINED_SAVED')
