"""Export candidate static-mesh geometry for a side-by-side Blender review."""
import json
from pathlib import Path
import unreal

ROOT = Path(r"D:\UE5Projects\GameAnimationSample\Pipeline\Unreal\comune_geometry_review")
ROOT.mkdir(parents=True, exist_ok=True)
AUDIT = Path(r"D:\UE5Projects\GameAnimationSample\Pipeline\Unreal\comune_candidate_audit.json")
records = json.loads(AUDIT.read_text(encoding="utf-8"))["candidates"]
names = {
    "SM_clothes_A_02", "SM_clothes_A_03", "SM_clothes_A_04", "SM_clothes_A_05",
    "SM_clothes_B_01", "SM_clothes_B_02", "SM_clothes_B_03",
    "SM_Clothes_01", "SM_Clothes_02", "SM_Clothes_03",
    "SM_stairs_01", "SM_Old_Stair_01", "SM_Old_Stair_02",
    "SM_Rain_Pipe_01", "SM_awning_01", "SM_Windows_grill_01",
    "SM_metal_fence_01", "SM_Metal_Fence_02", "SM_wooden_beams_01",
}
done = []
for record in records:
    name = record["path"].rsplit("/", 1)[-1]
    if name not in names:
        continue
    asset = unreal.EditorAssetLibrary.load_asset(record["path"])
    if not asset:
        done.append({"path": record["path"], "exported": False, "reason": "load failed"})
        continue
    filename = ROOT / (record["group"] + "__" + name + ".fbx")
    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = str(filename)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = unreal.StaticMeshExporterFBX()
    try:
        ok = bool(unreal.Exporter.run_asset_export_task(task))
        done.append({"path": record["path"], "fbx": str(filename), "exported": ok and filename.exists()})
    except Exception as error:
        done.append({"path": record["path"], "exported": False, "reason": str(error)})

(ROOT / "export_manifest.json").write_text(json.dumps(done, indent=2), encoding="utf-8")
print("COMUNE_GEOMETRY_EXPORT", len(done), sum(x["exported"] for x in done))
