"""Author one reusable tapered terracotta cover tile; centimeters, longitudinal X."""
from pathlib import Path
import math
root=Path(r'D:/UE5Projects/GameAnimationSample')
destination=root/'Research/Mazzarino80/Modules';destination.mkdir(parents=True,exist_ok=True)
points=[];uv=[];faces=[];sides=12;rings=4
for layer in range(2):
 for ring in range(rings):
  x=-21+42*ring/(rings-1);radius=10-ring/(rings-1)-layer*.9
  for k in range(sides+1):
   angle=math.pi*k/sides
   wear=.12*math.sin(k*3.1+ring*1.7)
   points.append((x,radius*math.cos(angle),radius*math.sin(angle)+1+wear))
   uv.append((ring/(rings-1),k/sides))
stride=sides+1;offset=rings*stride
for layer in range(2):
 for ring in range(rings-1):
  for k in range(sides):
   a=layer*offset+ring*stride+k;b=a+stride;c=b+1;d=a+1
   faces.append((a,b,c,d) if layer==0 else (d,c,b,a))
for ring in [0,rings-1]:
 for k in range(sides):
  a=ring*stride+k;faces.append((a,a+1,a+1+offset,a+offset) if ring==0 else (a+offset,a+1+offset,a+1,a))
for k in [0,sides]:
 for ring in range(rings-1):
  a=ring*stride+k;b=a+stride;faces.append((a,a+offset,b+offset,b) if k==0 else (b,b+offset,a+offset,a))
lines=['# Coppo tapered, reusable solid mesh; dimensions 42 x 20 x 11 cm','o Coppo_siciliano','s 1']
lines+=['v %.6f %.6f %.6f'%p for p in points]
lines+=['vt %.6f %.6f'%p for p in uv]
lines+=['f '+' '.join(f'{i+1}/{i+1}' for i in face) for face in faces]
(destination/'Coppo_siciliano.obj').write_text('\n'.join(lines)+'\n')
print('Coppo: %d vertices, %d faces'%(len(points),len(faces)))
