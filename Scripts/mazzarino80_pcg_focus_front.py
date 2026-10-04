"""Put the validation camera at pedestrian height before a chosen house."""
import math
import unreal

LOT = '1249069205'
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
source = next(a for a in actors if isinstance(a, unreal.MazzarinoHistoricBuilding)
              and a.get_editor_property('lot_id') == LOT)
spline = source.get_editor_property('footprint')
points = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
          for i in range(spline.get_number_of_spline_points())]
front = source.get_editor_property('front_edge')
a, b = points[front], points[(front + 1) % len(points)]
dx, dy = b.x - a.x, b.y - a.y
length = math.hypot(dx, dy)
signed = sum(v.x * points[(i+1) % len(points)].y -
             points[(i+1) % len(points)].x * v.y for i, v in enumerate(points))
outx, outy = (dy / length, -dx / length) if signed > 0 else (-dy / length, dx / length)
mid = unreal.Vector((a.x+b.x)*.5, (a.y+b.y)*.5, (a.z+b.z)*.5)
camera = unreal.Vector(mid.x+outx*1000, mid.y+outy*1000, mid.z+260)
look = unreal.Vector(mid.x, mid.y, mid.z+340)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
    camera, unreal.MathLibrary.find_look_at_rotation(camera, look))
unreal.log('M80_FOCUS_FRONT '+LOT+' '+str(camera))
