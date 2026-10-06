"""Real ground footprint of a hand-made building, found by tracing down from above on a 2 m grid.

A cell belongs to the building when the first thing hit from above is the building itself, standing
at least 2.5 m over the ground there: flat parts of the same mesh (squares, sidewalks, steps) and
trees do not count. Used by m80_town_zones.py (zone outlines that follow the walls, concave shapes
included) and by m80_houses_district.py (lots next to a landmark are built unless a wall is really there).
"""
import math

import unreal

CELL = 200.0
MIN_HEIGHT = 250.0
SKIP_MESH_WORDS = ("Tree", "Pine", "Poplar", "Grass", "Bush", "Plant", "Cypress", "Palm")


def _hit(world, x, y, top, bottom, ignore):
    result = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, top), unreal.Vector(x, y, bottom),
                                                    unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                    unreal.DrawDebugTrace.NONE, True)
    hit = result[1] if isinstance(result, tuple) else result
    f = hit.to_tuple() if hit else None
    return f if f and f[0] else None


def _is_plant(component):
    mesh = getattr(component, "static_mesh", None) if component else None
    return bool(mesh) and any(w in mesh.get_name() for w in SKIP_MESH_WORDS)


def structure_at(world, actor, x, y, top, bottom):
    """True when a wall or roof of `actor` stands at (x, y)."""
    f = _hit(world, x, y, top, bottom, [])
    if not f or f[9] != actor or _is_plant(f[10]):
        return False
    z = f[5].z
    g = _hit(world, x, y, z - 1, bottom, [actor])
    if g is None:
        return False
    if isinstance(g[9], unreal.M80House):
        return True  # a house below the building's own geometry: treat as built over
    return z - g[5].z >= MIN_HEIGHT


def occupied_cells(world, actor):
    origin, extent = actor.get_actor_bounds(False)
    top, bottom = origin.z + extent.z + 2000, origin.z - extent.z - 5000
    x0, y0 = origin.x - extent.x - CELL, origin.y - extent.y - CELL
    nx, ny = int(2 * (extent.x + CELL) / CELL) + 1, int(2 * (extent.y + CELL) / CELL) + 1
    cells = set()
    for i in range(nx):
        for j in range(ny):
            if structure_at(world, actor, x0 + (i + 0.5) * CELL, y0 + (j + 0.5) * CELL, top, bottom):
                cells.add((i, j))
    return cells, (x0, y0)


def clusters(cells, min_cells=3):
    left, out = set(cells), []
    while left:
        stack, group = [left.pop()], set()
        while stack:
            c = stack.pop()
            group.add(c)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    n = (c[0] + di, c[1] + dj)
                    if n in left:
                        left.remove(n)
                        stack.append(n)
        if len(group) >= min_cells:
            out.append(group)
    return out


def dilate(cells):
    return {(i + di, j + dj) for i, j in cells for di in (-1, 0, 1) for dj in (-1, 0, 1)}


def _area(loop):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1]))


def _simplify(loop, tol):
    """Douglas-Peucker on a closed loop (grid units)."""
    def dp(pts):
        if len(pts) < 3:
            return pts
        a, b = pts[0], pts[-1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        far, idx = 0.0, 0
        for k in range(1, len(pts) - 1):
            d = abs((pts[k][0] - a[0]) * dy - (pts[k][1] - a[1]) * dx) / n
            if d > far:
                far, idx = d, k
        if far <= tol:
            return [a, b]
        return dp(pts[:idx + 1])[:-1] + dp(pts[idx:])
    # Split at the point farthest from the first one so both halves are open chains.
    k = max(range(len(loop)), key=lambda i: (loop[i][0] - loop[0][0]) ** 2 + (loop[i][1] - loop[0][1]) ** 2)
    first = dp(loop[:k + 1])
    second = dp(loop[k:] + [loop[0]])
    return first[:-1] + second[:-1]


def outline(cells, origin, tol_cells=0.6):
    """Outer contour of a set of grid cells as a world-space polygon (concave shapes kept, holes ignored)."""
    edges = {}
    for i, j in cells:
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        for a, b in zip(corners, corners[1:] + corners[:1]):
            if (b, a) in edges:
                del edges[(b, a)]
            else:
                edges[(a, b)] = True
    nxt = {}
    for a, b in edges:
        nxt.setdefault(a, []).append(b)
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop, p = [start], start
        while True:
            q = nxt[p].pop()
            if not nxt[p]:
                del nxt[p]
            if q == start:
                break
            loop.append(q)
            p = q
            if p not in nxt:
                break
        loops.append(loop)
    loop = max(loops, key=lambda l: abs(_area(l)))
    # Drop the corners on straight runs, then smooth the staircases.
    pts = [p for k, p in enumerate(loop)
           if (loop[k - 1][0] - p[0]) * (loop[(k + 1) % len(loop)][1] - p[1]) != (loop[k - 1][1] - p[1]) * (loop[(k + 1) % len(loop)][0] - p[0])]
    if len(pts) > 8:
        pts = _simplify(pts, tol_cells)
    return [(origin[0] + i * CELL, origin[1] + j * CELL) for i, j in pts]


def footprints(world, actor, margin_cells=1):
    """One polygon per separate block of the building, grown by `margin_cells`."""
    cells, origin = occupied_cells(world, actor)
    return [outline(dilate(g) if margin_cells else g, origin) for g in clusters(cells)]
