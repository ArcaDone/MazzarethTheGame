"""Soften base dampness and restore irregular repair outlines."""
import unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir());folder='/Game/Mazzarino80/Historic/Materials'
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()=='Mazzarino80_CaseStoriche_Campione'
lib=unreal.MaterialEditingLibrary;assets=unreal.AssetToolsHelpers.get_asset_tools()
parent=unreal.load_asset(folder+'/M80_Umidita')
mat=unreal.load_asset(folder+'/MI_Umidita_sfumata')
if not mat:mat=assets.create_asset('MI_Umidita_sfumata',folder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(mat,parent)
lib.set_material_instance_scalar_parameter_value(mat,'Sfuma_umidita_in_altezza',7.5)
lib.set_material_instance_vector_parameter_value(mat,'Tinta',unreal.LinearColor(.36,.34,.29,1))
lib.set_material_instance_scalar_parameter_value(mat,'Rilievo_superficie',.08)
assert unreal.EditorAssetLibrary.save_loaded_asset(mat)
for name in ['M80_Rappezzo','M80_Pietra_esposta']:
    m=unreal.load_asset(folder+'/'+name);m.set_editor_property('opacity_mask_clip_value',.45)
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m)
for a in e.get_all_level_actors():
    if isinstance(a,unreal.MazzarinoHistoricBuilding):a.set_editor_property('damp_material',mat);a.rebuild_house()
unreal.log('M80_SOFT_AGING_FINISHED')
