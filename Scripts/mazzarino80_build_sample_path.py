"""Build a removable, collidable walking test along the central corridor.

The horizontal alignment is a two-church fit to 2026 OSM and is NOT certified
as the 1980 road. This is a temporary gameplay surface over damaged terrain.
"""

import json
import math
from pathlib import Path

import unreal


root = Path(unreal.Paths.project_dir())
audit = json.loads((root / "Saved" / "Mazzarino80" / "path_audit.json").read_text())
samples = audit["samples"]
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == "Mazzarino80_Base", world.get_path_name()
editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
prefix = "M80_Provvisorio_"
assert not any(a.get_actor_label().startswith(prefix)
               for a in editor.get_all_level_actors()), "Percorso gia presente"
mesh = unreal.load_asset("/Engine/BasicShapes/Cube")
assert mesh, "Mesh Cube di Unreal non disponibile"


def target_height(sample):
    s = sample["s_m"]
    base = 167.0 + min(s, 70.0) * (6.5 / 70.0)
    ground = sample["ground"]
    if ground and ground["z_m"] > 150:
        base = max(base, ground["z_m"] + 0.35)
    return base


def make_cube(label, x, y, z, length, width, thickness, yaw=0, pitch=0):
    actor = editor.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(x * 100, y * 100, z * 100),
        unreal.Rotator(pitch=pitch, yaw=yaw, roll=0))
    assert actor, label
    actor.set_actor_label(label)
    actor.set_folder_path("Mazzarino80/Percorso_campione_provvisorio")
    actor.set_actor_scale3d(unreal.Vector(length, width, thickness))
    component = actor.get_components_by_class(unreal.StaticMeshComponent)[0]
    component.set_static_mesh(mesh)
    component.set_collision_profile_name("BlockAll")
    return actor


created = []
for i, (a, b) in enumerate(zip(samples, samples[1:]), 1):
    dx = b["x_m"] - a["x_m"]
    dy = b["y_m"] - a["y_m"]
    length = math.hypot(dx, dy)
    if length < 0.01:
        continue
    za, zb = target_height(a), target_height(b)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(zb - za, length))
    actor = make_cube(
        f"{prefix}Tratto_{i:02d}",
        (a["x_m"] + b["x_m"]) / 2,
        (a["y_m"] + b["y_m"]) / 2,
        (za + zb) / 2 - 0.15,
        length + 0.15, 4.0, 0.30, yaw, pitch)
    created.append(actor)

for label, sample in (("Partenza_Matrice", samples[0]),
                      ("Arrivo_SanDomenico", samples[-1])):
    created.append(make_cube(
        prefix + label, sample["x_m"], sample["y_m"],
        target_height(sample) - 0.15, 6.0, 6.0, 0.30))

start = next((a for a in editor.get_all_level_actors()
              if a.get_class().get_name() == "PlayerStart"), None)
assert start, "PlayerStart non trovato"
old_start = start.get_actor_location()
start.set_actor_location(unreal.Vector(samples[0]["x_m"] * 100,
                                       samples[0]["y_m"] * 100,
                                       (target_height(samples[0]) + 1.2) * 100),
                         False, False)
saved = level.save_current_level()
assert saved, "Salvataggio della mappa fallito"
result = {"map": world.get_path_name(), "segments": len(created) - 2,
          "landing_pads": 2, "length_m": samples[-1]["s_m"],
          "width_m": 4.0, "source": "OSM 2026, two-church alignment, provisional",
          "old_player_start_cm": [old_start.x, old_start.y, old_start.z],
          "saved": bool(saved)}
out = root / "Saved" / "Mazzarino80" / "built_path.json"
out.write_text(json.dumps(result, indent=2), encoding="utf-8")
unreal.log("MAZZARINO80_PATH_BUILT " + json.dumps(result))
