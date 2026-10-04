import unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir())
exec(compile((root/'Scripts/mazzarino80_historic_tile_finish.py').read_text(),'tile_finish','exec'),{})
exec(compile((root/'Scripts/mazzarino80_historic_capture_finish.py').read_text(),'capture_finish','exec'),{})
