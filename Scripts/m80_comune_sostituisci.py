"""Puts the new Comune with its church (SM_M80_ComuneChiesa, from ComuneConChiesa.blend) in the town where the old
Comune Blueprint (M80_Recuperato_ComuneCompleto) has its main building, and hides in that Blueprint the pieces the new
mesh replaces: the Comune itself (MainComune, ComuneScale), the old ruined church (ChurchTownHall), the statue and the
Megapack doors, windows and garage gates that were stuck on the old facade. Fountain, lamps, grass and the rest stay.

Placement: the old main building came from ComuneScaled.blend, whose MainComune is the new file's MainBuilding
stretched 1.0565 along x and 1.0665 along y (same height) and moved; the new mesh gets the old actor's rotation and scale
times that stretch, so its main building lies on the old one.
Env: M80_PROVA=1 report and pictures only, save nothing.
Out: Saved/Mazzarino80/Comune/sostituisci.json + pictures
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_comune_sostituisci.py -TimeoutMinutes 30
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Comune"
PROVA = os.environ.get("M80_PROVA") == "1"
OLD = "M80_Recuperato_ComuneCompleto"
NEW = "M80_ComuneChiesa"
MESH = "/Game/Mazzarino80/Buildings/ComuneChiesa/SM_M80_ComuneChiesa.SM_M80_ComuneChiesa"
# ComuneScaled (old) = stretch * new file + offset, metres, from MainComune vs MainBuilding
AX, BX = 63.518 / 60.12, -37.87 + 63.518 / 60.12 * 47.891
AY, BY = 52.931 / 49.631, -23.916 + 52.931 / 49.631 * 22.379
HIDE = ("MainComune", "ComuneScale", "ChurchTownHall", "StatuaComume", "SM_windows_02", "SM_window_door_part_01",
        "SM_window_door_01", "SM_Door_02", "SM_Door_color_03", "SM_Door_Jamb_01", "SM_metal_gate_01", "Porta6")


def steps():
    info = json.loads((ROOT / "Saved/Mazzarino80/Import/out/ComuneChiesa.json").read_text(encoding="utf-8"))
    px, py, pz = info["pivot_blender_m"]
    unreal.EditorLoadingAndSavingUtils.load_map(m80_seq.TOWN_MAP)
    yield 60
    descs = m80_seq.actor_descs()
    old_desc = next(d for d in descs if str(d.get_editor_property("label")) == OLD)
    c = m80_seq.desc_center(old_desc)
    # the Comune and everything within 60 m (houses that the church may now overlap, the ground)
    m80_seq.load([d for d in m80_seq.near(descs, c.x, c.y, 6000.0) if "HLOD" not in str(d.get_editor_property("native_class"))])
    yield 120
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    old = next(a for a in actors if a.get_actor_label() == OLD)
    t = old.get_actor_transform()
    s = t.scale3d
    off = unreal.Vector(100 * (AX * px + BX), -100 * (AY * py + BY), 100 * pz)
    loc = unreal.MathLibrary.transform_location(t, off)
    rep = {"prova": PROVA, "vecchio": {"loc": [t.translation.x, t.translation.y, t.translation.z], "scala": [s.x, s.y, s.z],
                                       "yaw": t.rotation.rotator().yaw}}
    new = next((a for a in actors if a.get_actor_label() == NEW), None)
    if not new:
        new = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, t.rotation.rotator())
        new.set_actor_label(NEW)
    new.set_actor_location(loc, False, False)
    new.set_actor_rotation(t.rotation.rotator(), False)
    new.set_actor_scale3d(unreal.Vector(s.x * AX, s.y * AY, s.z))
    new.set_folder_path(old.get_folder_path())
    smc = new.get_component_by_class(unreal.StaticMeshComponent)
    smc.set_editor_property("static_mesh", unreal.load_asset(MESH))
    smc.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    rep["nuovo"] = {"loc": [loc.x, loc.y, loc.z], "scala": [s.x * AX, s.y * AY, s.z]}
    hidden = {}
    for comp in old.get_components_by_class(unreal.StaticMeshComponent):
        sm = comp.get_editor_property("static_mesh")
        if sm and sm.get_name() in HIDE:
            comp.set_visibility(False, True)
            comp.set_hidden_in_game(True, True)
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            hidden[sm.get_name()] = hidden.get(sm.get_name(), 0) + 1
    old.modify()
    rep["nascosti"] = hidden
    # houses that the new mesh overlaps (the church stands where the old Blueprint had nothing)
    origin, extent = new.get_actor_bounds(False)
    rep["nuovo_bounds"] = {"min": [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                           "max": [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}
    over = []
    for h in actors:
        if isinstance(h, unreal.M80House) and not h.is_excluded():
            ho, he = h.get_actor_bounds(False)
            if abs(ho.x - origin.x) < he.x + extent.x and abs(ho.y - origin.y) < he.y + extent.y:
                over.append(h.get_actor_label())
    rep["case_sovrapposte_bounds"] = over
    yield 200
    cap = m80_seq.ViewCapture(1600, 900, 60.0)
    right = unreal.MathLibrary.get_right_vector(t.rotation.rotator())
    # the old facade looked along the actor's +Y scaled by a negative factor: try both sides, from up high
    for name, d in (("da_sud", right * -1), ("da_nord", right), ("alto", None)):
        if d is None:
            eye = origin + unreal.Vector(-6000, -6000, 6000)
        else:
            eye = origin + d * 7000 + unreal.Vector(0, 0, 2500)
        cap.capture(eye, unreal.MathLibrary.find_look_at_rotation(eye, origin), OUT / ("sostituisci_%s.png" % name))
    yield 2
    cap.destroy()
    if not PROVA:
        unreal.EditorLoadingAndSavingUtils.save_packages([new.get_outermost(), old.get_outermost()], True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sostituisci.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    yield 2


m80_seq.Sequencer(steps(), log_file=str(OUT / "sostituisci_errore.txt"))
