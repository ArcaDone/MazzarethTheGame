"""Runs a generator step by step on editor frames.

Each `yield N` waits N rendered engine frames before resuming. Loading a map
inside a step is safe: re-entrant ticks are ignored while a step is running.
"""
import glob
import os
import shutil
import traceback
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())


def keep_rendering():
    """A background editor stops drawing frames; automation needs real frames.

    CPU throttling must also be disabled at launch, see run_editor_script.ps1.
    """
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_viewport_realtime(True)


class Sequencer:
    def __init__(self, steps, quit_when_done=True, log_file=None):
        self.steps = steps
        self.resume_at = 0
        self.busy = False
        self.quit = quit_when_done
        self.log_file = log_file
        keep_rendering()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        if self.quit:
            unreal.SystemLibrary.quit_editor()

    def tick(self, _dt):
        if self.busy or unreal.SystemLibrary.get_frame_count() < self.resume_at:
            return
        self.busy = True
        try:
            self.resume_at = unreal.SystemLibrary.get_frame_count() + (next(self.steps) or 0)
        except StopIteration:
            self.finish()
        except Exception:
            text = traceback.format_exc()
            unreal.log_error(text)
            if self.log_file:
                Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
                Path(self.log_file).write_text(text, encoding="utf-8")
            self.finish()
        finally:
            self.busy = False


def console(command):
    unreal.SystemLibrary.execute_console_command(None, command)


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def set_view(location, rotation):
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(location, rotation)


class ViewCapture:
    """Renders views with a SceneCapture2D into PNG files (independent of the editor viewport).

    The capture actor is transient: destroy() it before saving the level.
    """

    def __init__(self, width=1600, height=900, fov=70.0):
        world = editor_world()
        self.world = world
        self.rt = unreal.RenderingLibrary.create_render_target2d(world, width, height, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        self.actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
        comp = self.actor.get_editor_property("capture_component2d")
        comp.set_editor_property("texture_target", self.rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR)
        comp.set_editor_property("capture_every_frame", False)
        comp.set_editor_property("fov_angle", fov)
        self.comp = comp

    def capture(self, location, rotation, target_png):
        self.actor.set_actor_location_and_rotation(location, rotation, False, False)
        self.comp.capture_scene()
        folder, name = os.path.split(str(target_png))
        Path(folder).mkdir(parents=True, exist_ok=True)
        unreal.RenderingLibrary.export_render_target(self.world, self.rt, folder, name)
        return target_png

    def destroy(self):
        if self.actor:
            self.actor.destroy_actor()
            self.actor = None


def collect_screenshot(target_png, since):
    """Moves the newest screenshot written after `since` to target_png."""
    shots = [p for p in glob.glob(str(ROOT / "Saved/Screenshots/**/*.png"), recursive=True) if os.path.getmtime(p) >= since]
    if not shots:
        return None
    newest = max(shots, key=os.path.getmtime)
    Path(target_png).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(newest, target_png)
    return target_png
