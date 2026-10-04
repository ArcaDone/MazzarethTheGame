"""Inspect the loaded UE 5.5 PCG Python surface without changing assets."""
import json
from pathlib import Path

import unreal

names = [name for name in dir(unreal) if name.startswith("PCG")]
focus = [name for name in names if any(term in name.lower() for term in (
    "graph", "component", "spline", "subgraph", "spawn", "point", "mesh", "data", "settings"
))]
classes = {}
for name in focus:
    obj = getattr(unreal, name)
    if isinstance(obj, type):
        classes[name] = [method for method in dir(obj) if any(word in method.lower() for word in (
            "node", "edge", "graph", "generate", "setting", "point", "data", "input", "output"
        ))]
root = Path(unreal.Paths.project_dir())
out = root / "Saved/Mazzarino80/PCG/pcg_python_api.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"pcg_classes": classes}, indent=2), encoding="utf-8")
unreal.log("M80_PCG_API_PROBE " + str(out))
