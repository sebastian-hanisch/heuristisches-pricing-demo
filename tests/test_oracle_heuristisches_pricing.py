"""Orakel (ORACLE-PLAYBOOK §2): das Label-Verfahren mit und ohne Etikettenlimit und die Spaltenerzeugung gegen einen anderen Rechenweg.

1. `ref_price` (tests/ref_labeling.py): anders geschriebenes Label-Verfahren (Mengen und Listen statt Bitmasken) liefert dieselben Zähler, dieselben lebenden Labels und dieselben Routen
   an kleinen Zufallsinstanzen (7 Kunden, Gedächtnis 1, 3 und 7, Limit 1, 2, 3, 5 und ohne).
2. Aufzählung aller Routen durch Tiefensuche (ohne Labels): Das exakte Pricing mit elementarem Gedächtnis findet die beste Route der Aufzählung, jede gelieferte Route ist zulässig und hat
   korrekt nachgerechnete reduzierte Kosten; jedes Limit liefert nie eine bessere Route als die beste der Aufzählung.
3. Die Spaltenerzeugung (immer exakt und mit Limit) endet bei dem LP-Optimum über ALLE aufgezählten Routen (SciPy, HiGHS), wenn das Gedächtnis elementar ist (n = 6); bei kleinerem Gedächtnis
   ist die Schranke höchstens so groß (Relaxierung).
Läuft in wenigen Sekunden; die große Fassung (über 200 Instanzen) lief beim Bau außerhalb des Repos."""

import random

import pytest

import hpr_algorithm as A
import hpr_colgen as G
from hpr_scenario import make_instance
from ref_labeling import lp_over_routes, ref_all_routes, ref_price, route_rc

LIMITS = (None, 1, 2, 3, 5)


def _duals(inst, seed):
    rng = random.Random(seed)
    return [0.0] + [2 * inst.d[0][i] * rng.uniform(0.6, 1.5) for i in range(1, inst.n + 1)]


def _small(seed, n=7, width=100):
    return make_instance(n, seed, width, clustered=(seed % 2 == 1))


def test_the_kernel_equals_the_reference_in_counters_live_labels_and_routes():
    differ_by_limit = 0
    for seed in range(30):
        inst = _small(seed)
        pi = _duals(inst, seed)
        base = None
        for k in (1, 3, 7):
            for limit in LIMITS:
                mine = A.price(inst, pi, k, limit=limit, max_routes=10 ** 6)
                ref = ref_price(inst, pi, k, limit)
                assert (mine.generated, mine.dominated, mine.limited) == (ref["generated"], ref["dominated"], ref["limited"]), (seed, k, limit)
                assert {(node, t, c, q, tuple(i for i in range(1, 8) if (m >> i) & 1)) for node, t, c, q, m in mine.live} == ref["live"], (seed, k, limit)
                assert [round(rc, 9) for rc, _ in mine.routes] == [round(rc, 9) for rc, _ in ref["routes"]] and [r for _, r in mine.routes] == [r for _, r in ref["routes"]]
                if k == 7 and limit is None:
                    base = mine
                if k == 7 and limit is not None and base is not None and (mine.generated != base.generated or mine.best != base.best):
                    differ_by_limit += 1
    assert differ_by_limit > 0                                              # Zweig-Test: das Limit weicht auf mindestens einer Instanz vom exakten Pricing ab


def test_exact_pricing_finds_the_best_route_of_the_enumeration_and_every_route_is_correct():
    for seed in range(30):
        inst = _small(seed, n=6)
        pi = _duals(inst, seed + 100)
        routes = ref_all_routes(inst)
        best = min((route_rc(inst, pi, r) for r in routes), default=0.0)
        res = A.price(inst, pi, 6, max_routes=10 ** 6)
        if best < -1e-7:
            assert res.best is not None and res.best[0] == pytest.approx(best, abs=1e-9), seed
        else:
            assert res.best is None, seed
        enumerated = {tuple(r) for r in routes}
        for rc, r in res.routes:
            assert r in enumerated and rc == pytest.approx(route_rc(inst, pi, r), abs=1e-9) and rc < 0
        for limit in (1, 2, 3, 5):
            lim = A.price(inst, pi, 6, limit=limit, max_routes=10 ** 6)
            assert all(r in enumerated and rc == pytest.approx(route_rc(inst, pi, r), abs=1e-9) for rc, r in lim.routes)
            if lim.best is not None:
                assert lim.best[0] >= best - 1e-9                           # kein Limit findet etwas Besseres als die beste Route


def test_column_generation_ends_at_the_lp_optimum_over_all_routes_for_every_variant():
    checked = 0
    for seed in range(10):
        inst = make_instance(6, seed, 100, clustered=(seed % 2 == 1))
        routes = ref_all_routes(inst)
        lp = lp_over_routes(inst, routes)
        for limit in (None, 1, 2, 5):
            c = G.colgen(inst, 6, limit=limit)
            assert c.bound == pytest.approx(lp, rel=1e-9, abs=1e-9), (seed, limit)
            checked += 1
        relaxed = G.colgen(inst, 2, limit=None)
        assert relaxed.bound <= lp + 1e-9                                  # kleineres Gedächtnis: Relaxierung, Schranke höchstens so groß
    assert checked == 40


def test_the_duals_of_every_round_are_feasible_for_the_columns_and_optimal():
    inst = make_instance(10, 4, 100)
    for limit in (None, 5):
        c = G.colgen(inst, 8, limit=limit)
        cols = [(i,) for i in range(1, 11)]
        for rnd in c.rounds:
            pi = rnd.pi
            assert all(x >= -1e-9 for x in pi)
            assert all(sum(pi[i] for i in r) <= A.route_cost(inst, r) + 1e-7 for r in cols)
            assert sum(pi) == pytest.approx(rnd.z, rel=1e-9)
            assert G.master_highs(inst, cols)[0] == pytest.approx(rnd.z, rel=1e-9)
            cols += [r for _, r in rnd.new]


def test_the_exact_master_equals_highs_in_value_on_random_column_sets():
    for seed in range(15):
        inst = make_instance(6, seed, 100)
        routes = ref_all_routes(inst)
        rng = random.Random(seed)
        cols = [(i,) for i in range(1, 7)] + rng.sample([tuple(r) for r in routes], min(12, len(routes)))
        z_exact, pi = G.master_exact(inst, cols)
        z_highs, _ = G.master_highs(inst, cols)
        assert z_exact == pytest.approx(z_highs, rel=1e-9)
        assert all(sum(pi[i] for i in r) <= A.route_cost(inst, r) + 1e-9 for r in cols) and sum(pi) == pytest.approx(z_exact)
