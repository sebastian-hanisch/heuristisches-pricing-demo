"""Kern gegen die Handrechnung am Handbeispiel (Mini-Instanz in conftest.py) und je Einheit: Dominanzregel, Limitregel, Routenprüfer, Gedächtnis, Spaltenerzeugung, Master.

Die Handrechnung steht als Rechnung da (Abstände minus Dualpreise), nicht als abgeschriebenes Ergebnis. Die Zahlen der Planung (Handrechnung mit Brüchen) sind: 66 / 23 / 30 / 36 Labels im ersten
Preisproblem (ohne Limit, Limit 1, 2, 3), 65 zulässige Routen, immer exakt 5 Runden und 280 Labels, Limit 1 sechs Runden und 190 Labels, Endschranke 38."""

import pytest

import hpr_algorithm as A
import hpr_colgen as G
import hpr_constants as C
import hpr_evaluation as ev
from conftest import HAND_TABLE, build_hand, manhattan
from hpr_scenario import hand_first_duals, hand_instance, make_instance, ng_masks
from ref_labeling import lp_over_routes, ref_all_routes


def _d(a, b):
    return manhattan(HAND_TABLE[a][0], HAND_TABLE[b][0])


# --- Handbeispiel: Daten ----------------------------------------------------------------------------------------------------------------------

def test_the_scenario_module_equals_the_hand_table(hand):
    inst, pi = hand
    h = hand_instance()
    assert (h.n, h.points, h.d, h.demand, h.ready, h.due, h.service, h.horizon, h.capacity) == (inst.n, inst.points, inst.d, inst.demand, inst.ready, inst.due, inst.service, inst.horizon, inst.capacity)
    assert hand_first_duals() == pi == (0, 6, 10, 10, 12, 14, 12)


def test_the_hand_duals_are_the_lengths_of_the_single_routes():
    assert [2 * _d(0, i) for i in range(1, 7)] == [6, 10, 10, 12, 14, 12]


# --- Handbeispiel: erstes Preisproblem ----------------------------------------------------------------------------------------------------------

def test_the_best_route_has_the_hand_calculated_reduced_costs(hand):
    inst, pi = hand
    length = _d(0, 3) + _d(3, 5) + _d(5, 6) + _d(6, 0)        # 5 + 2 + 1 + 6
    assert length == 14 and length - (pi[3] + pi[5] + pi[6]) == 14 - 36 == -22
    assert A.check_route(inst, pi, (3, 5, 6)) == -22
    res = A.price(inst, pi, 6, max_routes=100)
    assert res.best == (-22.0, (3, 5, 6)) and res.routes[1] == (-22.0, (3, 6, 5))


@pytest.mark.parametrize("limit,generated,limited", [(None, 66, 0), (1, 23, 11), (2, 30, 13), (3, 36, 15)])
def test_label_counts_of_the_first_pricing_call_as_in_the_hand_calculation(hand, limit, generated, limited):
    inst, pi = hand
    res = A.price(inst, pi, 6, limit=limit, max_routes=10 ** 6, trace=True)
    assert (res.generated, res.limited) == (generated, limited)
    assert len(res.events) == generated - 1                         # ein Ereignis je neues Label, das Start-Label zählt nicht


def test_limit_1_misses_the_best_route_and_limit_2_finds_it(hand):
    inst, pi = hand
    assert A.price(inst, pi, 6, limit=1, max_routes=100).best == (-12.0, (3, 1, 5))
    assert A.price(inst, pi, 6, limit=2, max_routes=100).best == (-22.0, (3, 5, 6))
    assert A.price(inst, pi, 6, limit=3, max_routes=100).best == (-22.0, (3, 5, 6))


def test_the_displacement_of_f14_by_f21_with_the_reason_from_the_hand_calculation(hand):
    inst, pi = hand
    by_nr = {e["nr"]: e for e in A.price(inst, pi, 6, limit=1, max_routes=100, trace=True).events}
    f14, f21 = by_nr[14], by_nr[21]
    assert (f14["node"], f14["path"], f14["load"]) == (5, (3, 5), 4 + 2)
    assert f14["cost"] == _d(0, 3) + _d(3, 5) - (pi[3] + pi[5]) == 7 - 24 == -17
    assert (f21["node"], f21["path"], f21["load"]) == (5, (3, 1, 5), 4 + 2 + 2)
    assert f21["cost"] == _d(0, 3) + _d(3, 1) + _d(1, 5) - (pi[3] + pi[1] + pi[5]) == 11 - 30 == -19
    assert f21["victim"] == 14 and f21["status"] == "behalten" and -19 < -17          # das billigere Label verdrängt das teurere
    assert f21["load"] + inst.demand[6] == 11 > inst.capacity and f14["load"] + inst.demand[6] == 9 <= inst.capacity
    story = ev.displacement_story(1)
    assert story["reason"] == "Last 8 + 3 = 11 > 10" and story["victim_can"] is True and (story["victim"], story["newcomer"], story["next"]) == (14, 21, 6)
    assert ev.displacement_story(2) is None and ev.displacement_story(3) is None


def test_every_event_status_occurs_and_the_dominance_text_names_the_killer(hand):
    inst, pi = hand
    events = A.price(inst, pi, 6, limit=1, max_routes=10, trace=True).events
    statuses = {e["status"] for e in events}
    assert statuses == {"behalten", "dominiert"}                        # Limit 1: das neue Label ist in diesem Beispiel immer billiger als das lebende, es fliegt nie
    dominated = next(e for e in events if e["status"] == "dominiert")
    assert dominated["nr"] == 8 and dominated["killer"] == 4            # F08 (Weg 2, 4; Kosten -6) wird von F04 (Weg 4; Kosten -6) dominiert: gleiche Kosten, gleiche Zeit, weniger Last


def test_the_new_label_can_be_the_one_that_flies_and_the_text_says_so():
    """Im Handbeispiel kommt „das neue Label fliegt“ im ersten Preisproblem nicht vor; auf kleinen Zufallsinstanzen mit Limit 2 schon (Entscheidung „limit-neu“, mit dem Label, das bleibt)."""
    found = None
    for seed in range(60):
        inst = make_instance(8, seed, 100)
        pi = [0.0] + [2 * inst.d[0][i] for i in range(1, 9)]
        res = A.price(inst, pi, 8, limit=2, max_routes=10, trace=True)
        found = next((e for e in res.events if e["status"] == "limit-neu"), None)
        if found:
            by_nr = {e["nr"]: e for e in res.events}
            assert found["worst"] != found["nr"] and by_nr[found["worst"]]["cost"] <= found["cost"]      # das lebende Label ist nicht teurer als das neue
            assert "das neue fliegt" in ev.event_decision(found, by_nr)
            break
    assert found is not None


# --- Handbeispiel: Spaltenerzeugung -----------------------------------------------------------------------------------------------------------

def test_the_number_of_feasible_routes_and_the_lp_over_all_routes(hand):
    inst, _ = hand
    routes = ref_all_routes(inst)
    assert len(routes) == 65
    assert lp_over_routes(inst, routes) == pytest.approx(38.0)
    z, duals = G.master_exact(inst, [tuple(r) for r in routes])
    assert z == 38.0 and tuple(duals) == (0.0, 3.0, 10.0, 5.0, 11.0, 5.0, 4.0)


def test_exact_column_generation_of_the_hand_example_as_in_the_hand_calculation():
    c = G.colgen(hand_instance(), 6, limit=None, max_new=3, master="exakt")
    assert (c.iters, c.bound, c.labels, c.exact_calls, c.heur_ok) == (5, 38.0, 280, 5, 0)
    assert [r.labels_exact for r in c.rounds] == [66, 55, 52, 53, 54] and sum(r.labels_exact for r in c.rounds) == 280
    assert [r.z for r in c.rounds] == [64.0, 42.0, 38.0, 38.0, 38.0]
    assert c.rounds[0].pi[1:] == (6.0, 10.0, 10.0, 12.0, 14.0, 12.0) and c.rounds[-1].pi[1:] == (3.0, 10.0, 5.0, 11.0, 5.0, 4.0)
    assert [r for _, r in c.rounds[0].new] == [(3, 5, 6), (3, 6, 5), (2, 1, 5, 6)]


def test_limit_1_column_generation_of_the_hand_example_as_in_the_hand_calculation():
    c = G.colgen(hand_instance(), 6, limit=1, max_new=3, master="exakt")
    assert (c.iters, c.bound, c.labels, c.labels_heur, c.labels_exact, c.exact_calls, c.heur_ok) == (6, 38.0, 190, 136, 54, 1, 5)
    assert [r.labels_limit for r in c.rounds] == [23, 23, 20, 25, 23, 22] and c.rounds[-1].labels_exact == 54 and not c.rounds[-1].limit_found
    assert [r.z for r in c.rounds] == [64.0, 52.0, 42.0, 38.0, 38.0, 38.0]


@pytest.mark.parametrize("limit,iters,labels,exact_calls", [(2, 5, 238, 2), (3, 5, 211, 1)])
def test_limits_2_and_3_of_the_hand_example_differ_from_the_planning_log_by_the_tie_rule(limit, iters, labels, exact_calls):
    """Die Handrechnung der Planung ließ bei gleichen größten Kosten das später eingefügte Label fliegen (Limit 2: 188 Labels), der Messcode (und diese Demo) das früher eingefügte.
    Die Endschranke ist in beiden Fällen 38; die Zahlen unten gelten für die Regel dieser Demo."""
    c = G.colgen(hand_instance(), 6, limit=limit, max_new=3, master="exakt")
    assert (c.iters, c.labels, c.exact_calls, c.bound) == (iters, labels, exact_calls, 38.0)


def test_the_tie_rule_changes_the_path_of_the_column_generation_but_not_the_bound(monkeypatch):
    def later(labels, survivors, new_cost):
        worst = max(survivors, key=lambda x: (labels[x][A.COST], x))
        return None if labels[worst][A.COST] <= new_cost else worst

    inst = hand_instance()
    earlier = G.colgen(inst, 6, limit=2, max_new=3, master="exakt")
    big = make_instance(30, 1, 100)
    ref_big = G.colgen(big, 8, limit=5)
    monkeypatch.setattr(A, "limit_victim", later)
    alt = G.colgen(inst, 6, limit=2, max_new=3, master="exakt")
    alt_big = G.colgen(big, 8, limit=5)
    assert (alt.labels, alt.iters, alt.bound) == (188, 5, 38.0) and earlier.labels == 238 and earlier.bound == alt.bound
    # auch in der Zufallsinstanz kommen gleiche größte Kosten vor (Zufalls-Seed 1, Breite 100, Limit 5): 59 713 Labels (Messreihe) gegen 59 711 mit der anderen Regel
    assert (ref_big.labels, alt_big.labels) == (59713, 59711) and ref_big.iters == alt_big.iters and ref_big.bound == pytest.approx(alt_big.bound)


def test_the_master_duals_are_optimal_for_every_round_of_the_hand_example():
    """Die Dualpreise jeder Runde sind zulässig (Summe über eine Route höchstens ihre Länge, nicht negativ) und optimal (Summe gleich dem Zielwert, den HiGHS für dieselben Spalten findet)."""
    inst, _ = build_hand()
    for limit in (None, 1, 2):
        c = G.colgen(inst, 6, limit=limit, max_new=3, master="exakt")
        cols = [(i,) for i in range(1, 7)]
        for rnd in c.rounds:
            costs = {r: sum(_d(a, b) for a, b in zip((0,) + r, r + (0,))) for r in cols}
            assert all(x >= 0 for x in rnd.pi)
            assert all(sum(rnd.pi[i] for i in r) <= costs[r] + 1e-9 for r in cols)
            assert sum(rnd.pi) == pytest.approx(rnd.z)
            assert G.master_highs(inst, cols)[0] == pytest.approx(rnd.z)
            cols += [r for _, r in rnd.new]


# --- Einheiten ----------------------------------------------------------------------------------------------------------------------------------

def _lab(t, c, q, mem):
    return [t, c, q, mem, 1, -1, False, 0]


def test_dominance_rule_each_condition_alone_and_the_tolerance():
    old = _lab(10.0, -5.0, 4, 0b0110)
    assert A.dominates(old, -5.0, 10.0, 4, 0b0110)                     # alles gleich: dominiert (inklusive)
    assert not A.dominates(old, -5.1, 10.0, 4, 0b0110)                 # neues Label billiger
    assert not A.dominates(old, -5.0, 9.0, 4, 0b0110)                  # neues Label früher
    assert not A.dominates(old, -5.0, 10.0, 3, 0b0110)                 # neues Label leichter
    assert not A.dominates(old, -5.0, 10.0, 4, 0b0010)                 # Gedächtnis von old ist keine Teilmenge
    assert A.dominates(old, -5.0, 10.0, 4, 0b1110)                     # Obermenge reicht
    assert A.dominates(old, -5.0 - 5e-10, 10.0, 4, 0b0110) and not A.dominates(old, -5.0 - 5e-9, 10.0, 4, 0b0110)   # Toleranz 1e-9


def test_dominated_by_is_the_mirror_image_of_dominates():
    new = (-6.0, 9.0, 3, 0b0010)
    old = _lab(10.0, -5.0, 4, 0b0110)
    assert A.dominated_by(old, *new) and not A.dominates(old, *new)
    assert not A.dominated_by(old, -4.0, 9.0, 3, 0b0010) and not A.dominated_by(old, -6.0, 11.0, 3, 0b0010)
    assert not A.dominated_by(old, -6.0, 9.0, 5, 0b0010) and not A.dominated_by(old, -6.0, 9.0, 3, 0b1000)


def test_limit_victim_is_the_most_expensive_label_and_the_new_one_flies_on_a_tie():
    labels = [_lab(0, -3.0, 0, 0), _lab(0, -1.0, 0, 0), _lab(0, -5.0, 0, 0), _lab(0, -1.0, 0, 0)]
    assert A.limit_victim(labels, [0, 2], -4.0) == 0                     # -3 ist teurer als das neue Label -4: fliegt
    assert A.limit_victim(labels, [0, 2], -3.0) is None                  # gleiche Kosten: das neue fliegt
    assert A.limit_victim(labels, [0, 2], -2.0) is None                  # das neue ist teurer als alle lebenden: es fliegt
    assert A.limit_victim(labels, [1, 2, 3], -9.0) == 1                  # Gleichstand unter den lebenden: das früher eingefügte fliegt


def test_route_cost_and_the_route_checker(hand):
    inst, pi = hand
    assert A.route_cost(inst, (3,)) == 10 and A.route_cost(inst, (3, 5, 6)) == 14
    assert A.check_route(inst, pi, (3,)) == 10 - 10 == 0
    assert A.check_route(inst, pi, (4, 3)) is None                       # Kunde 3 ist nach Kunde 4 zu spät (Fenster bis 12)
    assert A.check_route(inst, pi, (1, 2, 3, 5)) is None                 # Last 2 + 3 + 4 + 2 = 11 > 10
    assert A.check_route(inst, pi, ()) == 0


def test_ng_neighbourhood_of_the_hand_example(hand):
    inst, _ = hand
    full = ng_masks(inst, 6)
    assert all(full[j] == sum(1 << i for i in range(1, 7)) for j in range(1, 7))        # k = n: elementar
    near = ng_masks(inst, 2)
    nearest = {j: min((i for i in range(1, 7) if i != j), key=lambda i: (inst.d[j][i], i)) for j in range(1, 7)}
    assert all(near[j] == (1 << j) | (1 << nearest[j]) for j in range(1, 7))
    assert ng_masks(inst, 1) == [0] + [1 << j for j in range(1, 7)]


# --- Spaltenerzeugung auf Zufallsinstanzen ---------------------------------------------------------------------------------------------------------

def test_a_small_random_instance_reaches_the_same_bound_with_and_without_limit():
    inst = make_instance(14, 3, 100)
    exact = G.colgen(inst, 8, limit=None)
    for limit in (1, 3, 5, 10, 20):
        heur = G.colgen(inst, 8, limit=limit)
        assert heur.bound == pytest.approx(exact.bound, rel=1e-9), limit
        assert heur.rounds[-1].labels_exact > 0 and not heur.rounds[-1].new      # die letzte Runde ist ein exaktes Pricing ohne neue Spalte


def test_the_master_value_never_rises_and_the_columns_never_repeat():
    inst = make_instance(14, 3, 100)
    for limit in (None, 5):
        c = G.colgen(inst, 8, limit=limit)
        zs = [r.z for r in c.rounds]
        assert all(b <= a + 1e-9 for a, b in zip(zs, zs[1:]))
        seen = [r for rnd in c.rounds for _, r in rnd.new]
        assert len(seen) == len(set(seen)) and c.cols == inst.n + len(seen)


def test_the_label_budget_aborts_and_reports_no_bound():
    inst = make_instance(30, 2, 100, clustered=True)
    c = G.colgen(inst, 8, limit=None, max_labels_total=50_000, max_labels_call=40_000)
    assert c.aborted and c.bound is None
    r = A.price(inst, [0.0] + [2 * inst.d[0][i] for i in range(1, 31)], 8, max_labels=1000)
    assert r.aborted and r.generated <= 1000 + 31


def test_worst_case_at_the_widget_maximum_stays_inside_the_budget():
    """Worst-Case (DEMO-PLAYBOOK §1c): n = 30, Fensterbreite 100, gruppiert, Gedächtnis 8, Limit 20 am Regler-Maximum; die Rechnung bricht am Labelbudget ab oder wird fertig, hängt aber nie.
    Kein Zeitvergleich: nur die Zähler sind begrenzt (Labelbudget je Aufruf und über alle Runden)."""
    exact, heur = ev.live_runs(ev.Settings(C.N_MAX, 100, "cluster", 8, 20, 2))
    assert exact.aborted or exact.labels <= C.MAX_LABELS_COLGEN + C.MAX_LABELS_CALL
    assert heur.aborted or heur.labels <= C.MAX_LABELS_COLGEN + C.MAX_LABELS_CALL
    assert exact.aborted == (exact.bound is None) and heur.aborted == (heur.bound is None)
