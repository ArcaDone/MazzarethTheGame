"""Check that PCG rooftop tank footprints stay inside their assigned lots."""
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = {row['building_id']:row for row in json.loads(
    (root/'Research/Mazzarino80/PCG/Buildings_Test18.json').read_text(encoding='utf-8'))['buildings']}
houses = json.loads((root/'Research/Mazzarino80/PCG/BakedSource/approved_modules.json').read_text(encoding='utf-8'))['houses']


def inside(p, poly):
    x,y = p
    result = False
    for a,b in zip(poly, poly[1:]+poly[:1]):
        if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            result = not result
    return result


report = {}
for lot,row in rows.items():
    if not row.get('rooftop_tank'):
        continue
    specs = [p for p in houses[lot]['stage_points']['Details'] if p['role']=='rooftop_water_tank']
    if len(specs)!=1:
        raise RuntimeError(f'{lot}: expected one rooftop tank point')
    spec = specs[0]
    x,y,z = spec['location_cm']
    poly = [p[:2] for p in row['footprint_world_cm']]
    a = poly[row['front_edge']]
    b = poly[(row['front_edge']+1)%len(poly)]
    yaw = math.atan2(b[1]-a[1],b[0]-a[0])
    c,s = math.cos(yaw),math.sin(yaw)
    corners = [(x+c*u-s*v,y+s*u+c*v) for u in (-80.81,80.81) for v in (-118.33,118.33)]
    report[lot] = {'center_inside':inside((x,y),poly),
                   'corners_inside':[inside(p,poly) for p in corners],
                   'z_cm':z}
path=root/'Saved/Mazzarino80/PCG/validate_tanks.json'
path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
