"""Copy the selected UE package closure without replacing project assets.

The closure is produced by Unreal's Asset Registry. Existing packages retain
their current version; copied files are verified by SHA-256 before use.
"""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(r"D:\UE5Projects\Comune\Content")
TARGET = ROOT / "Content"
PLAN = ROOT / "Pipeline/Unreal/comune_migration_plan.json"
OUT = ROOT / "Pipeline/Unreal/comune_migration_result.json"


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(data)
    return result.hexdigest()


packages = json.loads(PLAN.read_text(encoding="utf-8"))["packages"]
records = []
pending = []
for package in packages:
    assert package.startswith("/Game/") and ".." not in package
    relative = Path(*package.removeprefix("/Game/").split("/"))
    src_asset = (SOURCE / relative).with_suffix(".uasset")
    dst_asset = (TARGET / relative).with_suffix(".uasset")
    if not src_asset.is_file():
        raise FileNotFoundError(f"Missing source dependency: {package}")
    companions = sorted(p for p in src_asset.parent.glob(src_asset.stem + ".*")
                        if p.suffix in {".uasset", ".uexp", ".ubulk", ".uptnl"})
    if dst_asset.exists():
        records.append({"package": package, "status": "existing_identical" if
                        sha256(src_asset) == sha256(dst_asset) else "existing_preserved",
                        "files": [str(dst_asset)]})
        continue
    pending.extend((src, dst_asset.parent / src.name) for src in companions)
    records.append({"package": package, "status": "copied", "files":
                    [str(dst_asset.parent / src.name) for src in companions]})

for source, destination in pending:
    if destination.exists():
        raise FileExistsError(f"Unexpected existing sidecar: {destination}")

for source, destination in pending:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".migrating")
    shutil.copy2(source, temp)
    if sha256(temp) != sha256(source):
        raise OSError(f"Copy verification failed: {source}")
    temp.replace(destination)

result = {"source": str(SOURCE), "target": str(TARGET), "packages": records,
          "copied_files": len(pending), "bytes_copied": sum(src.stat().st_size for src, _ in pending)}
OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
print("COMUNE_MIGRATION", "packages", len(records), "files", len(pending),
      "MiB", round(result["bytes_copied"] / 1048576, 2))
