"""Auswertung: Handbeispiel, Live-Läufe, Kipp-Rechner, feste Messreihen, Zahlenformate und die Verdikte der App (reine Funktionen: Art, Text; DEMO-PLAYBOOK §12)."""

import itertools
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import hpr_algorithm as A
import hpr_colgen as G
import hpr_constants as C
from hpr_scenario import Instance, hand_first_duals, hand_instance, make_instance

DATA = Path(__file__).resolve().parent / "data"


# --- Formate --------------------------------------------------------------------------------------------------------------------------------

def fmt_int(n) -> str:
    """Ganze Zahl mit Leerzeichen als Tausendertrenner (4 424 statt 4424), echtes Minuszeichen."""
    return f"{int(round(n)):,}".replace(",", " ").replace("-", "−")


def fmt_dec(x: float, digits: int = 1) -> str:
    """Dezimalzahl mit deutschem Komma und immer gleich vielen Nachkommastellen (echtes Minuszeichen)."""
    return f"{x:.{digits}f}".replace(".", ",").replace("-", "−")


def fmt_pct(x: float, digits: int = 1) -> str:
    """Prozentwert (x ist schon in Prozent) mit deutschem Komma."""
    return f"{fmt_dec(x, digits)} %"


def fmt_ratio(x: float) -> str:
    """Verhältnis mit zwei Nachkommastellen und deutschem Komma (0,52)."""
    return fmt_dec(x, 2)


def fmt_num(x: float) -> str:
    """Zahl ohne Nachkommastellen, wenn sie ganz ist (Handbeispiel), sonst mit einer."""
    return fmt_int(x) if abs(x - round(x)) < 1e-9 else fmt_dec(x, 1)


def route_text(route) -> str:
    return " → ".join(str(j) for j in route) if route else "keine"


def label_name(nr: int) -> str:
    return f"F{nr:02d}"


def limit_name(limit) -> str:
    return "ohne Limit (exakt)" if limit is None else f"Limit {limit}"


# --- Handbeispiel ---------------------------------------------------------------------------------------------------------------------------

def hand_run(limit, trace: bool = True) -> A.PricingResult:
    """Ein Preisproblem-Aufruf am Handbeispiel bei den Dualpreisen der ersten Runde (alle negativen Routen, Gedächtnis elementar)."""
    return A.price(hand_instance(), hand_first_duals(), C.HAND_K, limit=limit, max_routes=10 ** 6, trace=trace)


def enumerate_routes(inst: Instance) -> list:
    """Gegenprobe ohne Labels: alle zulässigen elementaren Routen (Aufzählung aller Reihenfolgen), als Liste von Routen."""
    out = []
    for r in range(1, inst.n + 1):
        for perm in itertools.permutations(range(1, inst.n + 1), r):
            if A.check_route(inst, (0,) * (inst.n + 1), perm) is not None:
                out.append(perm)
    return out


def hand_enumeration() -> list:
    """Alle zulässigen elementaren Routen des Handbeispiels mit ihren reduzierten Kosten bei den Dualpreisen der ersten Runde, beste zuerst (bei Gleichstand nach Route)."""
    inst, pi = hand_instance(), hand_first_duals()
    return sorted((A.check_route(inst, pi, r), r) for r in enumerate_routes(inst))


def hand_overview() -> list:
    """Eine Zeile je Etikettenlimit (ohne, 1, 2, 3) für das erste Preisproblem: Labels, wie oft das Limit angewendet wurde, beste Route, Zahl der negativen Routen, besten Weg gefunden?"""
    base = hand_run(None, trace=False)
    rows = []
    for limit in (None,) + C.HAND_LIMIT_OPTIONS:
        r = base if limit is None else hand_run(limit, trace=False)
        rows.append({"limit": limit, "name": limit_name(limit), "generated": r.generated, "limited": r.limited, "n_routes": len(r.routes), "best": r.best,
                     "found_best": r.best is not None and r.best[1] == base.best[1] and abs(r.best[0] - base.best[0]) < 1e-9})
    return rows


def event_decision(ev: dict, by_nr: dict) -> str:
    """Die Entscheidung über ein neues Label als Satz (mit Begründung): behalten, dominiert, Limit."""
    if ev["status"] == "dominiert":
        return f"dominiert von {label_name(ev['killer'])}, weg"
    if ev["status"] == "limit-neu":
        w = by_nr[ev["worst"]]
        return f"Limit: Knoten voll, {label_name(w['nr'])} (Kosten {fmt_num(w['cost'])}) ist nicht teurer, das neue fliegt"
    text = "behalten"
    if ev["killed"]:
        text += "; streicht " + ", ".join(label_name(k) for k in ev["killed"])
    if ev["victim"] is not None:
        v = by_nr[ev["victim"]]
        text += f"; Limit: Knoten voll, {label_name(v['nr'])} (Kosten {fmt_num(v['cost'])}) fliegt, das neue ist billiger"
    return text


def event_rows(res: A.PricingResult) -> list:
    """Eine Zeile je neues Label (in der Reihenfolge der Entstehung) für die Tabelle der Handbeispiel-Labels."""
    by_nr = {e["nr"]: e for e in res.events}
    return [{"nr": e["nr"], "label": label_name(e["nr"]), "node": e["node"], "path": e["path"], "time": e["time"], "cost": e["cost"], "load": e["load"], "status": e["status"],
             "decision": event_decision(e, by_nr), "live_before": len(e["live_before"]), "limit": e["status"] == "limit-neu" or e["victim"] is not None} for e in res.events]


def extension_block(inst: Instance, path, time: float, load: int, j: int):
    """Warum ein Label mit diesem Weg, dieser Zeit und dieser Last den Kunden j nicht mehr besuchen kann (Handbeispiel, elementar): Satz oder None, wenn es geht."""
    if j in path:
        return f"Kunde {j} steht schon im Weg"
    if load + inst.demand[j] > inst.capacity:
        return f"Last {load} + {inst.demand[j]} = {load + inst.demand[j]} > {inst.capacity}"
    last = path[-1]
    arr = time + inst.service + inst.d[last][j]
    if arr > inst.due[j]:
        return f"Ankunft {fmt_num(arr)} > spätester Beginn {fmt_num(inst.due[j])}"
    return None


def displacement_story(limit: int):
    """Wo das Limit den besten Weg verliert (Handbeispiel, erstes Preisproblem): das erste Label, dessen Weg Anfang der besten Route ist und das vom Limit verdrängt wird, und warum
    der Verdränger die Route nicht fortsetzen kann. None, wenn das Limit den besten Weg findet oder kein solches Label existiert."""
    inst = hand_instance()
    best_exact = hand_run(None, trace=False).best
    res = hand_run(limit)
    if res.best is not None and res.best[1] == best_exact[1]:
        return None
    by_nr = {e["nr"]: e for e in res.events}
    target = best_exact[1]
    for e in res.events:
        if e["victim"] is None:
            continue
        v = by_nr[e["victim"]]
        p = v["path"]
        if target[: len(p)] == p and len(p) < len(target):
            nxt = target[len(p)]
            return {"victim": v["nr"], "victim_path": p, "victim_cost": v["cost"], "victim_load": v["load"], "newcomer": e["nr"], "newcomer_path": e["path"], "newcomer_cost": e["cost"],
                    "newcomer_load": e["load"], "best_route": target, "best_rc": best_exact[0], "next": nxt,
                    "reason": extension_block(inst, e["path"], e["time"], e["load"], nxt),
                    "victim_can": extension_block(inst, v["path"], v["time"], v["load"], nxt) is None}
    return None


def hand_colgen(limit, max_new: int) -> G.Colgen:
    """Die ganze Spaltenerzeugung des Handbeispiels (Überdeckungs-Master, Anfangsspalten = die sechs Einzelrouten, Master exakt mit Brüchen)."""
    return G.colgen(hand_instance(), C.HAND_K, limit=limit, max_new=max_new, master="exakt")


def hand_all_routes_lp() -> tuple:
    """Unabhängige Kontrolle: das Master-LP über ALLE zulässigen Routen (Aufzählung) mit exakten Brüchen: (Zielwert, Dualpreise)."""
    inst = hand_instance()
    return G.master_exact(inst, enumerate_routes(inst))


def loop_rows(exact: G.Colgen, heur: G.Colgen) -> list:
    """Tabelle Runde x Variante: je Runde Zielwert und Dualpreise des Masters und was das Preisproblem tat (nur die längere Variante füllt Zeilen, die kürzere lässt sie leer)."""
    rows = []
    for i in range(max(len(exact.rounds), len(heur.rounds))):
        a = exact.rounds[i] if i < len(exact.rounds) else None
        b = heur.rounds[i] if i < len(heur.rounds) else None
        rows.append({"nr": i + 1, "exact": a, "heur": b})
    return rows


def round_text(rnd: G.Round | None) -> tuple:
    """(Master, Pricing, neue Spalten) einer Runde als Texte."""
    if rnd is None:
        return "–", "–", "–"
    master = f"z = {fmt_num(rnd.z)}, π = ({', '.join(fmt_num(x) for x in rnd.pi[1:])})"
    if rnd.labels_limit and rnd.limit_found:
        pricing = f"Limit ({fmt_int(rnd.labels_limit)} Labels)"
    elif rnd.labels_limit:
        pricing = f"Limit ({fmt_int(rnd.labels_limit)}): nichts Neues; exakt ({fmt_int(rnd.labels_exact)} Labels)"
    else:
        pricing = f"exakt ({fmt_int(rnd.labels_exact)} Labels)"
    new = "; ".join(f"({route_text(r)}) {fmt_num(rc)}" for rc, r in rnd.new) if rnd.new else "keine negative Route: Schranke bewiesen"
    return master, pricing, new


# --- Live-Instanz ---------------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """Die Live-Instanz: Größe, Fensterbreite, Typ ('zufall' oder 'cluster'), Gedächtnis k, Etikettenlimit, Zufalls-Seed (Kapazität 70, Horizont 300, Bedienzeit 10)."""

    n: int
    width: int
    typ: str
    k: int
    limit: int
    seed: int


def instance_of(s: Settings) -> Instance:
    return make_instance(s.n, s.seed, s.width, clustered=(s.typ == "cluster"))


def live_runs(s: Settings) -> tuple:
    """Zwei Spaltenerzeugungen derselben Instanz: immer exakt und heuristisch zuerst (Limit s.limit), beide mit den Labelbudgets der App (Abbruch = aborted)."""
    inst = instance_of(s)
    kw = dict(max_new=C.HAND_MAX_NEW_FREE, master="highs", max_labels_call=C.MAX_LABELS_CALL, max_labels_total=C.MAX_LABELS_COLGEN)
    return G.colgen(inst, s.k, limit=None, **kw), G.colgen(inst, s.k, limit=s.limit, **kw)


def same_bound(a: G.Colgen, b: G.Colgen) -> bool:
    return a.bound is not None and b.bound is not None and abs(a.bound - b.bound) <= 1e-6 * max(1.0, abs(a.bound))


def best_rc_round1(run: G.Colgen):
    """Reduzierte Kosten der besten neuen Spalte der ersten Runde (None, wenn die erste Runde keine fand)."""
    return run.rounds[0].new[0][0] if run.rounds and run.rounds[0].new else None


def time_ratio(exact: G.Colgen, heur: G.Colgen):
    """Wanduhrzeit des heuristischen Laufs geteilt durch die des exakten (nur Information); None ohne messbare Zeit."""
    return None if exact.t_total <= 0 else heur.t_total / exact.t_total


# --- Verdikte -------------------------------------------------------------------------------------------------------------------------------

def verdict_hand_pricing(rows: list, limit: int) -> tuple:
    """Verdikt zu Experiment 1: findet das Limit den besten Weg des ersten Preisproblems?"""
    base = rows[0]
    row = next(r for r in rows if r["limit"] == limit)
    if row["best"] is None:
        return ("warning", f"{row['name']}: keine Route mit negativen reduzierten Kosten gefunden; das exakte Preisproblem findet {base['n_routes']}.")
    head = (f"{row['name']}: {row['generated']} statt {base['generated']} Labels, beste gefundene Route ({route_text(row['best'][1])}) mit {fmt_num(row['best'][0])}, "
            f"{row['n_routes']} statt {base['n_routes']} Routen mit negativen reduzierten Kosten.")
    if row["found_best"]:
        return ("success", head + f" Das Limit findet hier den besten Weg ({route_text(base['best'][1])}).")
    return ("warning", head + f" **Das Limit verfehlt den besten Weg** ({route_text(base['best'][1])} mit {fmt_num(base['best'][0])}); der exakte Aufruf findet ihn.")


def verdict_hand_loop(exact: G.Colgen, heur: G.Colgen, lp_value: float, limit: int) -> tuple:
    """Verdikt zu Experiment 2: gleiche Endschranke wie immer exakt und wie das LP über alle Routen; Labels und Runden im Vergleich."""
    if not (same_bound(exact, heur) and abs(exact.bound - lp_value) < 1e-9):
        return ("error", "Die Endschranke der Limit-Variante weicht von der exakten ab oder vom LP über alle Routen: Der Kern ist fehlerhaft.")
    more = heur.iters - exact.iters
    rounds = (f"{heur.iters} statt {exact.iters} Runden" if more > 0 else f"gleich viele Runden ({exact.iters})" if more == 0 else f"{heur.iters} statt {exact.iters} Runden (weniger)")
    return ("success", f"Dieselbe Endschranke {fmt_num(exact.bound)} wie bei immer exaktem Pricing und wie das LP über alle Routen. {limit_name(limit)}: {heur.labels} statt {exact.labels} Labels "
                       f"({fmt_ratio(heur.labels / exact.labels)}), {rounds}; das Limit reichte in {heur.heur_ok} von {heur.iters} Runden, exakte Aufrufe: {heur.exact_calls} statt {exact.exact_calls}.")


def verdict_bound(exact: G.Colgen, heur: G.Colgen) -> tuple:
    """Die Endschranke muss mit und ohne Limit gleich sein."""
    if exact.aborted or heur.aborted:
        return ("warning", f"Mindestens eine der beiden Rechnungen ist am Labelbudget abgebrochen ({fmt_int(C.MAX_LABELS_COLGEN)} Labels über alle Runden, {fmt_int(C.MAX_LABELS_CALL)} in einem Aufruf); "
                           "ohne zwei fertige Rechnungen gibt es keinen Vergleich. Eine kleinere Instanz oder schmalere Fenster wählen.")
    if same_bound(exact, heur):
        return ("success", f"Gleiche Endschranke wie bei immer exaktem Pricing: ja ({fmt_dec(exact.bound, 2)}).")
    return ("error", f"Die Endschranke weicht ab ({fmt_dec(heur.bound, 4)} gegen {fmt_dec(exact.bound, 4)}): Der Kern ist fehlerhaft.")


def verdict_labels(exact: G.Colgen, heur: G.Colgen, limit: int) -> tuple:
    """Labels, Runden, Limit-Treffer und exakte Aufrufe im Vergleich (Zählungen)."""
    if exact.aborted or heur.aborted:
        return ("warning", "Keine Zählung: Mindestens eine Rechnung ist abgebrochen.")
    ratio = heur.labels / exact.labels
    more = heur.iters - exact.iters
    runden = f"{more} Runden mehr" if more > 0 else "gleich viele Runden" if more == 0 else f"{-more} Runden weniger"
    text = (f"Limit {limit}: {fmt_int(heur.labels)} Labels gegen {fmt_int(exact.labels)} bei immer exaktem Pricing (Verhältnis {fmt_ratio(ratio)}); {runden} (Runden = Master-Aufgaben: "
            f"{heur.iters} statt {exact.iters}). Das Limit reichte in {heur.heur_ok} von {heur.iters} Runden; exakte Aufrufe: {heur.exact_calls} statt {exact.exact_calls}; "
            f"davon entstehen {fmt_pct(100 * heur.labels_exact / heur.labels)} der Labels im exakten Pricing.")
    return ("success" if ratio < 1 else "warning", text)


def verdict_round1(exact: G.Colgen, heur: G.Colgen) -> tuple:
    """Findet das Limit schon in der ersten Runde den besten Weg? Beide Läufe haben in Runde 1 dieselben Dualpreise."""
    a, b = best_rc_round1(exact), best_rc_round1(heur)
    if exact.aborted or heur.aborted or a is None or b is None:
        return ("info", "In der ersten Runde ist kein Vergleich der besten Wege möglich (keine Route mit negativen reduzierten Kosten oder Abbruch).")
    if abs(a - b) < 1e-9:
        return ("info", f"In der ersten Runde findet das Limit den besten Weg (reduzierte Kosten {fmt_dec(b, 2)}).")
    return ("info", f"In der ersten Runde verfehlt das Limit den besten Weg: beste gefundene Route {fmt_dec(b, 2)} statt {fmt_dec(a, 2)} beim exakten Pricing.")


def verdict_time(exact: G.Colgen, heur: G.Colgen) -> tuple:
    """Gesamtzeit (Wanduhr) nur als Information: sinkt, steigt oder gleichauf (Unterschied unter 5 %)."""
    if exact.aborted or heur.aborted:
        return ("info", "Keine Zeitangabe: Mindestens eine Rechnung ist abgebrochen.")
    ratio = time_ratio(exact, heur)
    tail = " Sekunden sind nur Information: Der Rechner ist nicht ruhig, gezählt werden Labels."
    if ratio is None:
        return ("info", "Die Zeit war zu kurz zum Messen." + tail)
    if abs(ratio - 1) < 0.05:
        return ("info", f"Gesamtzeit gleichauf ({fmt_dec(heur.t_total, 2)} s gegen {fmt_dec(exact.t_total, 2)} s, Unterschied unter 5 %)." + tail)
    if ratio < 1:
        return ("info", f"Die Gesamtzeit sinkt: {fmt_dec(heur.t_total, 2)} s gegen {fmt_dec(exact.t_total, 2)} s ({fmt_ratio(ratio)}; davon Master-LP {fmt_dec(heur.t_master, 2)} s gegen {fmt_dec(exact.t_master, 2)} s)." + tail)
    return ("info", f"Die Gesamtzeit steigt: {fmt_dec(heur.t_total, 2)} s gegen {fmt_dec(exact.t_total, 2)} s ({fmt_ratio(ratio)}; davon Master-LP {fmt_dec(heur.t_master, 2)} s gegen {fmt_dec(exact.t_master, 2)} s)." + tail)


# --- Kipp-Rechner ---------------------------------------------------------------------------------------------------------------------------

def model_stats(laeufe: list, breite: int = 100, typ=None) -> dict:
    """Summen über die Instanzen je Variante: Labels, davon im Limit-Pricing und im exakten Pricing, Runden (Master-Aufgaben), Zahl der Instanzen."""
    out = {}
    for v in C.BAND_VARIANTS:
        rows = [x for x in laeufe if x["breite"] == breite and x["variante"] == v and (typ is None or x["typ"] == typ)]
        out[v] = {"n": len(rows), "labels": sum(x["labels"] for x in rows), "labels_limit": sum(x["labels_limit"] for x in rows), "labels_exakt": sum(x["labels_exakt"] for x in rows),
                  "iterationen": sum(x["iterationen"] for x in rows)}
    return out


def model_effort(stats: dict, master_cost: float, label_cost: float = 1.0) -> float:
    """Aufwand in „Labels des exakten Preisproblems“: label_cost x Labels im Limit-Pricing + Labels im exakten Pricing + master_cost x Runden (Master-Aufgaben).
    master_cost und label_cost sind Annahmen (Voreinstellung 380 und 1)."""
    return label_cost * stats["labels_limit"] + stats["labels_exakt"] + master_cost * stats["iterationen"]


def model_ratio(stats_v: dict, stats_exact: dict, master_cost: float, label_cost: float = 1.0) -> float:
    """Aufwand der Variante geteilt durch den Aufwand bei immer exaktem Pricing (kleiner als 1: das Limit lohnt sich im Modell)."""
    return model_effort(stats_v, master_cost, label_cost) / model_effort(stats_exact, master_cost, 1.0)


def break_even(stats_v: dict, stats_exact: dict, label_cost: float = 1.0):
    """Kosten eines Master-LPs (in Labels des exakten Preisproblems), bei denen Variante und immer exaktes Pricing gleich teuer sind: Das Limit lohnt sich darunter.

    Gleichung: label_cost x Lh + Le + r x I_v = L_exakt + r x I_exakt, also r = (L_exakt - label_cost x Lh - Le) / (I_v - I_exakt). None, wenn die Variante nicht mehr
    Runden braucht als exakt (dann lohnt sie sich bei jedem r, sofern sie weniger Labels braucht)."""
    di = stats_v["iterationen"] - stats_exact["iterationen"]
    if di <= 0:
        return None
    return (stats_exact["labels_exakt"] - label_cost * stats_v["labels_limit"] - stats_v["labels_exakt"]) / di


def verdict_kipp(stats: dict, master_cost: float, label_cost: float) -> tuple:
    """Verdikt des Kipp-Rechners: welche Limits sich bei diesen Annahmen im Modell lohnen (Aufwand unter 1 gegen immer exakt)."""
    ex = stats["exakt"]
    wins, loses = [], []
    for v in C.BAND_VARIANTS[1:]:
        (wins if model_ratio(stats[v], ex, master_cost, label_cost) < 1 else loses).append(v)
    head = f"Bei {fmt_int(master_cost)} Labels je Master-LP und Kosten {fmt_dec(label_cost, 2)} je Limit-Label (beides Annahmen) "
    if not loses:
        return ("success", head + "lohnen sich im Modell alle drei Limits (L5, L10, L20).")
    if not wins:
        return ("warning", head + "lohnt sich im Modell keines der drei Limits mehr: Das exakte Pricing ist billiger.")
    return ("info", head + f"lohnen sich im Modell {', '.join(wins)}; nicht mehr {', '.join(loses)}.")


# --- Feste Messreihen -----------------------------------------------------------------------------------------------------------------------

def load_bands(path=None) -> list:
    """Die Läufe der festen Messreihen (data/laeufe_v13.json): eine Zeile je Instanz und Variante, mit Quelle."""
    return json.loads(Path(path or DATA / "laeufe_v13.json").read_text(encoding="utf-8"))["laeufe"]


def load_zeit(path=None) -> list:
    """Die Zeilen der Zeitmessung der Vormessung (data/zeit_vormessung.json): 30 Instanzen x 4 Varianten x 3 Wiederholungen."""
    return json.loads(Path(path or DATA / "zeit_vormessung.json").read_text(encoding="utf-8"))["zeilen"]


def by_instance(laeufe: list, breite: int, typ=None) -> dict:
    """(Typ, Zufalls-Seed) -> {Variante: Lauf} für eine Fensterbreite (und optional einen Typ)."""
    out = {}
    for x in laeufe:
        if x["breite"] == breite and (typ is None or x["typ"] == typ):
            out.setdefault((x["typ"], x["seed"]), {})[x["variante"]] = x
    return out


def stats_of(values) -> dict:
    """Mittel, Median, Minimum, Maximum und Zahl der Werte."""
    values = list(values)
    return {"mean": statistics.fmean(values), "median": statistics.median(values), "min": min(values), "max": max(values), "n": len(values)}


def band_table(laeufe: list, breite: int, typ=None) -> list:
    """Eine Zeile je Variante: Labels (Mittel), Verhältnis zu exakt (Mittel der Verhältnisse, Median, Minimum, Maximum), Instanzen mit weniger Labels, Runden, Limit-Treffer,
    exakte Aufrufe, Anteil der Labels im exakten Pricing."""
    inst = by_instance(laeufe, breite, typ)
    rows = []
    for v in C.BAND_VARIANTS:
        rs = [d[v] for d in inst.values()]
        ex = [d["exakt"] for d in inst.values()]
        ratios = [r["labels"] / e["labels"] for r, e in zip(rs, ex)]
        s = stats_of(ratios)
        its = sum(r["iterationen"] for r in rs)
        rows.append({"variante": v, "n": len(rs), "labels_mean": statistics.fmean(r["labels"] for r in rs), "ratio_mean": s["mean"], "ratio_median": s["median"], "ratio_min": s["min"],
                     "ratio_max": s["max"], "fewer": sum(1 for r, e in zip(rs, ex) if r["labels"] < e["labels"]), "iters_mean": statistics.fmean(r["iterationen"] for r in rs),
                     "iters_vs_exact": statistics.fmean(r["iterationen"] for r in rs) / statistics.fmean(e["iterationen"] for e in ex) - 1,
                     "limit_share": (sum(r["limit_reichte"] for r in rs) / its) if v != "exakt" else None, "exact_calls_mean": statistics.fmean(r["exakte_aufrufe"] for r in rs),
                     "exact_label_share": sum(r["labels_exakt"] for r in rs) / sum(r["labels"] for r in rs), "sum_ratio": sum(r["labels"] for r in rs) / sum(e["labels"] for e in ex)})
    return rows


def verdict_bands(laeufe: list, breite: int, typ, variante: str) -> tuple:
    """Verdikt einer Band-Zelle: in wie vielen Instanzen braucht die Variante weniger Labels als exakt, Verhältnis, Runden, gleiche Endschranke in allen Instanzen."""
    inst = by_instance(laeufe, breite, typ)
    row = next(r for r in band_table(laeufe, breite, typ) if r["variante"] == variante)
    same = sum(1 for d in inst.values() if abs(d[variante]["schranke"] - d["exakt"]["schranke"]) <= 1e-6 * max(1.0, abs(d["exakt"]["schranke"])))
    where = "alle Instanzen" if typ is None else ("zufällige Instanzen" if typ == "zufall" else "gruppierte Instanzen")
    text = (f"Fensterbreite {breite}, {where}, {variante}: weniger Labels als exakt in {row['fewer']} von {row['n']} Instanzen (Mittel der Verhältnisse {fmt_ratio(row['ratio_mean'])}, "
            f"kleinstes {fmt_ratio(row['ratio_min'])}, größtes {fmt_ratio(row['ratio_max'])}); Runden {fmt_dec(row['iters_mean'], 1)} im Mittel ({fmt_pct(100 * row['iters_vs_exact'], 0)} gegen exakt); "
            f"gleiche Endschranke wie exakt in {same} von {row['n']} Instanzen.")
    return ("success" if row["fewer"] == row["n"] and same == row["n"] else "warning", text)


def zeit_median_rows(zeit: list) -> dict:
    """(Typ, Seed, Variante) -> Zeile mit dem Median der Wiederholungen für jede Zeitspalte (wie in der Auswertung der Vormessung)."""
    groups = {}
    for z in zeit:
        groups.setdefault((z["typ"], z["seed"], z["variante"]), []).append(z)
    keys = ("wand", "cpu", "lp_wand", "lp_cpu", "limit_wand", "limit_cpu", "exakt_wand", "exakt_cpu", "iterationen", "labels")
    return {k: {m: statistics.median(z[m] for z in rows) for m in keys} | {"n": len(rows), "abgebrochen": any(z["abgebrochen"] for z in rows)} for k, rows in groups.items()}


def zeit_table(zeit: list) -> list:
    """Eine Zeile je Variante: Summe der CPU-Zeit (Median der Wiederholungen je Instanz), Summe geteilt durch exakt, Median/Mittel/Minimum/Maximum der Instanz-Verhältnisse, Instanzen, die
    schneller als exakt sind, die Wanduhrzeit entsprechend und die Aufteilung der CPU-Zeit (Master-LP, Pricing mit Limit, exaktes Pricing, Rest)."""
    med = zeit_median_rows(zeit)
    inst = sorted({(t, s) for t, s, _ in med})
    rows = []
    for v in C.BAND_VARIANTS:
        cpu = [med[(t, s, v)]["cpu"] for t, s in inst]
        cpu_ex = [med[(t, s, "exakt")]["cpu"] for t, s in inst]
        wand = [med[(t, s, v)]["wand"] for t, s in inst]
        wand_ex = [med[(t, s, "exakt")]["wand"] for t, s in inst]
        rc = [a / b for a, b in zip(cpu, cpu_ex)]
        rw = [a / b for a, b in zip(wand, wand_ex)]
        lp = sum(med[(t, s, v)]["lp_cpu"] for t, s in inst)
        ph = sum(med[(t, s, v)]["limit_cpu"] for t, s in inst)
        pe = sum(med[(t, s, v)]["exakt_cpu"] for t, s in inst)
        rows.append({"variante": v, "n": len(inst), "cpu_sum": sum(cpu), "cpu_sum_ratio": sum(cpu) / sum(cpu_ex), "cpu_median": statistics.median(rc), "cpu_min": min(rc), "cpu_max": max(rc),
                     "cpu_mean": statistics.fmean(rc), "cpu_faster": sum(1 for x in rc if x < 1), "wand_sum": sum(wand), "wand_mean": statistics.fmean(rw), "wand_faster": sum(1 for x in rw if x < 1),
                     "lp": lp, "limit": ph, "exakt": pe, "rest": sum(cpu) - lp - ph - pe})
    return rows


def time_costs(zeit: list, laeufe: list) -> dict:
    """Aus Zeitmessung (Vormessung) und Label-Zählungen der Messreihen: CPU-Zeit je Master-LP (ms), je Label im exakten Pricing und je Label im Limit-Pricing (µs, je Limit), und die Kosten eines
    Master-LPs in Labels des exakten Preisproblems. Summen über die 30 Instanzen der Breite 100 (Median der Wiederholungen je Instanz); Rechner ausgelastet, nur Größenordnung."""
    med = zeit_median_rows(zeit)
    inst = by_instance(laeufe, 100)
    keys = sorted(inst)
    lp_ms = 1000 * sum(med[(t, s, "exakt")]["lp_cpu"] for t, s in keys) / sum(med[(t, s, "exakt")]["iterationen"] for t, s in keys)
    exact_us = 1e6 * sum(med[(t, s, "exakt")]["exakt_cpu"] for t, s in keys) / sum(inst[(t, s)]["exakt"]["labels"] for t, s in keys)
    out = {"master_ms": lp_ms, "label_exact_us": exact_us, "master_in_labels": 1000 * lp_ms / exact_us, "limit_us": {}, "limit_vs_exact": {}}
    for v in C.BAND_VARIANTS[1:]:
        us = 1e6 * sum(med[(t, s, v)]["limit_cpu"] for t, s in keys) / sum(inst[(t, s)][v]["labels_limit"] for t, s in keys)
        out["limit_us"][v] = us
        out["limit_vs_exact"][v] = us / exact_us
    out["pricing_share_exact"] = sum(med[(t, s, "exakt")]["exakt_cpu"] for t, s in keys) / sum(med[(t, s, "exakt")]["cpu"] for t, s in keys)
    return out
