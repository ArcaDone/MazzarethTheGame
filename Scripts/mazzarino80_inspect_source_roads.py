"""Read source package references without changing the Comune project."""
import json, re, hashlib
from pathlib import Path

ROOT = Path(r'D:\UE5Projects\GameAnimationSample')
SRC = Path(r'D:\UE5Projects\Comune\Content')
def refs(path):
    data = path.read_bytes()
    return sorted(set(s.decode('ascii') for s in re.findall(rb'/Game/[A-Za-z0-9_/]+', data)))
names = ['Spline_StradaLavica', 'Spline_StradaLavica_simple', 'Spline_StradaSquared']
result = {}
for name in names:
    todo = ['/Game/Esercitazioni/' + name]
    found = {}
    while todo:
        package = todo.pop()
        if package in found: continue
        path = SRC / (package[6:] + '.uasset')
        if not path.exists():
            found[package] = {'missing': True}
            continue
        dependencies = refs(path)
        target = ROOT / 'Content' / (package[6:] + '.uasset')
        found[package] = {'bytes': path.stat().st_size, 'dependencies': dependencies,
                          'target_exists': target.exists(),
                          'same': target.exists() and hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()}
        todo.extend(p for p in dependencies if p not in found)
    result[name] = found
out = ROOT / 'Research/Mazzarino80/comune_road_dependencies.json'
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
