"""Download a public Copernicus GLO-30 terrain tile for a visual fallback."""

import shutil
import urllib.request
from pathlib import Path


name = "Copernicus_DSM_COG_10_N37_00_E014_00_DEM"
url = f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
target = Path(r"D:\UE5Projects\GameAnimationSample\Research\Mazzarino80\Copernicus_GLO30_N37_E014.tif")
request = urllib.request.Request(url, headers={"User-Agent": "Mazzarino80 terrain preview/1.0"})
with urllib.request.urlopen(request, timeout=180) as response, target.open("wb") as output:
    shutil.copyfileobj(response, output)
print(f"COPERNICUS_DEM {target.stat().st_size} {target}")
