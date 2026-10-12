"""Weapon wheel icons: the EXR captures of Scripts/m80_icone_armi.py (scene colour, 1 - coverage in alpha) become light
grey shaded PNGs with transparency (GTA V's look), in the same folder.
Run: blender -b --factory-startup --python m80_icone_alpha.py
"""
import glob
import os
import shutil

import bpy
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DIR = os.path.join(ROOT, "Saved", "Mazzarino80", "Icone")

for src in glob.glob(os.path.join(DIR, "*")):
    name, ext = os.path.splitext(os.path.basename(src))
    if ext not in ("", ".exr") or not os.path.isfile(src):
        continue
    exr = os.path.join(DIR, name + ".tmp.exr")
    shutil.copyfile(src, exr)
    img = bpy.data.images.load(exr)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    cover = np.clip(1.0 - px[:, :, 3], 0.0, 1.0)
    lum = px[:, :, 0] * 0.2126 + px[:, :, 1] * 0.7152 + px[:, :, 2] * 0.0722
    top = np.percentile(lum[cover > 0.5], 97) if (cover > 0.5).any() else 1.0
    grey = 0.4 + 0.6 * np.clip(lum / max(top, 1e-4), 0.0, 1.0)
    out = np.dstack([grey, grey, grey, cover]).astype(np.float32)
    png = bpy.data.images.new(name, w, h, alpha=True)
    png.pixels = out.ravel()
    png.filepath_raw = os.path.join(DIR, name + ".png")
    png.file_format = "PNG"
    png.save()
    bpy.data.images.remove(img)
    os.remove(exr)
    print("M80 icona", name, w, h, round(float(cover.mean()), 3))
