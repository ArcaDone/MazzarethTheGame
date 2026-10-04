"""Preserve the exact imported footprints in the corrected world coordinate frame."""
import json,math
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample');DATA=ROOT/'Research/Mazzarino80'
osm=json.loads((DATA/'Mazzarino_OSM_edifici_2026.json').read_text(encoding='utf-8-sig'))
vertices=[list(map(float,line.split()[1:])) for line in (DATA/'generated/M80_Edifici.obj').read_text().splitlines() if line.startswith('v ')]
roads=json.loads((DATA/'generated/road_splines.json').read_text())
segments=[]
for r in roads:
    if not r['corso']:continue
    for a,b in zip(r['points_cm'],r['points_cm'][1:]):segments.append(([a[0],-a[1]],[b[0],-b[1]]))
def nearest(p):
    candidates=[]
    for a,b in segments:
        dx,dy=b[0]-a[0],b[1]-a[1];l=dx*dx+dy*dy
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/l)) if l else 0
        q=[a[0]+t*dx,a[1]+t*dy]
        candidates.append((math.dist(p,q),q))
    return min(candidates)
rows=[];cursor=0
for e in osm['elements']:
    ring=[(p['lon'],p['lat']) for p in e.get('geometry',[])]
    if len(ring)<4:continue
    if ring[0]==ring[-1]:ring.pop()
    if len(ring)<3 or not all(14.204<=x<=14.227 and 37.296<=y<=37.313 for x,y in ring):continue
    n=len(ring);bottom=vertices[cursor:cursor+n];top=vertices[cursor+n:cursor+2*n];cursor+=2*n
    p=[[x+82373.88,-y+4006.4] for x,y,z in bottom]
    if sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1]))<0:p.reverse()
    cx=sum(x for x,y in p)/n;cy=sum(y for x,y in p)/n
    area=abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(p,p[1:]+p[:1])))*0.5/10000
    distance,q=nearest([cx,cy]);valid_edges=[k for k in range(n) if math.dist(p[k],p[(k+1)%n])>350]
    front=min(valid_edges or list(range(n)),key=lambda k:nearest([(p[k][0]+p[(k+1)%n][0])/2,(p[k][1]+p[(k+1)%n][1])/2])[0])
    edge=p[(front+1)%n][0]-p[front][0],p[(front+1)%n][1]-p[front][1]
    rows.append({'id':str(e['id']),'tags':e.get('tags',{}),'ring_cm':p,'center_cm':[cx,cy,bottom[0][2]+17100],
                 'height_m':(top[0][2]-bottom[0][2])/100,'area_m2':area,'distance_corso_m':distance/100,
                 'front_edge':front,'ridge_degrees':math.degrees(math.atan2(edge[1],edge[0]))})
assert cursor==len(vertices),(cursor,len(vertices))
# A compact continuous sample near Matrice; heights and styling remain explicitly indicative.
pilot=[r for r in rows if 69000<r['center_cm'][0]<82500 and r['distance_corso_m']<45 and 35<r['area_m2']<1500 and r['tags'].get('building') not in ('church','cathedral','roof','shed','garage')]
pilot=sorted(pilot,key=lambda r:(r['distance_corso_m'],abs(r['center_cm'][0]-79000)))[:14]
for r in rows:r['pilot']=r in pilot
(DATA/'building_footprint_plan.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'buildings':len(rows),'pilot':[r['id'] for r in pilot],'landmarks':[(r['id'],r['tags'],r['center_cm'],r['area_m2']) for r in rows if r['tags'].get('building') in ['church','cathedral'] or any(n in str(r['tags']).lower() for n in ['municip','comune','scuola'])]},ensure_ascii=False))

