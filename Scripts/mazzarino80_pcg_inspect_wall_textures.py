"""Export the already-imported candidate wall albedos for visual inspection."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
folder = root / 'Saved/Mazzarino80/PCG/WallTextureCandidates'
folder.mkdir(parents=True, exist_ok=True)
paths = {
    'stucco': '/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Stucco_Facade_wfnjdgl/T_Stucco_Facade_wfnjdgl_2K_D',
    'damaged_plaster': '/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Damaged_Brick_Wall_Plaster_vcvodh0/T_Damaged_Brick_Wall_Plaster_vcvodh0_4K_D',
    'cracked_concrete': '/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Painted_Cracked_Concrete_Wall_sionccva/T_Painted_Cracked_Concrete_Wall_sionccva_2K_D',
    'stone': '/Game/Mazzarino80/Library/Comune/Megascans/Surfaces/Roman_Stone_Wall_tf2kaa2n/T_Roman_Stone_Wall_tf2kaa2n_4K_D',
}
report = {}
for name, path in paths.items():
    texture = unreal.load_asset(path)
    assert texture, path
    if texture.virtual_texture_streaming:
        report[name] = {'asset': path, 'exported': False,
                        'reason': 'Virtual texture cannot be exported by TextureExporterPNG'}
        continue
    task = unreal.AssetExportTask()
    task.object = texture
    task.filename = str(folder / (name + '.png'))
    task.exporter = unreal.TextureExporterPNG()
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    success = unreal.Exporter.run_asset_export_task(task)
    report[name] = {'asset': path, 'exported': bool(success), 'file': task.filename}
out = root / 'Saved/Mazzarino80/PCG/wall_texture_candidates.json'
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('M80_WALL_TEXTURE_CANDIDATES ' + str(out))
