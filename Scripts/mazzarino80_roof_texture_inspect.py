import unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir())
tex=unreal.load_asset('/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Red_Roof_Tiles_tfqnfggs/T_Red_Roof_Tiles_tfqnfggs_4K_D')
assert tex
# UE 5.5's legacy TGA exporter asserts for this texture type. Keep inspection
# in the material editor; never pass this texture to that exporter again.
a=next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a,unreal.MazzarinoHistoricBuilding))
unreal.log('M80_TILE_MATERIAL '+str(a.get_editor_property('roof_tiles').get_material(0))+' Gray '+str(a.get_editor_property('gray_preview')))
