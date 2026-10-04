"""Copies assets from another UE 5.5 project (default D:/UE5Projects/Comune) keeping their /Game paths,
together with everything they reference, like the editor's "Migrate" but without opening the source project.

References are read from the package name tables (every "/Game/..." string in the .uasset), which is what
the editor Migrate follows too. Files that already exist in this project are left alone (they are
reported if they differ), so running it twice is harmless.

Usage (plain Python, editor closed):
  python Tools/Migrate/m80_migrate.py /Game/Drive/fiat126/BP_Fiat126 /Game/Decals_mazza [--dry-run]
A root can be a package or a folder (everything inside it).
"""
import argparse
import filecmp
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
REF = re.compile(rb"/Game/[A-Za-z0-9_/\-\.&]+")


def package_files(content, package):
    """The .uasset/.umap (+ .uexp/.ubulk) files of a /Game/... package, or [] if missing."""
    rel = package[len("/Game/"):]
    for ext in (".uasset", ".umap"):
        f = content / (rel + ext)
        if f.exists():
            return [f] + [f.with_suffix(s) for s in (".uexp", ".ubulk", ".uptnl") if f.with_suffix(s).exists()]
    return []


def numbered_packages(content, package):
    rel = Path(package[len("/Game/"):])
    folder = content / rel.parent
    if not folder.is_dir():
        return []
    pat = re.compile(re.escape(rel.name) + r"_\d+$")
    return ["/Game/" + (rel.parent / f.stem).as_posix() for f in folder.iterdir() if f.suffix in (".uasset", ".umap") and pat.match(f.stem)]


def references(path):
    out = set()
    for m in REF.findall(path.read_bytes()):
        name = m.decode("ascii", "ignore").split(".")[0].rstrip("/")
        out.add(name)
    return out


def expand_roots(content, roots):
    pkgs = []
    for r in roots:
        r = r.rstrip("/")
        folder = content / r[len("/Game/"):]
        if folder.is_dir():
            pkgs += ["/Game/" + p.relative_to(content).with_suffix("").as_posix() for p in folder.rglob("*") if p.suffix in (".uasset", ".umap")]
        else:
            pkgs.append(r.split(".")[0])
    return pkgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--source", default="D:/UE5Projects/Comune/Content")
    ap.add_argument("--dest", default=str(HERE / "Content"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default=str(HERE / "Saved/Mazzarino80/migrate_report.json"))
    a = ap.parse_args()
    src, dst = Path(a.source), Path(a.dest)
    todo = expand_roots(src, a.roots)
    seen, missing, copied, existing, differs = set(), [], [], [], []
    size = 0
    while todo:
        pkg = todo.pop()
        if pkg in seen:
            continue
        seen.add(pkg)
        files = package_files(src, pkg)
        if not files:
            # Names ending in _<n> are stored as FName "base" + number: "/Game/X/Cabin__Plane" may be Cabin__Plane_179.
            numbered = numbered_packages(src, pkg)
            if numbered:
                todo += [p for p in numbered if p not in seen]
            elif not package_files(dst, pkg) and not numbered_packages(dst, pkg):
                missing.append(pkg)
            continue
        todo += [r for r in references(files[0]) if r not in seen]
        for f in files:
            target = dst / f.relative_to(src)
            if target.exists():
                existing.append(target.relative_to(dst).as_posix())
                if not filecmp.cmp(f, target, shallow=False):
                    differs.append(target.relative_to(dst).as_posix())
                continue
            size += f.stat().st_size
            copied.append(target.relative_to(dst).as_posix())
            if not a.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, target)
    report = {"roots": a.roots, "dry_run": a.dry_run, "copied_mb": round(size / 1e6, 1), "copied": sorted(copied),
              "already_present": len(existing), "present_but_different": sorted(differs), "missing_in_source": sorted(missing)}
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("{} {} files, {} MB; {} already present ({} different); {} references not found".format(
        "would copy" if a.dry_run else "copied", len(copied), report["copied_mb"], len(existing), len(differs), len(missing)))


if __name__ == "__main__":
    main()
