"""Shop prototypes for the houses: each docs/prototipo_*.json of the shop packages in D:/Mazzarino80_Sorgenti/Interni_e_Negozi
(Alimentari, Abbigliamento, Ferramenta, Frutta, Farmacia, Officina, Negozio chiuso, Bar Sport, Tabaccheria, Edicola) becomes
a UM80PrototipoNegozio asset in /Game/Mazzarino/Prototipi/DA_Negozio_<name>: the room it wants and its zones (wall modules,
the counter chain, what goes on and over the counter, tables and chairs, middle and floor objects, wall things, ceiling
lamps), the pieces found by name among the imported packages (/Game/Mazzarino). A house's "Negozi" list picks one of them.
Left out for now: the side rooms (storeroom, toilet, card room), the tables outside, the kiosks and the phone booth.
powershell -File Scripts/run_editor_script.ps1 -Script Scripts/m80_negozi_prototipi.py -TimeoutMinutes 20
Env M80_NEGOZI_PROVA=1: also a test street (/Game/Mazzarino80/Negozi/Maps/L_M80_ProvaNegoziCase) with one house per
prototype, photographed from the street and inside. Report: Saved/Mazzarino80/Negozi/prototipi.json
"""
import glob
import json
import math
import os
import sys
from pathlib import Path

import unreal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import m80_seq  # noqa: E402

SRC = "D:/Mazzarino80_Sorgenti/Interni_e_Negozi"
DEST = "/Game/Mazzarino/Prototipi"
OUT = Path(unreal.Paths.project_dir()) / "Saved/Mazzarino80/Negozi"
SKIP = ("Edicola_Chiosco", "Cabina_SIP")   # stand alone in the street, not a room in a house
report = {"prototipi": {}, "mancanti": []}


def mesh_index():
    """Mesh name -> asset path for every static mesh of the imported packages."""
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    idx = {}
    flt = unreal.ARFilter(package_paths=["/Game/Mazzarino"], recursive_paths=True,
                          class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "StaticMesh")])
    for a in reg.get_assets(flt):
        idx[str(a.asset_name)] = str(a.package_name)
    return idx


def meshes(names, idx):
    out = []
    for n in names if isinstance(names, list) else [names]:
        if not isinstance(n, str):
            continue
        if n in idx:
            m = unreal.load_asset(idx[n])
            if m:
                out.append(m)
                continue
        report["mancanti"].append(n)
    return out


def wall(v):
    v = str(v or "")
    if v.startswith("laterale"):
        return unreal.M80MuroNegozio.LATERALE
    if "|" in v:
        return unreal.M80MuroNegozio.QUALSIASI
    return unreal.M80MuroNegozio.FONDO


def zone(name, kind, pieces, **kw):
    z = unreal.M80ZonaNegozio()
    z.set_editor_property("nome", name)
    z.set_editor_property("tipo", kind)
    z.set_editor_property("pezzi", pieces)
    for k, v in kw.items():
        z.set_editor_property(k, v)
    return z


def _zones(proto, idx):
    """The prototype's zones as UM80PrototipoNegozio zones (the kinds of the rules this generator understands)."""
    out = []
    for z in proto.get("zone", []):
        name = z.get("nome", "")
        if "stanza_cm" in z or "davanti_a" in z or "ai_lati" in z:
            continue   # side rooms, kiosk front: not yet
        if "catena" in z:
            out.append(zone(name, EZONE.BANCO, meshes(z["catena"], idx),
                            riempitivi=meshes(z.get("riempitivi", []), idx),
                            muro=unreal.M80MuroNegozio.LATERALE if str(z.get("parallelo_a", "")).startswith("laterale") or z.get("vicino") == "porta" else unreal.M80MuroNegozio.FONDO,
                            distanza=float(z.get("distanza_dal_muro_cm", z.get("distanza_dal_retro_cm", 150)))))
            for sp in z.get("su_piani", []) or []:
                if isinstance(sp, dict) and sp.get("oggetti"):
                    out.append(zone(name + "_piano", EZONE.SUL_BANCO, meshes(sp["oggetti"], idx), max=int(sp.get("max", 2))))
        elif "moduli" in z:
            out.append(zone(name, EZONE.MURO, meshes(z["moduli"], idx), muro=wall(z.get("muro")), riempi=bool(z.get("riempi", False)),
                            lunghezza=float(z.get("lunghezza_max_cm", 0)), max=int(z.get("max", 3))))
            if z.get("pareti_sopra"):
                out.append(zone(name + "_sopra", EZONE.PARETI, meshes(z["pareti_sopra"], idx), max=len(z["pareti_sopra"])))
        elif "su_piano_di" in z:
            out.append(zone(name, EZONE.SUL_BANCO, meshes(z.get("oggetti", []), idx), max=int(z.get("max", 2))))
        elif "sopra" in z and "muro" not in z:
            out.append(zone(name, EZONE.SOPRA_BANCO, meshes(z.get("oggetti", []), idx), max=int(z.get("max", 2))))
        elif "composizione" in z and "gruppo" in z:
            c = z["composizione"]
            out.append(zone(name, EZONE.TAVOLI, meshes([c.get("tavolo"), c.get("sedie")], idx), max=int(z.get("max", 3))))
        elif z.get("centro_stanza"):
            out.append(zone(name, EZONE.CENTRO, meshes(z.get("oggetti", []), idx), max=int(z.get("max", 2))))
        elif "pareti" in z and not z.get("oggetti"):
            out.append(zone(name, EZONE.PARETI, meshes(z["pareti"], idx), max=len(z["pareti"])))
        elif z.get("oggetti"):
            # Against a wall (a work bench, salt display, fridges), or on the floor somewhere along the walls.
            if "muro" in z:
                out.append(zone(name, EZONE.MURO, meshes(z["oggetti"], idx), muro=wall(z.get("muro")), riempi=False, max=int(z.get("max", 1))))
                if isinstance(z.get("sopra"), list):
                    out.append(zone(name + "_sopra", EZONE.PARETI, meshes(z["sopra"], idx), max=len(z["sopra"])))
            else:
                out.append(zone(name, EZONE.A_TERRA, meshes(z["oggetti"], idx), max=int(z.get("max", z.get("min", 1)))))
            if z.get("pareti"):
                out.append(zone(name + "_pareti", EZONE.PARETI, meshes(z["pareti"], idx), max=len(z["pareti"])))
    if proto.get("pareti"):
        out.append(zone("pareti", EZONE.PARETI, meshes(proto["pareti"], idx), max=min(6, len(proto["pareti"]))))
    s = proto.get("soffitto") or {}
    if s.get("oggetto"):
        out.append(zone("soffitto", EZONE.SOFFITTO, meshes([s["oggetto"]], idx), ogni_m2=float(s.get("ogni_m2", 8))))
    return out


EZONE = unreal.M80TipoZona


def steps():
    OUT.mkdir(parents=True, exist_ok=True)
    idx = mesh_index()
    report["meshes"] = len(idx)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    made = []
    for f in sorted(glob.glob(os.path.join(SRC, "*", "docs", "prototipo_*.json"))):
        proto = json.load(open(f, encoding="utf-8"))
        name = proto.get("prototipo") or os.path.basename(f)[10:-5]
        if any(k in name for k in SKIP):
            continue
        path = "%s/DA_Negozio_%s" % (DEST, name)
        da = unreal.load_asset(path) or tools.create_asset("DA_Negozio_%s" % name, DEST, unreal.M80PrototipoNegozio, None)
        da.set_editor_property("nome", name.replace("_", " "))
        da.set_editor_property("bar", str(proto.get("uso", "")).lower() == "bar")
        smin = proto.get("stanza_min_cm") or [480, 600]
        da.set_editor_property("stanza_min", unreal.Vector2D(float(smin[0]), float(smin[1])))
        zs = _zones(proto, idx)
        da.set_editor_property("zone", zs)
        unreal.EditorAssetLibrary.save_loaded_asset(da)
        report["prototipi"][name] = {"zone": len(zs), "pezzi": sum(len(z.get_editor_property("pezzi")) for z in zs)}
        made.append(path)
        yield 1
    report["mancanti"] = sorted(set(report["mancanti"]))
    (OUT / "prototipi.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


m80_seq.Sequencer(steps(), log_file=str(OUT / "prototipi_errore.txt"))
