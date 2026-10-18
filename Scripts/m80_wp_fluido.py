"""The town's (L_M80_Paese_WP) streaming against the freezes while driving:
- writes the runtime partitions with their Block On Slow Streaming and turns it off where it is on (2026-10-18 it was
  already off everywhere: the freezes are the houses' packages loading on the game thread in Play In Editor);
- with M80_TERRENO=1 the terrain (LandscapeStreamingProxy, 25 pieces, ~5 MB) becomes always loaded, so the ground is
  under the wheels whatever comes in late. Only after rebuilding the HLODs: 55 HLOD actors hold the landscape, and
  until rebuilt the far terrain would show twice.
Saves the map's package and the landscape pieces it changed, nothing else.
Out: Saved/Mazzarino80/Memoria/wp_fluido.txt
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_wp_fluido.py
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
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def prop(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception:  # noqa: BLE001
        return "?"


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 30
    world = m80_seq.editor_world()
    if world.get_path_name() != m80_seq.TOWN_MAP + "." + m80_seq.TOWN_MAP.rsplit("/", 1)[1]:
        raise RuntimeError("The open map is %s" % world.get_path_name())
    before = LIB.describe_runtime_partitions(world)
    lines += ["partitions before:", before]
    names = sorted({l.split()[0] for l in before.splitlines() if "BlockOnSlowStreaming=1" in l})
    for n in names:
        lines.append("block off %s: %s" % (n, LIB.set_runtime_partition_block_on_slow_streaming(world, n, False)))
    lines += ["partitions after:", LIB.describe_runtime_partitions(world)]
    if names:
        lines.append("map saved: %s" % unreal.EditorLoadingAndSavingUtils.save_packages([world.get_package()], False))

    m80_seq.load(m80_seq.actor_descs("LandscapeStreamingProxy"))
    yield 60
    proxies = [a for a in EAS.get_all_level_actors() if a.get_class().get_name() == "LandscapeStreamingProxy"]
    in_hlod = [p for p in proxies if prop(p, "hlod_layer") not in (None, "?")]
    lines.append("landscape pieces: %d, in an HLOD layer: %d %s" % (len(proxies), len(in_hlod),
                                                                     [str(prop(p, "hlod_layer").get_name()) for p in in_hlod[:3]]))
    if os.environ.get("M80_TERRENO") == "1" and proxies and not in_hlod:
        changed = []
        for p in proxies:
            if prop(p, "is_spatially_loaded"):
                p.set_editor_property("is_spatially_loaded", False)
                changed.append(p)
        lines.append("always loaded now: %d, saved: %s" % (len(changed), unreal.EditorLoadingAndSavingUtils.save_packages(
            [p.get_package() for p in changed], False) if changed else "-"))
    else:
        lines.append("terrain left spatially loaded (M80_TERRENO=1 after rebuilding the HLODs)")
    (OUT / "wp_fluido.txt").write_text("\n".join(lines), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "wp_fluido_error.txt"))
