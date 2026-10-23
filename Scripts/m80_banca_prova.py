"""The bank at its real size, in pieces (BancaPezzi.blend -> /Game/Mazzarino80/Buildings/BancaModulare), in a test level
/Game/Mazzarino80/Buildings/BancaModulare/L_M80_ProvaBanca (rebuilt each run): building, garden, gates and lettering where
the model had them, and the garden's perimeter drawn with AM80ModularFence and the bank's post and spear railing (open
at the front gate). A 1.80 m red figure stands at the gate. Pictures in Saved/Mazzarino80/Banca.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_banca_prova.py -ForceLit -TimeoutMinutes 30
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402
import m80_stairs_setup as kit  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
DEST = "/Game/Mazzarino80/Buildings/BancaModulare"
MAP = DEST + "/L_M80_ProvaBanca"
OUT = ROOT / "Saved/Mazzarino80/Banca"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
INFO = json.loads((ROOT / "Saved/Mazzarino80/Import/out/BancaModulare.json").read_text(encoding="utf-8"))
PX, PY, PZ = INFO["pivot_blender_m"]
STREET_Z = 2.4           # the garden walk in BancaPezzi.blend (m)


def ue(x, y, z=None):
    """A point of BancaPezzi.blend (m) in the level (cm), the building's pivot at the origin."""
    return unreal.Vector((x - PX) * 100, -(y - PY) * 100, ((z if z is not None else STREET_Z) - PZ) * 100)


def mesh_actor(label, mesh, loc):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(unreal.load_asset("%s/SM_M80_%s" % (DEST, mesh)))
    return a


def build():
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        unreal.EditorAssetLibrary.delete_asset(MAP)
    unreal.EditorLevelLibrary.new_level(MAP)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000), unreal.Rotator(0, -40, 150))
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("atmosphere_sun_light", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(7.0)
    EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
    gz = ue(0, 0).z
    ground = unreal.load_asset(kit.KIT + "/MI_M80_Cemento")
    kit.box("Suolo", (0, 0, gz - 50), (12000, 12000, 100), mat=ground)
    mesh_actor("Banca_Struttura", "BancaModulare", unreal.Vector(0, 0, 0))
    for part, off in INFO["pieces"].items():
        if part.startswith("Recinto"):
            continue
        o = off["offset_cm"]
        mesh_actor("Banca_" + part, "BancaModulare_" + part, unreal.Vector(o[0], -o[1], o[2]))
    # the garden's perimeter (real size), open at the front gate
    fence = EAS.spawn_actor_from_class(unreal.M80ModularFence, ue(-16.0, -31.2), unreal.Rotator(0, 0, 0))
    fence.set_actor_label("Banca_Recinzione")
    fence.set_editor_property("pillar_mesh", unreal.load_asset(DEST + "/SM_M80_BancaModulare_RecintoPilastro"))
    fence.set_editor_property("panel_mesh", unreal.load_asset(DEST + "/SM_M80_BancaModulare_RecintoPannello"))
    fence.set_editor_property("panels_per_bay", 1)
    fence.set_editor_property("wall_height_cm", 50.0)
    fence.set_editor_property("wall_thickness_cm", 40.0)
    path = fence.get_editor_property("path")
    path.clear_spline_points(False)
    for x, y in ((-16.0, -31.2), (-92.0, -31.2), (-92.0, 31.0), (-24.0, 31.0)):
        path.add_spline_point(ue(x, y), unreal.SplineCoordinateSpace.WORLD, False)
    path.update_spline()
    fence.rebuild()
    fig = kit.box("Persona_180", (ue(-14.0, -33.0).x, ue(-14.0, -33.0).y, gz + 90), (50, 30, 180))
    fig.static_mesh_component.set_material(0, unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
    return fence


VIEWS = {
    "ingresso": ((-12.0, -45.0, 1.7), (-12.0, -20.0, 4.0)),
    "recinto": ((-60.0, -40.0, 1.7), (-60.0, -31.0, 1.5)),
    "alto": ((30.0, -70.0, 40.0), (-35.0, 0.0, 0.0)),
}


def steps():
    fence = build()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 400
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (eye, at) in VIEWS.items():
        e, t = ue(*eye), ue(*at)
        rot = unreal.MathLibrary.find_look_at_rotation(e, t)
        m80_seq.set_view(e, rot)
        yield 90
        cap.capture(e, rot, OUT / ("%s.png" % name))
        yield 2
    cap.destroy()
    rep = {"campate": fence.get_editor_property("bay_count"),
           "pezzi": {a.get_actor_label(): str(a.static_mesh_component.static_mesh.get_name())
                     for a in EAS.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor) and a.get_actor_label().startswith("Banca")}}
    (OUT / "prova.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
