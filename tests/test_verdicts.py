"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Zahl im Text und jede Schwelle der Art steht hier.

Ein Verdikt ist eine reine Funktion (Art, Text) und bekommt Zeilen bzw. Ergebnisse, nicht Seeds."""

import hpr_colgen as G
import hpr_evaluation as ev


def _run(bound=100.0, iters=10, labels=1000, labels_heur=0, heur_ok=0, exact_calls=10, aborted=False, t_total=1.0, t_master=0.1, new_first=(-5.0,)):
    first = G.Round(1, 90.0, (0.0, 1.0), 0, 0, False, [(rc, (1,)) for rc in new_first])
    return G.Colgen(None if aborted else bound, iters, 20, labels, labels_heur, labels - labels_heur, 0, 0, heur_ok, exact_calls, aborted, [first], t_master, 0.0, 0.0, t_total)


def test_verdict_bound_three_cases():
    ex = _run()
    assert ev.verdict_bound(ex, _run()) == ("success", "Gleiche Endschranke wie bei immer exaktem Pricing: ja (100,00).")
    kind, text = ev.verdict_bound(ex, _run(bound=100.5))
    assert kind == "error" and "100,5000 gegen 100,0000" in text
    kind, text = ev.verdict_bound(ex, _run(aborted=True))
    assert kind == "warning" and "abgebrochen" in text and "600 000" in text and "300 000" in text


def test_verdict_labels_counts_ratio_and_rounds():
    ex = _run(iters=20, labels=1000, exact_calls=20)
    kind, text = ev.verdict_labels(ex, _run(iters=26, labels=600, labels_heur=450, heur_ok=22, exact_calls=4), 10)
    assert kind == "success"
    assert "Limit 10: 600 Labels gegen 1 000 bei immer exaktem Pricing (Verhältnis 0,60); 6 Runden mehr" in text and "26 statt 20" in text
    assert "Das Limit reichte in 22 von 26 Runden; exakte Aufrufe: 4 statt 20" in text and "davon entstehen 25,0 % der Labels im exakten Pricing" in text
    kind, text = ev.verdict_labels(ex, _run(iters=20, labels=1200, labels_heur=900, heur_ok=19, exact_calls=1), 20)
    assert kind == "warning" and "gleich viele Runden" in text and "Verhältnis 1,20" in text            # mehr Labels als exakt: Warnung
    kind, text = ev.verdict_labels(ex, _run(iters=17, labels=1000, labels_heur=400, heur_ok=16, exact_calls=1), 5)
    assert "3 Runden weniger" in text and kind == "warning"                                             # genau gleich viele Labels: kein Vorteil, also Warnung
    assert ev.verdict_labels(ex, _run(aborted=True), 5)[0] == "warning"


def test_verdict_round1_equal_and_different_best_routes():
    ex = _run(new_first=(-10.0,))
    assert ev.verdict_round1(ex, _run(new_first=(-10.0,)))[1].startswith("In der ersten Runde findet das Limit den besten Weg (reduzierte Kosten −10,00)")
    text = ev.verdict_round1(ex, _run(new_first=(-7.5,)))[1]
    assert "verfehlt das Limit den besten Weg" in text and "−7,50 statt −10,00" in text
    assert "kein Vergleich" in ev.verdict_round1(ex, _run(new_first=()))[1] and "kein Vergleich" in ev.verdict_round1(ex, _run(aborted=True))[1]


def test_verdict_time_threshold_at_five_percent():
    ex = _run(t_total=2.0, t_master=0.4)
    assert "Die Gesamtzeit sinkt: 1,00 s gegen 2,00 s (0,50; davon Master-LP 0,20 s gegen 0,40 s)" in ev.verdict_time(ex, _run(t_total=1.0, t_master=0.2))[1]
    assert "Gesamtzeit gleichauf" in ev.verdict_time(ex, _run(t_total=1.95))[1]                    # 0,975: unter 5 %
    assert "Gesamtzeit gleichauf" in ev.verdict_time(ex, _run(t_total=2.09))[1]                    # 1,045
    assert "Die Gesamtzeit sinkt" in ev.verdict_time(ex, _run(t_total=1.89))[1]                    # 0,945
    assert "Die Gesamtzeit steigt" in ev.verdict_time(ex, _run(t_total=2.2))[1]                    # 1,10
    assert "nur Information" in ev.verdict_time(ex, _run(t_total=1.0))[1] and ev.verdict_time(ex, _run(aborted=True))[0] == "info"


def test_verdict_hand_pricing_found_and_missed():
    rows = [{"limit": None, "name": "ohne Limit (exakt)", "generated": 66, "limited": 0, "n_routes": 48, "best": (-22.0, (3, 5, 6)), "found_best": True},
            {"limit": 1, "name": "Limit 1", "generated": 23, "limited": 11, "n_routes": 5, "best": (-12.0, (3, 1, 5)), "found_best": False},
            {"limit": 2, "name": "Limit 2", "generated": 30, "limited": 13, "n_routes": 10, "best": (-22.0, (3, 5, 6)), "found_best": True},
            {"limit": 3, "name": "Limit 3", "generated": 36, "limited": 15, "n_routes": 0, "best": None, "found_best": False}]
    kind, text = ev.verdict_hand_pricing(rows, 1)
    assert kind == "warning" and "23 statt 66 Labels" in text and "(3 → 1 → 5) mit −12" in text and "5 statt 48 Routen" in text and "Das Limit verfehlt den besten Weg** (3 → 5 → 6 mit −22)" in text
    kind, text = ev.verdict_hand_pricing(rows, 2)
    assert kind == "success" and "Das Limit findet hier den besten Weg (3 → 5 → 6)" in text
    kind, text = ev.verdict_hand_pricing(rows, 3)
    assert kind == "warning" and "keine Route" in text and "48" in text


def test_verdict_hand_loop_equal_bound_rounds_and_error():
    ex = _run(bound=38.0, iters=5, labels=280, exact_calls=5)
    kind, text = ev.verdict_hand_loop(ex, _run(bound=38.0, iters=6, labels=190, labels_heur=136, heur_ok=5, exact_calls=1), 38.0, 1)
    assert kind == "success" and "Limit 1: 190 statt 280 Labels (0,68), 6 statt 5 Runden" in text and "das Limit reichte in 5 von 6 Runden, exakte Aufrufe: 1 statt 5" in text
    assert "gleich viele Runden (5)" in ev.verdict_hand_loop(ex, _run(bound=38.0, iters=5, labels=238, labels_heur=131, heur_ok=3, exact_calls=2), 38.0, 2)[1]
    assert "(weniger)" in ev.verdict_hand_loop(ex, _run(bound=38.0, iters=4, labels=160, labels_heur=110, heur_ok=3, exact_calls=1), 38.0, 2)[1]
    assert ev.verdict_hand_loop(ex, _run(bound=38.0, iters=6, labels=190), 37.0, 1)[0] == "error"                # LP über alle Routen weicht ab
    assert ev.verdict_hand_loop(ex, _run(bound=39.0, iters=6, labels=190), 38.0, 1)[0] == "error"                # Endschranke weicht ab


def test_verdict_kipp_all_some_none():
    stats = {"exakt": dict(n=1, labels=1000, labels_limit=0, labels_exakt=1000, iterationen=10),
             "L5": dict(n=1, labels=500, labels_limit=300, labels_exakt=200, iterationen=20),        # Kipp-Stelle (1000 - 300 - 200) / 10 = 50
             "L10": dict(n=1, labels=600, labels_limit=300, labels_exakt=300, iterationen=15),       # (1000 - 300 - 300) / 5 = 80
             "L20": dict(n=1, labels=800, labels_limit=300, labels_exakt=500, iterationen=12)}       # (1000 - 300 - 500) / 2 = 100
    assert ev.break_even(stats["L5"], stats["exakt"]) == 50 and ev.break_even(stats["L10"], stats["exakt"]) == 80 and ev.break_even(stats["L20"], stats["exakt"]) == 100
    assert ev.break_even(stats["L5"], stats["exakt"], 0.5) == (1000 - 150 - 200) / 10 == 65
    assert ev.break_even(dict(stats["L5"], iterationen=10), stats["exakt"]) is None
    kind, text = ev.verdict_kipp(stats, 40, 1.0)
    assert kind == "success" and text.startswith("Bei 40 Labels je Master-LP und Kosten 1,00 je Limit-Label (beides Annahmen) lohnen sich im Modell alle drei Limits")
    kind, text = ev.verdict_kipp(stats, 60, 1.0)
    assert kind == "info" and "lohnen sich im Modell L10, L20; nicht mehr L5" in text
    kind, text = ev.verdict_kipp(stats, 90, 1.0)
    assert kind == "info" and "lohnen sich im Modell L20; nicht mehr L5, L10" in text
    kind, text = ev.verdict_kipp(stats, 1000, 1.0)
    assert kind == "warning" and "keines der drei Limits" in text
    assert ev.verdict_kipp(stats, 60, 0.5)[0] == "success"                       # billigere Limit-Labels verschieben die Kipp-Stellen nach oben (65, 110, 175)
    assert ev.model_ratio(stats["L5"], stats["exakt"], 50) == 1.0                # bei der Kipp-Stelle gleich teuer: 300 + 200 + 50 * 20 = 1500 = 1000 + 50 * 10


def test_verdict_bands_counts_and_kind():
    def lauf(typ, seed, v, labels, schranke=10.0):
        return {"typ": typ, "breite": 100, "seed": seed, "variante": v, "labels": labels, "iterationen": 10 if v == "exakt" else 12, "limit_reichte": 0 if v == "exakt" else 8,
                "exakte_aufrufe": 10 if v == "exakt" else 4, "labels_exakt": labels if v == "exakt" else labels // 2, "schranke": schranke}
    rows = []
    for seed, (lx, l5) in enumerate([(1000, 500), (2000, 1400)]):
        rows += [lauf("zufall", seed, "exakt", lx), lauf("zufall", seed, "L5", l5), lauf("zufall", seed, "L10", l5), lauf("zufall", seed, "L20", l5)]
    kind, text = ev.verdict_bands(rows, 100, None, "L5")
    assert kind == "success" and "weniger Labels als exakt in 2 von 2 Instanzen (Mittel der Verhältnisse 0,60, kleinstes 0,50, größtes 0,70)" in text and "Runden 12,0 im Mittel (20 % gegen exakt)" in text
    assert "gleiche Endschranke wie exakt in 2 von 2 Instanzen" in text and "zufällige Instanzen" in ev.verdict_bands(rows, 100, "zufall", "L5")[1]
    rows[5]["labels"] = 2500                                                   # eine Instanz mit mehr Labels als exakt
    assert ev.verdict_bands(rows, 100, None, "L5")[0] == "warning" and "1 von 2 Instanzen" in ev.verdict_bands(rows, 100, None, "L5")[1]
    rows[5]["labels"], rows[5]["schranke"] = 1400, 11.0                       # eine Instanz mit anderer Endschranke
    kind, text = ev.verdict_bands(rows, 100, None, "L5")
    assert kind == "warning" and "gleiche Endschranke wie exakt in 1 von 2 Instanzen" in text


def test_formats():
    assert ev.fmt_int(1234567) == "1 234 567" and ev.fmt_int(-17) == "−17" and ev.fmt_dec(0.5, 2) == "0,50" and ev.fmt_dec(-1.5, 1) == "−1,5"
    assert ev.fmt_num(-22.0) == "−22" and ev.fmt_num(2.5) == "2,5" and ev.fmt_pct(12.34) == "12,3 %" and ev.fmt_ratio(0.5165) == "0,52"
    assert ev.route_text((3, 5, 6)) == "3 → 5 → 6" and ev.route_text(()) == "keine" and ev.label_name(7) == "F07"
    assert ev.limit_name(None) == "ohne Limit (exakt)" and ev.limit_name(5) == "Limit 5"
