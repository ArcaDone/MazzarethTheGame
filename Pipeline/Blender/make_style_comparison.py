"""Place the four reference houses beside the latest Blender pilot renders."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "Pipeline/Blender/output/mazzarino_reuse_style_gates_v2"
REFERENCE = Image.open(r"C:\Users\12700K RTX3070Ti\Downloads\stili.png").convert("RGB")
ROWS = [
    ("01 - casa popolare in pietra", (12, 158, 224, 540), "1249069204_STYLE_01.png"),
    ("02 - palazzo urbano in pietra", (560, 158, 785, 540), "1249068307_STYLE_02.png"),
    ("03 - intonaco anni 50-70", (12, 646, 227, 1010), "1249069200_STYLE_03.png"),
    ("04 - casa povera / corte", (561, 646, 788, 1010), "1249069228_STYLE_04.png"),
]
font_path = Path(r"C:\Windows\Fonts\arial.ttf")
font = ImageFont.truetype(str(font_path), 24) if font_path.exists() else ImageFont.load_default()
small = ImageFont.truetype(str(font_path), 19) if font_path.exists() else ImageFont.load_default()
canvas = Image.new("RGB", (1420, 2150), "#ece9e3")
draw = ImageDraw.Draw(canvas)
draw.text((24, 10), "Confronto visivo - riferimenti / quattro provini Blender", fill="#202020", font=font)
draw.text((50, 52), "Riferimento visivo", fill="#404040", font=small)
draw.text((465, 52), "Provino Blender 4.3 alla quota del manichino", fill="#404040", font=small)
for index, (title, refbox, filename) in enumerate(ROWS):
    y = 88 + index * 512
    draw.text((24, y), title, fill="#202020", font=font)
    ref = REFERENCE.crop(refbox)
    render = Image.open(OUTDIR / filename).convert("RGB")
    render = render.crop((220, 105, 1050, 920))
    ref = ImageOps.contain(ref, (375, 465), Image.Resampling.LANCZOS)
    render = ImageOps.contain(render, (930, 465), Image.Resampling.LANCZOS)
    canvas.paste(ref, (26 + (375 - ref.width) // 2, y + 36 + (465 - ref.height) // 2))
    canvas.paste(render, (435 + (930 - render.width) // 2, y + 36 + (465 - render.height) // 2))
    draw.line((24, y + 506, 1396, y + 506), fill="#beb8ae", width=2)
out = OUTDIR / "style_reference_comparison.png"
canvas.save(out)
print(out)
