from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir())
for name in ['finish_aging','capture_refined']:
    p=root/'Scripts'/('mazzarino80_historic_'+name+'.py')
    exec(compile(p.read_text(encoding='utf-8-sig'),str(p),'exec'),{})
