"""Spaltenerzeugung mit Überdeckungs-Master, wahlweise mit heuristischem Pricing (erst Etikettenlimit, exakter Aufruf nur zum Beweis).

Master: kleinste Kosten, jeder Kunde mindestens einmal überdeckt (Überdeckung, >= 1), Spalten = Routen. Start: eine Einzelfahrt je Kunde. In jeder Runde löst der Master-Löser
die Aufgabe; die Dualpreise sind die Schattenpreise der Überdeckungsbedingungen. Das Preisproblem (`hpr_algorithm.price`, Gedächtnis k) liefert bis zu `max_new` neue Routen mit
negativen reduzierten Kosten.

**Heuristisches Pricing** (`limit` = L): Zuerst läuft das Preisproblem mit Etikettenlimit L. Findet es mindestens eine neue Spalte, kommt sie in den Master. Findet es keine, läuft das
exakte Preisproblem; **die Spaltenerzeugung endet erst, wenn das exakte Preisproblem keine neue Spalte findet** (dann ist die Schranke bewiesen). Ohne Limit läuft jede Runde exakt.

Zwei Master-Löser: `master_highs` (HiGHS über scipy, für Zufallsinstanzen) und `master_exact` (Brüche, Simplex auf dem dualen Problem; für das Handbeispiel, damit die Dualpreise
der Handrechnung eindeutig sind: HiGHS wählt bei entarteten Master-Problemen andere der gleichwertigen Dualpreise)."""

import time
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np
from scipy.optimize import linprog

import hpr_algorithm as A
from hpr_scenario import Instance


def master_highs(inst: Instance, columns) -> tuple:
    """Löst den Überdeckungs-Master über den gegebenen Spalten (Routen) mit HiGHS und gibt (Zielwert, Dualpreise mit pi[0] = 0) zurück."""
    n = inst.n
    costs = [A.route_cost(inst, r) for r in columns]
    mat = np.zeros((n, len(columns)))
    for c, r in enumerate(columns):
        for i in r:
            mat[i - 1, c] += 1
    res = linprog(costs, A_ub=-mat, b_ub=-np.ones(n), bounds=(0, None), method="highs")
    return float(res.fun), [0.0] + [float(x) for x in -res.ineqlin.marginals]


def master_exact(inst: Instance, columns) -> tuple:
    """Löst den Überdeckungs-Master exakt mit Brüchen und gibt (Zielwert, Dualpreise mit pi[0] = 0) als Zahlen zurück.

    Gelöst wird das duale Problem max sum(pi) mit sum(pi_i, i in Route) <= Kosten der Route, pi >= 0 (Simplex-Tableau, kleinster Index tritt ein; bei gleichem Verhältnis
    verlässt die Zeile mit der kleineren Basisvariablen das Tableau). Gedacht für kleine Beispiele (Handbeispiel); die Dualpreise des optimalen Tableaus sind die Dualpreise des Masters."""
    n = inst.n
    m = len(columns)
    ncol = n + m
    tab = []
    for ri, r in enumerate(columns):
        row = [Fraction(0)] * (ncol + 1)
        for i in r:
            row[i - 1] = Fraction(1)
        row[n + ri] = Fraction(1)
        row[ncol] = Fraction(A.route_cost(inst, r))
        tab.append(row)
    obj = [Fraction(1)] * n + [Fraction(0)] * (m + 1)
    basis = [n + r for r in range(m)]
    while True:
        enter = next((j for j in range(ncol) if obj[j] > 0), None)
        if enter is None:
            break
        best = None
        for r in range(m):
            if tab[r][enter] > 0:
                ratio = tab[r][ncol] / tab[r][enter]
                if best is None or ratio < best[0] or (ratio == best[0] and basis[r] < basis[best[1]]):
                    best = (ratio, r)
        r = best[1]
        pv = tab[r][enter]
        tab[r] = [x / pv for x in tab[r]]
        for rr in range(m):
            if rr != r and tab[rr][enter] != 0:
                f = tab[rr][enter]
                tab[rr] = [a - f * b for a, b in zip(tab[rr], tab[r])]
        f = obj[enter]
        obj = [a - f * b for a, b in zip(obj, tab[r])]
        basis[r] = enter
    sol = [Fraction(0)] * ncol
    for r in range(m):
        sol[basis[r]] = tab[r][ncol]
    return float(-obj[ncol]), [0.0] + [float(x) for x in sol[:n]]


MASTERS = {"highs": master_highs, "exakt": master_exact}


@dataclass
class Round:
    """Eine Runde der Spaltenerzeugung: Zielwert und Dualpreise des Masters, was das Preisproblem tat und fand."""

    nr: int
    z: float
    pi: tuple
    labels_limit: int          # Labels des Limit-Aufrufs (0 ohne Limit)
    labels_exact: int          # Labels des exakten Aufrufs (0, wenn das Limit reichte)
    limit_found: bool          # das Limit-Pricing fand mindestens eine neue Spalte
    new: list = field(default_factory=list)   # [(reduzierte Kosten, Route)] der neuen Spalten (leer in der letzten Runde)


@dataclass
class Colgen:
    """Ergebnis einer Spaltenerzeugung. `bound` ist None bei Abbruch am Labelbudget. Sekunden nur zur Information (Wanduhr)."""

    bound: float | None
    iters: int
    cols: int
    labels: int
    labels_heur: int
    labels_exact: int
    dominated: int
    limited: int
    heur_ok: int               # Runden, in denen das Limit-Pricing mindestens eine neue Spalte fand
    exact_calls: int
    aborted: bool
    rounds: list
    t_master: float
    t_heur: float
    t_exact: float
    t_total: float


def colgen(inst: Instance, k: int, limit=None, max_new: int = 15, master: str = "highs", max_iter: int = 400, max_labels_call=None, max_labels_total=None) -> Colgen:
    """Spaltenerzeugung, exakt (`limit` None) oder heuristisch zuerst (`limit` = L). `max_new`: neue Spalten je Runde. Labelbudgets: je Aufruf und über alle Runden (None = unbegrenzt)."""
    solve_master = MASTERS[master]
    n = inst.n
    cols = [(i,) for i in range(1, n + 1)]
    colset = set(cols)
    t0 = time.perf_counter()
    t_m = t_h = t_e = 0.0
    labels_h = labels_e = dominated = limited = heur_ok = exact_calls = 0
    rounds = []
    aborted = False
    it = 0
    z = None
    while it < max_iter:
        it += 1
        w = time.perf_counter()
        z, pi = solve_master(inst, cols)
        t_m += time.perf_counter() - w
        rnd = Round(it, z, tuple(pi), 0, 0, False)
        rounds.append(rnd)
        fresh = []
        if limit is not None:
            w = time.perf_counter()
            res = A.price(inst, pi, k, limit=limit, max_routes=max_new, max_labels=max_labels_call)
            t_h += time.perf_counter() - w
            labels_h += res.generated
            dominated += res.dominated
            limited += res.limited
            rnd.labels_limit = res.generated
            if res.aborted:
                aborted = True
                break
            fresh = [(rc, r) for rc, r in res.routes if r not in colset]
            rnd.limit_found = bool(fresh)
            heur_ok += 1 if fresh else 0
        if not fresh:
            w = time.perf_counter()
            res = A.price(inst, pi, k, max_routes=max_new, max_labels=max_labels_call)
            t_e += time.perf_counter() - w
            labels_e += res.generated
            dominated += res.dominated
            exact_calls += 1
            rnd.labels_exact = res.generated
            if res.aborted:
                aborted = True
                break
            fresh = [(rc, r) for rc, r in res.routes if r not in colset]
        if max_labels_total is not None and labels_h + labels_e > max_labels_total:
            aborted = True
            break
        rnd.new = fresh
        if not fresh:
            break
        for _, r in fresh:
            cols.append(r)
            colset.add(r)
    return Colgen(None if aborted else z, it, len(cols), labels_h + labels_e, labels_h, labels_e, dominated, limited, heur_ok, exact_calls, aborted, rounds, t_m, t_h, t_e,
                  time.perf_counter() - t0)
