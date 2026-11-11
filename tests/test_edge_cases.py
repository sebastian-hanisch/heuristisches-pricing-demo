"""Randfälle, an denen Kernroutinen erfahrungsgemäß brechen (DEMO-PLAYBOOK §12): ein und zwei Kunden, Limit 1 und Limit größer als alles, Instanz ohne negative Route (sofort exakt),
Gleichstand, Kapazität unter jeder Last, Zeitfenster unerreichbar, Gedächtnis 1, Labelbudget 0."""

import pytest

import hpr_algorithm as A
import hpr_colgen as G
from hpr_scenario import Instance, make_instance


def _line(points_x, demand=None, ready=None, due=None, capacity=100, horizon=1000.0, service=1.0):
    """Instanz auf einer Geraden: Depot bei x = 0, Kunden bei den angegebenen Stellen; Entfernung = Fahrzeit = Abstand auf der Geraden."""
    pts = [(0.0, 0.0)] + [(float(x), 0.0) for x in points_x]
    n = len(points_x)
    d = tuple(tuple(abs(a[0] - b[0]) for b in pts) for a in pts)
    return Instance(n, tuple(pts), d, tuple([0] + (demand or [1] * n)), tuple([0.0] + (ready or [0.0] * n)), tuple([horizon] + (due or [horizon] * n)), service, horizon, capacity)


def test_one_customer():
    """n = 1: ein Kunde, eine Route; Bei großem Dualpreis hat sie negative reduzierte Kosten, die Schranke ist die Länge der Einzelroute."""
    inst = _line([5])
    pi = [0.0, 20.0]
    assert A.price(inst, pi, 1).best == (10.0 - 20.0, (1,))
    assert A.price(inst, pi, 1, limit=1).best == (-10.0, (1,))
    for limit in (None, 1, 5):
        c = G.colgen(inst, 1, limit=limit)
        assert c.bound == pytest.approx(10.0) and c.iters == 1 and c.cols == 1 and c.exact_calls == 1


def test_exactly_two_customers():
    """n = 2: der kleinste Fall mit einer Entscheidung zwischen zwei Reihenfolgen."""
    inst = _line([4, 6])
    c = G.colgen(inst, 2, limit=None)
    assert c.bound == pytest.approx(12.0)                                    # eine Route 0-4-6-0 mit Länge 12 überdeckt beide Kunden
    c1 = G.colgen(inst, 2, limit=1)
    assert c1.bound == pytest.approx(12.0) and c1.rounds[-1].labels_exact > 0
    res = A.price(inst, [0.0, 8.0, 12.0], 2, max_routes=10)
    assert [r for _, r in res.routes][0] == (1, 2) and res.best[0] == pytest.approx(12 - 20)


def test_no_route_with_negative_reduced_costs_means_one_round_and_one_exact_call():
    """Dualpreise 0: keine Route hat negative reduzierte Kosten (beide Pricing-Arten finden nichts). Ein Kunde: Die erste Runde findet mit Limit nichts, der exakte Aufruf in derselben Runde
    auch: eine Runde, ein exakter Aufruf, das Limit reichte nie."""
    inst = make_instance(10, 1, 100)
    pi = [0.0] * 11
    assert A.price(inst, pi, 8).routes == [] and A.price(inst, pi, 8, limit=3).routes == []
    c = G.colgen(_line([5]), 1, limit=2)
    assert (c.iters, c.exact_calls, c.heur_ok, c.rounds[0].limit_found) == (1, 1, 0, False)
    assert c.rounds[0].labels_limit > 0 and c.rounds[0].labels_exact > 0 and c.labels == c.rounds[0].labels_limit + c.rounds[0].labels_exact


def test_limit_one_and_a_limit_larger_than_everything():
    inst = make_instance(12, 2, 100)
    pi = [0.0] + [2 * inst.d[0][i] for i in range(1, 13)]
    exact = A.price(inst, pi, 8, max_routes=10 ** 6)
    huge = A.price(inst, pi, 8, limit=10 ** 9, max_routes=10 ** 6)
    assert (huge.generated, huge.dominated, huge.limited, huge.routes, huge.live) == (exact.generated, exact.dominated, 0, exact.routes, exact.live)
    one = A.price(inst, pi, 8, limit=1, max_routes=10 ** 6)
    assert one.limited > 0 and one.generated < exact.generated
    counts = {}
    for _node, *_ in one.live:
        counts[_node] = counts.get(_node, 0) + 1
    assert max(counts.values()) <= 1                                         # Limit 1: höchstens ein lebendes Label je Kunde


def test_the_limit_never_leaves_more_live_labels_than_allowed_at_a_customer():
    inst = make_instance(15, 4, 100)
    pi = [0.0] + [2 * inst.d[0][i] for i in range(1, 16)]
    for limit in (2, 3, 7):
        res = A.price(inst, pi, 8, limit=limit, max_routes=10)
        counts = {}
        for node, *_ in res.live:
            counts[node] = counts.get(node, 0) + 1
        assert max(counts.values()) <= limit


def test_tie_in_costs_prefers_the_documented_label():
    """Gleichstand der Kosten: Zwei lebende Labels mit gleichen Kosten, ein neues Label mit kleineren Kosten: das früher eingefügte fliegt (Regel des Kerns)."""
    labels = [[0.0, -2.0, 1, 0b10, 1, -1, False, 1], [0.0, -2.0, 1, 0b100, 1, -1, False, 2]]
    assert A.limit_victim(labels, [0, 1], -3.0) == 0


def test_capacity_below_every_demand_and_unreachable_windows_give_no_route():
    inst = _line([5, 9], demand=[5, 7], capacity=4)
    assert A.price(inst, [0.0, 99.0, 99.0], 2).routes == []
    late = _line([5, 9], due=[2.0, 3.0])                                      # frühestens bei Zeit 5 und 9 am Kunden: Fenster zu früh zu
    assert A.price(late, [0.0, 99.0, 99.0], 2).routes == []


def test_arrival_exactly_at_the_horizon_and_exactly_at_the_window_end_are_allowed():
    inst = _line([5], horizon=11.0, due=[5.0])          # Hinfahrt 5, Bedienzeit 1, Rückfahrt 5: Rückkehr genau zur Zeit 11 = Horizont; Ankunft genau 5 = spätester Beginn
    assert A.price(inst, [0.0, 99.0], 1).best == (10.0 - 99.0, (1,))
    too_late = _line([5], horizon=10.9, due=[5.0])
    assert A.price(too_late, [0.0, 99.0], 1).routes == []
    too_early = _line([5], horizon=11.0, due=[4.9])
    assert A.price(too_early, [0.0, 99.0], 1).routes == []


def test_memory_of_one_forbids_only_the_immediate_return():
    inst = _line([2, 3, 4])
    res = A.price(inst, [0.0, 50.0, 50.0, 50.0], 1, max_routes=10 ** 6)
    routes = {r for _, r in res.routes}
    assert any(len(r) > len(set(r)) for r in routes)                       # mit k = 1 sind Wiederholungen nach einem Zwischenkunden erlaubt
    assert all(a != b for r in routes for a, b in zip(r, r[1:]))            # nie sofort


def test_label_budget_zero_aborts_at_the_first_label():
    inst = make_instance(8, 0, 100)
    res = A.price(inst, [0.0] + [2 * inst.d[0][i] for i in range(1, 9)], 8, max_labels=0)
    assert res.aborted and res.generated == 1 and res.routes == []
