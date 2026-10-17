"""Close look at the sidewalk (AM80Sidewalk, "Marciapiede (Mazzarino)"): a curving test sidewalk on uneven ground in a
level made in memory (/Temp, never saved), photographed from the road at kerb height and from above, and the sizes of its
pieces written down (slab and kerb meshes, how much the kerb is stretched in height).
Out: Saved/Mazzarino80/Marciapiede/*.png + marciapiede.json
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_marciapiede_prova.py -ForceLit -TimeoutMinutes 15
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Marciapiede"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector
report = {}


def box(mesh):
    b = mesh.get_bounding_box()
    return [round(b.min.x, 1), round(b.min.y, 1), round(b.min.z, 1), round(b.max.x, 1), round(b.max.y, 1), round(b.max.z, 1)]


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.png"):
        f.unlink()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level("/Temp/L_M80_ProvaMarciapiede", False)
    yield 20
    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), V(0, 0, 0))
    floor.set_actor_scale3d(V(200, 200, 1))
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 500), unreal.Rotator(0, -35, 40))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, V(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 300))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    yield 20
    origin = V(-1000, -1000, 0)
    # Uneven ground: a street sloping across at the start, a hump along the bend (the slab must follow both).
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    for at, size, rot in ((V(450, 0, -20), V(9, 7, 0.4), unreal.Rotator(7, 0, 0)),
                          (V(1700, 450, -35), V(10, 10, 0.8), unreal.Rotator(0, 6, 30))):
        ramp = EAS.spawn_actor_from_object(cube, origin + at)
        ramp.set_actor_rotation(rot, False)
        ramp.set_actor_scale3d(size)
    sw = EAS.spawn_actor_from_class(unreal.M80Sidewalk, origin)
    path = sw.get_editor_property("path")
    path.clear_spline_points(False)
    for i, (x, y) in enumerate([(0, 0), (900, 0), (1700, 450), (2200, 1300), (2300, 2300)]):
        path.add_spline_point(origin + V(x, y, 0), unreal.SplineCoordinateSpace.WORLD, False)
    path.update_spline()
    sw.set_editor_property("curb_side", unreal.M80CurbSide.RIGHT)
    sw.rebuild()
    yield 30
    slab = sw.get_editor_property("slab_mesh")
    curb = sw.get_editor_property("curb_mesh")
    report["slab_mesh"] = [slab.get_path_name(), box(slab)] if slab else None
    report["curb_mesh"] = [curb.get_path_name(), box(curb)] if curb else None
    if curb:
        b = curb.get_bounding_box()
        top = sw.get_editor_property("top_height_cm")
        report["curb_height_cm"] = round(b.max.z - b.min.z, 1)
        report["curb_stretch_z"] = round((top + 2 + 25 + top) / max(0.1, b.max.z - b.min.z), 2)
        report["curb_materials"] = [str(m.get_editor_property("material_interface").get_path_name())
                                    for m in curb.get_editor_property("static_materials") if m.get_editor_property("material_interface")]
    comps = sw.get_components_by_class(unreal.SplineMeshComponent)
    report["pieces"] = len(comps)
    cap = m80_seq.ViewCapture(1280, 720, 55)
    # From the road (the kerb side: right of the walking direction, +Y at the start), kerb height, and from above.
    for name, eye, at in (("strada_basso", origin + V(450, 320, 25), origin + V(450, 0, 15)),
                          ("strada_alto", origin + V(450, 500, 170), origin + V(600, 0, 0)),
                          ("curva", origin + V(1300, 900, 60), origin + V(1700, 450, 10)),
                          ("dall_alto", origin + V(1100, 1400, 900), origin + V(1300, 300, 0)),
                          ("lato_casa", origin + V(450, -380, 30), origin + V(450, 0, 10))):
        cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, at), str(OUT / (name + ".png")))
        yield 5
    cap.destroy()
    EAS.destroy_actor(sw)
    (OUT / "marciapiede.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
