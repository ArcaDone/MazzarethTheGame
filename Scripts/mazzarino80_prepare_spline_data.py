"""Create editable road centre lines using the same reference frame as the overview."""
import json, math
from pathlib import Path
ROOT=Path(r'D:\UE5Projects\GameAnimationSample')
namespace={}
code=(ROOT/'Scripts/mazzarino80_generate_overview.py').read_text(encoding='utf-8')
exec(code.split('roads = Obj(')[0],namespace)
point=namespace['point']
anchor_x,anchor_y,anchor_z=namespace['anchor_x'],namespace['anchor_y'],namespace['anchor_z']
south,west,north,east=[namespace[x] for x in ('south','west','north','east')]
widths={'primary':8,'secondary':7,'tertiary':6,'residential':5,'unclassified':4.5,
        'service':3.5,'pedestrian':4,'footway':1.8,'steps':1.5,'track':3}
features=json.loads((ROOT/'Research/Mazzarino80/Mazzarino_OSM_strade_chiese_2026.geojson').read_text(encoding='utf-8-sig'))['features']
roads=[]
for feature in features:
    if feature['geometry']['type']!='LineString':continue
    tags=feature.get('properties',{})
    highway=tags.get('highway')
    if highway not in widths:continue
    name=tags.get('name','')
    corso='corso vittorio emanuele' in name.lower()
    width=widths[highway]
    # Keep every segment represented in the earlier overview; split at the study boundary.
    runs=[]
    run=[]
    for a,b in zip(feature['geometry']['coordinates'],feature['geometry']['coordinates'][1:]):
        inside=all(west<=p[0]<=east and south<=p[1]<=north for p in (a,b))
        if not inside:
            if len(run)>1:runs.append(run)
            run=[]
            continue
        pa,pb=point(*a,drape=True),point(*b,drape=True)
        if math.hypot(pb[0]-pa[0],pb[1]-pa[1])<20:continue
        if not run:run.append(a)
        run.append(b)
    if len(run)>1:runs.append(run)
    for part,run in enumerate(runs):
        points=[]
        for a,b in zip(run,run[1:]):
            pa,pb=point(*a,drape=True),point(*b,drape=True)
            # Intermediate control points follow relief and can be edited individually.
            pieces=max(1,math.ceil(math.hypot(pb[0]-pa[0],pb[1]-pa[1])/1200))
            dx,dy=pb[0]-pa[0],pb[1]-pa[1]
            length=math.hypot(dx,dy)
            # Convert world perpendicular offsets back to longitude/latitude.
            r=namespace['rotation'];s=namespace['scale']
            px,py=-dy/length*width*0.5,dx/length*width*0.5
            e=(px*math.cos(r)-py*math.sin(r))*s
            n=(px*math.sin(r)+py*math.cos(r))*s
            dlon=e/namespace['metres_lon'];dlat=n/namespace['metres_lat']
            for index in range(pieces):
                t=index/pieces
                lon=a[0]+(b[0]-a[0])*t;lat=a[1]+(b[1]-a[1])*t
                x,y,z=point(lon,lat,drape=True)
                z=max(z,point(lon+dlon,lat+dlat,drape=True)[2],point(lon-dlon,lat-dlat,drape=True)[2])+25
                points.append([x+anchor_x*100,y+anchor_y*100,z+anchor_z*100])
        lon,lat=run[-1]
        x,y,z=point(lon,lat,drape=True)
        z=max(z,point(lon+dlon,lat+dlat,drape=True)[2],point(lon-dlon,lat-dlat,drape=True)[2])+25
        points.append([x+anchor_x*100,y+anchor_y*100,z+anchor_z*100])
        closed=math.dist(points[0][:2],points[-1][:2])<1
        if closed:points.pop()
        roads.append({'id':tags.get('@id',''),'part':part,'name':name,'highway':highway,
                      'width_m':width,'corso':corso,'closed':closed,'points_cm':points})
out=ROOT/'Research/Mazzarino80/generated/road_splines.json'
out.write_text(json.dumps(roads,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'roads':len(roads),'points':sum(len(r['points_cm']) for r in roads),
                  'corso':[{'id':r['id'],'name':r['name'],'points':len(r['points_cm'])} for r in roads if r['corso']]}))
# Flat neutral pavement for the remaining roads, with predictable width and UVs.
obj=ROOT/'Research/Mazzarino80/generated/M80_RoadSlab.obj'
obj.write_text('o M80_RoadSlab\nv -500 -50 -8\nv 500 -50 -8\nv 500 50 -8\nv -500 50 -8\nv -500 -50 0\nv 500 -50 0\nv 500 50 0\nv -500 50 0\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nf 5/1 6/2 7/3 8/4\nf 4/1 3/2 2/3 1/4\nf 1/1 2/2 6/3 5/4\nf 2/1 3/2 7/3 6/4\nf 3/1 4/2 8/3 7/4\nf 4/1 1/2 5/3 8/4\n',encoding='ascii')
