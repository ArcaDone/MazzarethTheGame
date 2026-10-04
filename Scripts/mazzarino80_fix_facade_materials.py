import runpy
from pathlib import Path
# Reuse only the material definitions, without changing the map or actor parameters.
p=Path(r'D:\UE5Projects\GameAnimationSample\Scripts\mazzarino80_enrich_facades.py')
s=p.read_text().split('def footprint(a):')[0]
s=s.replace("assert levels.load_level('/Game/Levels/Mazzarino80_Panoramica')",'')
exec(compile(s,str(p),'exec'))
unreal.log('M80_VIRTUAL_TEXTURE_MATERIALS_FIXED')
