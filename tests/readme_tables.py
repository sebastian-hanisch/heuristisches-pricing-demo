"""Tabellen der README aus den Daten (zeichengleich); die Tests in `test_claims.py` verlangen, dass genau diese Zeilen in der README stehen. Aufruf zum Erzeugen: python tests/readme_tables.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hpr_constants as C  # noqa: E402
import hpr_evaluation as ev  # noqa: E402

BAND_HEADER = ("| Variante | Instanzen | Labels (Mittel) | Labels / exakt (Mittel der Verhältnisse) | Median | Minimum | Maximum | Instanzen mit weniger Labels | Runden (Mittel) | Runden gegen exakt "
               "| Limit reichte (Anteil der Runden) | Exakte Aufrufe (Mittel) | Labels im exakten Pricing (Anteil) |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def band_rows(laeufe, breite, typ=None) -> list:
    rows = []
    for r in ev.band_table(laeufe, breite, typ):
        ex = r["variante"] == "exakt"
        rows.append(f"| {r['variante']} | {r['n']} | {ev.fmt_int(r['labels_mean'])} | {ev.fmt_ratio(r['ratio_mean'])} | {ev.fmt_ratio(r['ratio_median'])} | {ev.fmt_ratio(r['ratio_min'])} | {ev.fmt_ratio(r['ratio_max'])} | "
                    f"{'–' if ex else str(r['fewer']) + ' von ' + str(r['n'])} | {ev.fmt_dec(r['iters_mean'], 1)} | "
                    f"{'–' if ex else ('+' if r['iters_vs_exact'] > 0 else '-') + ev.fmt_pct(abs(100 * r['iters_vs_exact']), 0)} | "
                    f"{'–' if ex else ev.fmt_pct(100 * r['limit_share'])} | {ev.fmt_dec(r['exact_calls_mean'], 1)} | {ev.fmt_pct(100 * r['exact_label_share'])} |")
    return rows


ZEIT_HEADER = ("| Variante | CPU-Zeit, Summe (s) | Summe / exakt | Median der Instanz-Verhältnisse (Minimum bis Maximum) | Mittel der Instanz-Verhältnisse | Schneller als exakt (CPU) "
               "| Wanduhr, Mittel der Instanz-Verhältnisse | Schneller als exakt (Wanduhr) |\n|---|---|---|---|---|---|---|---|")


def zeit_rows(zeit) -> list:
    rows = []
    for r in ev.zeit_table(zeit):
        ex = r["variante"] == "exakt"
        rows.append(f"| {r['variante']} | {ev.fmt_dec(r['cpu_sum'], 2)} | {ev.fmt_ratio(r['cpu_sum_ratio'])} | {ev.fmt_ratio(r['cpu_median'])} ({ev.fmt_ratio(r['cpu_min'])} bis {ev.fmt_ratio(r['cpu_max'])}) | "
                    f"{ev.fmt_ratio(r['cpu_mean'])} | {'–' if ex else str(r['cpu_faster']) + ' von ' + str(r['n'])} | {ev.fmt_ratio(r['wand_mean'])} | {'–' if ex else str(r['wand_faster']) + ' von ' + str(r['n'])} |")
    return rows


SPLIT_HEADER = "| Variante | gesamt (s) | Master-LP (s) | Pricing mit Limit (s) | Exaktes Pricing (s) | Rest (s) |\n|---|---|---|---|---|---|"


def split_rows(zeit) -> list:
    return [f"| {r['variante']} | {ev.fmt_dec(r['cpu_sum'], 2)} | {ev.fmt_dec(r['lp'], 2)} | {'–' if r['variante'] == 'exakt' else ev.fmt_dec(r['limit'], 2)} | {ev.fmt_dec(r['exakt'], 2)} | {ev.fmt_dec(r['rest'], 2)} |"
            for r in ev.zeit_table(zeit)]


KIPP_HEADER = "| Limit | Kipp-Stelle bei gleich teuren Labels (Labels je Master-LP) | Aufwand gegen exakt bei 380 | Aufwand gegen exakt bei 20 000 |\n|---|---|---|---|"


def kipp_rows(laeufe) -> list:
    st = ev.model_stats(laeufe, 100)
    rows = []
    for v in C.BAND_VARIANTS[1:]:
        be = ev.break_even(st[v], st["exakt"], 1.0)
        rows.append(f"| {v} | {ev.fmt_int(round(be, -2))} | {ev.fmt_ratio(ev.model_ratio(st[v], st['exakt'], 380))} | {ev.fmt_ratio(ev.model_ratio(st[v], st['exakt'], 20000))} |")
    return rows


if __name__ == "__main__":
    b, z = ev.load_bands(), ev.load_zeit()
    for title, rows in (("Breite 100, alle", band_rows(b, 100)), ("Breite 100, zufällig", band_rows(b, 100, "zufall")), ("Breite 100, gruppiert", band_rows(b, 100, "cluster")),
                        ("Breite 150, alle", band_rows(b, 150))):
        print(title + "\n" + BAND_HEADER)
        print("\n".join(rows) + "\n")
    print(ZEIT_HEADER)
    print("\n".join(zeit_rows(z)) + "\n")
    print(SPLIT_HEADER)
    print("\n".join(split_rows(z)) + "\n")
    print(KIPP_HEADER)
    print("\n".join(kipp_rows(b)))
