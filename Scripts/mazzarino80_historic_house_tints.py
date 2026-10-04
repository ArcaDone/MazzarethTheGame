"""Give each sample house an editable plaster instance, retaining its seed."""
import unreal,json,random
from pathlib import Path
root=Path(unreal.Paths.project_dir())
editor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()=='Mazzarino80_CaseStoriche_Campione'
lib=unreal.MaterialEditingLibrary;assets=unreal.AssetToolsHelpers.get_asset_tools()
folder='/Game/Mazzarino80/Historic/Materials/Case'
palette=[(.54,.49,.40),(.65,.59,.48),(.42,.41,.35),(.60,.46,.33),(.69,.66,.56),(.51,.43,.36)]
rows=[]
for a in editor.get_all_level_actors():
    if not isinstance(a,unreal.MazzarinoHistoricBuilding):continue
    lot=a.get_editor_property('lot_id');parent=a.get_editor_property('plaster_material')
    while isinstance(parent,unreal.MaterialInstance):parent=parent.parent
    index=int(parent.get_name().rsplit('_',1)[1])
    rng=random.Random(a.get_editor_property('seed'));brightness=rng.uniform(.94,1.06)
    tint=tuple(c*brightness for c in palette[index]);decay=a.get_editor_property('decay')
    instance=unreal.load_asset(folder+'/MI_Calce_'+lot)
    if not instance:instance=assets.create_asset('MI_Calce_'+lot,folder,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance,parent)
    lib.set_material_instance_vector_parameter_value(instance,'Tinta',unreal.LinearColor(*tint,1))
    lib.set_material_instance_scalar_parameter_value(instance,'Contrasto_superficie',.18+decay*.27)
    lib.set_material_instance_scalar_parameter_value(instance,'Rilievo_superficie',.09+decay*.13)
    lib.set_material_instance_scalar_parameter_value(instance,'Rugosita',.87+decay*.1)
    assert unreal.EditorAssetLibrary.save_loaded_asset(instance)
    a.set_editor_property('plaster_material',instance);a.rebuild_house()
    rows.append({'lot':lot,'material':instance.get_path_name(),'tint':tint,'decay':decay})
assert len(rows)==18
(root/'Saved/Mazzarino80/Historic/house_materials.json').write_text(json.dumps(rows,indent=2))
unreal.log('M80_HOUSE_TINTS_FINISHED')
