"""End-to-end-Tests über Streamlits AppTest: lädt app.py mit den Standardeinstellungen, klickt jeden Knopf, fährt jeden Regler an seine Grenzen, wählt jede Option,
prüft den Permalink und je Schnellstart-Szenario die erwartete Verdikt-Zeile. Expander werden nie per Index angesprochen (DEMO-PLAYBOOK §2 Punkt 7)."""

import os
import re

import pytest
from streamlit.testing.v1 import AppTest

import hpr_constants as C
import hpr_presets as P

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
AUTOPLAY_MARKER = "▶"  # Auto-Play-Buttons (Animation mit sleep) im Smoke-Test auslassen
SLIDER_KEYS = [k for k, spec in P.SETTING_SPECS.items() if spec.choices is None and spec.hi is not None and k != "seed_input"]
CHOICE_KEYS = {"hand_limit_radio": ("radio", C.HAND_LIMIT_OPTIONS), "hand_new_radio": ("radio", C.HAND_NEW_OPTIONS), "width_radio": ("radio", C.WIDTH_OPTIONS), "typ_radio": ("radio", C.TYP_OPTIONS),
               "k_radio": ("radio", C.K_OPTIONS), "limit_radio": ("radio", C.LIMIT_OPTIONS), "master_cost_select": ("select_slider", C.MASTER_COST_OPTIONS)}


def _fresh_app(query=None) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    if query:
        at.query_params.update(query)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texts(at, kind):
    return [e.value for e in getattr(at, kind)]


def _widget(at, kind, key):
    return getattr(at.sidebar, kind)(key=key)


def test_app_loads_without_exception():
    at = _fresh_app()
    assert at.title[0].value.endswith("Heuristisches Pricing: erst gelockert, exakt nur zum Beweis")


def test_the_buttons_are_the_presets_and_the_new_instance_button():
    labels = [b.label for b in _fresh_app().sidebar.button]
    assert labels[: len(C.PRESETS)] == list(C.PRESETS) and labels[len(C.PRESETS):] == ["🎲 Neue Instanz generieren"]


@pytest.mark.parametrize("index", range(len(C.PRESETS) + 1))
def test_every_button_click_does_not_raise(index):
    at = _fresh_app()
    label = at.sidebar.button[index].label
    if AUTOPLAY_MARKER in label:
        pytest.skip("Auto-Play")
    at.sidebar.button[index].click().run(timeout=TIMEOUT)
    assert not at.exception, (label, [str(e) for e in at.exception])


@pytest.mark.parametrize("state_key", SLIDER_KEYS)
@pytest.mark.parametrize("edge", ["min", "max"])
def test_every_slider_at_its_min_and_max_does_not_raise(state_key, edge):
    at = _fresh_app()
    spec = P.SETTING_SPECS[state_key]
    value = spec.lo if edge == "min" else spec.hi
    at.sidebar.slider(key=state_key).set_value(value if isinstance(spec.default, float) else int(value)).run(timeout=TIMEOUT)
    assert not at.exception, (state_key, edge, [str(e) for e in at.exception])


@pytest.mark.parametrize("key", list(CHOICE_KEYS))
def test_every_option_of_every_choice_widget_does_not_raise(key):
    kind, options = CHOICE_KEYS[key]
    for option in options:
        at = _fresh_app()
        _widget(at, kind, key).set_value(option).run(timeout=TIMEOUT)
        assert not at.exception, (key, option, [str(e) for e in at.exception])


@pytest.mark.parametrize("n,width,typ,k,limit,seed", [(C.N_MIN, 40, "zufall", 4, 5, 0), (C.N_MIN, 100, "cluster", 8, 20, C.SEED_MAX), (C.N_MAX, 40, "zufall", 8, 5, 0), (C.N_MAX, 100, "zufall", 6, 20, C.SEED_MAX)])
def test_corner_matrix_at_the_widget_edges(n, width, typ, k, limit, seed):
    """Eckfall-Matrix (DEMO-PLAYBOOK §1d): Kundenzahl, Fensterbreite, Verteilung, Gedächtnis, Limit und Zufalls-Seed an den Rändern gemeinsam."""
    at = _fresh_app()
    at.sidebar.slider(key="n_slider").set_value(n)
    at.sidebar.radio(key="width_radio").set_value(width)
    at.sidebar.radio(key="typ_radio").set_value(typ)
    at.sidebar.radio(key="k_radio").set_value(k)
    at.sidebar.radio(key="limit_radio").set_value(limit)
    at.sidebar.number_input(key="seed_input").set_value(seed)
    at.run(timeout=TIMEOUT)
    assert not at.exception, ((n, width, typ, k, limit, seed), [str(e) for e in at.exception])
    assert at.sidebar.slider(key="n_slider").value == n


def test_worst_case_at_the_widget_maximum_stays_inside_the_budget():
    """Worst-Case (DEMO-PLAYBOOK §1c): n = 30, Fensterbreite 100, gruppiert, Gedächtnis 8, Zufalls-Seed 2 würde über 1 Million Labels in der exakten Spaltenerzeugung erzeugen. Die App bricht ab,
    zeigt den Abbruch als Warnung statt als Fehler, und die Experimente 1, 2, 4 und 5 erscheinen trotzdem."""
    at = _fresh_app({"n": "30", "breite": "100", "typ": "cluster", "k": "8", "limit": "20", "seed": "2"})
    warnings = _texts(at, "warning")
    assert any("abgebrochen" in w and "Labelbudget" in w for w in warnings)
    subheaders = [s.value for s in at.subheader]
    for number in (1, 2, 4, 5):
        assert any(s.startswith(f"🔬 Experiment {number}:") for s in subheaders), number
    assert not at.error


def test_largest_instance_inside_the_budget_shows_every_experiment():
    at = _fresh_app({"n": "30", "breite": "100", "typ": "cluster", "k": "8", "limit": "20", "seed": "3"})
    subheaders = [s.value for s in at.subheader]
    for number in range(1, 6):
        assert any(s.startswith(f"🔬 Experiment {number}:") for s in subheaders), number
    assert not at.error and not at.exception


def test_permalink_sets_the_widgets_and_clamps_invalid_values():
    at = _fresh_app({"hlimit": "2", "hneu": "5", "n": "14", "breite": "100", "typ": "cluster", "k": "6", "limit": "5", "seed": "7", "mkosten": "3000", "lkosten": "0.55"})
    assert at.sidebar.radio(key="hand_limit_radio").value == 2 and at.sidebar.radio(key="hand_new_radio").value == 5
    assert at.sidebar.slider(key="n_slider").value == 14 and at.sidebar.radio(key="width_radio").value == 100 and at.sidebar.radio(key="typ_radio").value == "cluster"
    assert at.sidebar.radio(key="k_radio").value == 6 and at.sidebar.radio(key="limit_radio").value == 5 and at.sidebar.number_input(key="seed_input").value == 7
    assert at.sidebar.select_slider(key="master_cost_select").value == 3000 and at.sidebar.slider(key="label_cost_slider").value == pytest.approx(0.55)
    bad = _fresh_app({"hlimit": "9", "n": "999", "breite": "123", "typ": "x", "k": "5", "limit": "7", "seed": "-5", "mkosten": "123", "lkosten": "9"})
    assert bad.sidebar.radio(key="hand_limit_radio").value == C.DEFAULT_HAND_LIMIT and bad.sidebar.slider(key="n_slider").value == C.N_MAX
    assert bad.sidebar.radio(key="width_radio").value == C.DEFAULT_WIDTH and bad.sidebar.radio(key="typ_radio").value == C.DEFAULT_TYP and bad.sidebar.radio(key="k_radio").value == C.DEFAULT_K
    assert bad.sidebar.radio(key="limit_radio").value == C.DEFAULT_LIMIT and bad.sidebar.number_input(key="seed_input").value == 0
    assert bad.sidebar.select_slider(key="master_cost_select").value == C.DEFAULT_MASTER_COST and bad.sidebar.slider(key="label_cost_slider").value == C.LABEL_COST_MAX
    garbage = _fresh_app({"n": "abc", "seed": "1.5", "lkosten": "nan", "hlimit": "x"})
    assert garbage.sidebar.slider(key="n_slider").value == C.DEFAULT_N and garbage.sidebar.number_input(key="seed_input").value == C.DEFAULT_SEED
    assert garbage.sidebar.radio(key="hand_limit_radio").value == C.DEFAULT_HAND_LIMIT and not garbage.exception


def test_query_params_follow_the_settings():
    at = _fresh_app()
    at.sidebar.radio(key="limit_radio").set_value(20).run(timeout=TIMEOUT)
    assert at.query_params["limit"] in (["20"], "20")


def test_settings_in_the_url_match_the_setting_specs():
    assert {spec.url_param for spec in P.SETTING_SPECS.values()} == {"hlimit", "hneu", "n", "breite", "typ", "k", "limit", "seed", "mkosten", "lkosten"}
    assert re.fullmatch(r"[a-z0-9]+", "".join(spec.url_param for spec in P.SETTING_SPECS.values()))


def test_sections_are_present_by_title_not_by_index():
    at = _fresh_app()
    expanders = {e.label: e for e in at.expander}
    assert "So funktioniert heuristisches Pricing" in expanders and expanders["So funktioniert heuristisches Pricing"].proto.expanded
    assert "📐 Mathematische Formulierung" in expanders and "⚠️ Annahmen, Grenzen und bekannte Probleme" in expanders
    subheaders = [s.value for s in at.subheader]
    for number in range(1, 6):
        assert any(s.startswith(f"🔬 Experiment {number}:") for s in subheaders), number
    assert any(s.startswith("🚧 Wo die Annahmen enden") for s in subheaders)
    math = expanders["📐 Mathematische Formulierung"].markdown[0].value
    assert math.startswith("**Lesehilfe.**") and "| Symbol | Bedeutung |" in math
    assert "Prüfstand" in math and "keine eigene Quelle gefunden" in math


def test_assumptions_expander_text_equals_the_constant_and_the_readme():
    at = _fresh_app()
    box = next(e for e in at.expander if e.label == "⚠️ Annahmen, Grenzen und bekannte Probleme")
    assert box.markdown[0].value.strip() == C.ASSUMPTIONS_MARKDOWN.strip()
    readme = open(os.path.join(os.path.dirname(APP_PATH), "README.md"), encoding="utf-8").read()
    assert C.ASSUMPTIONS_MARKDOWN.strip() in readme


def _first_frame(at, column):
    frames = [d.value for d in at.dataframe if hasattr(d.value, "columns") and column in d.value.columns]
    assert frames, column
    return frames[0]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_shows_its_expected_verdict_lines(name):
    from test_presets import EXPECTED
    at = _fresh_app()
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    (k_labels, piece_labels), (k_hand, piece_hand), (k_kipp, piece_kipp) = EXPECTED[name]
    for kind, piece in ((k_labels, piece_labels), (k_hand, piece_hand), (k_kipp, piece_kipp)):
        assert any(piece in t for t in _texts(at, kind)), (name, piece, _texts(at, kind))
    assert any(t.startswith("Gleiche Endschranke wie bei immer exaktem Pricing: ja") for t in _texts(at, "success"))
    assert any(t.startswith("Dieselbe Endschranke 38 wie bei immer exaktem Pricing und wie das LP über alle Routen") for t in _texts(at, "success"))
    # genau eine der drei Zeitaussagen steht da (Sekunden sind nur Information: welche, hängt vom Rechner ab)
    time_lines = [t for t in _texts(at, "info") if t.startswith(("Die Gesamtzeit sinkt", "Die Gesamtzeit steigt", "Gesamtzeit gleichauf"))]
    assert len(time_lines) == 1 and "nur Information" in time_lines[0]


def test_the_hand_tables_show_the_limit_decisions_and_all_labels_on_request():
    at = _fresh_app()
    over = _first_frame(at, "Besten Weg gefunden")
    assert list(over["Erzeugte Labels"]) == [66, 23, 30, 36] and list(over["Besten Weg gefunden"]) == ["ja", "NEIN", "ja", "ja"] and list(over["Limit angewendet"]) == [0, 11, 13, 15]
    events = _first_frame(at, "Entscheidung")
    assert len(events) == 11 and "F21" in list(events["Label"])
    assert any("F14 (Kosten −17) fliegt, das neue ist billiger" in e for e in events["Entscheidung"])
    text = " ".join(m.value for m in at.markdown)
    assert "Warum das Limit hier scheitert" in text and "Last 8 + 3 = 11 > 10" in text
    at.checkbox(key="show_all_labels").set_value(True).run(timeout=TIMEOUT)
    assert not at.exception
    allrows = _first_frame(at, "Lebende Labels am Kunden vorher")
    assert len(allrows) == 22 and allrows["Label"][0] == "F01" and allrows["Label"][21] == "F22"


def test_the_hand_loop_table_has_the_rounds_of_both_variants():
    at = _fresh_app()
    loop = _first_frame(at, "Neue Spalten und Kosten (immer exakt)")
    assert list(loop["Runde"]) == [1, 2, 3, 4, 5, 6] and loop["Neue Spalten und Kosten (immer exakt)"][5] == "–"
    assert "Schranke bewiesen" in loop["Neue Spalten und Kosten (Limit 1)"][5] and "Schranke bewiesen" in loop["Neue Spalten und Kosten (immer exakt)"][4]
    at.sidebar.radio(key="hand_new_radio").set_value(1).run(timeout=TIMEOUT)
    assert not at.exception
    again = _first_frame(at, "Neue Spalten und Kosten (immer exakt)")
    assert len(again) > 6


def test_the_band_table_follows_the_width_and_type_widgets():
    at = _fresh_app()
    table = _first_frame(at, "Labels / exakt (Mittel der Verhältnisse)")
    assert list(table["Instanzen"]) == [30] * 4 and list(table["Variante"]) == ["exakt", "L5", "L10", "L20"] and list(table["Labels / exakt (Mittel der Verhältnisse)"]) == ["1,00", "0,52", "0,60", "0,71"]
    at.radio(key="band_breite").set_value(150).run(timeout=TIMEOUT)
    at.selectbox(key="band_typ").set_value("gruppiert").run(timeout=TIMEOUT)
    assert not at.exception
    t2 = _first_frame(at, "Labels / exakt (Mittel der Verhältnisse)")
    assert list(t2["Instanzen"]) == [8] * 4 and list(t2["Labels / exakt (Mittel der Verhältnisse)"])[1] != "0,52"


def test_the_kipp_table_and_the_time_table_are_there():
    at = _fresh_app()
    kipp = _first_frame(at, "Lohnt sich bei den gewählten Kosten?")
    assert list(kipp["Limit"]) == ["L5", "L10", "L20"] and list(kipp["Lohnt sich bei den gewählten Kosten?"]) == ["ja", "ja", "ja"]
    zeit = _first_frame(at, "Summe / exakt")
    assert list(zeit["Summe / exakt"]) == ["1,00", "0,36", "0,39", "0,46"]
    at.sidebar.select_slider(key="master_cost_select").set_value(20000).run(timeout=TIMEOUT)
    assert list(_first_frame(at, "Lohnt sich bei den gewählten Kosten?")["Lohnt sich bei den gewählten Kosten?"]) == ["NEIN", "ja", "ja"]


def test_the_delta_values_of_the_metrics_use_the_ascii_minus():
    """Streamlit zeigt bei einem echten Minuszeichen im Delta einen Pfeil nach oben in Rot: Deltas beginnen mit „+“ oder dem ASCII-„-“."""
    at = _fresh_app()
    deltas = [m.delta for m in at.metric if m.delta]
    assert deltas and all(not d.startswith("−") and "−" not in d.split(" ")[0] for d in deltas), deltas
