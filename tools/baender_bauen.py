"""Erzeugt die festen Messreihen (data/*.json): rechnet die Spaltenerzeugungen der Messung mit dem Kern der Demo neu und gleicht sie mit den Rohausgaben der Vormessung ab.

Zwei Schritte (im Ordner der Demo, Python des Test-venv):

1. Messen (neu gerechnet mit dem Kern der Demo, `hpr_colgen.colgen`, Gedächtnis k = 8, Überdeckungs-Master, höchstens 15 neue Spalten je Runde, ohne Labelbudget):
       python tools/baender_bauen.py messen --typ zufall --breite 100 --von 0 --bis 15 --out roh_zufall_100.jsonl
   Je Instanz (n = 30) die vier Varianten exakt, L5, L10, L20; eine Zeile je Lauf. Ein Lauf bricht nie ab (kein Budget); die Zeile enthält `aborted` trotzdem.
2. Bauen (liest die Rohzeilen und die Rohausgaben der Vormessung):
       python tools/baender_bauen.py bauen roh_*.jsonl --vormessung <Ordner label-setting-planung/vormessung>
   schreibt data/laeufe_v13.json (alle neu gerechneten Läufe mit Quelle je Lauf), data/zeit_vormessung.json (die 360 Zeilen der Zeitmessung aus `run_p14_zeit.log`, NICHT neu gemessen) und
   data/vormessung_abgleich.json (Vergleich jeder neu gerechneten Zeile mit der Rohausgabe `out_v13_*.txt`: Endschranke, Iterationen, Labels, Spalten, exakte Aufrufe)."""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
VARIANTS = (("exakt", None), ("L5", 5), ("L10", 10), ("L20", 20))
N, K = 30, 8


def messen(args) -> None:
    import hpr_colgen as G
    from hpr_scenario import make_instance

    with open(args.out, "a", encoding="utf-8") as out:
        for seed in range(args.von, args.bis):
            inst = make_instance(N, seed, args.breite, clustered=(args.typ == "cluster"))
            for name, limit in VARIANTS:
                t0 = time.perf_counter()
                r = G.colgen(inst, K, limit=limit)
                row = {"typ": args.typ, "breite": args.breite, "seed": seed, "variante": name, "schranke": r.bound, "iterationen": r.iters, "spalten": r.cols, "labels": r.labels,
                       "labels_limit": r.labels_heur, "labels_exakt": r.labels_exact, "limit_reichte": r.heur_ok, "exakte_aufrufe": r.exact_calls, "gestrichen": r.dominated,
                       "limit_angewendet": r.limited, "abgebrochen": r.aborted, "sekunden": round(time.perf_counter() - t0, 2)}
                out.write(json.dumps(row) + "\n")
                out.flush()
            print(args.typ, args.breite, seed, "fertig", flush=True)


def _rohzeilen(folder: Path) -> dict:
    """Rohausgaben der Messung V13: (typ, breite, seed, Variante) -> (Schranke, Iterationen, Spalten, Labels, Labels Limit, Labels exakt, Limit reichte, exakte Aufrufe, Datei)."""
    raw = {}
    for f in sorted(folder.glob("out_v13_*.txt")):
        if "auswertung" in f.name:
            continue
        for line in f.read_text(encoding="utf-8").splitlines()[1:]:
            p = line.split()
            if len(p) < 16 or p[0] not in ("zufall", "cluster"):
                continue
            raw[(p[0], int(p[2]), int(p[3]), p[5])] = (float(p[6]), int(p[7]), int(p[8]), int(p[9]), int(p[10]), int(p[11]), int(p[12]), int(p[13]), f.name)
    return raw


def _zeitzeilen(path: Path) -> list:
    """Die Rohzeilen der Zeitmessung (`run_p14_zeit.log`): typ seed rep variante schranke iter labels wall_s cpu_s lp_wall lp_cpu ph_wall ph_cpu pe_wall pe_cpu abgebrochen."""
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        p = line.split()
        if len(p) == 16 and p[0] in ("zufall", "cluster") and p[1].isdigit():
            rows.append({"typ": p[0], "seed": int(p[1]), "wiederholung": int(p[2]), "variante": p[3], "schranke": float(p[4]), "iterationen": int(p[5]), "labels": int(p[6]),
                         "wand": float(p[7]), "cpu": float(p[8]), "lp_wand": float(p[9]), "lp_cpu": float(p[10]), "limit_wand": float(p[11]), "limit_cpu": float(p[12]),
                         "exakt_wand": float(p[13]), "exakt_cpu": float(p[14]), "abgebrochen": bool(int(p[15]))})
    return rows


def bauen(args) -> None:
    rows = []
    for path in args.rohdateien:
        rows += [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    order = {"zufall": 0, "cluster": 1}
    names = {n: i for i, (n, _) in enumerate(VARIANTS)}
    rows.sort(key=lambda r: (r["breite"], order[r["typ"]], r["seed"], names[r["variante"]]))
    folder = Path(args.vormessung)
    raw = _rohzeilen(folder)
    heute = date.today().isoformat()
    laeufe, gleich, ungleich, fehlend, dmax = [], 0, 0, 0, 0.0
    for r in rows:
        ref = raw.get((r["typ"], r["breite"], r["seed"], r["variante"]))
        src = None
        if ref is None:
            fehlend += 1
        else:
            src = ref[8]
            same = (r["iterationen"] == ref[1] and r["spalten"] == ref[2] and r["labels"] == ref[3] and r["labels_limit"] == ref[4] and r["labels_exakt"] == ref[5]
                    and r["limit_reichte"] == ref[6] and r["exakte_aufrufe"] == ref[7] and r["schranke"] is not None and abs(r["schranke"] - ref[0]) < 1e-5)
            if r["schranke"] is not None:
                dmax = max(dmax, abs(r["schranke"] - ref[0]))
            gleich += 1 if same else 0
            ungleich += 0 if same else 1
        laeufe.append({**{k: v for k, v in r.items() if k != "sekunden"}, "sekunden": r["sekunden"],
                       "quelle": f"neu gerechnet mit dem Kern der Demo (tools/baender_bauen.py, Lauf vom {heute}); verglichen mit {src or 'keiner Rohausgabe'} (Vormessung)"})
    DATA.mkdir(exist_ok=True)
    (DATA / "laeufe_v13.json").write_text(json.dumps({
        "hinweis": "Je Lauf (Instanz x Variante) die Spaltenerzeugung mit Überdeckungs-Master, n = 30, Gedächtnis k = 8, höchstens 15 neue Spalten je Runde. Varianten: exakt (jede Runde exaktes "
                   "Pricing) und L5, L10, L20 (erst Etikettenlimit, exaktes Pricing nur wenn das Limit nichts Neues findet). Sekunden nur zur Information (Wanduhr, Rechner ausgelastet).",
        "laeufe": laeufe}, ensure_ascii=False, indent=0), encoding="utf-8")
    zeit = _zeitzeilen(folder / "run_p14_zeit.log")
    (DATA / "zeit_vormessung.json").write_text(json.dumps({
        "hinweis": "Zeitmessung der Vormessung (run_p14_zeit.log): 30 Instanzen (n = 30, Breite 100, k = 8), vier Varianten, drei Wiederholungen, ein Prozess, Rechner durch andere Sitzungen "
                   "ausgelastet. NICHT mit dem Kern dieser Demo neu gemessen; Sekunden sind nur Information (Größenordnung).",
        "quelle": "label-setting-planung/vormessung/run_p14_zeit.log, Rechnerlast: run_p14_zeit_last.txt", "zeilen": zeit}, ensure_ascii=False, indent=0), encoding="utf-8")
    (DATA / "vormessung_abgleich.json").write_text(json.dumps({
        "hinweis": "Vergleich jeder neu gerechneten Zeile mit der Rohausgabe der Vormessung (out_v13_*.txt) in Iterationen, Spalten, Labels (gesamt, Limit, exakt), Limit-Treffern, exakten Aufrufen "
                   "und Endschranke (Toleranz 1e-5).",
        "stand": heute, "zeilen_neu": len(laeufe), "zeilen_gleich": gleich, "zeilen_abweichend": ungleich, "zeilen_ohne_rohzeile": fehlend, "schranke_groesste_abweichung": dmax,
        "abgebrochene_laeufe": sum(1 for r in rows if r["abgebrochen"]), "zeitzeilen": len(zeit)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(laeufe)} Läufe, gleich {gleich}, abweichend {ungleich}, ohne Rohzeile {fehlend}, Zeitzeilen {len(zeit)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("messen")
    m.add_argument("--typ", choices=("zufall", "cluster"), required=True)
    m.add_argument("--breite", type=int, required=True)
    m.add_argument("--von", type=int, default=0)
    m.add_argument("--bis", type=int, required=True)
    m.add_argument("--out", required=True)
    b = sub.add_parser("bauen")
    b.add_argument("rohdateien", nargs="+")
    b.add_argument("--vormessung", required=True)
    args = ap.parse_args()
    (messen if args.cmd == "messen" else bauen)(args)


if __name__ == "__main__":
    main()
