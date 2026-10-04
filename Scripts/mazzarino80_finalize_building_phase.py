from pathlib import Path
import gc,unreal
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
for name in ['mazzarino80_fit_restored_buildings.py','mazzarino80_finish_buildings.py','mazzarino80_validate_buildings.py']:
    scope={'__name__':'__main__'}
    exec(compile((ROOT/'Scripts'/name).read_text(encoding='utf-8-sig'),str(ROOT/'Scripts'/name),'exec'),scope)
    del scope;gc.collect()
unreal.log('M80_BUILDING_PHASE_FINALIZED')
