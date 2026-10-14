"""The town's World Partition runtime grid (L_M80_Paese_WP): writes its runtime partitions (cell size and loading range
of the main layer and of the HLOD layers) and, with M80_GRID="<cell m>,<range m>", sets the main layer's ones and saves
the map. The HLODs are built on the old cells: rebuild them afterwards (Build > Build HLODs).
Needs UM80EditorLibrary.DescribeRuntimePartitions/SetRuntimePartitionGrid (the runtime hash set is hidden from Python).
Output: Saved/Mazzarino80/Memoria/wp_griglia.txt
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_wp_griglia.py
$env:M80_GRID="64,192"; powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_wp_griglia.py
"""
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Memoria"
LIB = unreal.M80EditorLibrary


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 30
    world = m80_seq.editor_world()
    if world.get_path_name() != m80_seq.TOWN_MAP + "." + m80_seq.TOWN_MAP.rsplit("/", 1)[1]:
        raise RuntimeError("The open map is %s" % world.get_path_name())
    before = LIB.describe_runtime_partitions(world)
    lines = ["before:", before]
    grid = os.environ.get("M80_GRID", "").strip()
    if grid:
        cell_m, range_m = (float(x) for x in grid.split(","))
        # The partition to change is the one whose main layer is a grid (has a cell size).
        names = [l.split()[0] for l in before.splitlines() if l.split()[1:2] == ["Main"] and "CellSize=" in l]
        if len(names) != 1:
            raise RuntimeError("Not one grid partition: %s" % names)
        if not LIB.set_runtime_partition_grid(world, names[0], int(cell_m * 100), int(range_m * 100)):
            raise RuntimeError("SetRuntimePartitionGrid failed")
        lines += ["after:", LIB.describe_runtime_partitions(world)]
        lines.append("saved: %s" % unreal.EditorLoadingAndSavingUtils.save_packages([world.get_package()], False))
    (OUT / "wp_griglia.txt").write_text("\n".join(lines), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "wp_griglia_error.txt"))
