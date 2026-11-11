"""Heuristisches Pricing: erst gelockert, exakt nur zum Beweis - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Spaltenerzeugung mit Etikettenlimit im Preisproblem: Handbeispiel Schritt für Schritt und als ganze Schleife, Live-Rechnung auf einer Zufallsinstanz mit bis zu 30 Kunden (immer exakt gegen
Limit zuerst, Labels und Runden gezählt, Sekunden nur zur Information), ein Rechner für die Frage, wann sich das Limit nicht mehr lohnt, und die festen Messreihen (46 Instanzen).

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import hpr_constants as C
import hpr_evaluation as ev
from hpr_layout import dunkles_design, kopf_css
from hpr_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from hpr_scenario import hand_first_duals, hand_instance
from hpr_visualization import (
    build_band_chart,
    build_hand_map,
    build_kipp_chart,
    build_loop_chart,
    build_round_chart,
    build_time_chart,
)

st.set_page_config(page_title="Heuristisches Pricing – Sebastian Hanisch", layout="wide")

TYP_NAMES = {"zufall": "zufällig verteilt", "cluster": "gruppiert"}


@st.cache_data(show_spinner=False)
def _hand_overview():
    return ev.hand_overview()


@st.cache_data(show_spinner=False)
def _hand_events(limit):
    res = ev.hand_run(limit)
    return ev.event_rows(res), res.best


@st.cache_data(show_spinner=False)
def _hand_story(limit):
    return ev.displacement_story(limit)


@st.cache_data(show_spinner=False)
def _hand_enumeration():
    return ev.hand_enumeration()


@st.cache_data(show_spinner=False)
def _hand_loop(limit, max_new):
    return ev.hand_colgen(None, max_new), ev.hand_colgen(limit, max_new)


@st.cache_data(show_spinner=False)
def _hand_lp():
    return ev.hand_all_routes_lp()


@st.cache_data(show_spinner=False)
def _live(n, width, typ, k, limit, seed):
    return ev.live_runs(ev.Settings(n, width, typ, k, limit, seed))


@st.cache_data(show_spinner=False)
def _bands():
    return ev.load_bands()


@st.cache_data(show_spinner=False)
def _zeit():
    return ev.load_zeit()


def _delta(x) -> str:
    """Differenz „mein Wert minus Bezug“ mit Vorzeichen. Streamlit erkennt die Richtung am ASCII-Zeichen „-“ am Anfang (ein echtes Minuszeichen „−“ zeigte einen Pfeil nach oben und die falsche Farbe)."""
    return ("+" if x > 0 else "-") + ev.fmt_int(abs(x)).replace("−", "-")


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in hpr_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🧩 Heuristisches Pricing: erst gelockert, exakt nur zum Beweis")
st.markdown(
    """
Die **Spaltenerzeugung** löst eine große Routenplanung in Runden: Ein **Master-Problem** (ein lineares Programm) wählt aus den bisher bekannten Routen die billigste Überdeckung der Kunden und liefert **Dualpreise**
(der Betrag, den es jedem Kunden zurechnet). Das **Pricing** sucht dann eine neue Route mit negativen **reduzierten Kosten** (Weglänge minus die Dualpreise der besuchten Kunden); findet es keine, ist die Schranke bewiesen.
Gesucht wird mit dem **Label-Verfahren**: Teilwege (**Labels**) werden Kunde für Kunde verlängert, dominierte gestrichen. Diese Demo fragt: **Muss jedes Pricing beweisen, dass es die beste Route gefunden hat? Oder genügt es, in den meisten Runden irgendeine gute neue Route
zu finden, und der teure exakte Aufruf kommt erst, wenn die Heuristik nichts mehr findet?** Die Heuristik ist ein **Etikettenlimit**: Jeder Kunde darf höchstens L lebende Labels behalten. Gemessen werden **Labels** und **Runden**, keine Sekunden.

**Die Endschranke bleibt dieselbe** (die Rechnung endet erst, wenn das exakte Pricing nichts findet). Was sich ändert, sind die Zahl der Labels und die Zahl der Runden, also der Master-Aufgaben; ob das Zeit spart, hängt daran, wie teuer ein Master-LP im Vergleich zu den Labels ist.
Gemessen ist das für eine bestimmte Größe und einen bestimmten Aufbau (30 Kunden, Gedächtnis 8, Überdeckungs-Master, Python); die Experimente nennen ihre Voraussetzungen.

Weiter unten: der Expander **So funktioniert heuristisches Pricing** (zuerst), fünf Experimente (**🔬**), **🚧 Wo die Annahmen enden**, **📐 Mathematische Formulierung** und **⚠️ Annahmen, Grenzen und bekannte Probleme**.
Die Anwendung in einem Fall (Besatzungsplanung im Zugverkehr) zeigt [crew-pairing-demo](https://github.com/sebastian-hanisch/crew-pairing-demo). Aus derselben Linie: [pricing-dualpreise-demo](https://github.com/sebastian-hanisch/pricing-dualpreise-demo) (die Schleife Master–Pricing),
[elementar-pricing-demo](https://github.com/sebastian-hanisch/elementar-pricing-demo) (jeden Kunden höchstens einmal besuchen) und [eimer-labeling-demo](https://github.com/sebastian-hanisch/eimer-labeling-demo) (Sparmaßnahme im Pricing, die das Ergebnis nie ändert).
Nicht zu verwechseln mit [hub-labeling-demo](https://github.com/sebastian-hanisch/hub-labeling-demo): Dort sind Labels vorberechnete Listen für schnelle Abfragen kürzester Wege, hier sind es Teilwege im Preisproblem.
"""
)

with st.expander("So funktioniert heuristisches Pricing", expanded=True):
    st.markdown(
        """
1. **Die Schleife:** Das Master-Problem liefert Dualpreise; das Pricing sucht Routen, deren Länge kleiner ist als die Summe der Dualpreise ihrer Kunden (negative reduzierte Kosten). Diese Routen kommen als neue Spalten in den Master. Das wiederholt sich, bis das Pricing nichts mehr findet.
2. **Exaktes Pricing beweist:** Findet das exakte Pricing keine Route mit negativen reduzierten Kosten, gibt es keine; die Dualpreise passen dann zu allen zulässigen Routen (bei Gedächtnis k < n sind das die ng-Routen), und der Master ist optimal über alle. Dafür muss es alle Labels erzeugen, die nicht dominiert sind: Das ist der teure Teil.
3. **Das Etikettenlimit** ist die Abkürzung: Ein Kunde behält höchstens L lebende Labels. Kommt ein weiteres, fliegt das mit den größten Kosten (das neue eingeschlossen). Das Limit sieht nur die Kosten; es kann einen Teilweg verlieren, den der beste Weg braucht. Es liefert oft gute Routen, aber nie einen Beweis.
4. **Heuristisch zuerst:** Erst läuft das Limit-Pricing. Findet es mindestens eine neue Spalte, geht es mit dieser weiter. Findet es keine, läuft das exakte Pricing; **nur wenn auch dieses nichts findet, endet die Rechnung.** So bleibt die Endschranke dieselbe wie bei immer exaktem Pricing.
5. **Der Preis:** Die Limit-Spalten sind schwächer als die besten Routen, die Schleife braucht daher meist mehr Runden (mehr Master-Aufgaben). Wer spart, hängt also an einem Verhältnis: Labels, die das Limit spart, gegen Master-Aufgaben, die es zusätzlich kostet.

Merksatz: **Das Limit spart Labels und kostet Runden; der Beweis am Ende bleibt exakt.** Die Zahlen dazu stehen in den Experimenten 3 bis 5, das Handbeispiel (Experimente 1 und 2) zeigt den Mechanismus im Kleinen.
"""
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Szenario ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Handbeispiel** (Experimente 1 und 2)")
    hand_limit = st.radio("Etikettenlimit L (Handbeispiel)", C.HAND_LIMIT_OPTIONS, key="hand_limit_radio", horizontal=True,
                          help="Wie viele lebende Labels jeder der sechs Kunden im Handbeispiel höchstens behält. Mit L = 1 verfehlt das Limit den besten Weg des ersten Preisproblems.")
    hand_new = st.radio("Neue Spalten je Runde", C.HAND_NEW_OPTIONS, key="hand_new_radio", horizontal=True,
                        help="Wie viele neue Routen (die besten mit negativen reduzierten Kosten) das Pricing je Runde in den Master gibt (Experiment 2); die Handrechnung nimmt 3.")
    st.markdown("**Zufallsinstanz** (Ergebnis und Experiment 3)")
    n = st.slider("Kunden n", *bounds("n_slider"), key="n_slider", help="Zahl der Kunden der Zufallsinstanz (8 bis 30).")
    width = st.radio("Fensterbreite", C.WIDTH_OPTIONS, key="width_radio", horizontal=True, help="Breite der Zeitfenster der Kunden in Zeiteinheiten (Horizont 300). Die festen Messreihen (Experiment 5) haben Breite 100 und 150.")
    typ = st.radio("Verteilung der Kunden", C.TYP_OPTIONS, key="typ_radio", horizontal=True, format_func=TYP_NAMES.get, help="Zufällig im Quadrat verteilt oder in fünf Gruppen.")
    k = st.radio("Gedächtnis k", C.K_OPTIONS, key="k_radio", horizontal=True,
                 help="Wie viele Nachbarn jedes Kunden die Route „im Gedächtnis“ behält (ng-Nachbarschaft): Ein Kunde darf erst wieder besucht werden, wenn ihn die Route aus dem Gedächtnis verloren hat. Größer heißt genauer und teurer. Die festen Messreihen rechnen mit 8.")
    limit = st.radio("Etikettenlimit L (Zufallsinstanz)", C.LIMIT_OPTIONS, key="limit_radio", horizontal=True, help="Wie viele lebende Labels jeder Kunde im Limit-Pricing höchstens behält.")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    st.markdown("**Rechner** (Experiment 4)")
    master_cost = st.select_slider("Kosten eines Master-LPs in Labels (Annahme)", C.MASTER_COST_OPTIONS, key="master_cost_select",
                                   help="Wie viele Labels des exakten Preisproblems ein Master-LP kostet. Voreinstellung 380: so viel kostete es im Rechner der Zeitmessung (3,18 ms gegen 8,34 µs je Label); für jeden anderen Aufbau ist es eine Annahme.")
    label_cost = st.slider("Kosten eines Limit-Labels im Verhältnis zu einem exakten (Annahme)", *bounds("label_cost_slider"), key="label_cost_slider", step=C.LABEL_COST_STEP,
                           help="1: Ein Label im Limit-Pricing kostet so viel wie eins im exakten Pricing. Kleiner als 1: Labels sind im Limit-Pricing billiger, weil die Dominanzprüfung nur wenige lebende Labels ansieht. Voreinstellung 1.")

sync_query_params({"hand_limit_radio": int(hand_limit), "hand_new_radio": int(hand_new), "n_slider": int(n), "width_radio": int(width), "typ_radio": typ, "k_radio": int(k), "limit_radio": int(limit),
                   "seed_input": int(seed), "master_cost_select": int(master_cost), "label_cost_slider": float(label_cost)})

inst_args = (int(n), int(width), typ, int(k), int(limit), int(seed))
instance_text = f"{n} Kunden, {TYP_NAMES[typ]}, Fensterbreite {width}, Gedächtnis {k}, Zufalls-Seed {seed}"

# --- Ergebnis: Zufallsinstanz ---------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis: eine Zufallsinstanz")
with st.spinner("Spaltenerzeugung rechnen (immer exakt und mit Limit) …"):
    exact, heur = _live(*inst_args)
st.markdown(f"Instanz: **{instance_text}** (Kapazität 70, Horizont 300, Überdeckungs-Master, höchstens 15 neue Spalten je Runde). Zweimal dieselbe Spaltenerzeugung: **immer exakt** und **Limit {limit} zuerst, exakt nur zum Beweis**.")
kind, text = ev.verdict_bound(exact, heur)
if exact.aborted or heur.aborted:
    st.warning(text)
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Labels, immer exakt", ev.fmt_int(exact.labels), help=f"Erzeugte Labels über alle {exact.iters} Runden (Start-Labels und sofort verworfene mitgezählt).")
    m2.metric(f"Labels, Limit {limit}", ev.fmt_int(heur.labels), delta=_delta(heur.labels - exact.labels) if heur.labels != exact.labels else "wie exakt", delta_color="inverse" if heur.labels != exact.labels else "off",
              help=f"Davon {ev.fmt_int(heur.labels_heur)} im Limit-Pricing und {ev.fmt_int(heur.labels_exact)} im exakten Pricing.")
    m3.metric("Runden (Master-Aufgaben)", f"{heur.iters}", delta=_delta(heur.iters - exact.iters) + " gegen exakt" if heur.iters != exact.iters else "wie exakt", delta_color="inverse" if heur.iters != exact.iters else "off",
              help=f"Bei immer exaktem Pricing {exact.iters} Runden.")
    m4.metric("Exakte Aufrufe", f"{heur.exact_calls}", delta=_delta(heur.exact_calls - exact.exact_calls) + " gegen exakt" if heur.exact_calls != exact.exact_calls else "wie exakt",
              delta_color="inverse" if heur.exact_calls != exact.exact_calls else "off", help=f"Bei immer exaktem Pricing {exact.exact_calls} (jede Runde).")

    # --- Kernfrage -------------------------------------------------------------------------------------------------------------------------

    st.markdown("## ❓ Kernfrage: Was spart das Limit, und was kostet es?")
    getattr(st, kind)(text)
    kind, text = ev.verdict_labels(exact, heur, int(limit))
    getattr(st, kind)(text)
    kind, text = ev.verdict_round1(exact, heur)
    getattr(st, kind)(text)
    kind, text = ev.verdict_time(exact, heur)
    getattr(st, kind)(text)
    st.caption("Das ist eine einzelne Instanz. Wie stark die Ersparnis über viele Instanzen streut, zeigt Experiment 5 (46 feste Instanzen mit Mittel, Minimum und Maximum).")

st.markdown("---")

# --- Experiment 1 --------------------------------------------------------------------------------------------------------------------------

inst_h = hand_instance()
pi_h = hand_first_duals(inst_h)
st.subheader("🔬 Experiment 1: Das Limit Schritt für Schritt (Handbeispiel)")
st.markdown(
    f"Ein Fahrzeug startet im Depot D (Gitterpunkt {inst_h.points[0]}) und besucht Kunden. **Entfernung = Fahrzeit = Kosten = Manhattan-Abstand**, Bedienzeit {inst_h.service}, Rückkehr spätestens zur Zeit {inst_h.horizon}, "
    f"Last höchstens {inst_h.capacity}; wer vor Beginn seines Fensters ankommt, wartet kostenlos; jeder Kunde höchstens einmal. Die **Dualpreise** sind die der ersten Runde einer Überdeckungs-Rechnung: der Dualpreis eines Kunden ist die Länge seiner Einzelroute "
    "Depot – Kunde – Depot. Reduzierte Kosten einer Route = Summe der Entfernungen minus Summe der Dualpreise der besuchten Kunden."
)
st.dataframe(pd.DataFrame({
    "Kunde": list(range(1, inst_h.n + 1)),
    "Punkt": [f"({inst_h.points[i][0]}, {inst_h.points[i][1]})" for i in range(1, inst_h.n + 1)],
    "Zeitfenster [früh, spät]": [f"[{inst_h.ready[i]}, {inst_h.due[i]}]" for i in range(1, inst_h.n + 1)],
    "Last": [inst_h.demand[i] for i in range(1, inst_h.n + 1)],
    "Dualpreis (Einzelroute)": [ev.fmt_num(pi_h[i]) for i in range(1, inst_h.n + 1)],
}), hide_index=True, width="stretch")
hand_rows = _hand_overview()
hbase = hand_rows[0]
hsel = next(r for r in hand_rows if r["limit"] == int(hand_limit))
h1, h2, h3, h4 = st.columns(4)
h1.metric("Labels exakt", hbase["generated"], help="Das Start-Label im Depot eingeschlossen; sofort verworfene Labels zählen mit.")
h2.metric(f"Labels, Limit {hand_limit}", hsel["generated"], delta=_delta(hsel["generated"] - hbase["generated"]) if hsel["generated"] != hbase["generated"] else "wie exakt",
          delta_color="inverse" if hsel["generated"] != hbase["generated"] else "off")
h3.metric("Limit angewendet", hsel["limited"], help="Wie oft ein Kunde voll war und ein Label wegen des Limits fliegen musste (das neue oder ein lebendes).")
h4.metric("Negative Routen", hsel["n_routes"], help="Gelieferte Routen mit negativen reduzierten Kosten (das Label-Verfahren liefert nicht alle: Routen über dominierte Labels entstehen nicht).", delta=_delta(hsel["n_routes"] - hbase["n_routes"]) if hsel["n_routes"] != hbase["n_routes"] else "wie exakt", delta_color="off")
kind, text = ev.verdict_hand_pricing(hand_rows, int(hand_limit))
getattr(st, kind)(text)
enum = _hand_enumeration()
best_enum = enum[0]
ok_enum = hbase["best"] is not None and hbase["best"][1] == best_enum[1] and abs(hbase["best"][0] - best_enum[0]) < 1e-9
if not ok_enum:
    st.error("Das exakte Pricing findet nicht die beste Route der Aufzählung: Der Kern ist fehlerhaft.")
st.plotly_chart(build_hand_map(inst_h, hbase["best"][1], hsel["best"][1] if hsel["best"] else None), width="stretch", key="hand_map")
st.caption(f"Die Aufzählung aller {len(enum)} zulässigen elementaren Routen (ohne Labels) bestätigt: Die beste Route ist {ev.route_text(best_enum[1])} mit reduzierten Kosten {ev.fmt_num(best_enum[0])}; "
           f"{sum(1 for rc, _ in enum if rc < 0)} von ihnen haben negative reduzierte Kosten; das Label-Verfahren liefert {hbase['n_routes']} davon (Routen über gestrichene, dominierte Labels entstehen nicht).")
story = _hand_story(int(hand_limit))
if story is not None:
    st.markdown(
        f"**Warum das Limit hier scheitert.** Das Label {ev.label_name(story['victim'])} (Weg {ev.route_text(story['victim_path'])}; Kosten {ev.fmt_num(story['victim_cost'])}, Last {story['victim_load']}) wird von "
        f"{ev.label_name(story['newcomer'])} (Weg {ev.route_text(story['newcomer_path'])}; Kosten {ev.fmt_num(story['newcomer_cost'])}, Last {story['newcomer_load']}) verdrängt: Das neue Label ist **billiger** "
        f"({ev.fmt_num(story['newcomer_cost'])} gegen {ev.fmt_num(story['victim_cost'])}), und der Kunde darf nur {hand_limit} Label(s) behalten."
        + (f" Von {ev.label_name(story['newcomer'])} aus kann Kunde {story['next']} nicht mehr bedient werden ({story['reason']}); " if story["reason"] else " ")
        + (f"von {ev.label_name(story['victim'])} aus ging es, und es ergab die beste Route ({ev.route_text(story['best_route'])}) mit {ev.fmt_num(story['best_rc'])}. " if story["victim_can"] else "")
        + "Das Limit sieht nur die Kosten, nicht, dass das billigere Label voller ist. Der exakte Aufruf findet die beste Route."
    )
else:
    st.markdown(f"Hier verfehlt das Limit den besten Weg nicht. Es lässt aber trotzdem {hsel['limited']}-mal ein Label fliegen (Tabelle unten); ob das später etwas kostet, hängt davon ab, ob der beste Weg über ein verdrängtes Label gelaufen wäre.")
events, _best = _hand_events(int(hand_limit))
only_limit = [e for e in events if e["limit"]]
st.markdown(f"**Alle {len(only_limit)} Entscheidungen des Limits** (Limit {hand_limit}; {len(events)} neue Labels insgesamt):")
st.dataframe(pd.DataFrame({
    "Label": [e["label"] for e in only_limit],
    "Kunde": [e["node"] for e in only_limit],
    "Weg": [ev.route_text(e["path"]) for e in only_limit],
    "Zeit": [ev.fmt_num(e["time"]) for e in only_limit],
    "Kosten": [ev.fmt_num(e["cost"]) for e in only_limit],
    "Last": [e["load"] for e in only_limit],
    "Entscheidung": [e["decision"] for e in only_limit],
}), hide_index=True, width="stretch", height=min(420, 38 + 35 * max(len(only_limit), 1)))
if st.checkbox("Alle neuen Labels dieses Laufs zeigen", key="show_all_labels"):
    st.dataframe(pd.DataFrame({
        "Label": [e["label"] for e in events],
        "Kunde": [e["node"] for e in events],
        "Weg": [ev.route_text(e["path"]) for e in events],
        "Zeit": [ev.fmt_num(e["time"]) for e in events],
        "Kosten": [ev.fmt_num(e["cost"]) for e in events],
        "Last": [e["load"] for e in events],
        "Lebende Labels am Kunden vorher": [e["live_before"] for e in events],
        "Entscheidung": [e["decision"] for e in events],
    }), hide_index=True, width="stretch", height=420)
st.markdown("**Alle Limits im Vergleich** (erstes Preisproblem, dieselben Dualpreise):")
st.dataframe(pd.DataFrame({
    "Pricing": [r["name"] for r in hand_rows],
    "Erzeugte Labels": [r["generated"] for r in hand_rows],
    "Limit angewendet": [r["limited"] for r in hand_rows],
    "Negative Routen": [r["n_routes"] for r in hand_rows],
    "Beste gefundene Route": [ev.route_text(r["best"][1]) if r["best"] else "keine" for r in hand_rows],
    "Reduzierte Kosten": [ev.fmt_num(r["best"][0]) if r["best"] else "–" for r in hand_rows],
    "Besten Weg gefunden": ["ja" if r["found_best"] else "NEIN" for r in hand_rows],
}), hide_index=True, width="stretch")

st.markdown("---")

# --- Experiment 2 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 2: Die ganze Schleife im Kleinen (Handbeispiel)")
st.caption(
    "Die Spaltenerzeugung des Handbeispiels mit Überdeckungs-Master (jeder Kunde mindestens einmal; Anfangsspalten sind die sechs Einzelrouten; das Master-LP ist hier mit Brüchen exakt gelöst). Links immer exaktes Pricing, rechts das Limit zuerst: "
    "Findet es nichts Neues, läuft der exakte Aufruf, und erst wenn auch der nichts findet, endet die Rechnung."
)
ex_h, he_h = _hand_loop(int(hand_limit), int(hand_new))
lp_z, lp_pi = _hand_lp()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Endschranke", ev.fmt_num(he_h.bound), help=f"Gleich bei immer exaktem Pricing ({ev.fmt_num(ex_h.bound)}) und gleich dem Master über alle {len(enum)} zulässigen Routen ({ev.fmt_num(lp_z)}).")
c2.metric("Labels", he_h.labels, delta=_delta(he_h.labels - ex_h.labels) + " gegen exakt" if he_h.labels != ex_h.labels else "wie exakt", delta_color="inverse" if he_h.labels != ex_h.labels else "off",
          help=f"Bei immer exaktem Pricing {ex_h.labels}; davon {he_h.labels_heur} im Limit-Pricing und {he_h.labels_exact} im exakten.")
c3.metric("Runden", he_h.iters, delta=_delta(he_h.iters - ex_h.iters) + " gegen exakt" if he_h.iters != ex_h.iters else "wie exakt", delta_color="inverse" if he_h.iters != ex_h.iters else "off", help=f"Bei immer exaktem Pricing {ex_h.iters}.")
c4.metric("Exakte Aufrufe", he_h.exact_calls, delta=_delta(he_h.exact_calls - ex_h.exact_calls) + " gegen exakt" if he_h.exact_calls != ex_h.exact_calls else "wie exakt", delta_color="inverse" if he_h.exact_calls != ex_h.exact_calls else "off",
          help=f"Das Limit reichte in {he_h.heur_ok} von {he_h.iters} Runden.")
kind, text = ev.verdict_hand_loop(ex_h, he_h, lp_z, int(hand_limit))
getattr(st, kind)(text)
loop = ev.loop_rows(ex_h, he_h)
table_rows = []
for r in loop:
    a_master, a_pricing, a_new = ev.round_text(r["exact"])
    b_master, b_pricing, b_new = ev.round_text(r["heur"])
    table_rows.append({"Runde": r["nr"], "Master (immer exakt)": a_master, "Pricing (immer exakt)": a_pricing, "Neue Spalten und Kosten (immer exakt)": a_new,
                       f"Master (Limit {hand_limit})": b_master, f"Pricing (Limit {hand_limit})": b_pricing, f"Neue Spalten und Kosten (Limit {hand_limit})": b_new})
st.dataframe(pd.DataFrame(table_rows), hide_index=True, width="stretch")
st.plotly_chart(build_loop_chart(ex_h, he_h, int(hand_limit)), width="stretch", key="loop_chart")
st.caption(f"Das Master-LP über alle {len(enum)} zulässigen Routen hat den Wert {ev.fmt_num(lp_z)} und die Dualpreise ({', '.join(ev.fmt_num(x) for x in lp_pi[1:])}); beide Schleifen enden dort. "
           "„π“ sind die Dualpreise der Runde, „z“ der Zielwert des Masters; in jeder Runde stehen bis zu so viele neue Spalten, wie der Regler „Neue Spalten je Runde“ sagt.")

st.markdown("---")

# --- Experiment 3 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 3: Wo die Labels gespart werden und wo die Zeit hingeht (Zufallsinstanz)")
if exact.aborted or heur.aborted:
    st.info("Dieses Experiment braucht zwei fertige Rechnungen der Zufallsinstanz, die hier nicht fertig wurden (siehe oben); mit einer kleineren Instanz rechnen sie.")
else:
    st.caption(
        f"Dieselbe Instanz wie oben ({instance_text}). Je Runde die erzeugten Labels: oben bei immer exaktem Pricing, unten mit Limit {limit} (orange: Limit-Pricing, blau: exakter Aufruf, nur wenn das Limit nichts Neues fand). "
        "Beide Läufe haben in Runde 1 dieselben Dualpreise."
    )
    st.plotly_chart(build_round_chart(exact, heur, int(limit)), width="stretch", key="round_chart")
    st.dataframe(pd.DataFrame({
        "": ["Labels", "davon im Limit-Pricing", "davon im exakten Pricing", "Runden", "Runden, in denen das Limit reichte", "exakte Aufrufe", "Spalten am Ende", "Endschranke"],
        "immer exakt": [ev.fmt_int(exact.labels), "–", ev.fmt_int(exact.labels_exact), str(exact.iters), "–", str(exact.exact_calls), str(exact.cols), ev.fmt_dec(exact.bound, 2)],
        f"Limit {limit} zuerst": [ev.fmt_int(heur.labels), ev.fmt_int(heur.labels_heur), ev.fmt_int(heur.labels_exact), str(heur.iters), str(heur.heur_ok), str(heur.exact_calls), str(heur.cols), ev.fmt_dec(heur.bound, 2)],
    }), hide_index=True, width="stretch")
    st.markdown("**Wohin die Zeit geht** (Wanduhr in Sekunden, **nur Information**: Der Rechner ist nicht ruhig und rechnet mehrere Sitzungen; gezählt werden Labels):")
    st.dataframe(pd.DataFrame({
        "": ["Master-LP", "Pricing mit Limit", "exaktes Pricing", "gesamt"],
        "immer exakt (s)": [ev.fmt_dec(exact.t_master, 2), "–", ev.fmt_dec(exact.t_exact, 2), ev.fmt_dec(exact.t_total, 2)],
        f"Limit {limit} zuerst (s)": [ev.fmt_dec(heur.t_master, 2), ev.fmt_dec(heur.t_heur, 2), ev.fmt_dec(heur.t_exact, 2), ev.fmt_dec(heur.t_total, 2)],
    }), hide_index=True, width="stretch")
    st.caption("Bei einer so kleinen Instanz sind die Zeiten kurz und streuen stark; der Master-Löser (HiGHS) und die Label-Verfahren laufen in Python. Die gemessene Zeitreihe steht in Experiment 5.")

st.markdown("---")

# --- Experiment 4 --------------------------------------------------------------------------------------------------------------------------

bands = _bands()
zeit = _zeit()
mstats = ev.model_stats(bands, 100)
costs = ev.time_costs(zeit, bands)
st.subheader("🔬 Experiment 4: Wann kippt es? (Rechner)")
st.markdown(
    "Das Limit spart Labels und kostet Runden. Ein Modell: **Aufwand = Kosten je Limit-Label × Labels im Limit-Pricing + Labels im exakten Pricing + Kosten eines Master-LPs × Runden**, gemessen in „Labels des exakten Preisproblems“. "
    "Die Zahl der Labels und Runden stammt aus den 30 gemessenen Instanzen der Breite 100 (Experiment 5, Summen über die Instanzen); **die Kosten eines Master-LPs und eines Limit-Labels sind Annahmen** (Regler in der Seitenleiste). "
    "Unterhalb der Kipp-Stelle (Raute) ist das Limit im Modell billiger als immer exaktes Pricing, darüber nicht."
)
rows4 = []
for v in C.BAND_VARIANTS[1:]:
    ratio = ev.model_ratio(mstats[v], mstats["exakt"], float(master_cost), float(label_cost))
    be = ev.break_even(mstats[v], mstats["exakt"], float(label_cost))
    rows4.append({"Limit": v, "Aufwand gegen immer exakt (Modell)": ev.fmt_ratio(ratio), "Lohnt sich bei den gewählten Kosten?": "ja" if ratio < 1 else "NEIN",
                  "Kipp-Stelle (Labels je Master-LP, Modell)": "kippt nie" if be is None else ev.fmt_int(round(be, -2) if be >= 1000 else be)})
kind, text = ev.verdict_kipp(mstats, float(master_cost), float(label_cost))
getattr(st, kind)(text)
st.plotly_chart(build_kipp_chart(mstats, float(label_cost), float(master_cost)), width="stretch", key="kipp_chart")
st.dataframe(pd.DataFrame(rows4), hide_index=True, width="stretch")
tz = next(r for r in ev.zeit_table(zeit) if r["variante"] == "exakt")
st.caption(
    f"**Was gemessen ist** (CPU-Zeit der Zeitmessung der Vormessung, 30 Instanzen mit Breite 100, bei immer exaktem Pricing; Rechner ausgelastet, nur Größenordnung): Ein Master-LP kostet im Mittel {ev.fmt_dec(costs['master_ms'], 2)} ms, ein Label im exakten Pricing "
    f"{ev.fmt_dec(costs['label_exact_us'], 2)} µs, also kostet ein Master-LP etwa {ev.fmt_int(round(costs['master_in_labels'], -1))} Labels (Voreinstellung des Reglers); das Pricing macht {ev.fmt_pct(100 * costs['pricing_share_exact'])} der CPU-Zeit aus. "
    f"Ein Label im Limit-Pricing kostet {ev.fmt_dec(costs['limit_us']['L5'], 2)} µs bei L5, {ev.fmt_dec(costs['limit_us']['L10'], 2)} µs bei L10 und {ev.fmt_dec(costs['limit_us']['L20'], 2)} µs bei L20, im Verhältnis zum exakten "
    f"{ev.fmt_ratio(costs['limit_vs_exact']['L5'])}, {ev.fmt_ratio(costs['limit_vs_exact']['L10'])} und {ev.fmt_ratio(costs['limit_vs_exact']['L20'])}. "
    "**Deutung (nicht eigens geprüft):** Im Limit-Pricing sehen die Dominanzprüfungen weniger lebende Labels an. Mit dem Regler „Kosten eines Limit-Labels“ lässt sich das ins Modell einsetzen. "
    "Bei einem Master mit viel mehr Zeilen und Spalten oder mit Schnitten wäre das Verhältnis anders; das ist nicht gemessen."
)

st.markdown("---")

# --- Experiment 5 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 5: Die festen Messreihen (46 Instanzen)")
st.caption(
    "Fest gemessen und mit dem Kern dieser Demo neu gerechnet (nicht aus einer Messdatei übernommen): **30 Kunden**, Gedächtnis k = 8, Überdeckungs-Master, höchstens 15 neue Spalten je Runde, vier Varianten (immer exakt, Limit 5, 10 und 20). "
    "Fensterbreite 100: 15 zufällig verteilte und 15 gruppierte Instanzen (Zufalls-Seeds 0 bis 14); Fensterbreite 150: je 8 (Zufalls-Seeds 0 bis 7). **Je Typ sind es wenige Instanzen; das Verhältnis streut stark.**"
)
b1, b2 = st.columns(2)
bbreite = b1.radio("Fensterbreite", C.BAND_WIDTHS, key="band_breite", horizontal=True)
btyp_name = b2.selectbox("Instanzen", ("alle", "zufällig verteilt", "gruppiert"), key="band_typ")
btyp = {"alle": None, "zufällig verteilt": "zufall", "gruppiert": "cluster"}[btyp_name]
btable = ev.band_table(bands, int(bbreite), btyp)
st.dataframe(pd.DataFrame({
    "Variante": [r["variante"] for r in btable],
    "Instanzen": [r["n"] for r in btable],
    "Labels (Mittel)": [ev.fmt_int(r["labels_mean"]) for r in btable],
    "Labels / exakt (Mittel der Verhältnisse)": [ev.fmt_ratio(r["ratio_mean"]) for r in btable],
    "Median": [ev.fmt_ratio(r["ratio_median"]) for r in btable],
    "Minimum": [ev.fmt_ratio(r["ratio_min"]) for r in btable],
    "Maximum": [ev.fmt_ratio(r["ratio_max"]) for r in btable],
    "Instanzen mit weniger Labels": [f"{r['fewer']} von {r['n']}" if r["variante"] != "exakt" else "–" for r in btable],
    "Runden (Mittel)": [ev.fmt_dec(r["iters_mean"], 1) for r in btable],
    "Runden gegen exakt": [("+" if r["iters_vs_exact"] > 0 else "-") + ev.fmt_pct(abs(100 * r["iters_vs_exact"]), 0) if r["variante"] != "exakt" else "–" for r in btable],
    "Limit reichte (Anteil der Runden)": [ev.fmt_pct(100 * r["limit_share"]) if r["limit_share"] is not None else "–" for r in btable],
    "Exakte Aufrufe (Mittel)": [ev.fmt_dec(r["exact_calls_mean"], 1) for r in btable],
    "Labels im exakten Pricing (Anteil)": [ev.fmt_pct(100 * r["exact_label_share"]) for r in btable],
}), hide_index=True, width="stretch")
st.plotly_chart(build_band_chart(bands, int(bbreite), btyp), width="stretch", key="band_chart")
bvar = st.selectbox("Variante für das Verdikt", C.BAND_VARIANTS[1:], key="band_variant", index=C.BAND_VARIANTS[1:].index(f"L{limit}") if f"L{limit}" in C.BAND_VARIANTS else 0)
kind, text = ev.verdict_bands(bands, int(bbreite), btyp, bvar)
getattr(st, kind)(text)
n_lines = len(bands)
st.caption(
    "„Labels / exakt“ ist je Instanz die Zahl der Labels der Variante geteilt durch die bei immer exaktem Pricing; angegeben sind Mittel der Verhältnisse, Median, Minimum und Maximum über die Instanzen. "
    "„Limit reichte“ ist der Anteil der Runden, in denen das Limit-Pricing mindestens eine neue Spalte fand; trotzdem entsteht ein großer Teil der Labels im exakten Pricing, weil mindestens der Abschlussaufruf exakt sein muss. "
    f"Kein Lauf ist abgebrochen ({n_lines} Läufe); in jeder Instanz ist die Endschranke bei allen vier Varianten gleich."
)
st.markdown("**Die Zeit (Breite 100, 30 Instanzen, drei Wiederholungen, Rechner ausgelastet; nur Information):**")
zt = ev.zeit_table(zeit)
st.dataframe(pd.DataFrame({
    "Variante": [r["variante"] for r in zt],
    "CPU-Zeit, Summe (s)": [ev.fmt_dec(r["cpu_sum"], 2) for r in zt],
    "Summe / exakt": [ev.fmt_ratio(r["cpu_sum_ratio"]) for r in zt],
    "Median der Instanz-Verhältnisse (Minimum bis Maximum)": [f"{ev.fmt_ratio(r['cpu_median'])} ({ev.fmt_ratio(r['cpu_min'])} bis {ev.fmt_ratio(r['cpu_max'])})" for r in zt],
    "Mittel der Instanz-Verhältnisse": [ev.fmt_ratio(r["cpu_mean"]) for r in zt],
    "Schneller als exakt": [f"{r['cpu_faster']} von {r['n']}" if r["variante"] != "exakt" else "–" for r in zt],
    "Wanduhr, Mittel der Instanz-Verhältnisse": [ev.fmt_ratio(r["wand_mean"]) for r in zt],
}), hide_index=True, width="stretch")
st.plotly_chart(build_time_chart(zt), width="stretch", key="time_chart")
st.caption(
    "**Diese Zeitreihe stammt aus der Messdatei der Vormessung (`data/zeit_vormessung.json`, 360 Läufe) und ist nicht mit dem Kern dieser Demo neu gemessen;** die Zählungen derselben Läufe (Labels, Runden) stimmen mit den neu gerechneten überein. "
    "Der Rechner war durch andere Sitzungen ausgelastet, die Wanduhrzeit streut, die CPU-Zeit hat eine grobe Auflösung: Die Zahlen sind Größenordnungen für diesen Aufbau (Python, HiGHS, Master-LP etwa 380 Labels), keine Festschreibung. "
    "Bei Limit 20 liegt das größte Instanz-Verhältnis bei 0,98, also innerhalb der Messunschärfe: „Schneller als exakt“ ist dort nicht scharf. "
    "Bei Breite 150 ist die Zeit nicht gemessen."
)

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was gilt, wenn sie nicht stimmt | Belegt durch |
|---|---|---|
| **Das Limit ist ein Limit nach Kosten** | Die gelockerte Dominanz der Literatur ist weder gebaut noch gemessen; was hier steht, gilt nur für dieses Limit. Es kann den besten Weg einer Runde verfehlen (Handbeispiel, Limit 1). | Experiment 1 |
| **Master-LP kostet wenig gegen das Pricing (hier etwa 380 Labels)** | Je teurer der Master, desto kleiner der Gewinn; im Modell kippt es bei etwa 16 000 (L5), 22 000 (L10) und 40 000 (L20) Labels je Master-LP. Bei einem Master mit vielen Zeilen oder mit Schnitten nicht gemessen. | Experiment 4 |
| **30 Kunden, Gedächtnis 8, Überdeckungs-Master, Python** | Für größere Instanzen, andere Master und Branch-and-Price ist nichts gemessen. | Experiment 5 |
| **Wenige Instanzen je Typ** | Das Verhältnis der Labels zu „exakt“ streut je nach Instanz; ein Mittel sagt nichts über die einzelne Instanz. | Experiment 5 |
| **Zeit nur für Breite 100, mit der Messdatei der Planung** | Bei Breite 150 und bei ruhigem Rechner nicht gemessen; keine Aussage „heuristisches Pricing ist schneller“. | Experiment 5 |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Lesehilfe.** *Gegeben:* ein Depot $0$ und Kunden $1,\dots,n$ mit Entfernungen $d_{ij}$, Lasten $q_j$ und Zeitfenstern $[e_j, l_j]$. *Gesucht:* die billigste Menge von Routen, die jeden Kunden mindestens einmal überdeckt (Master-Problem), gefunden
durch Spaltenerzeugung. Das Pricing sucht Routen mit negativen reduzierten Kosten; *neu hier:* wie man es in den meisten Runden billiger macht (Etikettenlimit) und trotzdem am Ende beweist, dass keine Route fehlt.

| Symbol | Bedeutung |
|---|---|
| $R$ | Menge der zulässigen Routen; $c_r$ Länge der Route $r$ |
| $x_r$ | Master-Variable: wie oft die Route $r$ gewählt wird |
| $\pi_i$ | Dualpreis des Kunden $i$ (Schattenpreis der Überdeckungsbedingung), $\pi_0 = 0$ |
| $\bar c_r$ | reduzierte Kosten der Route $r$ |
| $s$, $H$, $Q$ | Bedienzeit je Kunde; Horizont (späteste Rückkehr); Kapazität |
| $(T, C, R, M)$ | Label: Zeit, reduzierte Kosten, verbrauchte Last, Gedächtnis (Menge) |
| $O \preceq N$ | Label $O$ dominiert Label $N$ (am selben Kunden) |
| $k$ | Größe des Gedächtnisses (ng-Nachbarschaft $NG(j)$); $k = n$ heißt elementar |
| $L$ | Etikettenlimit: höchste Zahl lebender Labels je Kunde |
| $I_v$, $\Lambda^{\mathrm{L}}_v$, $\Lambda^{\mathrm{E}}_v$ | Runden, Labels im Limit-Pricing und Labels im exakten Pricing der Variante $v$ |
| $\rho$, $\gamma$ | Kosten eines Master-LPs und eines Limit-Labels, in Labels des exakten Preisproblems (Annahmen) |

**Master (Überdeckung) und Dual.** Über einer Teilmenge $R' \subseteq R$ bekannter Routen:

$$\min \sum_{r \in R'} c_r x_r \;\;\text{u. d. N.}\;\; \sum_{r \ni i} x_r \ge 1 \;\;(i = 1,\dots,n),\; x \ge 0, \qquad \max \sum_i \pi_i \;\;\text{u. d. N.}\;\; \sum_{i \in r} \pi_i \le c_r \;\;(r \in R'),\; \pi \ge 0$$

**Reduzierte Kosten** einer Route: $\bar c_r = c_r - \sum_{i \in r} \pi_i$. Das Pricing sucht Routen mit $\bar c_r < 0$ (nicht im Master enthalten).

**Fortsetzung** eines Labels $(T, C, R, M)$ am Knoten $i$ zum Kunden $j \notin M$ (mit $s\,[i \ne 0]$: im Depot entfällt die Bedienzeit):

$$T' = \max\bigl(e_j,\; T + s\,[i \ne 0] + d_{ij}\bigr), \quad C' = C + d_{ij} - \pi_j, \quad R' = R + q_j, \quad M' = (M \cap NG(j)) \cup \{j\}$$

Zulässig ist sie, wenn $T + s\,[i \ne 0] + d_{ij} \le l_j$ und $R' \le Q$ gelten. **Dominanz:**

$$O \preceq N \iff C_O \le C_N, \quad T_O \le T_N, \quad R_O \le R_N, \quad M_O \subseteq M_N$$

**Etikettenlimit.** Nach der Dominanzprüfung hält der Kunde $j$ die Menge $S_j$ lebender Labels. Ist $|S_j| \ge L$, sei $O^\ast \in S_j$ das Label mit den größten Kosten $C$ (bei Gleichstand das früher eingefügte). Gilt $C_{O^\ast} \le C_N$, fliegt das neue Label
$N$, sonst fliegt $O^\ast$ und $N$ bleibt. Ohne Limit ($L = \infty$) ist das Verfahren exakt; mit Limit kann es ein Label verlieren, das der beste Weg braucht (ein billigeres Label mit mehr Last oder späterer Zeit verdrängt es).

**Spaltenerzeugung mit Limit zuerst.** In jeder Runde: Master lösen, $\pi$ lesen; Pricing mit Limit $L$; findet es eine neue Route mit $\bar c < 0$, in den Master und weiter. Sonst exaktes Pricing; findet es eine, weiter; findet es keine, **Ende**.
Am Ende gilt $\bar c_r \ge 0$ für alle zulässigen Routen $r$ (das exakte Pricing hat alle geprüft), also ist $\pi$ zulässig im Dual über allen Routen und der Zielwert des Masters gleich dem LP-Optimum über alle zulässigen Routen (bei Gedächtnis $k < n$ alle ng-Routen): **Die Endschranke hängt nicht vom Limit ab.**
Dass die Rechnung mit Limit dieselbe Schranke erreicht, ist zusätzlich in allen 46 Instanzen der Messreihen und im Handbeispiel (gegen das LP über alle 65 Routen) geprüft.

**Modell des Aufwands (Experiment 4).** In Labels des exakten Preisproblems, mit $\rho$ den Kosten eines Master-LPs und $\gamma$ den Kosten eines Limit-Labels (beide angenommen):

$$A_{\mathrm{exakt}} = \Lambda^{\mathrm{E}}_{\mathrm{exakt}} + \rho\, I_{\mathrm{exakt}}, \qquad A_v = \gamma\, \Lambda^{\mathrm{L}}_v + \Lambda^{\mathrm{E}}_v + \rho\, I_v, \qquad \rho^\ast_v = \frac{\Lambda^{\mathrm{E}}_{\mathrm{exakt}} - \gamma\, \Lambda^{\mathrm{L}}_v - \Lambda^{\mathrm{E}}_v}{I_v - I_{\mathrm{exakt}}} \;\;(I_v > I_{\mathrm{exakt}})$$

Für $\rho < \rho^\ast_v$ ist $A_v < A_{\mathrm{exakt}}$, das Limit lohnt sich im Modell. Das Modell ist eine Rechnung mit Annahmen, keine Messung der Laufzeit.

**Zählgrößen.** *Labels:* jedes erzeugte Label, auch ein sofort verworfenes, plus das Start-Label je Preisproblem-Aufruf. *Runden:* Zahl der Master-Aufgaben. *Limit reichte:* Runden, in denen das Limit-Pricing mindestens eine neue Spalte fand.

**Literatur** (Prüfstand: was gelesen wurde, steht dabei; die Demo übernimmt keine Zahl daraus). Für das Schema „heuristisches Pricing zuerst, exakt nur zum Beweis“ als Ganzes wurde keine eigene Quelle gefunden; die Demo stellt es als Messung dar.
- Salani, Basso (arXiv 2306.08622): Literaturteil gelesen; er nennt Heuristiken im Pricing mit gelockerten Dominanzregeln und mit Etikettenlimits je Knoten. Die dort zitierten Originalarbeiten wurden nicht gesehen und sind deshalb hier nicht aufgeführt.
- Basso, Salani (arXiv 2605.03760): Literaturteil gelesen.
        """
    )

st.markdown("---")

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(C.ASSUMPTIONS_MARKDOWN)

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html)."
)
