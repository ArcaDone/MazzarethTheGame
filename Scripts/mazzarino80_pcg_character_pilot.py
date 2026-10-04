"""Apply one photo-informed geometry pilot in the isolated PCG validation level."""
import importlib
import json
import sys
import traceback
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir())
sys.path.insert(0, str(ROOT / "Scripts"))
OUT = ROOT / "Saved/Mazzarino80/PCG/character_pilot.json"


def main():
    result = {"level": "/Game/Mazzarino80/PCG/Validation/L_PCGBuildings_WithContext",
              "lot": "1249069202"}
    try:
        if not unreal.EditorLevelLibrary.load_level(result["level"]):
            raise RuntimeError("Could not load isolated validation map")
        import mazzarino80_pcg_create_catalog_bp as catalog_module
        importlib.reload(catalog_module)
        import mazzarino80_pcg_refresh_one as refresh_module
        refresh_module = importlib.reload(refresh_module)
        result["refresh"] = refresh_module.refresh(result["lot"], save=True)
        result["saved"] = unreal.EditorLevelLibrary.save_current_level()
    except Exception:
        result["error"] = traceback.format_exc()
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    unreal.log("M80_CHARACTER_PILOT " + str(OUT))


main()
