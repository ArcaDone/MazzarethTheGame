import json
from pathlib import Path
import unreal

root=Path(unreal.Paths.project_dir())
lot='1249069275'
rows=[]
for section in (0,1,2,4):
    path=root/f'Research/Mazzarino80/PCG/BakedSource/Surface_{lot}_S{section}.obj'
    verts=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('v '):
            verts.append([float(v) for v in line.split()[1:4]])
    mesh=unreal.load_asset(f'/Game/Mazzarino80/PCG/ApprovedModules/SM_PCG_Source_{lot}_S{section}')
    rows.append({'section':section,'source_min':[min(v[i] for v in verts) for i in range(3)],
                 'source_max':[max(v[i] for v in verts) for i in range(3)],
                 'mesh_bounds':str(mesh.get_bounds())})
(root/'Saved/Mazzarino80/PCG/audit_mesh_bounds.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
