"""Parallax interiors for the house windows (houses V3, step 7).

1. Builds furnished rooms in the studio map /Game/Mazzarino80/Rooms/L_M80_RoomStudio
   (homes: kitchen, bedroom, living room, storeroom; shops: grocery, hardware; bar).
2. Captures each room into a TextureCube (UM80EditorLibrary.CaptureRoomCube) and packs them in
   the TextureCubeArray TCA_M80_Rooms, one slice per room in the order of ROOMS.
3. Builds M_M80_GlassInterior: interior mapping on the 0-1 glass UVs, room picked by vertex
   colour B (homes 0-0.69, shops 0.7-0.89, bar 0.9-1), some dark windows and curtains, and
   assigns it to the house styles.
Env: M80_ROOMS_SIZE (cube size, default 256), M80_ROOMS_SKIP_CAPTURE=1 rebuilds only the material.
"""
import json
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

ROOT = Path(unreal.Paths.project_dir())
DIR = "/Game/Mazzarino80/Rooms"
STUDIO = DIR + "/L_M80_RoomStudio"
STYLE_DIR = "/Game/Mazzarino80/Houses/Styles"
REPORT = ROOT / "Saved/Mazzarino80/HousesV2/rooms_report.json"
SIZE = int(os.environ.get("M80_ROOMS_SIZE", "256"))
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
CUBE = "/Engine/BasicShapes/Cube"
MAT = "/Game/Mazzarino80/Houses/Materials/"
OW1 = "/Game/OldWestAssets/OldWestVol1/VOL1/Meshes/"
OW3 = "/Game/OldWestAssets/OldWestVol3/VOL3/Meshes/"
OW5 = "/Game/OldWestAssets/OldWestVol5/VOL5/Meshes/"
MP = "/Game/Megapack/Meshes/"
HALF = 180.0  # rooms are 3.6 m cubes: the interior mapping assumes a cube

# (name, wall material, floor material, light colour, furniture: (mesh, x, y, yaw) in cm from the room centre.
# +X is the back wall seen through the window, +Y is to the right.
ROOMS = [
    ("Kitchen", "MI_M80_Wall_Plaster", "MI_M80_Terrace", (1.0, 0.82, 0.6), [
        (OW5 + "SM_Stove_01a", 140, -90, 180), (OW1 + "SM_Table_01a", 20, 30, 0), (OW5 + "SM_Chair_04a", 20, -40, 90),
        (OW1 + "SM_Cabinet_02a", 150, 100, 180), (OW1 + "SM_Wall_Shelf_01a", 170, 0, 180), (OW3 + "SM_Lamp_01a", 20, 30, 0)]),
    ("Bedroom", "MI_M80_Wall_PlasterWorn", "MI_M80_Terrace", (1.0, 0.78, 0.55), [
        (OW1 + "SM_Bed_01a", 110, 0, 180), (OW1 + "SM_Cabinet_02a", 60, 160, 270), (OW5 + "SM_Chair_04a", -40, -150, 45)]),
    ("Living", "MI_M80_Wall_Plaster", "MI_M80_Wood_Painted", (1.0, 0.85, 0.65), [
        (OW1 + "SM_Table_01a", 40, 0, 0), (OW5 + "SM_Chair_04a", 40, 70, 270), (OW5 + "SM_Chair_04a", 40, -70, 90),
        (OW1 + "SM_Wall_Shelf_01a", 170, 60, 180), (OW1 + "SM_Cabinet_02a", 150, -110, 180), (OW3 + "SM_Lamp_01a", 40, 0, 0)]),
    ("Storeroom", "MI_M80_Wall_Raw", "MI_M80_Terrace", (0.9, 0.8, 0.65), [
        (OW5 + "SM_Barrels_01a", 120, -100, 0), (OW5 + "SM_Crate_01a", 130, 60, 20), (OW5 + "SM_Crate_01a", 60, 130, 70)]),
    ("ShopGrocery", "MI_M80_Wall_Plaster", "MI_M80_Terrace", (1.0, 0.95, 0.85), [
        (MP + "Favela/SM_Shelf_01", 160, -80, 180), (MP + "Favela/SM_Shelf_03", 160, 80, 180), (MP + "MiddleEast/SM_market_table_01", 30, 0, 90),
        (MP + "MiddleEast/SM_Cardboard_box_01", 80, -150, 10), (MP + "Yakohama/SM_PlasticBox_01", 100, 150, 0)]),
    ("ShopHardware", "MI_M80_Wall_Raw", "MI_M80_Terrace", (0.95, 0.95, 1.0), [
        (MP + "Favela/SM_Shelf_03", 160, -60, 180), (MP + "Favela/SM_Shelf_01", 160, 90, 180), (MP + "MiddleEast/SM_Cardboard_box_01", 40, -120, 30),
        (OW5 + "SM_Crate_01a", 60, 120, 0)]),
    ("Bar", "MI_M80_Wall_PlasterWorn", "MI_M80_Terrace", (1.0, 0.8, 0.55), [
        (MP + "Favela/SM_Shelf_01", 165, 0, 180), (MP + "Favela/SM_Table_01", 60, 0, 90), (MP + "Yakohama/SM_Bottle_01", 60, -20, 0),
        (MP + "Yakohama/SM_Bottle_02", 60, 20, 0), (MP + "Favela/SM_Table_01", -60, 110, 0), (OW5 + "SM_Chair_04a", -60, 60, 0)]),
]
N_HOME, N_SHOP = 4, 2


def spawn_mesh(path, loc, rot=0.0, scale=(1, 1, 1), material=None, label=None):
    mesh = unreal.load_asset(path)
    if not mesh:
        return None
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, unreal.Vector(*loc), unreal.Rotator(0, 0, rot))
    actor.set_actor_scale3d(unreal.Vector(*scale))
    if material:
        actor.static_mesh_component.set_material(0, unreal.load_asset(MAT + material))
    if label:
        actor.set_actor_label(label)
    return actor


def build_room(index, room, report):
    name, wall, floor, light, furniture = room
    cx = index * 1500.0
    s = HALF / 50.0  # the engine cube is 100 cm
    t = 0.1
    spawn_mesh(CUBE, (cx, 0, -5), 0, (s * 2, s * 2, t), floor, name + "_Floor")
    spawn_mesh(CUBE, (cx, 0, HALF * 2 + 5), 0, (s * 2, s * 2, t), wall, name + "_Ceiling")
    for (x, y, sx, sy) in ((HALF + 5, 0, t, s * 2), (-HALF - 5, 0, t, s * 2), (0, HALF + 5, s * 2, t), (0, -HALF - 5, s * 2, t)):
        spawn_mesh(CUBE, (cx + x, y, HALF), 0, (sx, sy, s * 2.1), wall, name + "_Wall")
    for path, x, y, yaw in furniture:
        actor = spawn_mesh(path, (cx + x, y, 0), yaw)
        if actor is None:
            report.setdefault("missing", []).append(path)
    lamp = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight, unreal.Vector(cx, 0, HALF * 2 - 40))
    comp = lamp.point_light_component
    comp.set_intensity(1800.0)
    comp.set_light_color(unreal.LinearColor(*light, 1))
    comp.set_attenuation_radius(900.0)
    fill = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PointLight, unreal.Vector(cx - 120, 0, 120))
    fill.point_light_component.set_intensity(400.0)
    fill.point_light_component.set_attenuation_radius(600.0)
    fill.point_light_component.set_cast_shadows(False)
    return unreal.Vector(cx, 0, HALF)


class Graph:
    def __init__(self, material):
        self.m = material

    def node(self, cls, x, y, **props):
        expr = MEL.create_material_expression(self.m, cls, x, y)
        for key, value in props.items():
            expr.set_editor_property(key, value)
        return expr

    def link(self, src, src_out, dst, dst_in):
        if not MEL.connect_material_expressions(src, src_out, dst, dst_in):
            raise RuntimeError("Cannot connect {}.{} -> {}.{}".format(src.get_name(), src_out, dst.get_name(), dst_in))


INTERIOR_HLSL = r"""
// Interior mapping in world space. UV is the position on the front wall of the room (0-1 across,
// 0 ceiling, 1 floor): the window is an opening in that wall. Room box: x, y in [-1, 1], glass
// at z = 1, back wall at z = -1 (Depth stretches the room).
float3 n = normalize(N);
float3 u = normalize(cross(float3(0, 0, 1), n));          // along the wall, = +U of the glass
float3 v = -normalize(View);                              // ray from the camera into the room
float3 d = float3(dot(v, u), -v.z, dot(v, n) / max(Depth, 0.2));
d.z = min(d.z, -1e-3);
float3 p = float3(saturate(UV.x) * 2 - 1, saturate(UV.y) * 2 - 1, 1);
float3 id = 1.0 / (d + (abs(d) < 1e-5) * 1e-5);
float3 k = abs(id) - p * id;
float t = min(min(k.x, k.y), k.z);
float3 h = clamp(p + t * d, -1, 1);                      // hit point on the room box
float3 dir = float3(-h.z, h.x, -h.y);                    // studio axes: +X back wall, +Y right, +Z up
float b = saturate(Room);
float slice = b < 0.7 ? floor(b / 0.7 * NHome) : (b < 0.9 ? NHome + floor((b - 0.7) / 0.2 * NShop) : NHome + NShop);
slice = min(slice, NHome + NShop);
float3 c = Rooms.SampleLevel(RoomsSampler, float4(dir, slice), 0).rgb * Exposure;
// Light falls off towards the back and the corners of the room.
float back = saturate((1 - h.z) * 0.5);
c *= lerp(1.0, 0.35, back) * (1 - 0.35 * saturate(max(abs(h.x), abs(h.y)) - 0.6) / 0.4);
// Homes: some rooms dark, some behind lace curtains.
float hsh = frac(b * 37.13);
if (b < 0.7 && hsh < 0.22) c *= 0.06;
float lace = (b < 0.7 && hsh > 0.22 && hsh < 0.5) ? saturate(0.6 + 0.25 * sin(UV.x * 600) * sin(UV.y * 450)) : 0;
c = lerp(c, CurtainColor * 0.3 * Exposure / 0.015, lace);
return c;
"""


def build_material(array, report):
    path = DIR + "/M_M80_GlassInterior"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        m = unreal.load_asset(path)
        MEL.delete_all_material_expressions(m)
    else:
        m = TOOLS.create_asset("M_M80_GlassInterior", DIR, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_nanite", True)
    m.set_editor_property("used_with_instanced_static_meshes", True)
    g = Graph(m)
    uv = g.node(unreal.MaterialExpressionTextureCoordinate, -1200, 0)
    cam = g.node(unreal.MaterialExpressionCameraVectorWS, -1200, 150)
    normal = g.node(unreal.MaterialExpressionVertexNormalWS, -1200, 220)
    depth = g.node(unreal.MaterialExpressionScalarParameter, -1200, 900, parameter_name="Depth", default_value=1.0)
    vcol = g.node(unreal.MaterialExpressionVertexColor, -1200, 300)
    tex = g.node(unreal.MaterialExpressionTextureObjectParameter, -1200, 450, parameter_name="Rooms", texture=array,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    exposure = g.node(unreal.MaterialExpressionScalarParameter, -1200, 600, parameter_name="Exposure", default_value=0.015)
    nhome = g.node(unreal.MaterialExpressionConstant, -1200, 680, r=float(N_HOME))
    nshop = g.node(unreal.MaterialExpressionConstant, -1200, 740, r=float(N_SHOP))
    curtain = g.node(unreal.MaterialExpressionVectorParameter, -1200, 800, parameter_name="CurtainColor",
                     default_value=unreal.LinearColor(0.9, 0.86, 0.76, 1))
    custom = g.node(unreal.MaterialExpressionCustom, -800, 200, code=INTERIOR_HLSL,
                    output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, description="InteriorMapping")
    names = ["UV", "View", "N", "Room", "Rooms", "Exposure", "NHome", "NShop", "CurtainColor", "Depth"]
    inputs = []
    for n in names:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        inputs.append(ci)
    custom.set_editor_property("inputs", inputs)
    for src, out, name in ((uv, "", "UV"), (cam, "", "View"), (normal, "", "N"), (vcol, "B", "Room"), (tex, "", "Rooms"), (exposure, "", "Exposure"),
                           (nhome, "", "NHome"), (nshop, "", "NShop"), (curtain, "", "CurtainColor"), (depth, "", "Depth")):
        g.link(src, out, custom, name)
    MEL.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(g.node(unreal.MaterialExpressionConstant3Vector, -400, 400, constant=unreal.LinearColor(0.01, 0.012, 0.014, 1)), "",
                                  unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(g.node(unreal.MaterialExpressionConstant, -400, 480, r=0.04), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(g.node(unreal.MaterialExpressionConstant, -400, 540, r=0.6), "", unreal.MaterialProperty.MP_SPECULAR)
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m, only_if_is_dirty=False)
    report["material"] = path
    return m


def run():
    report = {"rooms": [r[0] for r in ROOMS], "size": SIZE}
    cubes = []
    if os.environ.get("M80_ROOMS_SKIP_CAPTURE") != "1":
        if unreal.EditorAssetLibrary.does_asset_exist(STUDIO):
            unreal.EditorLoadingAndSavingUtils.load_map(STUDIO)
            yield 20
            world = m80_seq.editor_world()
            if not world.get_path_name().startswith(STUDIO):
                raise RuntimeError("Wrong map open: " + world.get_path_name())
            for actor in unreal.EditorLevelLibrary.get_all_level_actors():
                unreal.EditorLevelLibrary.destroy_actor(actor)
        else:
            unreal.EditorLevelLibrary.new_level(STUDIO)
            yield 20
        centers = [build_room(i, room, report) for i, room in enumerate(ROOMS)]
        unreal.EditorLoadingAndSavingUtils.save_current_level()
        yield 600  # furniture shaders and distance fields
        for attempt in range(2):
            cubes = []
            for (name, *_), center in zip(ROOMS, centers):
                cube = unreal.M80EditorLibrary.capture_room_cube(center, SIZE, DIR + "/TC_M80_Room_" + name)
                cubes.append(cube)
                yield 5
            yield 120
        for cube in cubes:
            unreal.EditorAssetLibrary.save_loaded_asset(cube, only_if_is_dirty=False)
    else:
        cubes = [unreal.load_asset(DIR + "/TC_M80_Room_" + r[0]) for r in ROOMS]
    array = unreal.M80EditorLibrary.make_cube_array(cubes, DIR + "/TCA_M80_Rooms")
    if not array:
        raise RuntimeError("TextureCubeArray failed")
    unreal.EditorAssetLibrary.save_loaded_asset(array, only_if_is_dirty=False)
    yield 10
    material = build_material(array, report)
    yield 30
    for data in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(STYLE_DIR):
        style = unreal.load_asset(str(data.package_name))
        if isinstance(style, unreal.M80HouseStyle):
            style.set_editor_property("glass_material", material)
            unreal.EditorAssetLibrary.save_loaded_asset(style, only_if_is_dirty=False)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


m80_seq.Sequencer(run(), log_file=str(REPORT.with_suffix(".error.txt")))
