"""Plotly-Abbildungen. Alle Achsen fest (`fixedrange`), damit Touch-Scrollen auf der Seite nicht am Diagramm hängen bleibt; keine Log-Achsen mit Nullwerten (feste Bereiche),
Kategorienachsen mit ausdrücklichem Typ (nie zahlartige Beschriftungen ohne Typ), feste Wertebereiche aus den Daten (nie leer, nie unendlich)."""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import hpr_constants as C
import hpr_evaluation as ev


def _layout(fig, height, title=None, legend_bottom=False):
    """Einheitliches Layout; die Legende steht oben (ohne Titel) oder unter dem Diagramm (bei Titeln und Teildiagrammen, damit nichts überlappt)."""
    legend = dict(orientation="h", yanchor="top", y=-0.18, x=0) if legend_bottom else dict(orientation="h", yanchor="bottom", y=1.02, x=0)
    fig.update_layout(height=height, margin=dict(l=55, r=20, t=40 if title else 15, b=95 if legend_bottom else 45), title=title, legend=legend, dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _top(values, factor=1.12, minimum=1.0) -> float:
    """Obergrenze einer Achse aus den Daten: nie 0 und nie unendlich."""
    finite = [v for v in values if v is not None and math.isfinite(v)]
    return max(max(finite, default=0.0) * factor, minimum)


def build_hand_map(inst, best_exact, best_limit=None) -> go.Figure:
    """Das Handbeispiel: Depot und sechs Kunden auf dem Gitter; die beste Route des exakten Aufrufs (grün) und, wenn sie sich unterscheidet, die beste des Limit-Aufrufs (orange gestrichelt)."""
    fig = go.Figure()

    def path(route, color, dash, name, shift):
        seq = (0,) + tuple(route) + (0,)
        xs, ys = [], []
        for a, b in zip(seq, seq[1:]):
            (x0, y0), (x1, y1) = inst.points[a], inst.points[b]
            xs += [x0 + shift, x1 + shift, x1 + shift]
            ys += [y0 + shift, y0 + shift, y1 + shift]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=3, dash=dash), name=name, hoverinfo="skip"))

    if best_exact:
        path(best_exact, C.COLOR_OK, "solid", f"beste Route (exakt): {ev.route_text(best_exact)}", 0.0)
    if best_limit and tuple(best_limit) != tuple(best_exact or ()):
        path(best_limit, C.COLOR_LINE2, "dash", f"beste Route des Limits: {ev.route_text(best_limit)}", 0.12)
    xs = [p[0] for p in inst.points]
    ys = [p[1] for p in inst.points]
    # Beschriftungen als Text der Spuren (nicht als Annotationen): Annotationen melden beim ersten Zeichnen in noch schmalem Container „attribute y: Expected length, -Infinity“
    fig.add_trace(go.Scatter(x=xs[1:], y=ys[1:], mode="markers+text", marker=dict(size=22, color=C.COLOR_LINE), text=[f"<b>{i}</b>" for i in range(1, inst.n + 1)], textposition="middle center",
                             textfont=dict(color="white", size=12), name="Kunde", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs[:1], y=ys[:1], mode="markers+text", marker=dict(size=22, color=C.COLOR_LINE3, symbol="square"), text=["<b>D</b>"], textposition="middle center",
                             textfont=dict(color="white", size=12), name="Depot", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs[1:], y=[y - 0.85 for y in ys[1:]], mode="text", text=[f"[{inst.ready[i]}, {inst.due[i]}] · Last {inst.demand[i]}" for i in range(1, inst.n + 1)],
                             textfont=dict(size=10), showlegend=False, hoverinfo="skip"))
    fig.update_xaxes(range=[-0.5, 11.5], showgrid=True, zeroline=False, dtick=1)
    fig.update_yaxes(range=[-1.7, 8.5], showgrid=True, zeroline=False, dtick=1)
    return _layout(fig, 400, legend_bottom=True)


def build_loop_chart(exact, heur, limit) -> go.Figure:
    """Experiment 2: Zielwert des Masters je Runde bei immer exaktem Pricing und mit Limit (beide enden bei derselben Endschranke); feste Achsen."""
    fig = go.Figure()
    top = max(len(exact.rounds), len(heur.rounds))
    zs = [r.z for r in exact.rounds] + [r.z for r in heur.rounds]
    fig.add_trace(go.Scatter(x=[r.nr for r in exact.rounds], y=[r.z for r in exact.rounds], mode="lines+markers", name="immer exakt", line=dict(color=C.COLOR_LINE, width=3)))
    fig.add_trace(go.Scatter(x=[r.nr for r in heur.rounds], y=[r.z for r in heur.rounds], mode="lines+markers", name=ev.limit_name(limit), line=dict(color=C.COLOR_LINE2, width=3, dash="dash")))
    fig.update_xaxes(title_text="Runde der Spaltenerzeugung", range=[0.5, top + 0.5], dtick=1, type="linear")
    lo, hi = min(zs), max(zs)
    pad = max((hi - lo) * 0.08, 1.0)
    fig.update_yaxes(title_text="Zielwert des Masters", range=[lo - pad, hi + pad])
    return _layout(fig, 340)


def build_round_chart(exact, heur, limit) -> go.Figure:
    """Experiment 3: erzeugte Labels je Runde. Oben immer exakt, unten die Limit-Variante (Limit-Aufruf und, wenn nötig, exakter Aufruf übereinander); gleiche Skala."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.2, subplot_titles=("immer exaktes Pricing", f"{ev.limit_name(limit)} zuerst, exakt zum Beweis"))
    fig.add_trace(go.Bar(x=[r.nr for r in exact.rounds], y=[r.labels_exact for r in exact.rounds], name="exaktes Pricing", marker_color=C.COLOR_LINE), row=1, col=1)
    fig.add_trace(go.Bar(x=[r.nr for r in heur.rounds], y=[r.labels_limit for r in heur.rounds], name="Limit-Pricing", marker_color=C.COLOR_LINE2), row=2, col=1)
    fig.add_trace(go.Bar(x=[r.nr for r in heur.rounds], y=[r.labels_exact for r in heur.rounds], name="exaktes Pricing", marker_color=C.COLOR_LINE, showlegend=False), row=2, col=1)
    top = _top([r.labels_exact for r in exact.rounds] + [r.labels_limit + r.labels_exact for r in heur.rounds])
    most = max(len(exact.rounds), len(heur.rounds))
    for row in (1, 2):
        fig.update_yaxes(range=[0, top], title_text="Labels", row=row, col=1)
        fig.update_xaxes(range=[0.5, most + 0.5], dtick=max(1, most // 12), type="linear", title_text="Runde" if row == 2 else None, row=row, col=1)
    fig.update_layout(barmode="stack")
    return _layout(fig, 520, legend_bottom=True)


def build_kipp_chart(stats: dict, label_cost: float, master_cost: float) -> go.Figure:
    """Experiment 4: Aufwand der drei Limits im Verhältnis zu immer exaktem Pricing über den Kosten eines Master-LPs (in Labels); darunter lohnt sich das Limit. Logarithmische Achse mit festem
    Bereich (alle Werte positiv); die gewählten Kosten sind markiert."""
    xs = [10 ** (e / 20) for e in range(20, 101)]       # 10 bis 100 000
    fig = go.Figure()
    colors = {"L5": C.COLOR_LINE, "L10": C.COLOR_LINE2, "L20": C.COLOR_LINE3}
    ys = []
    for v in C.BAND_VARIANTS[1:]:
        y = [ev.model_ratio(stats[v], stats["exakt"], x, label_cost) for x in xs]
        ys += y
        fig.add_trace(go.Scatter(x=xs, y=y, mode="lines", name=v, line=dict(color=colors[v], width=3), hovertemplate="%{x:.0f} Labels je Master-LP: %{y:.2f}<extra>" + v + "</extra>"))
        be = ev.break_even(stats[v], stats["exakt"], label_cost)
        if be is not None and xs[0] <= be <= xs[-1]:
            fig.add_trace(go.Scatter(x=[be], y=[1.0], mode="markers", marker=dict(color=colors[v], size=10, symbol="diamond"), showlegend=False, hovertemplate=f"Kipp-Stelle {v}: %{{x:.0f}}<extra></extra>"))
    top = _top(ys, 1.08, 1.2)
    fig.add_trace(go.Scatter(x=[xs[0], xs[-1]], y=[1.0, 1.0], mode="lines", line=dict(color="gray", dash="dot"), name="gleich teuer wie exakt", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[master_cost, master_cost], y=[0, top], mode="lines", line=dict(color=C.COLOR_BAD, dash="dash"), name="gewählte Kosten", hoverinfo="skip"))
    fig.update_xaxes(type="log", range=[1, 5], title_text="Kosten eines Master-LPs in Labels (Annahme)")
    fig.update_yaxes(range=[0, top], title_text="Aufwand / Aufwand bei immer exakt")
    return _layout(fig, 400)


def build_band_chart(laeufe: list, breite: int, typ) -> go.Figure:
    """Experiment 5: Labels im Verhältnis zu immer exakt je Instanz (Punkte) und Kasten je Variante; Linie bei 1. Kategorienachse mit Typ „category“."""
    inst = ev.by_instance(laeufe, breite, typ)
    fig = go.Figure()
    colors = {"L5": C.COLOR_LINE, "L10": C.COLOR_LINE2, "L20": C.COLOR_LINE3}
    ys = []
    for v in C.BAND_VARIANTS[1:]:
        y = [d[v]["labels"] / d["exakt"]["labels"] for d in inst.values()]
        ys += y
        fig.add_trace(go.Box(y=y, x=[v] * len(y), name=v, boxpoints="all", jitter=0.5, pointpos=0, marker=dict(color=colors[v], size=5), line=dict(color=colors[v]),
                             hovertemplate="Verhältnis %{y:.2f}<extra>" + v + "</extra>"))
    fig.add_hline(y=1.0, line=dict(color="gray", dash="dot"))
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=list(C.BAND_VARIANTS[1:]))
    fig.update_yaxes(range=[0, _top(ys, 1.08, 1.1)], title_text="Labels / Labels bei immer exakt (je Instanz)")
    fig.update_layout(showlegend=False)
    return _layout(fig, 360)


def build_time_chart(rows: list) -> go.Figure:
    """Zeitreihe (Vormessung): CPU-Zeit der 30 Instanzen je Variante, aufgeteilt in Master-LP, Pricing mit Limit, exaktes Pricing und Rest (nur Information)."""
    names = [r["variante"] for r in rows]
    fig = go.Figure()
    for key, label, color in (("lp", "Master-LP", C.COLOR_LINE3), ("limit", "Pricing mit Limit", C.COLOR_LINE2), ("exakt", "exaktes Pricing", C.COLOR_LINE), ("rest", "Rest", C.COLOR_OTHER)):
        fig.add_trace(go.Bar(x=names, y=[max(r[key], 0.0) for r in rows], name=label, marker_color=color))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=names)
    fig.update_yaxes(range=[0, _top([r["cpu_sum"] for r in rows], 1.08, 1.0)], title_text="CPU-Zeit (s), Summe über 30 Instanzen")
    return _layout(fig, 340, legend_bottom=True)
