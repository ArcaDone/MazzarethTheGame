"""Imports the Italian phone booth package (D:/BlenderTest/Da importare/parte4/Cabina_Telefonica) into
/Game/Mazzarino80/Kit/CabinaTelefonica with the package's own importer (unreal/import_cabina.py: skeletal mesh with the
folding door, four condition variants on the same skeleton, open/close clips, weathered PBR materials, five sounds),
then stores the colour and ORM sources as JPEG (normals stay lossless) to keep the repository light.

powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_cabina_import.py
"""
import os
import re
import sys

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

PKG = "D:/BlenderTest/Da importare/parte4/Cabina_Telefonica"
DEST = "/Game/Mazzarino80/Kit/CabinaTelefonica"
LIGHT = os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/Cabina/exports")
EAL = unreal.EditorAssetLibrary
# "obj.prop=value" (also after "if ...:"), not "obj.prop==value".
ASSIGN = re.compile(r"^(\s*(?:if [^:]+:)?)([A-Za-z_][\w.]*)\.(\w+)=(?!=)(.+)$")


def as_editor_properties(code):
    """This engine exposes many import and material-expression options only as editor properties, not as Python
    attributes: every attribute assignment becomes obj.set_editor_property('prop', value)."""
    return "\n".join(";".join(ASSIGN.sub(r"\1\2.set_editor_property('\3', \4)", st) for st in line.split(";"))
                     for line in code.split("\n"))


def steps():
    code = open(os.path.join(PKG, "unreal", "import_cabina.py"), encoding="utf-8").read()
    code = code.replace("ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))", "ROOT=%r" % PKG)
    code = code.replace("DEST='/Game/CabinaTelefonica'", "DEST=%r" % DEST)
    # The meshes from m80_cabina_gioco.py (25k triangles instead of 91k), imported again over what is there, the base
    # one onto its own skeleton when it has one; the clips, textures and sounds stay the package's.
    code = code.replace("os.path.join(ROOT,'exports','SK_Cabina_Telefonica.fbx')", "os.path.join(LIGHT,'SK_Cabina_Telefonica.fbx')")
    code = code.replace("os.path.join(ROOT,variant['fbx'])", "os.path.join(LIGHT,os.path.basename(variant['fbx']))")
    code = code.replace("if not mesh:", "if True:\n    if mesh and mesh.get_editor_property('skeleton'):opt_skeleton=mesh.get_editor_property('skeleton')\n    else:opt_skeleton=None")
    code = code.replace("opt.create_physics_asset=False\n    axes(", "opt.create_physics_asset=False\n    if opt_skeleton:opt.skeleton=opt_skeleton\n    axes(")
    code = code.replace("if not variant_mesh:", "if True:")
    code = code.replace("t.replace_existing=False", "t.replace_existing=True")
    code = as_editor_properties(code)
    assert ("ROOT=%r" % PKG) in code and ("DEST=%r" % DEST) in code and code.count("LIGHT,") == 2
    assert "opt.set_editor_property('skeleton', opt_skeleton)" in code
    exec(compile(code, "import_cabina.py", "exec"), {"__name__": "import_cabina", "LIGHT": LIGHT})
    yield 30
    # Slots the package left empty (the base mesh, imported again over itself) take the material of their name.
    for path in EAL.list_assets(DEST + "/Meshes", recursive=False):
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.SkeletalMesh):
            continue
        slots = mesh.get_editor_property("materials")
        empty = [i for i, s in enumerate(slots) if not s.get_editor_property("material_interface")]
        for i in empty:
            # The array hands out copies: the slot is changed and put back.
            s = slots[i]
            s.set_editor_property("material_interface", unreal.load_asset("%s/Materials/%s" % (DEST, s.get_editor_property("material_slot_name"))))
            slots[i] = s
        if empty:
            mesh.set_editor_property("materials", slots)
            EAL.save_loaded_asset(mesh, False)
    yield 5
    for path in EAL.list_assets(DEST + "/Textures", recursive=False):
        tex = unreal.load_asset(path)
        if isinstance(tex, unreal.Texture2D) and "_Normal" not in tex.get_name():
            unreal.M80EditorLibrary.compress_texture_source_jpeg(tex, 90)
            EAL.save_loaded_asset(tex, False)
    yield 5


m80_seq.Sequencer(steps(), log_file=str(os.path.join(unreal.Paths.project_dir(), "Saved/Mazzarino80/Chiese/cabina_error.txt")))
