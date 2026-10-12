"""Icons of the weapons for the weapon wheel (GTA V style: the weapon from the side, light grey, on transparency).
M80_ICONE_FASE=cattura (default): each weapon mesh is photographed alone from its side by an orthographic scene capture
  (scene colour in RGB, coverage in alpha) into Saved/Mazzarino80/Icone/<Weapon>.exr;
  then Research/Mazzarino80/Blender/m80_icone_alpha.py turns them into greyscale PNGs with alpha;
M80_ICONE_FASE=importa: the PNGs become /Game/Mazzarino80/UI/Icone/T_M80_Icona_<Weapon> (UI textures, no mips).
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_icone_armi.py
blender -b --factory-startup --python Research/Mazzarino80/Blender/m80_icone_alpha.py
(set M80_ICONE_FASE=importa) powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_icone_armi.py
"""
import glob
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT / "Saved/Mazzarino80/Icone"
DEST = "/Game/Mazzarino80/UI/Icone"
WEAPONS = {"Coltello": "SM_M80_Coltello", "Mazza": "SM_M80_Mazza", "Revolver": "SM_M80_Revolver", "Beretta": "SM_M80_Beretta",
           "Lupara": "SM_M80_Lupara", "Fucile": "SM_M80_Fucile"}
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
SPOT = unreal.Vector(-300000, -300000, 60000)
V = unreal.Vector


def capture():
    OUT.mkdir(parents=True, exist_ok=True)
    unreal.EditorLoadingAndSavingUtils.load_map("/Game/Mazzarino80/Player/Maps/L_M80_ProvaAzione")
    yield 30
    world = m80_seq.editor_world()
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, SPOT + V(0, 0, 500))
    sun.set_actor_rotation(unreal.Rotator(pitch=-35.0, yaw=60.0, roll=0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(5.0)
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, SPOT + V(0, 0, 400))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    rt = unreal.RenderingLibrary.create_render_target2d(world, 512, 256, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
    report = {}
    for name, mesh in WEAPONS.items():
        asset = unreal.load_asset("/Game/Mazzarino80/Weapons/" + mesh)
        if not asset:
            continue
        actor = EAS.spawn_actor_from_object(asset, SPOT)
        # All parts in the steel: wood in the sun comes out brighter than the dark steel and the grips would be white blocks.
        smc = actor.get_component_by_class(unreal.StaticMeshComponent)
        for i in range(smc.get_num_materials()):
            smc.set_material(i, unreal.load_asset("/Game/Mazzarino80/Weapons/M_M80_Arma_Metallo"))
        yield 20
        o, e = actor.get_actor_bounds(False)
        # The barrel lies along +X: seen from -Y, muzzle to the right.
        cam = EAS.spawn_actor_from_class(unreal.SceneCapture2D, o - V(0, 400, 0))
        cam.set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=90.0, roll=0.0), False)
        comp = cam.get_editor_property("capture_component2d")
        comp.set_editor_property("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC)
        comp.set_editor_property("ortho_width", max(e.x * 2.0, e.z * 4.0) * 1.12)
        comp.set_editor_property("texture_target", rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
        comp.set_editor_property("primitive_render_mode", unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
        comp.show_only_actor_components(actor, False)
        comp.set_editor_property("capture_every_frame", False)
        yield 30
        comp.capture_scene()
        yield 5
        unreal.RenderingLibrary.export_render_target(world, rt, str(OUT), name)
        report[name] = [round(e.x * 2), round(e.y * 2), round(e.z * 2)]
        cam.destroy_actor()
        actor.destroy_actor()
        yield 5
    report["files"] = sorted(os.path.basename(p) for p in glob.glob(str(OUT / "*")))
    (OUT / "cattura.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


def import_icons():
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    done = []
    for png in sorted(OUT.glob("*.png")):
        name = "T_M80_Icona_" + png.stem
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", str(png))
        t.set_editor_property("destination_path", DEST)
        t.set_editor_property("destination_name", name)
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", False)
        tools.import_asset_tasks([t])
        tex = unreal.load_asset("%s/%s" % (DEST, name))
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        unreal.EditorAssetLibrary.save_loaded_asset(tex, False)
        done.append(name)
        yield 1
    (OUT / "importa.json").write_text(json.dumps(done, indent=1), encoding="utf-8")


PHASE = os.environ.get("M80_ICONE_FASE", "cattura")
m80_seq.Sequencer(capture() if PHASE == "cattura" else import_icons(), log_file=str(OUT / "error.txt"))
