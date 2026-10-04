"""Validate the dedicated sample and export the comparison views."""
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())
for name in ['validate','routes','integrity','step_passage','capture_refined']:
    script=root/'Scripts'/('mazzarino80_historic_'+name+'.py')
    exec(compile(script.read_text(encoding='utf-8-sig'),str(script),'exec'),{})
