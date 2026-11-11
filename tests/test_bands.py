"""Die festen Messreihen (data/laeufe_v13.json, data/zeit_vormessung.json): Aufbau, Quellenangaben, Stichprobe neu gerechnet mit dem Kern.

Die Zählungen (184 Läufe: 46 Instanzen x 4 Varianten) sind mit dem Kern dieser Demo neu gerechnet (tools/baender_bauen.py) und beim Bau mit den Rohausgaben der Vormessung abgeglichen
(data/vormessung_abgleich.json); der Abgleich selbst läuft nicht in der Testsuite (die Rohausgaben liegen nicht im Repo). Hier wird geprüft, dass die Datei vollständig ist und dass eine
Stichprobe der Läufe mit dem Kern dieselben Zahlen ergibt. Die Zeitreihe stammt aus der Messdatei der Vormessung und ist NICHT neu gemessen; Zeiten werden nie festgeschrieben."""

import json
from pathlib import Path

import pytest

import hpr_colgen as G
import hpr_constants as C
import hpr_evaluation as ev
from hpr_scenario import make_instance

DATA = Path(__file__).resolve().parent.parent / "data"
BANDS = ev.load_bands()
ZEIT = ev.load_zeit()


def _row(typ, breite, seed, variante):
    return next(x for x in BANDS if (x["typ"], x["breite"], x["seed"], x["variante"]) == (typ, breite, seed, variante))


def test_the_bands_have_the_documented_shape():
    assert len(BANDS) == 184
    for breite, seeds in C.BAND_SEEDS.items():
        inst = ev.by_instance(BANDS, breite)
        assert sorted(inst) == sorted((t, s) for t in ("zufall", "cluster") for s in seeds)
        assert all(set(d) == set(C.BAND_VARIANTS) for d in inst.values())
    assert (len(ev.by_instance(BANDS, 100)), len(ev.by_instance(BANDS, 150))) == (30, 16)
    assert all(x["abgebrochen"] is False and x["schranke"] is not None for x in BANDS)


def test_every_run_names_its_source():
    for x in BANDS:
        assert "tools/baender_bauen.py" in x["quelle"] and "out_v13_" in x["quelle"] and "neu gerechnet mit dem Kern der Demo" in x["quelle"]
    assert {x["quelle"].split("verglichen mit ")[1].split(" ")[0] for x in BANDS} == {"out_v13_zufall.txt", "out_v13_cluster.txt", "out_v13_zufall_b150.txt", "out_v13_cluster_b150.txt"}


def test_the_counters_are_consistent_within_each_run():
    for x in BANDS:
        assert x["labels"] == x["labels_limit"] + x["labels_exakt"]
        if x["variante"] == "exakt":
            assert x["labels_limit"] == 0 and x["limit_reichte"] == 0 and x["exakte_aufrufe"] == x["iterationen"]
        else:
            assert x["limit_reichte"] + x["exakte_aufrufe"] == x["iterationen"]         # jede Runde: entweder reichte das Limit, oder es lief der exakte Aufruf (nie beides)
            assert 1 <= x["exakte_aufrufe"] <= x["iterationen"] and x["labels_limit"] > 0


def test_the_end_bound_is_the_same_for_all_four_variants_in_all_46_instances():
    inst = {**ev.by_instance(BANDS, 100), **{(t, s + 1000): d for (t, s), d in ev.by_instance(BANDS, 150).items()}}
    assert len(inst) == 46
    for key, d in inst.items():
        assert max(abs(d[v]["schranke"] - d["exakt"]["schranke"]) for v in C.BAND_VARIANTS) <= 1e-6, key           # in der Datei auf 6 Stellen gerundet


@pytest.mark.parametrize("typ,breite,seed", [("zufall", 100, 0), ("zufall", 100, 10), ("cluster", 100, 1), ("zufall", 150, 5)])
def test_a_sample_of_instances_recomputes_to_the_stored_counters(typ, breite, seed):
    inst = make_instance(30, seed, breite, clustered=(typ == "cluster"))
    for name, limit in (("exakt", None), ("L5", 5), ("L10", 10), ("L20", 20)):
        c = G.colgen(inst, 8, limit=limit)
        x = _row(typ, breite, seed, name)
        assert (c.iters, c.cols, c.labels, c.labels_heur, c.labels_exact, c.heur_ok, c.exact_calls, c.dominated, c.limited) == \
               (x["iterationen"], x["spalten"], x["labels"], x["labels_limit"], x["labels_exakt"], x["limit_reichte"], x["exakte_aufrufe"], x["gestrichen"], x["limit_angewendet"]), (typ, seed, name)
        assert c.bound == pytest.approx(x["schranke"], abs=1e-6)


def test_the_comparison_with_the_raw_output_of_the_earlier_measurement_is_recorded():
    rec = json.loads((DATA / "vormessung_abgleich.json").read_text(encoding="utf-8"))
    assert rec["zeilen_neu"] == rec["zeilen_gleich"] == 184 and rec["zeilen_abweichend"] == 0 and rec["zeilen_ohne_rohzeile"] == 0
    assert rec["abgebrochene_laeufe"] == 0 and rec["schranke_groesste_abweichung"] < 1e-6 and rec["zeitzeilen"] == 360


def test_the_time_series_is_the_file_of_the_earlier_measurement_and_its_counters_match_the_recomputed_runs():
    raw = json.loads((DATA / "zeit_vormessung.json").read_text(encoding="utf-8"))
    assert "NICHT mit dem Kern dieser Demo neu gemessen" in raw["hinweis"] and "run_p14_zeit.log" in raw["quelle"]
    assert len(ZEIT) == 360 and not any(z["abgebrochen"] for z in ZEIT)
    assert {z["wiederholung"] for z in ZEIT} == {1, 2, 3} and len({(z["typ"], z["seed"]) for z in ZEIT}) == 30
    for z in ZEIT:
        x = _row(z["typ"], 100, z["seed"], z["variante"])
        assert (z["iterationen"], z["labels"]) == (x["iterationen"], x["labels"]) and z["schranke"] == pytest.approx(x["schranke"], abs=1e-6)


def test_the_evaluation_helpers_on_the_bands():
    table = ev.band_table(BANDS, 100)
    assert [r["variante"] for r in table] == list(C.BAND_VARIANTS) and all(r["n"] == 30 for r in table)
    assert table[0]["ratio_mean"] == table[0]["ratio_min"] == table[0]["ratio_max"] == 1.0
    for r in table[1:]:
        assert r["ratio_min"] <= r["ratio_median"] <= r["ratio_max"] and r["ratio_min"] <= r["ratio_mean"] <= r["ratio_max"]
    zt = ev.zeit_table(ZEIT)
    assert [r["variante"] for r in zt] == list(C.BAND_VARIANTS) and zt[0]["cpu_sum_ratio"] == 1.0
    for r in zt:
        assert r["lp"] + r["limit"] + r["exakt"] + r["rest"] == pytest.approx(r["cpu_sum"])
