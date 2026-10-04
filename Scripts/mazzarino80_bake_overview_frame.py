"""Bake the axis correction into new mesh assets rather than using negative actor scale."""
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
for name in ['M80_Terreno','M80_Edifici']:
    source=ROOT/'Research/Mazzarino80/generated'/f'{name}.obj'
    destination=source.with_name(name+'_Corrected.obj')
    with source.open() as original,destination.open('w',encoding='ascii') as corrected:
        for line in original:
            if line.startswith('v '):
                x,y,z=map(float,line.split()[1:])
                corrected.write(f'v {x:.2f} {-y:.2f} {z:.2f}\n')
            elif line.startswith('f '):corrected.write('f '+' '.join(reversed(line.split()[1:]))+'\n')
            else:corrected.write(line)
    print(destination)
