"""Check that courtyard props fit into the existing front-yard grammar."""
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = json.loads((root/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))['buildings']
for row in rows:
    if row['family'] != 'COURTYARD':
        continue
    points = row['footprint_world_cm']
    i = row['front_edge']
    a,b = points[i],points[(i+1)%len(points)]
    dx,dy = b[0]-a[0],b[1]-a[1]
    length = math.hypot(dx,dy)
    edge = dx/length,dy/length
    signed = sum(q[0]*points[(j+1)%len(points)][1]-points[(j+1)%len(points)][0]*q[1]
                 for j,q in enumerate(points))
    out = (dy/length,-dx/length) if signed>0 else (-dy/length,dx/length)
    inside = -out[0],-out[1]
    s = [q[0]*edge[0]+q[1]*edge[1] for q in points]
    t = [q[0]*inside[0]+q[1]*inside[1] for q in points]
    width,depth=max(s)-min(s),max(t)-min(t)
    front_t=a[0]*inside[0]+a[1]*inside[1]-min(t)
    front_s=((a[0]+b[0])*.5*edge[0]+(a[1]+b[1])*.5*edge[1]-min(s))
    print(row['building_id'], 'width_cm',round(width), 'depth_cm',round(depth),
          'courtyard_width_cm',round(width*.36), 'yard_depth_cm',round(depth*.42),
          'front_t_cm',round(front_t), 'front_s_cm',round(front_s),
          'courtyard_s_mid_cm',round(width*.5))
