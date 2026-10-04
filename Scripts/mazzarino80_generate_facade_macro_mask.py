"""Make a small seamless low-frequency mask for facade color variation."""
from pathlib import Path
import math
import random
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[1]
out=root/'Research/Mazzarino80/PCG/Textures/T_M80_FacadeMacroNoise.png'
out.parent.mkdir(parents=True,exist_ok=True)
size=256
rng=random.Random(1980)
yy,xx=np.mgrid[0:size,0:size].astype(np.float32)
xx*=2*math.pi/size
yy*=2*math.pi/size
field=np.zeros((size,size),dtype=np.float32)
for i in range(22):
    fx=rng.randint(1,6)
    fy=rng.randint(1,6)
    phase=rng.random()*2*math.pi
    amplitude=1/math.sqrt(fx*fx+fy*fy)
    field+=amplitude*np.sin(fx*xx+fy*yy+phase)
field=(field-field.min())/(field.max()-field.min())
field=(field*.72+.14)*255
Image.fromarray(field.astype(np.uint8),'L').convert('RGB').save(out)
print(out)
