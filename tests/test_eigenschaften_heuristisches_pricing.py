"""Eigenschaftstests (metamorph, ORACLE-PLAYBOOK §5.2): Aussagen, die für das Verfahren gelten müssen, ohne dass man das richtige Ergebnis kennt.

- Ein Limit größer als jede Zahl lebender Labels ändert nichts (gleiche Zähler, Routen, lebende Labels wie exakt).
- Die Endschranke hängt nicht vom Limit ab (alle Limits, alle Instanzen); die letzte Runde ist immer ein exaktes Pricing ohne neue Spalte.
- Umnummerieren der Kunden ändert die Endschranke und die beste Route des exakten Pricings nicht.
- Jede gelieferte Route ist zulässig und hat korrekt nachgerechnete negative reduzierte Kosten (`check_route`), auch mit Limit.
- Das Limit kann den besten Weg einer Runde verfehlen, nie aber die Endschranke ändern.
- Die Zähler hängen nicht an der Hash-Randomisierung (zweiter Prozess mit anderem PYTHONHASHSEED).
Je Eigenschaft 12 bis 30 Instanzen mit festem Seed."""

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

import hpr_algorithm as A
import hpr_colgen as G
from hpr_scenario import Instance, make_instance

ROOT = Path(__file__).resolve().parent.parent


def _pi(inst, factor=1.0):
    return [0.0] + [factor * 2 * inst.d[0][i] for i in range(1, inst.n + 1)]


def test_a_huge_limit_changes_nothing():
    for seed in range(20):
        inst = make_instance(9, seed, 100, clustered=(seed % 2 == 1))
        pi = _pi(inst, 1.2)
        exact = A.price(inst, pi, 6, max_routes=10 ** 6)
        huge = A.price(inst, pi, 6, limit=10 ** 6, max_routes=10 ** 6)
        assert (huge.generated, huge.dominated, huge.routes, huge.live) == (exact.generated, exact.dominated, exact.routes, exact.live) and huge.limited == 0


def test_the_end_bound_does_not_depend_on_the_limit_and_the_last_round_is_exact():
    for seed in range(12):
        inst = make_instance(14, seed, 100, clustered=(seed % 2 == 1))
        exact = G.colgen(inst, 8, limit=None)
        for limit in (1, 2, 5, 10, 20):
            heur = G.colgen(inst, 8, limit=limit)
            assert heur.bound == pytest.approx(exact.bound, rel=1e-9), (seed, limit)
            last = heur.rounds[-1]
            assert last.labels_exact > 0 and last.new == [] and heur.exact_calls >= 1


def test_the_end_bound_and_the_best_route_do_not_depend_on_the_numbering_of_the_customers():
    for seed in range(12):
        inst = make_instance(12, seed, 100, clustered=(seed % 2 == 1))
        perm = list(range(1, 13))
        random.Random(seed).shuffle(perm)
        pts = [inst.points[0]] + [inst.points[old] for old in perm]
        d = tuple(tuple(inst.d[a][b] for b in [0] + perm) for a in [0] + perm)
        ren = Instance(12, tuple(pts), d, (0,) + tuple(inst.demand[o] for o in perm), (0.0,) + tuple(inst.ready[o] for o in perm), (inst.due[0],) + tuple(inst.due[o] for o in perm),
                       inst.service, inst.horizon, inst.capacity)
        pi = _pi(inst, 1.1)
        pi_ren = [0.0] + [pi[o] for o in perm]
        a = A.price(inst, pi, 12, max_routes=5)
        b = A.price(ren, pi_ren, 12, max_routes=5)
        assert a.best[0] == pytest.approx(b.best[0], abs=1e-9)
        assert G.colgen(inst, 12, limit=None).bound == pytest.approx(G.colgen(ren, 12, limit=None).bound, rel=1e-7)


def test_every_route_of_every_pricing_call_is_feasible_and_has_the_reported_reduced_costs():
    for seed in range(15):
        inst = make_instance(12, seed, 100, clustered=(seed % 2 == 1))
        pi = _pi(inst, 1.15)
        for limit in (None, 1, 3, 10):
            for rc, route in A.price(inst, pi, 8, limit=limit, max_routes=50).routes:
                check = A.check_route(inst, pi, route)
                assert check is not None and check == pytest.approx(rc, abs=1e-7) and rc < 0, (seed, limit, route)
                assert all(a != b for a, b in zip(route, route[1:]))                           # Gedächtnis 8: nie sofort derselbe Kunde


def test_the_limit_can_miss_the_best_route_of_a_round_but_never_changes_the_end_bound():
    missed = 0
    for seed in range(30):
        inst = make_instance(14, seed, 100, clustered=(seed % 2 == 1))
        pi = _pi(inst, 1.2)
        best = A.price(inst, pi, 8).best
        lim = A.price(inst, pi, 8, limit=1).best
        if best is not None and (lim is None or lim[0] > best[0] + 1e-9):
            missed += 1
        if lim is not None:
            assert best is not None and lim[0] >= best[0] - 1e-9                              # nie besser als exakt
    assert missed > 0                                                                         # Zweig-Test: Limit 1 verfehlt auf mindestens einer Instanz den besten Weg
    for seed in (0, 1, 2):
        inst = make_instance(14, seed, 100)
        assert G.colgen(inst, 8, limit=1).bound == pytest.approx(G.colgen(inst, 8, limit=None).bound, rel=1e-9)


SCRIPT = """
import json, sys
sys.path.insert(0, sys.argv[1])
import hpr_colgen as G
from hpr_scenario import make_instance
out = []
for seed in (0, 1, 2):
    inst = make_instance(12, seed, 100, clustered=(seed == 1))
    for limit in (None, 5):
        c = G.colgen(inst, 8, limit=limit)
        out.append([c.iters, c.labels, c.labels_heur, c.exact_calls, c.heur_ok, round(c.bound, 6)])
print(json.dumps(out))
"""


def test_counters_do_not_depend_on_the_hash_randomisation():
    results = []
    for hash_seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed, PYTHONIOENCODING="utf-8")
        out = subprocess.run([sys.executable, "-c", SCRIPT, str(ROOT)], capture_output=True, text=True, env=env, timeout=120, check=True).stdout
        results.append(json.loads(out))
    assert results[0] == results[1] and len(results[0]) == 6
