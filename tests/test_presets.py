"""Schnellstart-Szenarien: Vollständigkeit, gültige Werte, Standard-Szenario = Standardeinstellungen, und die erwartete Verdikt-Zeile je Szenario (DEMO-PLAYBOOK §11a Punkt 7).
Hilfetexte sind Behauptungen: Jede wird hier an den Zählungen des Szenarios geprüft."""

import pytest

import hpr_constants as C
import hpr_evaluation as ev
import hpr_presets as P

DEFAULT = "Limit 1 verfehlt den besten Weg (Voreinstellung)"
# Erwartung je Szenario: (Art, Textstück) des Verdikts „Labels“ der Zufallsinstanz, des Handbeispiel-Verdikts (erstes Preisproblem) und des Kipp-Rechners
EXPECTED = {
    "Limit 1 verfehlt den besten Weg (Voreinstellung)": (("success", "Limit 10: 10 537 Labels gegen 17 998"), ("warning", "Das Limit verfehlt den besten Weg"), ("success", "lohnen sich im Modell alle drei Limits")),
    "Limit 2 im Handbeispiel": (("success", "Limit 10: 10 537 Labels gegen 17 998"), ("success", "Das Limit findet hier den besten Weg"), ("success", "lohnen sich im Modell alle drei Limits")),
    "Kleines Limit 5 auf einer Zufallsinstanz": (("success", "Limit 5: 9 882 Labels gegen 17 998"), ("warning", "Das Limit verfehlt den besten Weg"), ("success", "lohnen sich im Modell alle drei Limits")),
    "Gruppierte Kunden, Breite 100, Limit 20": (("success", "Limit 20: 179 293 Labels gegen 254 029"), ("warning", "Das Limit verfehlt den besten Weg"), ("success", "lohnen sich im Modell alle drei Limits")),
    "Teurer Master: 20 000 Labels je Master-LP": (("success", "Limit 10: 10 537 Labels gegen 17 998"), ("warning", "Das Limit verfehlt den besten Weg"), ("info", "lohnen sich im Modell L10, L20; nicht mehr L5")),
    "Kleine Instanz: das Limit spart nichts": (("warning", "Limit 20: 220 Labels gegen 185"), ("warning", "Das Limit verfehlt den besten Weg"), ("success", "lohnen sich im Modell alle drei Limits")),
}
BANDS = ev.load_bands()
STATS = ev.model_stats(BANDS, 100)


def _live(p):
    return ev.live_runs(ev.Settings(p["n"], p["width"], p["typ"], p["k"], p["limit"], p["seed"]))


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) == set(EXPECTED)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_widget_bounds():
    for name, p in C.PRESETS.items():
        assert p["hand_limit"] in C.HAND_LIMIT_OPTIONS and p["hand_new"] in C.HAND_NEW_OPTIONS, name
        assert C.N_MIN <= p["n"] <= C.N_MAX and p["width"] in C.WIDTH_OPTIONS and p["typ"] in C.TYP_OPTIONS and p["k"] in C.K_OPTIONS and p["limit"] in C.LIMIT_OPTIONS, name
        assert 0 <= p["seed"] <= C.SEED_MAX and p["master_cost"] in C.MASTER_COST_OPTIONS and C.LABEL_COST_MIN <= p["label_cost"] <= C.LABEL_COST_MAX, name


def test_default_preset_equals_the_default_settings():
    preset = C.PRESETS[DEFAULT]
    assert next(iter(C.PRESETS)) == DEFAULT
    for state_key, spec in P.SETTING_SPECS.items():
        key = next(k for k, v in P.PRESET_KEYS.items() if v == state_key)
        assert preset[key] == spec.default, state_key


def test_setting_specs_cover_every_preset_key_and_choices_are_the_constants():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)
    s = P.SETTING_SPECS
    assert (s["hand_limit_radio"].choices, s["hand_new_radio"].choices, s["width_radio"].choices, s["typ_radio"].choices, s["k_radio"].choices, s["limit_radio"].choices,
            s["master_cost_select"].choices) == (C.HAND_LIMIT_OPTIONS, C.HAND_NEW_OPTIONS, C.WIDTH_OPTIONS, C.TYP_OPTIONS, C.K_OPTIONS, C.LIMIT_OPTIONS, C.MASTER_COST_OPTIONS)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_expected_verdict_lines_of_every_preset(name):
    (k_labels, piece_labels), (k_hand, piece_hand), (k_kipp, piece_kipp) = EXPECTED[name]
    p = C.PRESETS[name]
    exact, heur = _live(p)
    assert not exact.aborted and not heur.aborted
    assert ev.verdict_bound(exact, heur)[0] == "success"
    kind, text = ev.verdict_labels(exact, heur, p["limit"])
    assert kind == k_labels and piece_labels in text, text
    kind, text = ev.verdict_hand_pricing(ev.hand_overview(), p["hand_limit"])
    assert kind == k_hand and piece_hand in text, text
    kind, text = ev.verdict_kipp(STATS, p["master_cost"], p["label_cost"])
    assert kind == k_kipp and piece_kipp in text, text
    exh, heh = ev.hand_colgen(None, p["hand_new"]), ev.hand_colgen(p["hand_limit"], p["hand_new"])
    assert ev.verdict_hand_loop(exh, heh, 38.0, p["hand_limit"])[0] == "success"


def test_the_help_texts_state_what_the_scenarios_show():
    """Hilfetexte sind Behauptungen: gemessen an den Zählungen des Szenarios."""
    rows = ev.hand_overview()
    assert next(r for r in rows if r["limit"] == 1)["found_best"] is False and "verfehlt den besten Weg" in DEFAULT            # der Name des Voreinstellungs-Szenarios ist eine Behauptung
    assert next(r for r in rows if r["limit"] == 2)["found_best"] is True and "findet im ersten Preisproblem den besten Weg" in C.PRESET_HELP["Limit 2 im Handbeispiel"]
    # Limit 5 spart auf der Voreinstellungs-Instanz mehr Labels als Limit 10
    _, h5 = _live(C.PRESETS["Kleines Limit 5 auf einer Zufallsinstanz"])
    _, h10 = _live(C.PRESETS[DEFAULT])
    assert h5.labels < h10.labels and "kleinere Limits sparen im Mittel mehr Labels" in C.PRESET_HELP["Kleines Limit 5 auf einer Zufallsinstanz"]
    # die gruppierte Instanz ist größer als die Voreinstellung
    big, _ = _live(C.PRESETS["Gruppierte Kunden, Breite 100, Limit 20"])
    default_exact, _ = _live(C.PRESETS[DEFAULT])
    assert big.labels > default_exact.labels and "eine größere Rechnung als die Voreinstellung" in C.PRESET_HELP["Gruppierte Kunden, Breite 100, Limit 20"]
    # Teurer Master: Limit 5 lohnt sich nicht mehr, Limit 10 und 20 noch
    p = C.PRESETS["Teurer Master: 20 000 Labels je Master-LP"]
    ratios = {v: ev.model_ratio(STATS[v], STATS["exakt"], p["master_cost"], p["label_cost"]) for v in ("L5", "L10", "L20")}
    assert ratios["L5"] > 1 > ratios["L10"] and ratios["L20"] < 1
    assert "Das Limit 5 lohnt sich dann nicht mehr, Limit 10 und 20 noch" in C.PRESET_HELP["Teurer Master: 20 000 Labels je Master-LP"]
    # Kleine Instanz: das Limit greift nur wenige Male und braucht mehr Labels als immer exakt
    small_exact, small_heur = _live(C.PRESETS["Kleine Instanz: das Limit spart nichts"])
    assert 0 < small_heur.limited <= 10 and small_heur.labels > small_exact.labels
    assert "braucht die Rechnung mehr Labels als immer exakt" in C.PRESET_HELP["Kleine Instanz: das Limit spart nichts"]
