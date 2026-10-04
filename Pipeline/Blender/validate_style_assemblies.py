"""Check metre-scale shell and attachment geometry before any UE import."""
from pathlib import Path
import json
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BLEND = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2/Mazzarino_4_Stili_Reuse_Gates_v2.blend"
OUT = BLEND.with_name("assembly_validation.json")
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
records = json.loads(BLEND.with_name("manifest.json").read_text(encoding="utf-8"))


def bounds(obj):
    verts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return ([min(v[a] for v in verts) for a in range(3)],
            [max(v[a] for v in verts) for a in range(3)])


results = []
for index, record in enumerate(records):
    style = record["style"]
    xoff = 13 * index
    depth = record["footprint_m"][1]
    height = record["floors"] * record["floor_height_m"]
    issues = []
    for name in (f"{style}_Ground_0", f"{style}_Ground_1", f"{style}_Door",
                 f"{style}_right_0_0", f"{style}_Rear_0_0"):
        if name not in bpy.data.objects:
            issues.append("missing " + name)
    if record["floors"] != (2 if style in ("STYLE_01", "STYLE_02", "STYLE_03", "STYLE_04") else -1):
        issues.append("pilot floor count differs from lot")
    if abs(record["floor_height_m"] * 100 - record["lot_floor_height_cm"]) > .01:
        issues.append("floor height differs from lot")
    if style in ("STYLE_01", "STYLE_04"):
        roof = bpy.data.objects[f"{style}_Roof"]
        low, high = bounds(roof)
        if low[1] > .2 or high[1] < depth - .1 or low[0] > xoff - 2.9 or high[0] < xoff + 2.9:
            issues.append("gable roof does not cover house footprint")
        if abs(low[2] - height) > .12:
            issues.append("gable roof eave not aligned to upper wall")
        chimney = bpy.data.objects[f"{style}_Chimney"]
        local_x = chimney.location.x - roof.location.x
        local_y = chimney.location.y - roof.location.y
        nearby = [v.co.z for v in roof.data.vertices
                  if abs(v.co.x - local_x) < .19 and abs(v.co.y - local_y) < .19]
        if not nearby or abs(bounds(chimney)[0][2] - (roof.location.z + max(nearby))) > .16:
            issues.append("chimney does not touch roof surface")
    else:
        slab = bpy.data.objects[f"{style}_TerraceSlab"]
        low, high = bounds(slab)
        if low[1] > .1 or high[1] < depth - .1 or low[2] < height - .1:
            issues.append("terrace does not cover upper wall")
    for side in ("left", "right"):
        spans = [bounds(obj) for obj in bpy.data.objects
                 if obj.name.startswith(f"{style}_{side}_0_") and obj.type == "MESH"]
        if not spans or min(pair[0][1] for pair in spans) > .05 or max(pair[1][1] for pair in spans) < depth - .05:
            issues.append(side + " ground wall has a depth gap")
    if style == "STYLE_04":
        gate_low, gate_high = bounds(bpy.data.objects[f"{style}_Gate_Candidate"])
        if abs(gate_low[2]) > .02 or gate_high[0] - gate_low[0] < 2.5:
            issues.append("courtyard gate floating or too narrow")
        if f"SOCKET_{style}_GateHinge" not in bpy.data.objects:
            issues.append("gate hinge socket missing")
        if f"{style}_CourtPaving" not in bpy.data.objects:
            issues.append("courtyard paving missing")
    if style == "STYLE_03":
        shutter = bpy.data.objects.get(f"{style}_GarageRoller_01")
        if not shutter or bounds(shutter)[0][2] > .05:
            issues.append("garage shutter missing or above ground")
    pipe = bpy.data.objects.get(f"{style}_Drainpipe_Right")
    if not pipe or bounds(pipe)[0][2] > .10 or bounds(pipe)[1][2] < height:
        issues.append("drainpipe missing or not connected from roof to ground")
    results.append({"style": style, "lot": record["lot"], "issues": issues,
                    "visual_status": "review_required"})

report = {"blend": str(BLEND), "pilots": results,
          "technical_pass": all(not item["issues"] for item in results)}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("STYLE_ASSEMBLY_VALIDATION", "technical_pass", report["technical_pass"],
      "issues", sum(len(x["issues"]) for x in results), OUT)
