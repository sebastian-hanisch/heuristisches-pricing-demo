"""Jede Zahl der README an festen Zufalls-Seeds (DEMO-PLAYBOOK §4, §11a): Handbeispiel exakt, Messreihen aus ihren Läufen abgeleitet (die Tabellen der README müssen zeichengleich aus
`data/laeufe_v13.json` und `data/zeit_vormessung.json` entstehen), Zählungen statt Urteilswörter.

Zeiten werden nie festgeschrieben: Die Zeitzahlen der README stammen aus der Messdatei der früheren Messung (`data/zeit_vormessung.json`), nicht aus einem Lauf dieser Suite; geprüft wird,
dass die README die Zahlen nennt, die aus dieser Datei folgen. Der Abgleich der Messreihe mit den Rohausgaben der früheren Messung steht in `data/vormessung_abgleich.json`.
Zahl-zu-Test-Tabelle: README, Abschnitt „Befunde“."""

import re
from pathlib import Path

import pytest

import hpr_constants as C
import hpr_evaluation as ev
import readme_tables as T
from hpr_scenario import hand_instance

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
BANDS = ev.load_bands()
ZEIT = ev.load_zeit()


def _table(breite, typ=None):
    return {r["variante"]: r for r in ev.band_table(BANDS, breite, typ)}


# --- Handbeispiel ---------------------------------------------------------------------------------------------------------------------------

def test_hand_example_numbers_of_the_readme():
    rows = {r["limit"]: r for r in ev.hand_overview()}
    assert [(rows[L]["generated"], rows[L]["limited"]) for L in (None, 1, 2, 3)] == [(66, 0), (23, 11), (30, 13), (36, 15)]
    assert rows[None]["n_routes"] == 48 and [rows[L]["found_best"] for L in (1, 2, 3)] == [False, True, True]
    enum = ev.hand_enumeration()
    assert len(enum) == 65 and sum(1 for rc, _ in enum if rc < 0) == 58 and enum[0] == (-22.0, (3, 5, 6))
    assert rows[1]["best"] == (-12.0, (3, 1, 5))
    for text in ("Ohne Limit 66 Labels (48 gelieferte Routen mit negativen reduzierten Kosten), Limit 1: 23 (Limit 11-mal angewendet), Limit 2: 30 (13-mal), Limit 3: 36 (15-mal)",
                 "die Aufzählung findet 65 zulässige elementare Routen, 58 davon mit negativen Kosten", "Die beste Route ist 3 → 5 → 6 mit reduzierten Kosten −22 (Länge 14 minus Dualpreise 36",
                 "Limit 1 findet nur 3 → 1 → 5 mit −12 und **verfehlt den besten Weg**; Limit 2 und 3 finden ihn",
                 "58 der 65 zulässigen Routen haben bei den Dualpreisen der ersten Runde negative reduzierte Kosten, das exakte Label-Verfahren liefert 48",
                 "Dualpreise der ersten Runde 6; 10; 10; 12; 14; 12"):
        assert text in README, text
    assert tuple(hand_instance().d[0][i] * 2 for i in range(1, 7)) == (6, 10, 10, 12, 14, 12)


def test_hand_displacement_sentence_of_the_readme():
    s = ev.displacement_story(1)
    assert (s["victim"], s["victim_path"], s["victim_cost"], s["victim_load"]) == (14, (3, 5), -17, 6)
    assert (s["newcomer"], s["newcomer_path"], s["newcomer_cost"], s["newcomer_load"]) == (21, (3, 1, 5), -19, 8) and s["reason"] == "Last 8 + 3 = 11 > 10"
    assert "Das Label F14 (Weg 3 → 5, Kosten −17, Last 6) wird von F21 (Weg 3 → 1 → 5, Kosten −19, Last 8) verdrängt" in README
    assert "von F21 aus ist Kunde 6 nicht mehr zu bedienen (Last 8 + 3 = 11 > 10), von F14 aus ging es (6 + 3 = 9 ≤ 10)" in README


def test_hand_column_generation_numbers_of_the_readme():
    ex = ev.hand_colgen(None, 3)
    runs = {L: ev.hand_colgen(L, 3) for L in (1, 2, 3)}
    assert (ex.iters, ex.labels, ex.bound) == (5, 280, 38.0)
    assert [(runs[L].iters, runs[L].labels, runs[L].exact_calls, runs[L].bound) for L in (1, 2, 3)] == [(6, 190, 1, 38.0), (5, 238, 2, 38.0), (5, 211, 1, 38.0)]
    assert (runs[1].labels_heur, runs[1].labels_exact, runs[1].heur_ok) == (136, 54, 5)
    z, pi = ev.hand_all_routes_lp()
    assert z == 38.0 and tuple(pi[1:]) == (3.0, 10.0, 5.0, 11.0, 5.0, 4.0)
    for text in ("Immer exakt: 5 Runden, 280 Labels. Limit 1: 6 Runden, 190 Labels (136 im Limit-Pricing, 54 im exakten; das Limit reichte in 5 von 6 Runden). Limit 2: 5 Runden, 238 Labels (2 exakte Aufrufe); "
                 "Limit 3: 5 Runden, 211 Labels (1 exakter Aufruf). Endschranke in allen Varianten 38, gleich dem LP über alle 65 Routen (Dualpreise 3; 10; 5; 11; 5; 4)",
                 "Im Handbeispiel mit Limit 2 braucht die Spaltenerzeugung mit der Regel dieser Demo 238 Labels,\n  mit der anderen Regel 188", "(190 und 280 Labels wie in der Handrechnung)",
                 "in der Zufallsinstanz mit Zufalls-Seed 1, Breite 100 und Limit 5 sind es 59 713 Labels gegen 59 711"):
        assert text in README, text


# --- Messreihen -----------------------------------------------------------------------------------------------------------------------------

def test_the_band_tables_of_the_readme_are_derived_from_the_data():
    for breite, typ in ((100, None), (100, "zufall"), (100, "cluster"), (150, None)):
        block = "\n".join(T.band_rows(BANDS, breite, typ))
        assert len(T.band_rows(BANDS, breite, typ)) == 4 and block in README, (breite, typ)
    assert T.BAND_HEADER in README and T.ZEIT_HEADER in README and T.SPLIT_HEADER in README and T.KIPP_HEADER in README
    assert "\n".join(T.zeit_rows(ZEIT)) in README and "\n".join(T.split_rows(ZEIT)) in README and "\n".join(T.kipp_rows(BANDS)) in README


def test_label_ratios_of_the_readme():
    t100, t150 = _table(100), _table(150)
    zu, cl = _table(100, "zufall"), _table(100, "cluster")
    assert [round(t100[v]["ratio_mean"], 2) for v in ("L5", "L10", "L20")] == [0.52, 0.60, 0.71]
    assert [(round(t100[v]["ratio_min"], 2), round(t100[v]["ratio_max"], 2)) for v in ("L5", "L10", "L20")] == [(0.25, 0.91), (0.33, 0.88), (0.38, 0.98)]
    assert [t100[v]["fewer"] for v in ("L5", "L10", "L20")] == [30, 30, 30] and t100["L5"]["n"] == 30
    assert [round(zu[v]["ratio_mean"], 2) for v in ("L5", "L10", "L20")] == [0.57, 0.67, 0.79] and [round(cl[v]["ratio_mean"], 2) for v in ("L5", "L10", "L20")] == [0.47, 0.53, 0.64]
    assert [round(100 * t100[v]["sum_ratio"], 1) for v in ("L5", "L10", "L20")] == [46.5, 53.2, 62.3]
    assert [round(t150[v]["ratio_mean"], 2) for v in ("L5", "L10", "L20")] == [0.43, 0.49, 0.63] and [t150[v]["fewer"] for v in ("L5", "L10", "L20")] == [16, 16, 15]
    assert round(t150["L20"]["ratio_max"], 2) == 1.02 and [round(100 * t150[v]["sum_ratio"], 1) for v in ("L5", "L10", "L20")] == [37.7, 40.6, 50.3]
    for text in ("Im Mittel der Verhältnisse 0,52 / 0,60 / 0,71 der Labels bei Limit 5 / 10 / 20 (kleinste und größte 0,25 bis 0,91 / 0,33 bis 0,88 / 0,38 bis 0,98), in 30 von 30 Instanzen weniger Labels; "
                 "zufällig 0,57 / 0,67 / 0,79, gruppiert 0,47 / 0,53 / 0,64 (je 15 Instanzen); Summe der Labels gegen exakt 46,5 / 53,2 / 62,3 %",
                 "Im Mittel 0,43 / 0,49 / 0,63; weniger Labels als exakt in 16, 16 und 15 von 16 Instanzen (bei Limit 20 einmal 1,02); Summe der Labels gegen exakt 37,7 / 40,6 / 50,3 %",
                 "Bei Fensterbreite 100 braucht das Limit im Mittel der Verhältnisse 0,52 / 0,60 / 0,71 der Labels\n(Limit 5 / 10 / 20; in allen 30 Instanzen weniger)",
                 "Bei Breite 150 braucht Limit 20 in 1 von 16 Instanzen mehr Labels als exakt (1,02)"):
        assert text in README, text


def test_rounds_and_limit_hits_of_the_readme():
    t100, t150 = _table(100), _table(150)
    assert [round(t100[v]["iters_mean"], 1) for v in C.BAND_VARIANTS] == [21.7, 29.5, 26.7, 23.9]
    assert [round(100 * t100[v]["iters_vs_exact"]) for v in ("L5", "L10", "L20")] == [36, 23, 10]
    assert [round(t150[v]["iters_mean"], 1) for v in C.BAND_VARIANTS] == [25.1, 32.5, 31.6, 29.4]
    assert [round(100 * t100[v]["limit_share"], 1) for v in ("L5", "L10", "L20")] == [79.4, 82.4, 87.3]
    assert [round(100 * t100[v]["exact_label_share"], 1) for v in ("L5", "L10", "L20")] == [55.8, 39.3, 22.3]
    assert [round(t100[v]["exact_calls_mean"], 1) for v in C.BAND_VARIANTS] == [21.7, 6.1, 4.7, 3.0]
    for text in ("Runden (Master-Aufgaben) bei Breite 100: 21,7 bei immer exakt gegen 29,5 / 26,7 / 23,9, also +36 / +23 / +10 %; bei Breite 150 25,1 gegen 32,5 / 31,6 / 29,4",
                 "Das Limit-Pricing fand in 79,4 / 82,4 / 87,3 % der Runden eine neue Spalte (Breite 100); trotzdem entstehen 55,8 / 39,3 / 22,3 % der Labels im exakten Pricing",
                 "exakte Aufrufe im Mittel 6,1 / 4,7 / 3,0 gegen 21,7", "aber +36 / +23 / +10 % Runden, also mehr Master-Aufgaben"):
        assert text in README, text


def test_all_46_instances_have_the_same_end_bound_and_no_run_is_aborted():
    assert len(BANDS) == 184 and not any(x["abgebrochen"] for x in BANDS)
    inst = list(ev.by_instance(BANDS, 100).values()) + list(ev.by_instance(BANDS, 150).values())
    assert len(inst) == 46 and all(max(abs(d[v]["schranke"] - d["exakt"]["schranke"]) for v in C.BAND_VARIANTS) <= 1e-6 for d in inst)
    for text in ("In allen 46 gemessenen Instanzen", "184 Läufe, alle vollständig gerechnet", "kein Lauf ist abgebrochen", "In allen 46 Instanzen (30 Kunden, Gedächtnis 8, Breite 100 und 150)"):
        assert text in README, text


def test_time_numbers_of_the_readme():
    zt = {r["variante"]: r for r in ev.zeit_table(ZEIT)}
    assert [round(zt[v]["cpu_sum_ratio"], 2) for v in ("L5", "L10", "L20")] == [0.36, 0.39, 0.46]
    assert [round(zt[v]["cpu_mean"], 2) for v in ("L5", "L10", "L20")] == [0.44, 0.49, 0.61] and [zt[v]["cpu_faster"] for v in ("L5", "L10", "L20")] == [30, 30, 30]
    assert zt["L20"]["wand_faster"] == 28 and zt["L5"]["wand_faster"] == zt["L10"]["wand_faster"] == 30
    assert round(zt["L20"]["cpu_max"], 2) == 0.98 and "Bei Limit 20 liegt das größte Instanz-Verhältnis bei 0,98 und damit innerhalb der Messunschärfe" in README
    assert (round(zt["exakt"]["cpu_sum"], 2), round(zt["exakt"]["lp"], 2), round(zt["exakt"]["exakt"], 2)) == (61.55, 2.07, 59.19)
    costs = ev.time_costs(ZEIT, BANDS)
    assert round(costs["master_ms"], 2) == 3.18 and round(costs["label_exact_us"], 2) == 8.34 and round(costs["master_in_labels"], -1) == 380 and round(100 * costs["pricing_share_exact"], 1) == 96.2
    assert [round(costs["limit_us"][v], 2) for v in ("L5", "L10", "L20")] == [3.40, 4.15, 5.10] and [round(costs["limit_vs_exact"][v], 2) for v in ("L5", "L10", "L20")] == [0.41, 0.50, 0.61]
    iters = sum(r["iterationen"] for r in (ev.zeit_median_rows(ZEIT)[(t, s, "exakt")] for t, s in {(z["typ"], z["seed"]) for z in ZEIT}))
    labels = sum(x["labels"] for x in BANDS if x["breite"] == 100 and x["variante"] == "exakt")
    assert (iters, labels) == (651, 7096412)
    for text in ("CPU-Zeit der Summe über die 30 Instanzen gegen exakt 0,36 / 0,39 / 0,46; Mittel der Instanz-Verhältnisse 0,44 / 0,49 / 0,61, in 30 von 30 Instanzen schneller als exakt; Wanduhrzeit: Limit 20 in 28 von 30 schneller",
                 "Master-LP 2,07 s von 61,55 s, exaktes Pricing 59,19 s (96,2 %)", "im Mittel 3,18 ms (651 Aufrufe) gegen 8,34 µs je erzeugtem Label (7 096 412 Labels), also etwa 380 Labels je Master-LP",
                 "CPU-Zeit je Label im Limit-Pricing 3,40 / 4,15 / 5,10 µs (Limit 5 / 10 / 20) gegen 8,34 µs im exakten Pricing, also 0,41 / 0,50 / 0,61",
                 "macht das exakte Pricing 96,2 % der CPU-Zeit bei immer exaktem Pricing aus", "eine CPU-Zeit von 0,36 / 0,39 / 0,46 der CPU-Zeit bei immer exaktem Pricing", "die CPU-Zeit mit Limit 0,36 / 0,39 / 0,46 der Zeit bei immer exaktem Pricing betrug",
                 "(360 Läufe: 30 Instanzen × 4 Varianten × 3 Wiederholungen", "**nicht mit dem Kern dieser Demo neu gemessen.**"):
        assert text in README, text
    assert "Pricing 96,2 % der CPU-Zeit bei immer exaktem Pricing, ein Master-LP etwa 380 Labels" in README


def test_kipp_numbers_of_the_readme():
    st = ev.model_stats(BANDS, 100)
    be = {v: ev.break_even(st[v], st["exakt"], 1.0) for v in ("L5", "L10", "L20")}
    assert [round(be[v], -2) for v in ("L5", "L10", "L20")] == [16300, 22000, 40500]
    assert [round(ev.model_ratio(st[v], st["exakt"], 380), 2) for v in ("L5", "L10", "L20")] == [0.49, 0.56, 0.64]
    assert [round(ev.model_ratio(st[v], st["exakt"], 20000), 2) for v in ("L5", "L10", "L20")] == [1.04, 0.99, 0.93]
    zt = {r["variante"]: r for r in ev.zeit_table(ZEIT)}
    assert all(ev.model_ratio(st[v], st["exakt"], 380) > zt[v]["cpu_sum_ratio"] for v in ("L5", "L10", "L20"))               # das Modell überschätzt gegen die gemessene CPU-Summe
    # mit den gemessenen Kosten je Limit-Label rückt das Modell an die gemessene CPU-Summe heran
    costs = ev.time_costs(ZEIT, BANDS)
    near = [ev.model_ratio(st[v], st["exakt"], costs["master_in_labels"], costs["limit_vs_exact"][v]) for v in ("L5", "L10", "L20")]
    assert all(abs(n - zt[v]["cpu_sum_ratio"]) < 0.06 for n, v in zip(near, ("L5", "L10", "L20")))
    assert [round(n, 2) for n in near] == [0.38, 0.40, 0.46] and "liegt es bei 0,38 / 0,40 / 0,46 gegen gemessen 0,36 / 0,39 / 0,46" in README
    for text in ("solange ein Master-LP weniger als etwa 16 300 (Limit 5), 22 000 (Limit 10) und 40 500 Labels (Limit 20) kostet; bei 380 liegt der modellierte Aufwand bei 0,49 / 0,56 / 0,64 des Aufwands bei immer exakt "
                 "(gemessen CPU-Summe 0,36 / 0,39 / 0,46: das Modell überschätzt), bei 20 000 bei 1,04 / 0,99 / 0,93",
                 "im Modell kippt es bei etwa 16 300 / 22 000 / 40 500 Labels je Master-LP (nicht gemessen)", "Im Modell kippt er bei etwa 16 300 / 22 000 / 40 500 Labels je Master-LP"):
        assert text in README, text


def test_scenario_numbers_of_the_readme():
    from test_presets import _live
    out = {}
    for name in ("Limit 1 verfehlt den besten Weg (Voreinstellung)", "Kleines Limit 5 auf einer Zufallsinstanz", "Gruppierte Kunden, Breite 100, Limit 20", "Kleine Instanz: das Limit spart nichts"):
        ex, he = _live(C.PRESETS[name])
        out[name] = (ex.labels, he.labels, ex.iters, he.iters)
    assert out["Limit 1 verfehlt den besten Weg (Voreinstellung)"] == (17998, 10537, 23, 16) and out["Kleines Limit 5 auf einer Zufallsinstanz"] == (17998, 9882, 23, 21)
    assert out["Gruppierte Kunden, Breite 100, Limit 20"] == (254029, 179293, 23, 25) and out["Kleine Instanz: das Limit spart nichts"][:2] == (185, 220)
    for text in ("20 Kunden, Breite 40, Zufalls-Seed 0, Limit 10: 17 998 → 10 537 (16 statt 23 Runden); Limit 5: 17 998 → 9 882 (21 statt 23 Runden); 30 Kunden, gruppiert, Breite 100, Limit 20: 254 029 → 179 293 (25 statt 23 Runden); "
                 "**8 Kunden, Limit 20: 185 → 220 (das Limit braucht dort mehr Labels als immer exakt)**",
                 "bei der Live-Instanz mit 8 Kunden und Limit 20 braucht das Limit mehr Labels als immer exakt (220 gegen 185)"):
        assert text in README, text


# --- Rechenbudget, Zusagen, Verweise ------------------------------------------------------------------------------------------------------------

def test_budget_numbers_of_the_readme():
    assert (C.MAX_LABELS_COLGEN, C.MAX_LABELS_CALL) == (600_000, 300_000)
    assert "Abbruch bei mehr als 600 000 erzeugten Labels über alle Runden oder mehr als 300 000 in einem Aufruf" in README


def test_the_abgleich_record_is_stated_in_the_readme():
    assert "Runden, Spalten,\n  Labels (gesamt, im Limit-Pricing, im exakten Pricing), Limit-Treffer und exakte Aufrufe stimmen in 184 von 184 Zeilen überein" in README
    assert "größte Abweichung unter 10⁻⁶" in README and "`data/vormessung_abgleich.json`" in README and "eine Stichprobe von 4 Instanzen (16 Läufe)" in README


def test_the_test_count_of_the_readme_equals_the_suite():
    import subprocess
    import sys
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "tests", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True, timeout=300).stdout
    count = int(re.search(r"(\d+) tests? collected", out).group(1))
    assert f"**Testzahl:** {count} Tests (`pytest --collect-only -q tests`)" in README


def test_linked_demos_of_the_readme_exist_in_the_portfolio():
    """Verweise nur auf Demos, deren Ordner im Projektordner existiert (DEMO-PLAYBOOK §11 Punkt 1); ohne Projektordner (CI) entfällt die Prüfung."""
    portfolio = ROOT.parent
    names = set(re.findall(r"github\.com/sebastian-hanisch/([a-z0-9-]+)\)", README))
    assert {"crew-pairing-demo", "pricing-dualpreise-demo", "elementar-pricing-demo", "eimer-labeling-demo", "hub-labeling-demo"} <= names
    if (portfolio / "crew-pairing-demo").exists():
        assert all((portfolio / n).exists() for n in names), [n for n in names if not (portfolio / n).exists()]


def test_the_assumptions_text_of_the_readme_is_the_text_of_the_app():
    assert C.ASSUMPTIONS_MARKDOWN.strip() in README
