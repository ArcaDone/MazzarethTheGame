"""Apply corrected structural/detail grammar to the existing 18 lots only."""
import unreal,json,random
from pathlib import Path
root=Path(unreal.Paths.project_dir());lib=unreal.MaterialEditingLibrary
e=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_name()=='Mazzarino80_CaseStoriche_Campione'
houses=[a for a in e.get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding)];assert len(houses)==18
folder='/Game/Mazzarino80/Historic/Materials';modules='/Game/Mazzarino80/Historic/Modules'
def expression(m,cls):return lib.create_material_expression(m,cls)
def connect(a,b,pin='',output=''):assert lib.connect_material_expressions(a,output,b,pin),(a,b,pin)
def material(name,tint,roughness=.9):
 m=unreal.load_asset(folder+'/'+name)
 if not m:m=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
 lib.delete_all_material_expressions(m)
 m.set_editor_property('used_with_instanced_static_meshes',True)
 n=expression(m,unreal.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name','Tinta');n.set_editor_property('default_value',unreal.LinearColor(*tint,1))
 lib.connect_material_property(n,'',unreal.MaterialProperty.MP_BASE_COLOR)
 r=expression(m,unreal.MaterialExpressionScalarParameter);r.set_editor_property('parameter_name','Rugosita');r.set_editor_property('default_value',roughness);lib.connect_material_property(r,'',unreal.MaterialProperty.MP_ROUGHNESS)
 return m,n
drain,_=material('M80_Canaletta_pietra_opaca',(.22,.20,.16));lib.recompile_material(drain);assert unreal.EditorAssetLibrary.save_loaded_asset(drain)
tilemat,tint=material('M80_Coppi_terracotta_3D',(.27,.13,.065))
noise=expression(tilemat,unreal.MaterialExpressionNoise);noise.set_editor_property('scale',.15);noise.set_editor_property('levels',3);noise.set_editor_property('output_min',.72);noise.set_editor_property('output_max',1.05)
multiply=expression(tilemat,unreal.MaterialExpressionMultiply);connect(tint,multiply,'A');connect(noise,multiply,'B')
instance=expression(tilemat,unreal.MaterialExpressionPerInstanceRandom)
add=expression(tilemat,unreal.MaterialExpressionAdd);add.set_editor_property('const_b',.72)
weight=expression(tilemat,unreal.MaterialExpressionMultiply);weight.set_editor_property('const_b',.35);connect(instance,weight,'A');connect(weight,add,'A')
result=expression(tilemat,unreal.MaterialExpressionMultiply);connect(multiply,result,'A');connect(add,result,'B');lib.connect_material_property(result,'',unreal.MaterialProperty.MP_BASE_COLOR)
lib.recompile_material(tilemat);assert unreal.EditorAssetLibrary.save_loaded_asset(tilemat)
exec(compile((root/'Scripts/mazzarino80_historic_tile_finish.py').read_text(),'tile_finish','exec'),{})
tile=unreal.load_asset(modules+'/SM_Coppo_siciliano')
if not tile:
 task=unreal.AssetImportTask();task.filename=str(root/'Research/Mazzarino80/Modules/Coppo_siciliano.obj');task.destination_path=modules;task.destination_name='SM_Coppo_siciliano';task.automated=True;task.save=True
 options=unreal.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH;options.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs',True);options.static_mesh_import_data.set_editor_property('auto_generate_collision',False);task.options=options
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tile=unreal.load_asset(modules+'/SM_Coppo_siciliano')
assert tile
bounds=tile.get_bounds();unreal.log('M80_TILE_BOUNDS '+str(bounds))
assert bounds.box_extent.x>19 and bounds.box_extent.z<8,('Coppo axis needs correction',bounds)
tile.set_material(0,tilemat);assert unreal.EditorAssetLibrary.save_loaded_asset(tile)
library='/Game/Mazzarino80/Library/ComuneDetail'
wire=unreal.load_asset(library+'/Megapack/Meshes/MiddleEast/Wires/SM_wire_part_01');assert wire
balcony=unreal.load_asset(library+'/Megascans/3D_Assets/Modular_Building_Balcony_ukjsdavdw/S_Modular_Building_Balcony_ukjsdavdw_lod3_Var1');assert balcony
for mesh in [balcony,wire]:
 for slot in range(mesh.get_num_sections(0)):
  chain=[];mat=mesh.get_material(slot)
  while mat and isinstance(mat,unreal.MaterialInstance):chain.append(mat);mat=mat.parent
  if mat:
   mat.set_editor_property('used_with_instanced_static_meshes',True);mat.set_editor_property('used_with_spline_meshes',True);lib.recompile_material(mat);assert unreal.EditorAssetLibrary.save_loaded_asset(mat)
   for child in reversed(chain):assert unreal.EditorAssetLibrary.save_loaded_asset(child,False)
report=[]
for a in houses:
 a.set_editor_property('sill_projection',.055);a.set_editor_property('sill_thickness',.045)
 a.set_editor_property('drain_material',drain);a.set_editor_property('roof_tile_mesh',tile);a.set_editor_property('tile_material',tilemat);a.set_editor_property('cable_mesh',wire)
 a.set_editor_property('balcony_module_mesh',balcony);a.set_editor_property('show_roof_tiles',True);a.set_editor_property('gray_preview',False)
 iron=a.get_editor_property('iron_material');iron.set_editor_property('used_with_spline_meshes',True);lib.recompile_material(iron);assert unreal.EditorAssetLibrary.save_loaded_asset(iron)
 a.rebuild_house()
 report.append({'lot':a.get_editor_property('lot_id'),'sill_projection_cm':a.get_editor_property('sill_projection')*100,'tiles':a.get_editor_property('roof_tiles').get_instance_count(),'complete_balconies':a.get_editor_property('balcony_modules').get_instance_count(),'service_splines':len([s for s in a.get_components_by_class(unreal.SplineComponent) if 'M80ServicePath' in [str(t) for t in s.component_tags]])})
(root/'Saved/Mazzarino80/Historic/details.json').write_text(json.dumps(report,indent=2))
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
unreal.log('M80_DETAILS_APPLIED '+json.dumps(report))
