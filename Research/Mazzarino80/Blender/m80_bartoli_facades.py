"""Facades of the Palazzo Bartoli block (specs for m80_arch_facade.build), local metres (x east, y north).

Every facade is walked with its building on the left, so the street (or courtyard) is on the right.
Sources: the reference photos in D:/BlenderTest/Palazzo Bartoli and the user's Street View screenshots,
the OSM footprint and the game terrain. Heights: C 12.0 m (measured on the frontal photo), D 16 m
(one storey more than C), B 9.6 m (one storey less, hanging garden on top), cream house 15.5 m,
cinema 9.8 m.
"""
import math

import m80_arch_facade as A

Z_CORSO = 0.9


def bays(u_first, step, n):
    return [u_first + step * k for k in range(n)]


def ow(id_, uc, w, v0, v1, kind="window", fit="shutters", arch=0.0, **kw):
    d = {"id": id_, "u0": uc - w / 2, "u1": uc + w / 2, "v0": v0, "v1": v1, "arch": arch, "kind": kind, "fit": fit}
    d.update(kw)
    return d


# ---------------------------------------------------------------------------------------------
# C - Palazzo Bartoli on the Corso (rubble stone, 3 storeys, 5 bays)

def facade_c():
    B = [2.6, 7.1, 11.0, 15.25, 19.65]
    o = []
    for k, uc in enumerate(B):
        o.append(ow("C_W%d" % (k + 1), uc, 1.05, 9.25, 11.15, fit="glazed", sill=True))
    for k in range(4):
        o.append(ow("C_F%d" % (k + 1), B[k], 1.12, 5.0, 7.85, kind="french", fit="shutters"))
    o.append(ow("C_F5", B[4], 1.10, 5.75, 7.70, fit="shutters", sill=True))
    o += [
        {"id": "C_G1", "u0": 1.36, "u1": 3.12, "v0": 0.0, "v1": 2.85, "arch": 0.88, "kind": "arch_door", "fit": "roll",
         "lunette": True, "frame": {"w": 0.20, "proj": 0.08, "mat": "stone"}},
        ow("C_G2", 7.08, 1.0, 1.95, 3.85, fit="grille", sill=True, frame={"w": 0.14, "proj": 0.055, "mat": "stone"}),
        {"id": "C_G3", "u0": 10.1, "u1": 11.85, "v0": 0.0, "v1": 2.9, "kind": "shop", "fit": "shop"},
        {"id": "C_G4", "u0": 14.41, "u1": 16.09, "v0": 0.0, "v1": 3.05, "arch": 0.84, "kind": "portal", "fit": "portal",
         "frame": {"w": 0.30, "proj": 0.08, "mat": "portal"}, "keystone": True},
        {"id": "C_G5", "u0": 18.9, "u1": 20.4, "v0": 0.0, "v1": 3.0, "kind": "door", "fit": "door"},
    ]
    # Piano nobile: bellied railings on carved consoles (the central one richer, in the portal's stone).
    bal = [{"u0": B[0] - 1.55, "u1": B[0] + 1.55, "v": 5.0, "d": 0.75, "railing": "bombe", "brackets": "rich", "n": 3, "bracket_h": 0.55},
           {"u0": B[1] - 1.5, "u1": B[1] + 1.5, "v": 5.0, "d": 0.75, "railing": "bombe", "brackets": "rich", "n": 3, "bracket_h": 0.55},
           {"u0": B[2] - 1.52, "u1": B[2] + 1.52, "v": 5.0, "d": 0.75, "railing": "bombe", "brackets": "rich", "n": 3, "bracket_h": 0.55},
           {"u0": B[3] - 1.6, "u1": B[3] + 1.6, "v": 5.0, "d": 0.88, "railing": "bombe", "brackets": "rich", "n": 4, "mat": "portal"}]

    def extra(F, ops):
        import bmesh
        import m80_arch_kit as K
        M = A.mats()
        # Portal: rusticated pilasters, imposts and entablature under the central balcony.
        o4 = [op for nm, op, d in ops if nm == "C_G4"][0]
        for side in (-1, 1):
            ux = o4.u0 - 0.30 - 0.36 if side < 0 else o4.u1 + 0.30
            K.ashlar_strip("C_G4_lesena%d" % side, ux, ux + 0.36, 0.0, 4.55, 0.10, 0.42, F.high, F.low, M["portal"], M["low"], F.frame, seed=11 + side)
            for coll, mat, sfx in ((F.high, M["portal"], "_hi"), (F.low, M["low"], "")):
                bm = bmesh.new()
                x0 = o4.u0 - 0.30 if side < 0 else o4.u1
                K.box_bm(bm, x0 - 0.02, x0 + 0.32, -0.12, 0.0, o4.v1 - 0.10, o4.v1 + 0.08)
                K.bm_object("C_G4_imposta%d%s" % (side, sfx), bm, coll, F.frame, mat)
        path = [(o4.u0 - 0.75, 4.55), (o4.u1 + 0.75, 4.55)]
        K.sweep("C_G4_trabeazione_hi", path, K.frame_profile(0.20, 0.14, 8), F.high, F.frame, M["portal"], smooth=True)
        K.sweep("C_G4_trabeazione", path, K.frame_profile(0.20, 0.14, 1), F.low, F.frame, M["low"])
        # Central window: aedicule with side strips, pediment, coat of arms.
        f4 = [op for nm, op, d in ops if nm == "C_F4"][0]
        for coll, mat, sfx, seg in ((F.high, M["portal"], "_hi", 8), (F.low, M["low"], "", 1)):
            for side in (-1, 1):
                ux = f4.u0 - 0.32 if side < 0 else f4.u1 + 0.16
                bm = bmesh.new()
                K.box_bm(bm, ux, ux + 0.16, -0.09, 0.0, f4.v0, f4.top + 0.25)
                K.bm_object("C_F4_lesena%d%s" % (side, sfx), bm, coll, F.frame, mat)
            K.sweep("C_F4_timpano" + sfx, [(f4.u0 - 0.42, f4.top + 0.25), (f4.u1 + 0.42, f4.top + 0.25)], K.cornice_profile(seg), coll, F.frame, mat, smooth=bool(sfx))
            bm = bmesh.new()
            mid = (f4.u0 + f4.u1) / 2
            K.box_bm(bm, mid - 0.26, mid + 0.26, -0.11, 0.0, f4.top + 0.80, f4.top + 1.38)
            ob = K.bm_object("C_F4_stemma" + sfx, bm, coll, F.frame, mat)
            if sfx:
                K.add_bevel(ob, 0.05, 4)
                s = ob.modifiers.new("Sub", "SUBSURF")
                s.levels = s.render_levels = 3
                tex = bpy_tex("M80_Stemma", "STUCCI", 0.05)
                dd = ob.modifiers.new("Scolpito", "DISPLACE")
                dd.texture = tex
                dd.strength = 0.035
                dd.texture_coords = "GLOBAL"
        # Left corner: the palace is taller than the old body B beside it; its corner pilaster rises
        # with a capital above B's terrace (seen as a "tower" from the street).
        for coll, mat, sfx in ((F.high, M["stone"], "_hi"), (F.low, M["low"], "")):
            bm = bmesh.new()
            K.box_bm(bm, -0.05, 1.30, -0.16, 0.0, 11.30, 11.95)
            ob = K.bm_object("C_capitello%s" % sfx, bm, coll, F.frame, mat)
        # Belvedere over the left corner and a small roof altana in the middle (plastered, tiled).
        plaster = A.principled("Intonaco_belvedere", (0.55, 0.47, 0.34), 0.9)
        for nm, (a, b, c, d, top) in (("C_belvedere", (0.2, 3.4, 1.0, 4.4, 15.4)), ("C_altana", (8.2, 10.6, 5.5, 8.2, 14.6))):
            bm = bmesh.new()
            K.box_bm(bm, a, b, c, d, 11.9, top)
            K.bm_object(nm, bm, F.high, F.frame, plaster)
            bm = bmesh.new()
            K.box_bm(bm, a, b, c, d, 11.9, top)
            K.bm_object(nm + "_lo", bm, F.low, F.frame, M["low"])
            bm = bmesh.new()
            K.box_bm(bm, a - 0.25, b + 0.25, c - 0.25, d + 0.25, top, top + 0.18)
            K.bm_object(nm + "_tetto", bm, F.detail, F.frame, M["coppi"])
        for k, u in enumerate((1.0, 2.6)):
            o = K.Opening(u, u + 0.8, 12.9, 14.4, 0.4)
            bm = bmesh.new()
            K.box_bm(bm, o.u0, o.u1, 0.95, 1.0, o.v0, o.v1)
            K.bm_object("C_belvedere_finestra%d" % k, bm, F.detail, F.frame, M["green"])

    return {
        "name": "C_Corso", "p0": [-12.5, -32.3], "p1": [8.2, -26.2], "z0": Z_CORSO, "height": 12.0,
        # Small stones in plenty of mortar.
        "wall": {"type": "rubble", "seed": 7, "cell": (0.16, 0.11), "mortar": 0.02},
        "openings": o, "balconies": bal,
        "pilasters": [[0.0, 1.21, 0.07, "quoin"], [9.04, 9.29, 0.04, ""], [13.23, 13.57, 0.05, ""], [17.03, 17.8, 0.06, ""], [21.23, 21.6, 0.06, ""]],
        "bands": [{"v": 11.15, "profile": "string", "u0": 0.0, "u1": 21.6}],
        "cornice": {"v": 11.48, "tiles": True},
        "anchors": [[4.75, 8.45], [9.17, 8.45], [13.4, 8.45], [17.4, 8.45], [4.75, 4.55], [13.4, 4.55]],
        "plaques": [[12.55, 13.15, 2.2, 2.95], [16.9, 17.35, 2.3, 2.85]],
        "signs": [{"u0": 9.95, "u1": 12.0, "v": 3.05, "text": "ALIMENTARI", "bg": (0.30, 0.05, 0.03), "fg": (0.85, 0.75, 0.45)}],
        "extra": extra,
    }


def bpy_tex(name, kind, scale):
    import bpy
    t = bpy.data.textures.get(name) or bpy.data.textures.new(name, kind)
    t.noise_scale = scale
    return t


# ---------------------------------------------------------------------------------------------
# D - corner palace on the Corso and Piazza Monterosso (sandstone ashlar, 4 storeys)

D_FLOORS = {"g": (0.0, 3.0, 0.75), "f1": (5.0, 7.9), "f2": (9.0, 11.6), "f3": (12.5, 14.8)}


def _d_upper(prefix, B, o, bal, f3_balcony=True):
    for k, uc in enumerate(B):
        o.append(ow("%s_P1_%d" % (prefix, k), uc, 1.15, *D_FLOORS["f1"], kind="french", fit="shutters_open" if k % 3 == 1 else "shutters"))
        o.append(ow("%s_P2_%d" % (prefix, k), uc, 1.05, *D_FLOORS["f2"], kind="french", fit="shutters"))
        o.append(ow("%s_P3_%d" % (prefix, k), uc, 0.95, *D_FLOORS["f3"], kind="french", fit="shutters" if k % 2 else "glazed"))
        bal.append({"u0": uc - 1.25, "u1": uc + 1.25, "v": 5.0, "d": 0.85, "brackets": "rich", "n": 4, "railing": "bombe"})
        bal.append({"u0": uc - 0.95, "u1": uc + 0.95, "v": 9.0, "d": 0.70, "brackets": "rich", "n": 3, "bracket_h": 0.5})
        if f3_balcony:
            bal.append({"u0": uc - 0.8, "u1": uc + 0.8, "v": 12.5, "d": 0.55, "n": 3, "bracket_h": 0.4})


def facade_d_corso():
    B = bays(2.5, 4.45, 8)
    o, bal = [], []
    # Ground floor in the 1980s: the carriage gate to the courtyard (green doors, fan light), a green
    # door, shops, the bar, the pharmacy near the corner.
    o.append({"id": "D_Androne", "u0": B[0] - 1.05, "u1": B[0] + 1.05, "v0": 0.0, "v1": 3.3, "arch": 1.05, "kind": "portal",
              "fit": "portal", "door_mat": "green", "lunette": True, "keystone": True, "depth": 0.6,
              "frame": {"w": 0.32, "proj": 0.09, "mat": "stone"}})
    kinds = [None, ("door", "door", "green"), ("shop", "shop", None), ("shop", "shop", None), ("shop", "shop", None),
             ("door", "door", "wood"), ("shop", "shop", None), ("shop", "shop", None)]
    for k in range(1, 8):
        kind, fit, mat = kinds[k]
        d = {"id": "D_T%d" % k, "u0": B[k] - 0.85, "u1": B[k] + 0.85, "v0": 0.0, "v1": 3.0, "arch": 0.85,
             "kind": "arch_door", "fit": fit, "frame": {"w": 0.22, "proj": 0.07, "mat": "stone"}}
        if mat:
            d["door_mat"] = mat
        o.append(d)
    _d_upper("D_C", B, o, bal)
    return {
        "name": "D_Corso", "p0": [8.2, -26.2], "p1": [42.73, -11.99], "z0": Z_CORSO, "height": 16.0,
        "wall": {"type": "ashlar", "course": 0.34, "length": 0.66, "seed": 4},
        "grime": 1.8,  # the corner palace is darkened by the weather all over
        "openings": o, "balconies": bal,
        "pilasters": [[0.0, 0.55, 0.05, ""], [36.72, 37.34, 0.07, "quoin"]],
        "bands": [{"v": 4.55, "profile": "string"}, {"v": 0.0, "profile": "plinth", "h": 0.55}],
        "cornice": {"v": 15.48, "tiles": True, "modillions": 0.75},
        "anchors": [[B[k] + 2.2, 8.55] for k in range(0, 7, 2)],
        "signs": [{"u0": B[7] - 1.3, "u1": B[7] + 1.3, "v": 3.95, "text": "FARMACIA", "bg": (0.01, 0.10, 0.04), "fg": (0.85, 0.85, 0.8),
                   "flag": {"u": B[7] + 1.6, "v": 4.9, "shape": "cross", "color": (0.05, 0.6, 0.12), "glow": 4.0}},
                  {"u0": B[4] - 1.2, "u1": B[4] + 1.2, "v": 3.95, "text": "BAR", "bg": (0.30, 0.02, 0.02), "fg": (0.95, 0.85, 0.5)},
                  {"u0": B[3] - 1.2, "u1": B[3] + 1.2, "v": 3.95, "text": "TABACCHI", "bg": (0.02, 0.04, 0.18), "fg": (0.9, 0.9, 0.9),
                   "flag": {"u": B[3] + 1.5, "v": 4.9, "shape": "T", "color": (0.02, 0.05, 0.30)}},
                  {"u0": B[6] - 1.2, "u1": B[6] + 1.2, "v": 3.95, "text": "TESSUTI", "bg": (0.12, 0.10, 0.06), "fg": (0.85, 0.75, 0.45)}],
    }


def facade_d_piazza():
    B = bays(2.4, 4.3, 3)
    o, bal = [], []
    for k, uc in enumerate(B):
        o.append({"id": "D_PT%d" % k, "u0": uc - 0.85, "u1": uc + 0.85, "v0": 0.0, "v1": 3.0, "arch": 0.85, "kind": "arch_door",
                  "fit": "shop" if k == 0 else "door", "door_mat": "green", "frame": {"w": 0.22, "proj": 0.07, "mat": "stone"}})
    _d_upper("D_P", B, o, bal)
    # The north end on the piazza is a roofless ruin: the facade wall stands to the second floor, an
    # empty window, ivy over everything.
    o.append(ow("D_P_rudere", 14.6, 1.0, 5.2, 7.6, kind="window", fit="none", frame={"w": 0.16, "proj": 0.05, "mat": "stone"}, dark=False))
    return {
        "name": "D_Piazza", "p0": [42.73, -11.99], "p1": [37.0, 3.8], "z0": 1.04, "height": 16.0,
        "wall": {"type": "ashlar", "course": 0.34, "length": 0.66, "seed": 5},
        "grime": 1.8,  # the corner palace is darkened by the weather all over
        "openings": o, "balconies": bal,
        "pilasters": [[0.0, 0.6, 0.07, "quoin"]],
        "bands": [{"v": 4.55, "profile": "string", "u1": 12.6}, {"v": 0.0, "profile": "plinth", "h": 0.55, "u1": 12.6}],
        "cornice": None,
        "ruin": {"u0": 12.6, "u1": 16.8, "top": 9.0},
        "ivy": [[11.8, 16.7, 0.4, 10.4]],
        "extra": _d_piazza_cornice,
    }


def _d_piazza_cornice(F, ops):
    import m80_arch_kit as K
    M = A.mats()
    path = [(-0.06, 15.48), (12.6, 15.48)]
    K.sweep("D_Piazza_cornicione_hi", path, K.cornice_profile(10), F.high, F.frame, M["stone"], smooth=True)
    K.sweep("D_Piazza_cornicione", path, K.cornice_profile(2), F.low, F.frame, M["low"])
    A.modillions(F, "D_Piazza", 0.0, 12.6, 15.48, M["stone"], 0.75)
    A.coppi_eave(F, "D_Piazza_coppi", -0.05, 12.6, 16.02, 0.50)


# ---------------------------------------------------------------------------------------------
# B - old body: ground floor of doors and shops on the Corso, upper level = wall of the hanging
# garden with arched openings (railings on the Corso, shuttered windows on Salita Teatro)

def facade_b_corso():
    o = [
        {"id": "B_T1", "u0": 1.0, "u1": 2.35, "v0": 0.0, "v1": 2.6, "arch": 0.68, "kind": "arch_door", "fit": "door", "door_mat": "green",
         "frame": {"w": 0.18, "proj": 0.06, "mat": "stone"}},
        {"id": "B_T2", "u0": 3.6, "u1": 4.75, "v0": 0.0, "v1": 2.75, "kind": "door", "fit": "door", "frame": {"w": 0.16, "proj": 0.05, "mat": "stone"}},
        {"id": "B_T3", "u0": 6.3, "u1": 8.6, "v0": 0.0, "v1": 3.55, "kind": "door", "fit": "door", "door_mat": "wood_light",
         "frame": {"w": 0.28, "proj": 0.07, "mat": "stone"}},
        {"id": "B_T4", "u0": 9.9, "u1": 11.45, "v0": 0.0, "v1": 2.75, "arch": 0.78, "kind": "arch_door", "fit": "shop", "keystone": True,
         "frame": {"w": 0.26, "proj": 0.08, "mat": "portal"}},
        {"id": "B_T5", "u0": 12.75, "u1": 14.1, "v0": 0.0, "v1": 2.7, "kind": "shop", "fit": "shop", "frame": {"w": 0.20, "proj": 0.06, "mat": "white"}},
        ow("B_T6", 15.55, 0.75, 2.3, 3.25, fit="grille", sill=True, frame={"w": 0.13, "proj": 0.05, "mat": "stone"}),
    ]
    for k, uc in enumerate(bays(2.3, 3.55, 5)):
        o.append({"id": "B_A%d" % k, "u0": uc - 0.62, "u1": uc + 0.62, "v0": 5.6, "v1": 7.55, "arch": 0.62, "kind": "open_arch",
                  "fit": "rail", "frame": {"w": 0.15, "proj": 0.05, "mat": "stone"}, "depth": 0.6})
    return {
        "name": "B_Corso", "p0": [-31.0, -36.8], "p1": [-12.5, -32.3], "z0": Z_CORSO, "height": 9.6,
        "wall": {"type": "rubble", "seed": 11},
        "openings": o,
        "pilasters": [[0.0, 0.85, 0.06, "quoin"]],
        "bands": [{"v": 4.75, "profile": "string"}],
        "cornice": {"v": 9.15, "tiles": False, "profile": "string"},
        "anchors": [[5.2, 4.4], [12.0, 4.4]],
        "signs": [{"u0": 9.7, "u1": 11.65, "v": 3.75, "h": 0.38, "text": "OROLOGERIA", "bg": (0.05, 0.05, 0.05), "fg": (0.8, 0.65, 0.3)},
                  {"u0": 12.6, "u1": 14.25, "v": 3.0, "h": 0.38, "text": "MERCERIA", "bg": (0.25, 0.18, 0.08), "fg": (0.9, 0.85, 0.7)}],
    }


def facade_b_salita():
    L = 29.2
    o = []
    for k, uc in enumerate(bays(3.0, 4.0, 7)):
        o.append({"id": "B_S%d" % k, "u0": uc - 0.6, "u1": uc + 0.6, "v0": 5.7, "v1": 7.45, "arch": 0.6, "kind": "window",
                  "fit": "shutters", "frame": {"w": 0.15, "proj": 0.05, "mat": "stone"}})
    for k, uc in enumerate((9.0, 14.5, 20.0, 25.5)):
        g = 4.3 * (1 - uc / L)          # the street climbs towards the cinema
        o.append(ow("B_SG%d" % k, uc, 0.8, g + 1.25, g + 2.4, fit="grille", sill=True, frame={"w": 0.14, "proj": 0.05, "mat": "stone"}))
    return {
        "name": "B_Salita", "p0": [-40.1, -9.1], "p1": [-31.0, -36.8], "z0": Z_CORSO, "height": 9.6,
        "wall": {"type": "rubble", "seed": 13},
        "openings": o,
        "pilasters": [[28.35, 29.2, 0.06, "quoin"]],
        "bands": [{"v": 5.2, "profile": "string"}],
        "cornice": {"v": 9.15, "tiles": False, "profile": "string"},
    }


# ---------------------------------------------------------------------------------------------
# Cream house at the top of Salita Teatro (plastered, 4 storeys + roof terrace)

def facade_crema():
    o = [
        {"id": "CR_T1", "u0": 3.0, "u1": 4.3, "v0": 0.0, "v1": 2.6, "arch": 0.65, "kind": "arch_door", "fit": "door", "door_mat": "green",
         "frame": {"w": 0.18, "proj": 0.06, "mat": "white"}},
        ow("CR_T2", 6.6, 0.8, 1.3, 2.5, fit="grille", sill=True, frame={"w": 0.13, "proj": 0.05, "mat": "white"}),
        ow("CR_P1a", 3.6, 1.0, 4.3, 6.2, fit="shutters", sill=True, frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
        ow("CR_P1b", 6.6, 1.0, 4.3, 6.2, fit="shutters", sill=True, frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
        ow("CR_P2a", 3.6, 1.05, 7.4, 9.9, kind="french", fit="shutters", frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
        ow("CR_P2b", 6.6, 1.05, 7.4, 9.9, kind="french", fit="shutters_open", frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
        ow("CR_P3a", 3.6, 1.0, 10.9, 12.7, kind="french", fit="shutters", arch=0.5, frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
        ow("CR_P3b", 6.6, 1.0, 10.9, 12.7, kind="french", fit="glazed", arch=0.5, frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
    ]
    bal = [{"u0": 2.6, "u1": 7.6, "v": 7.4, "d": 0.75, "n": 5, "mat": "white"},
           {"u0": 2.8, "u1": 7.4, "v": 10.9, "d": 0.6, "n": 4, "mat": "white", "railing": "bombe"}]
    return {
        "name": "Crema_Salita", "p0": [-42.0, -0.4], "p1": [-40.1, -9.1], "z0": 5.2, "height": 14.4,
        "wall": {"type": "plaster", "color": (0.70, 0.62, 0.48), "peel": 0.25, "seed": 21},
        "openings": o, "balconies": bal,
        "pilasters": [[8.3, 8.9, 0.06, "quoin"]],
        "bands": [{"v": 3.8, "profile": "string", "mat": "white"}, {"v": 0.0, "profile": "plinth", "h": 0.8, "mat": "white"}],
        "cornice": {"v": 13.9, "tiles": False, "profile": "string", "mat": "white"},
    }


def facade_crema_sud():
    o = [ow("CR_S1", 3.0, 1.0, 7.4, 9.9, kind="french", fit="shutters", frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
         ow("CR_S2", 6.5, 1.0, 7.4, 9.9, kind="french", fit="shutters", frame={"w": 0.14, "proj": 0.05, "mat": "white"}),
         ow("CR_S3", 3.0, 1.0, 10.9, 12.7, fit="shutters", sill=True, frame={"w": 0.14, "proj": 0.05, "mat": "white"})]
    return {
        "name": "Crema_Sud", "p0": [-40.1, -9.1], "p1": [-29.6, -5.5], "z0": 5.2, "height": 14.4,
        "wall": {"type": "plaster", "color": (0.70, 0.62, 0.48), "peel": 0.2, "seed": 22},
        "openings": o,
        "balconies": [{"u0": 2.3, "u1": 7.2, "v": 7.4, "d": 0.7, "n": 4, "mat": "white"}],
        "pilasters": [[0.0, 0.6, 0.06, "quoin"]],
        "cornice": {"v": 13.9, "tiles": False, "profile": "string", "mat": "white"},
    }


# ---------------------------------------------------------------------------------------------
# Courtyard facades (plastered, peeling; ballatoio = balcony gallery on brackets at the first floor)

def facade_cortile_sud():
    L = 15.5
    o = [{"id": "CS_Androne", "u0": 6.0, "u1": 9.4, "v0": 0.0, "v1": 2.9, "arch": 1.7, "kind": "open_arch", "fit": "none",
          "frame": {"w": 0.25, "proj": 0.06, "mat": "stone"}, "depth": 0.6},
         ow("CS_T1", 3.0, 1.1, 0.0, 2.4, kind="door", fit="door", door_mat="green"),
         ow("CS_T2", 11.8, 0.9, 1.0, 2.2, fit="grille", sill=True),
         ow("CS_T3", 13.9, 1.0, 0.0, 2.3, kind="door", fit="door")]
    for k, uc in enumerate((2.6, 5.6, 9.9, 12.9)):
        o.append(ow("CS_P1_%d" % k, uc, 1.05, 4.9, 7.5, kind="french", fit="shutters" if k != 2 else "shutters_open"))
        o.append(ow("CS_P2_%d" % k, uc, 0.95, 8.6, 10.2, fit="glazed" if k % 2 else "shutters", sill=True))
    return {
        "name": "Cortile_Sud", "p0": [11.5, -7.9], "p1": [-2.6, -14.3], "z0": 1.0, "height": 11.6,
        "wall": {"type": "plaster", "color": (0.74, 0.63, 0.42), "peel": 0.25, "seed": 31},
        "openings": o,
        "balconies": [{"u0": 0.6, "u1": L - 0.6, "v": 4.9, "d": 0.95, "n": 8, "railing": "straight"}],
        "cornice": {"v": 11.1, "tiles": True, "profile": "string"},
    }


def facade_cortile_ovest():
    o = [ow("CO_T1", 2.4, 2.0, 0.0, 2.6, kind="door", fit="door", door_mat="green", arch=0.5),
         ow("CO_T2", 5.6, 0.9, 1.0, 2.2, fit="grille", sill=True),
         ow("CO_T3", 9.0, 1.0, 0.0, 2.3, kind="door", fit="door")]
    for k, uc in enumerate((2.4, 5.6, 9.0, 12.0)):
        o.append(ow("CO_P1_%d" % k, uc, 1.05, 4.9, 7.5, kind="french", fit="shutters_open" if k == 1 else "shutters"))
        o.append(ow("CO_P2_%d" % k, uc, 0.95, 8.6, 10.2, fit="shutters", sill=True))
    return {
        "name": "Cortile_Ovest", "p0": [-2.6, -14.3], "p1": [-7.6, -0.9], "z0": 1.0, "height": 11.6,
        "wall": {"type": "plaster", "color": (0.75, 0.64, 0.43), "peel": 0.22, "seed": 32},
        "openings": o,
        "balconies": [{"u0": 0.6, "u1": 13.6, "v": 4.9, "d": 0.95, "n": 7}],
        "cornice": {"v": 11.1, "tiles": True, "profile": "string"},
        "ivy": [[11.5, 14.3, 0.0, 6.5]],
    }


def facade_cortile_est():
    o = [{"id": "CE_T1", "u0": 2.0, "u1": 3.9, "v0": 0.0, "v1": 2.5, "arch": 0.95, "kind": "arch_door", "fit": "door", "door_mat": "green",
          "frame": {"w": 0.2, "proj": 0.06, "mat": "stone"}},
         ow("CE_T2", 6.0, 0.9, 0.0, 2.3, kind="door", fit="door"),
         ow("CE_T3", 8.6, 1.0, 0.0, 2.3, kind="door", fit="none"),
         ow("CE_T4", 12.4, 1.1, 0.0, 2.5, kind="door", fit="door", door_mat="green")]
    for k, uc in enumerate((3.0, 6.6, 10.2)):
        o.append(ow("CE_P1_%d" % k, uc, 1.05, 4.9, 7.5, kind="french", fit="shutters_open" if k == 0 else "shutters"))
        o.append(ow("CE_P2_%d" % k, uc, 0.95, 8.6, 10.2, fit="shutters", sill=True))
    return {
        "name": "Cortile_Est", "p0": [2.3, 9.0], "p1": [9.8, -4.9], "z0": 1.0, "height": 12.8,
        "wall": {"type": "plaster", "color": (0.73, 0.62, 0.41), "peel": 0.28, "seed": 33},
        "openings": o,
        "balconies": [{"u0": 0.8, "u1": 12.0, "v": 4.9, "d": 0.95, "n": 6}],
        "cornice": {"v": 12.3, "tiles": True, "profile": "string"},
        "anchors": [[4.8, 8.2], [8.4, 8.2]],
        "ivy": [[0.0, 2.2, 0.0, 9.0]],
    }


# ---------------------------------------------------------------------------------------------
# Cinema (Cine-Teatro Bartolotta): red plaster, portico of four white pillars, three wooden doors,
# steps in lava stone, a band of three windows, white frieze; the corner on the left is curved.

def facade_cinema():
    o = []
    for k, uc in enumerate((1.12, 2.92, 4.72)):
        o.append(ow("CI_Porta%d" % k, uc, 1.45, 0.95, 4.4, kind="door", fit="door", door_mat="wood", frame=None))
    for k, uc in enumerate((1.12, 2.92, 4.72)):
        o.append(ow("CI_F%d" % k, uc, 1.4, 6.3, 7.8, fit="glazed", frame={"w": 0.10, "proj": 0.04, "mat": "white"}))
    return {
        "name": "Cinema_Fronte", "p0": [-49.6, -9.4], "p1": [-43.8, -9.75], "z0": 5.4, "height": 9.8,
        "wall": {"type": "plaster", "color": (0.44, 0.11, 0.08), "peel": 0.1, "seed": 41},
        "openings": o,
        "bands": [{"v": 0.0, "profile": "plinth", "h": 0.95, "mat": "lava"}, {"v": 5.6, "profile": "string", "mat": "white"}],
        "cornice": {"v": 9.2, "tiles": False, "profile": "string", "mat": "white"},
        "extra": _cinema_portico,
    }


def _cinema_portico(F, ops):
    import bmesh
    import m80_arch_kit as K
    M = A.mats()
    W = F.width
    for coll, mat, sfx in ((F.high, M["white"], "_hi"), (F.low, M["low"], "")):
        # Four square pillars, the canopy slab, five steps of lava stone.
        for k, u in enumerate((0.25, 2.02, 3.82, 5.6)):
            bm = bmesh.new()
            K.box_bm(bm, u - 0.22, u + 0.22, -1.45, -1.0, 0.95, 4.6)
            K.bm_object("CI_pilastro%d%s" % (k, sfx), bm, coll, F.frame, mat)
        bm = bmesh.new()
        K.box_bm(bm, -0.1, W + 0.1, -1.7, 0.0, 4.6, 5.05)
        K.bm_object("CI_pensilina%s" % sfx, bm, coll, F.frame, mat)
        for s in range(6):
            bm = bmesh.new()
            K.box_bm(bm, -0.3, W + 0.3, -1.7 - 0.32 * (5 - s), 0.0, -1.2, 0.16 * (s + 1))
            K.bm_object("CI_gradino%d%s" % (s, sfx), bm, coll, F.frame, M["lava"] if sfx else M["low"])


# ---------------------------------------------------------------------------------------------

def all_specs():
    return [facade_c(), facade_d_corso(), facade_d_piazza(), facade_b_corso(), facade_b_salita(),
            facade_crema(), facade_crema_sud(), facade_cortile_sud(), facade_cortile_ovest(), facade_cortile_est(),
            facade_cinema()]


# ---------------------------------------------------------------------------------------------
# Facades seen from the gardens and the side lanes (plainer: windows on a grid)

def plain(name, p0, p1, z0, height, wall, rows, every=3.6, w=1.0, fit="shutters", margin=1.6, ground_door=None, cornice=True):
    """rows: list of (v0, v1) for each storey's windows."""
    L = math.dist(p0, p1)
    n = max(1, int((L - 2 * margin) / every) + 1)
    us = [L / 2] if n == 1 else [margin + (L - 2 * margin) * k / (n - 1) for k in range(n)]
    o = []
    for r, (v0, v1) in enumerate(rows):
        for k, u in enumerate(us):
            if ground_door is not None and r == 0 and k == ground_door:
                o.append(ow("%s_porta" % name, u, 1.2, v0 if v0 < 0.5 else 0.0, 2.6, kind="door", fit="door", door_mat="green"))
                continue
            f = fit if (k + r) % 4 else ("shutters_open" if fit == "shutters" else fit)
            if fit == "door":
                o.append(ow("%s_%d_%d" % (name, r, k), u, w, v0, v1, kind="door", fit="door", door_mat="wood"))
            else:
                o.append(ow("%s_%d_%d" % (name, r, k), u, w, v0, v1, fit=f, sill=True))
    spec = {"name": name, "p0": list(p0), "p1": list(p1), "z0": z0, "height": height, "wall": wall, "openings": o}
    if cornice:
        spec["cornice"] = {"v": height - 0.5, "tiles": True, "profile": "string"}
    return spec


def secondary_specs(ground):
    def zmin(p0, p1):
        return min(ground(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t) for t in (0, 0.25, 0.5, 0.75, 1)) - 0.2

    plaster = lambda c, s: {"type": "plaster", "color": c, "peel": 0.45, "seed": s}  # noqa: E731
    red = (0.44, 0.11, 0.08)
    specs = [
        plain("E_Giardino", (-4.5, 20.7), (1.3, 8.6), 7.5, 6.35, plaster((0.64, 0.56, 0.43), 71), [(1.6, 3.4)], every=3.4),
        plain("N_Giardino1", (-32.0, 19.0), (-17.3, 23.1), 7.5, 9.7, plaster((0.62, 0.55, 0.42), 72), [(1.0, 2.6), (4.6, 6.4)], ground_door=1),
        plain("N_Giardino2", (-15.4, 14.6), (-4.5, 20.7), 7.5, 9.7, plaster((0.62, 0.55, 0.42), 73), [(1.0, 2.6), (4.6, 6.4)]),
        plain("Crema_Est", (-27.6, -1.9), (-31.0, 8.0), 7.5, 12.1, plaster((0.70, 0.62, 0.48), 74), [(1.4, 3.2), (4.6, 6.4), (7.9, 9.7)], every=3.2, cornice=False),
        plain("C_Giardino", (-20.4, -5.5), (-7.6, -0.9), 7.5, 5.45, plaster((0.66, 0.58, 0.44), 75), [(1.4, 3.6)], every=3.2),
        plain("B_Giardino", (-28.4, -8.8), (-20.4, -5.5), 7.5, 2.9, {"type": "rubble", "seed": 76}, [], cornice=False),
        plain("E_GiardinoNE", (21.3, 4.4), (8.2, 30.9), zmin((21.3, 4.4), (8.2, 30.9)), 13.85 - zmin((21.3, 4.4), (8.2, 30.9)),
              plaster((0.64, 0.56, 0.43), 77), [(2.0, 3.6), (5.6, 7.4), (9.0, 10.6)], every=4.0),
        plain("D_Retro", (33.5, -1.8), (25.2, -3.5), zmin((33.5, -1.8), (25.2, -3.5)), 16.95 - zmin((33.5, -1.8), (25.2, -3.5)),
              plaster((0.64, 0.56, 0.43), 78), [(5.4, 7.4), (9.4, 11.2), (12.8, 14.6)], every=3.4),
        # Cinema: sides and back in red plaster, exits, the curved corner of the front.
        plain("Cinema_Est", (-34.8, 7.0), (-38.4, 19.9), 7.5, 7.7, plaster(red, 79), [(2.6, 4.2)], every=4.5, w=0.9, fit="glazed"),
        plain("Cinema_Ovest1", (-52.7, 22.1), (-52.4, 11.9), zmin((-52.7, 22.1), (-52.4, 11.9)), 15.2 - zmin((-52.7, 22.1), (-52.4, 11.9)),
              plaster(red, 80), [(0.0, 2.4)], every=5.0, w=1.4, fit="door", cornice=False),
        plain("Cinema_Ovest2", (-52.4, 11.9), (-50.9, -7.4), zmin((-52.4, 11.9), (-50.9, -7.4)), 15.2 - zmin((-52.4, 11.9), (-50.9, -7.4)),
              plaster(red, 81), [(6.8, 8.0)], every=4.6, w=0.8, fit="glazed", cornice=False),
        plain("Cinema_Nord", (-43.0, 25.3), (-52.7, 22.1), zmin((-43.0, 25.3), (-52.7, 22.1)), 15.2 - zmin((-43.0, 25.3), (-52.7, 22.1)),
              plaster(red, 82), [(0.0, 2.4)], every=6.0, w=1.4, fit="door", cornice=False),
    ]
    # The courtyard's north-west side: retaining wall of the garden, with the gallery joining the loggia.
    specs.append({"name": "Cortile_Nordovest", "p0": [-7.6, -0.9], "p1": [-6.9, 5.9], "z0": 1.0, "height": 7.6,
                  "wall": plaster((0.62, 0.55, 0.42), 86), "openings": [ow("CNO_T1", 3.4, 1.1, 0.0, 2.4, kind="door", fit="door", door_mat="green")],
                  "balconies": [{"u0": 0.0, "u1": 6.84, "v": 4.9, "d": 0.95, "n": 4}],
                  "cornice": {"v": 7.1, "tiles": False, "profile": "string"}})
    arc = [(-49.6, -9.4), (-50.35, -9.15), (-50.8, -8.45), (-50.9, -7.4)]
    for k in range(3):
        specs.append({"name": "Cinema_Curva%d" % k, "p0": list(arc[k]), "p1": list(arc[k + 1]), "z0": 5.4, "height": 9.8,
                      "wall": plaster(red, 83 + k), "openings": [],
                      "bands": [{"v": 0.0, "profile": "plinth", "h": 0.95, "mat": "lava"}, {"v": 5.6, "profile": "string", "mat": "white"}],
                      "cornice": {"v": 9.2, "tiles": False, "profile": "string", "mat": "white"}})
    return specs
