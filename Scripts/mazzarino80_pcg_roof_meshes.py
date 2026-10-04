"""Create exact, local-space roof slabs for irregular catalog footprints.

The geometry is an exception to the reusable module kit: every footprint is
triangulated once; PCG still chooses and instances its roof in the roof stage.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'Research/Mazzarino80/PCG/Buildings_Test18.json'
OUT = ROOT / 'Research/Mazzarino80/PCG/RoofMeshes_Source'
OUT.mkdir(parents=True, exist_ok=True)


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def area(poly):
    return sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(poly, poly[1:]+poly[:1])) / 2


def triangles(poly):
    verts = list(range(len(poly)))
    if area(poly) < 0:
        verts.reverse()
    result = []
    while len(verts) > 3:
        found = False
        for j in range(len(verts)):
            ia, ib, ic = verts[j-1], verts[j], verts[(j+1) % len(verts)]
            a, b, c = poly[ia], poly[ib], poly[ic]
            if cross(a,b,c) <= 0.001:
                continue
            if any(k not in (ia,ib,ic) and cross(a,b,poly[k]) >= -0.001 and
                   cross(b,c,poly[k]) >= -0.001 and cross(c,a,poly[k]) >= -0.001 for k in verts):
                continue
            result.append((ia,ib,ic))
            verts.pop(j)
            found = True
            break
        if not found:
            raise ValueError('Cannot triangulate footprint')
    result.append(tuple(verts))
    total = sum(cross(poly[a],poly[b],poly[c])/2 for a,b,c in result)
    if abs(total-abs(area(poly))) > 1:
        raise ValueError('Triangulation area differs')
    return result


def clip(points, direction, limit, keep_low):
    result = []
    for a,b in zip(points, points[1:]+points[:1]):
        va = a[0]*direction[0]+a[1]*direction[1]-limit
        vb = b[0]*direction[0]+b[1]*direction[1]-limit
        inside_a = va <= 0.0001 if keep_low else va >= -0.0001
        inside_b = vb <= 0.0001 if keep_low else vb >= -0.0001
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            t = va/(va-vb)
            result.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
    return result


def roof(record, obj_y_flip=False):
    poly = [(p[0],p[1]) for p in record['footprint_world_cm']]
    tris = triangles(poly)
    xmin,xmax = min(p[0] for p in poly),max(p[0] for p in poly)
    ymin,ymax = min(p[1] for p in poly),max(p[1] for p in poly)
    cx,cy = (xmin+xmax)/2,(ymin+ymax)/2
    front = record['front_edge']
    a,b = poly[front],poly[(front+1)%len(poly)]
    dx,dy = b[0]-a[0],b[1]-a[1]
    length = math.hypot(dx,dy)
    sign = -1 if area(poly)>0 else 1
    direction = (-sign*dy/length,sign*dx/length)
    projections = [p[0]*direction[0]+p[1]*direction[1] for p in poly]
    low,high = min(projections),max(projections)
    ridge = (low+high)/2
    rise = 0 if record['roof_type']=='Terrace' else float(record['roof_rise_cm'])
    span = max(1,high-low)

    def top(p):
        q = (p[0]*direction[0]+p[1]*direction[1]-low)/span
        return rise*max(0,1-abs(2*q-1))-7

    vertices=[]
    tex=[]
    faces=[]

    def tri(points, zfunc, flip=False):
        indices=[]
        for p in points:
            vertices.append((p[0]-cx,p[1]-cy,zfunc(p)))
            tex.append(((p[0]-cx)/220,(p[1]-cy)/220))
            indices.append(len(vertices))
        faces.append(tuple(reversed(indices)) if flip else tuple(indices))

    for inds in tris:
        source=[poly[i] for i in inds]
        if rise:
            for side in (True,False):
                polygon=clip(source,direction,ridge,side)
                for j in range(1,len(polygon)-1):
                    tri([polygon[0],polygon[j],polygon[j+1]],top)
        else:
            tri(source,top)
        tri(source,lambda p:-21,True)
    ccw = poly if area(poly)>0 else list(reversed(poly))
    for a,b in zip(ccw,ccw[1:]+ccw[:1]):
        verts=[(a[0]-cx,a[1]-cy,top(a)),(a[0]-cx,a[1]-cy,-21),
               (b[0]-cx,b[1]-cy,-21),(b[0]-cx,b[1]-cy,top(b))]
        start=len(vertices)+1
        vertices.extend(verts)
        edge=math.hypot(b[0]-a[0],b[1]-a[1])/220
        tex.extend([(0,1),(0,0),(edge,0),(edge,1)])
        faces.extend([(start,start+1,start+2),(start,start+2,start+3)])
    name='SM_PCG_Roof_'+record['building_id']
    path=OUT/(name+'.obj')
    lines=['o '+name]
    # Unreal's OBJ importer mirrors Y. Batch01 requests an inverse mirror so
    # the imported roof matches the source spline and facade module anchors.
    lines.extend('v %.5f %.5f %.5f' % (x, -y if obj_y_flip else y, z)
                 for x, y, z in vertices)
    lines.extend('vt %.5f %.5f'%uv for uv in tex)
    lines.extend('f '+' '.join('%d/%d'%(i,i) for i in face) for face in faces)
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'path':str(path),'triangles':len(faces),'vertices':len(vertices),'area_cm2':abs(area(poly)),
            'center_xy_cm':[cx,cy],'roof_base_z_cm':min(p[2] for p in record['footprint_world_cm'])+record['primary_floors']*record['floor_height_cm']}


def main():
    records=json.loads(CATALOG.read_text(encoding='utf-8'))['buildings']
    result={r['building_id']:roof(r) for r in records}
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'houses':len(result),'triangles':sum(x['triangles'] for x in result.values())}))


if __name__=='__main__':
    main()
