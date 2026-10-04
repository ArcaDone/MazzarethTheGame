"""Read copied Comune packages, collect dependencies and prepare an isolated library."""
import unreal, json, shutil
from pathlib import Path
main=Path(r'D:/UE5Projects/GameAnimationSample')
source=Path(r'D:/UE5Projects/Comune/Content')
stage=Path(unreal.Paths.project_dir()).resolve()
registry=unreal.AssetRegistryHelpers.get_asset_registry()
selected=[
 '/Game/Megascans/3D_Assets/Modular_Building_Balcony_ukjsdavdw/S_Modular_Building_Balcony_ukjsdavdw_lod3_Var1',
 *['/Game/Megascans/3D_Assets/Modular_Building_Roof_Kit_ukjsdfvdw/S_Modular_Building_Roof_Kit_ukjsdfvdw_lod3_Var'+str(i) for i in range(1,6)],
 '/Game/Megapack/Meshes/MiddleEast/Wires/BP_Wires',
 '/Game/Megapack/Meshes/MiddleEast/Wires/SM_wire_part_01',
 '/Game/Migrated/Balcony2',
 '/Game/Migrated/Balcony']
packages=set();pending=list(selected);missing=[]
options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
while pending:
 p=pending.pop()
 if p in packages or not p.startswith('/Game/'):continue
 original=source/(p[6:]+'.uasset');target=stage/'Content'/(p[6:]+'.uasset')
 if not original.exists():missing.append(p);continue
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,target)
 registry.scan_files_synchronous([str(target)],True)
 packages.add(p)
 pending.extend(str(d) for d in registry.get_dependencies(p,options))
registry.scan_paths_synchronous(['/Game'],True)
report={'selected':selected,'packages':sorted(packages),'missing':missing,'assets':[],'wire_blueprint':{}}
for p in selected:
 a=unreal.load_asset(p)
 if not a:continue
 row={'path':p,'class':a.get_class().get_name()}
 if isinstance(a,unreal.StaticMesh):
  bounds=a.get_bounds();row.update(origin=list(bounds.origin.to_tuple()),extent=list(bounds.box_extent.to_tuple()),materials=[a.get_material(i).get_path_name() if a.get_material(i) else None for i in range(a.get_num_sections(0))])
 if isinstance(a,unreal.Blueprint):
  c=unreal.EditorAssetLibrary.load_blueprint_class(p);actor=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(c,unreal.Vector())
  for component in actor.get_components_by_class(unreal.SplineMeshComponent):
   if component.static_mesh:report['wire_blueprint'][component.get_name()]={'mesh':component.static_mesh.get_path_name(),'axis':str(component.get_forward_axis())}
 report['assets'].append(row)
(main/'Research/Mazzarino80/comune_detail_resources.json').write_text(json.dumps(report,indent=2))
assert not missing,missing
renames={p:'/Game/Mazzarino80/Library/ComuneDetail/'+p[6:] for p in sorted(packages)}
for p in packages:assert unreal.load_asset(p),p
for p,new in renames.items():assert unreal.EditorAssetLibrary.rename_asset(p,new),p
assert unreal.EditorAssetLibrary.save_directory('/Game/Mazzarino80/Library/ComuneDetail',only_if_is_dirty=False,recursive=True)
(main/'Research/Mazzarino80/comune_detail_renames.json').write_text(json.dumps(renames,indent=2))
unreal.log('M80_DETAIL_RESOURCES_READY '+str(len(packages)))
