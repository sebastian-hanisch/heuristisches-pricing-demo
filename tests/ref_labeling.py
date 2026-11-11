"""Unabhängiger Rechenweg für das Label-Verfahren mit Etikettenlimit (Orakel, DEMO-PLAYBOOK §12): Mengen und Listen statt Bitmasken, Wörterbücher statt Listen mit Positionen,
kein Zugriff auf `hpr_algorithm`. Dazu eine Aufzählung aller Routen durch Tiefensuche (ohne Labels).

Gleiche Regeln wie der Kern, anders geschrieben: Gedächtnis als frozenset, nächstes Label per `min` über die offenen Labels (Zeit, Nummer), Dominanz als Teilmengenvergleich."""

import math

EPS = 1e-9


class Lab:
    def __init__(self, time, cost, load, mem, node, parent):
        self.time, self.cost, self.load, self.mem, self.node, self.parent = time, cost, load, mem, node, parent
        self.alive = True


def neighbourhoods(inst, k):
    out = {}
    for j in range(1, inst.n + 1):
        order = sorted(range(1, inst.n + 1), key=lambda i: inst.d[j][i])
        out[j] = frozenset(order[:k]) | {j}
    return out


def ref_price(inst, pi, k, limit=None, max_routes=10 ** 6):
    """Ergebnis als dict: generated, dominated, limited, live (Menge von (Knoten, Zeit, Kosten, Last, Gedächtnis als sortiertes Tupel)), routes ([(rc, route)] aufsteigend)."""
    nb = neighbourhoods(inst, k)
    labs = [Lab(0.0, 0.0, 0, frozenset(), 0, None)]
    alive_at = {j: [] for j in range(1, inst.n + 1)}
    open_ = [0]
    generated, dominated, limited = 1, 0, 0
    ended = []
    while open_:
        li = min(open_, key=lambda x: (labs[x].time, x))
        open_.remove(li)
        L = labs[li]
        if not L.alive:
            continue
        i = L.node
        if i != 0 and L.time + inst.service + inst.d[i][0] <= inst.horizon:
            ended.append((L.cost + inst.d[i][0], li))
        for j in range(1, inst.n + 1):
            if j == i or j in L.mem:
                continue
            load = L.load + inst.demand[j]
            if load > inst.capacity:
                continue
            arr = L.time + (inst.service if i != 0 else 0.0) + inst.d[i][j]
            if arr > inst.due[j] + EPS:
                continue
            t2 = max(arr, inst.ready[j])
            c2 = L.cost + inst.d[i][j] - pi[j]
            m2 = (L.mem & nb[j]) | {j}
            generated += 1
            here = alive_at[j]
            if any(o.cost <= c2 + EPS and o.time <= t2 + EPS and o.load <= load and o.mem <= m2 for o in (labs[x] for x in here)):
                dominated += 1
                continue
            keep = []
            for x in here:
                o = labs[x]
                if c2 <= o.cost + EPS and t2 <= o.time + EPS and load <= o.load and m2 <= o.mem:
                    o.alive = False
                    dominated += 1
                else:
                    keep.append(x)
            alive_at[j] = keep
            if limit is not None and len(keep) >= limit:
                limited += 1
                worst_cost = max(labs[x].cost for x in keep)
                worst = next(x for x in keep if labs[x].cost == worst_cost)      # bei gleichen Kosten das früher eingefügte
                if worst_cost <= c2:
                    continue                                                      # das neue Label fliegt
                labs[worst].alive = False
                keep.remove(worst)
            labs.append(Lab(t2, c2, load, m2, j, li))
            alive_at[j].append(len(labs) - 1)
            open_.append(len(labs) - 1)
    found = {}
    for rc, li in ended:
        path, x = [], li
        while x is not None:
            path.append(labs[x].node)
            x = labs[x].parent
        route = tuple(reversed(path))[1:]
        if rc < -1e-7 and route not in found:
            found[route] = rc
    live = {(L.node, L.time, L.cost, L.load, tuple(sorted(L.mem))) for L in labs if L.alive}
    return {"generated": generated, "dominated": dominated, "limited": limited, "live": live, "routes": sorted((rc, r) for r, rc in found.items())[:max_routes]}


def ref_all_routes(inst):
    """Alle zulässigen elementaren Routen durch Tiefensuche (Fenster, Last, Horizont), ohne Labels: Liste von Routen."""
    out = []

    def go(node, time, load, seen, route):
        if node != 0:
            if time + inst.service + inst.d[node][0] <= inst.horizon:
                out.append(tuple(route))
        for j in range(1, inst.n + 1):
            if j in seen or load + inst.demand[j] > inst.capacity:
                continue
            arr = time + (inst.service if node != 0 else 0.0) + inst.d[node][j]
            if arr > inst.due[j]:
                continue
            go(j, max(arr, inst.ready[j]), load + inst.demand[j], seen | {j}, route + [j])

    go(0, 0.0, 0, frozenset(), [])
    return out


def route_rc(inst, pi, route):
    """Reduzierte Kosten einer zulässigen Route: Länge minus Dualpreise."""
    seq = [0, *route, 0]
    return sum(inst.d[a][b] for a, b in zip(seq, seq[1:])) - sum(pi[j] for j in route)


def lp_over_routes(inst, routes):
    """Optimum des Überdeckungs-LPs über eine Routenmenge mit scipy (HiGHS): Zielwert."""
    import numpy as np
    from scipy.optimize import linprog
    costs = [sum(inst.d[a][b] for a, b in zip([0, *r], [*r, 0])) for r in routes]
    mat = np.zeros((inst.n, len(routes)))
    for c, r in enumerate(routes):
        for i in r:
            mat[i - 1, c] += 1
    res = linprog(costs, A_ub=-mat, b_ub=-np.ones(inst.n), bounds=(0, None), method="highs")
    return float(res.fun) if res.success else math.inf
