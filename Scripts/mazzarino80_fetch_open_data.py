"""Fetch public OSM building footprints and Sicily terrain service metadata."""

import json
import urllib.parse
import urllib.request
from pathlib import Path


root = Path(r"D:\UE5Projects\GameAnimationSample\Research\Mazzarino80")
root.mkdir(parents=True, exist_ok=True)
headers = {"User-Agent": "Mazzarino80 research prototype/1.0 (OpenStreetMap attribution retained)"}

south, west, north, east = 37.296, 14.204, 37.313, 14.227
query = f"[out:json][timeout:120];way[building]({south},{west},{north},{east});out geom;"
body = urllib.parse.urlencode({"data": query}).encode("ascii")
sources = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
errors = []
for url in sources:
    try:
        request = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(request, timeout=150) as response:
            data = json.load(response)
        if not isinstance(data.get("elements"), list):
            raise ValueError("Overpass response has no elements")
        target = root / "Mazzarino_OSM_edifici_2026.json"
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"OSM_BUILDINGS {len(data['elements'])} {target}")
        break
    except Exception as exc:
        errors.append(f"{url}: {exc}")
else:
    print("OSM_FAILED " + " | ".join(errors))

url = "https://map.sitr.regione.sicilia.it/gis/rest/services/modelli_digitali/mdt_2013/ImageServer?f=pjson"
try:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.load(response)
    target = root / "Sicilia_MDT_2013_ImageServer_metadata.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MDT_METADATA {data.get('pixelSizeX')} {data.get('pixelSizeY')} {target}")
except Exception as exc:
    print(f"MDT_FAILED {exc}")
