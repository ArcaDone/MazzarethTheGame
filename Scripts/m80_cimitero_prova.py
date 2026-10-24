"""The cemetery in pieces (CimiteroPezzi.blend -> /Game/Mazzarino80/Buildings/Cimitero) put together in a test level,
/Game/Mazzarino80/Buildings/Cimitero/L_M80_ProvaCimitero (rebuilt each run), on flat ground:
- the entrance (the level's origin is its pivot), the gate, the galleries, the family chapels and the walks where they
  stand in the master file (D:/Cimitero_Mazzarino, site_inventory.json);
- the wall drawn with AM80ModularFence (RecintoPilastro / RecintoPannello) along the master's outline, open at the
  entrance building;
- the eight plots as AM80CemeteryField, each filled with the tomb library (every Tomba_* kind, same weight), its rows
  across the cemetery's axis as in the master, a seed of its own.
A 1.80 m red figure stands in the main walk. Pictures in Saved/Mazzarino80/Cimitero.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_cimitero_prova.py -ForceLit -TimeoutMinutes 40
"""
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402
import m80_stairs_setup as kit  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
DEST = "/Game/Mazzarino80/Buildings/Cimitero"
MAP = DEST + "/L_M80_ProvaCimitero"
OUT = ROOT / "Saved/Mazzarino80/Cimitero"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
INFO = json.loads((ROOT / "Saved/Mazzarino80/Import/out/Cimitero.json").read_text(encoding="utf-8"))
SITE = json.loads(Path("D:/Cimitero_Mazzarino/source/site_inventory.json").read_text(encoding="utf-8"))
PX, PY, PZ = INFO["pivot_blender_m"]
SPINE = math.radians(SITE["spine_rotation_degrees"])
WALK_Z = 0.0           # the walks' level in the master (m); the plots stand about 0.5 m higher there
SITE_PIECES = ("Cancello", "Gallerie", "Cappelle", "Viali")


def master(u, d):
    """The site's own frame (u across, d from the entrance southwards, m) -> the master file's x, y (m)."""
    x, y = u, -d
    return (x * math.cos(SPINE) - y * math.sin(SPINE), x * math.sin(SPINE) + y * math.cos(SPINE))


def ue(x, y, z=None):
    """A point of the master file (m) in the level (cm), the entrance's pivot at the origin."""
    return unreal.Vector((x - PX) * 100, -(y - PY) * 100, ((z if z is not None else WALK_Z) - PZ) * 100)


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
    c = ue(*master(0, 60))
    kit.box("Suolo", (c.x, c.y, gz - 50), (20000, 20000, 100), mat=unreal.load_asset(kit.KIT + "/MI_M80_Cemento"))
    mesh_actor("Cimitero_Ingresso", "Cimitero", unreal.Vector(0, 0, 0))
    for part in SITE_PIECES:
        o = INFO["pieces"][part]["offset_cm"]
        mesh_actor("Cimitero_" + part, "Cimitero_" + part, unreal.Vector(o[0], -o[1], o[2]))
    # the wall along the outline, from the entrance building's east end round to its west end
    outline = SITE["footprint_local"]
    fence = EAS.spawn_actor_from_class(unreal.M80ModularFence, ue(*master(*outline[1])), unreal.Rotator(0, 0, 0))
    fence.set_actor_label("Cimitero_Recinto")
    fence.set_editor_property("pillar_mesh", unreal.load_asset(DEST + "/SM_M80_Cimitero_RecintoPilastro"))
    fence.set_editor_property("panel_mesh", unreal.load_asset(DEST + "/SM_M80_Cimitero_RecintoPannello"))
    fence.set_editor_property("panels_per_bay", 2)
    fence.set_editor_property("wall", False)
    path = fence.get_editor_property("path")
    path.clear_spline_points(False)
    for u, d in outline[1:] + outline[:1]:
        path.add_spline_point(ue(*master(u, d)), unreal.SplineCoordinateSpace.WORLD, False)
    path.update_spline()
    fence.rebuild()
    # the plots, filled with the tomb library
    tombs = sorted(a for a in unreal.EditorAssetLibrary.list_assets(DEST, recursive=False)
                   if a.split("/")[-1].startswith("SM_M80_Cimitero_Tomba_"))
    kinds = []
    for t in tombs:
        k = unreal.M80TombKind()
        k.set_editor_property("mesh", unreal.load_asset(t))
        k.set_editor_property("weight", 1.0)
        kinds.append(k)
    a = ue(*master(0, 0))
    b = ue(*master(10, 0))
    row_yaw = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
    fields = []
    for i, (name, u0, u1, d0, d1) in enumerate(SITE["plots"]):
        corners = [ue(*master(u, d), WALK_Z + 0.02) for u, d in ((u0, d0), (u1, d0), (u1, d1), (u0, d1))]
        f = EAS.spawn_actor_from_class(unreal.M80CemeteryField, corners[0], unreal.Rotator(0, 0, 0))
        f.set_actor_label("Cimitero_Campo_" + name.split()[0])
        area = f.get_editor_property("area")
        area.clear_spline_points(False)
        for p in corners:
            area.add_spline_point(p, unreal.SplineCoordinateSpace.WORLD, False)
        area.update_spline()
        f.set_editor_property("kinds", kinds)
        f.set_editor_property("seed", 1980 + i)
        f.set_editor_property("row_yaw_deg", row_yaw)
        f.set_editor_property("aisle_every", 3)
        f.rebuild()
        fields.append(f)
    fig = kit.box("Persona_180", (ue(*master(0, 30)).x, ue(*master(0, 30)).y, gz + 90), (50, 30, 180))
    fig.static_mesh_component.set_material(0, unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
    return fence, fields


def view(u, d, h):
    x, y = master(u, d)
    return ue(x, y, WALK_Z + h)


VIEWS = {
    "ingresso": (view(3, -25, 1.7), view(3, 10, 4.0)),
    "viale": (view(0, 22, 1.7), view(0, 80, 1.5)),
    "campo": (view(-2, 60, 2.5), view(-15, 70, 0.0)),
    "alto": (view(70, -40, 70), view(0, 55, 0.0)),
    "alto_sud": (view(-60, 160, 60), view(0, 55, 0.0)),
}


def steps():
    fence, fields = build()
    unreal.EditorLoadingAndSavingUtils.save_current_level()
    yield 400
    cap = m80_seq.ViewCapture(1600, 900, 70.0)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (e, t) in VIEWS.items():
        rot = unreal.MathLibrary.find_look_at_rotation(e, t)
        m80_seq.set_view(e, rot)
        yield 150
        cap.capture(e, rot, OUT / ("%s.png" % name))
        yield 2
    cap.destroy()
    rep = {"campate_muro": fence.get_editor_property("bay_count"),
           "tombe_per_campo": {f.get_actor_label(): f.get_editor_property("tomb_count") for f in fields}}
    (OUT / "prova.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "errore.txt"))
