"""Checks the retargeted player animations (m80_animazioni_import.py) on the UEFN mannequin, away from the houses:
each clip posed at its start, middle and end, photographed from the side, with the hands, pelvis and root measured
in the actor's frame (where the hands grip a ledge and how far the body travels). Nothing saved.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_animazioni_verifica.py -ForceLit
Out: Saved/Mazzarino80/Player/Animazioni/<clip>_<t>.png, misure.json
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Player/Animazioni"
ANIM = "/Game/Mazzarino80/Player/Anim/"
CLIPS = ["A_M80_Appeso_Presa", "A_M80_Appeso_Laterale", "A_M80_Appeso_Salita", "A_M80_Appeso_Lascia", "A_M80_Salto_Appeso",
         "A_M80_Salto_Corsa_Appeso", "A_M80_Pugni_Combo", "A_M80_Fucile_Mira", "A_M80_Pistola_Mira_Sweep", "A_M80_Pistola_Pose",
         "A_M80_Fucile_Mira_Sweep", "A_M80_Fucile_Pose"]
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
SPOT = unreal.Vector(-300000, -300000, 60000)
V = unreal.Vector


# Bone chains of the UEFN mannequin, from the root.
CHAINS = {"root": ["root"], "pelvis": ["root", "pelvis"],
          "hand_r": ["root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r"],
          "hand_l": ["root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l"],
          "foot_l": ["root", "pelvis", "thigh_l", "calf_l", "foot_l"],
          "head": ["root", "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head"]}


def measure(anim, bone, t):
    """Component-space position of a bone at time t (root motion left in the root bone)."""
    xf = unreal.Transform()
    for b in CHAINS[bone]:
        local = unreal.AnimationLibrary.get_bone_pose_for_time(anim, b, t, False)
        xf = local.multiply(xf)
    p = xf.translation
    return [round(p.x), round(p.y), round(p.z)]


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map("/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione")
    yield 30
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, SPOT + V(0, 0, 3000))
    sun.set_actor_rotation(unreal.Rotator(pitch=-40.0, yaw=-60.0, roll=0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(6.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, SPOT + V(0, 0, 2000))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    floor = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Plane"), SPOT)
    floor.set_actor_scale3d(V(40, 40, 1))
    # A ledge 2.3 m high in front of the dummy, for the hanging clips.
    ledge = EAS.spawn_actor_from_object(unreal.load_asset("/Engine/BasicShapes/Cube"), SPOT + V(60, 0, 115))
    ledge.set_actor_scale3d(V(0.6, 3, 2.3))
    actor = EAS.spawn_actor_from_object(unreal.load_asset("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin"), SPOT)
    comp = actor.skeletal_mesh_component
    comp.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    comp.set_update_animation_in_editor(True)
    yield 30
    report = {}
    for name in CLIPS:
        anim = unreal.load_asset(ANIM + name)
        if not anim:
            report[name] = "missing"
            continue
        length = anim.get_play_length()
        rows = {}
        for t in (0.0, 0.5, 1.0):
            comp.override_animation_data(anim, False, False, length * t * 0.999, 0.0)
            comp.set_position(length * t * 0.999, False)
            yield 3
            row = {b: measure(anim, b, length * t * 0.999) for b in CHAINS}
            rows["%d" % int(t * 100)] = row
            eye = SPOT + V(-120, -380, 140)
            rot = unreal.MathLibrary.find_look_at_rotation(eye, SPOT + V(20, 0, 120))
            m80_seq.set_view(eye, rot)
            yield 10
            cap = m80_seq.ViewCapture(800, 600, 60)
            cap.capture(eye, rot, OUT / ("%s_%03d.png" % (name, int(t * 100))))
            cap.destroy()
            yield 2
        report[name] = {"length": round(length, 2), "poses": rows}
    (OUT / "misure.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "error.txt"))
