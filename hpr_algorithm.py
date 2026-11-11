"""Kern: Label-Verfahren für den Weg mit den kleinsten reduzierten Kosten (Preisproblem der Spaltenerzeugung), wahlweise mit Etikettenlimit je Knoten.

Ein Label ist ein Teilweg: (Zeit, Kosten, Last, Gedächtnis, Knoten). Das Verfahren verlängert Labels in Zeitreihenfolge und streicht dominierte Labels (Kosten, Zeit, Last
und Gedächtnis des anderen Labels sind alle höchstens so groß, das Gedächtnis als Teilmenge). **Etikettenlimit L:** Ein Knoten darf höchstens L lebende Labels behalten; ist er
voll, fliegt das Label mit den größten Kosten (das neue eingeschlossen). Das Limit sieht nur die Kosten; es kann den besten Weg verlieren. Ohne Limit ist das Verfahren exakt.

Einheiten (je eine Regel, DEMO-PLAYBOOK §1b): `dominates`, `dominated_by`, `limit_victim`, `price` (Komposition), `check_route` (unabhängiger Routenprüfer), `route_cost`.
Gezählt werden Labels (keine Sekunden). Zufall kommt nur in `hpr_scenario.make_instance` vor (Generator `random.Random(seed)`).

Gleichstände beim Limit (wie im Messcode der Planung): Unter den lebenden Labels des vollen Knotens fliegt bei gleichen größten Kosten das **früher** eingefügte (erstes Maximum);
ist das so bestimmte Label nicht teurer als das neue (`<=`), fliegt stattdessen das neue. Die Regel ist nicht gleichgültig: Gleiche größte Kosten kommen vor (im Handbeispiel und in den
Zufallsinstanzen), und eine andere Regel (das später eingefügte fliegt) ändert Labels und Weg der Spaltenerzeugung, nicht die Endschranke (`tests/test_algorithm.py`)."""

import heapq

from hpr_scenario import Instance, ng_masks

EPS = 1e-9

# Positionen im Label (Liste, damit „gestrichen“ in place gesetzt werden kann)
T, COST, LOAD, MEM, NODE, PARENT, DEAD, NR = range(8)


class PricingResult:
    """Ergebnis eines Preisproblem-Laufs: negative Routen, Zähler, lebende Labels; bei `trace` die Entscheidung je neuem Label in `events`."""

    def __init__(self, routes, generated, dominated, limited, aborted, live, events):
        self.routes = routes            # [(reduzierte Kosten, Route)], aufsteigend, höchstens max_routes
        self.generated = generated      # erzeugte Labels, Start im Depot und sofort verworfene mitgezählt
        self.dominated = dominated      # durch Dominanz gestrichene Labels (neue und alte)
        self.limited = limited          # wie oft das Limit angewendet wurde (Knoten voll)
        self.aborted = aborted          # Abbruch am Labelbudget
        self.live = live                # sortierte (Knoten, Zeit, Kosten, Last, Gedächtnis) aller lebenden Labels
        self.events = events            # nur bei trace=True

    @property
    def best(self):
        """Beste Route (reduzierte Kosten, Route) oder None, wenn keine Route negative Kosten hat."""
        return self.routes[0] if self.routes else None


def dominates(old, cost, time, load, mem) -> bool:
    """Regel der Dominanz: Das Label `old` (Liste mit T, COST, LOAD, MEM) dominiert ein neues Label (cost, time, load, mem) am selben Knoten,
    wenn Kosten, Zeit und Last nicht höher sind und das Gedächtnis von `old` eine Teilmenge ist (Toleranz EPS bei Kosten und Zeit)."""
    return old[COST] <= cost + EPS and old[T] <= time + EPS and old[LOAD] <= load and (old[MEM] & ~mem) == 0


def dominated_by(old, cost, time, load, mem) -> bool:
    """Umkehrung: das neue Label (cost, time, load, mem) dominiert das alte `old`."""
    return cost <= old[COST] + EPS and time <= old[T] + EPS and load <= old[LOAD] and (mem & ~old[MEM]) == 0


def limit_victim(labels, survivors, new_cost):
    """Regel des Etikettenlimits für einen vollen Knoten: Index des Labels, das fliegt. `survivors` sind die Indizes der lebenden Labels des Knotens (in Einfügereihenfolge).
    Das Label mit den größten Kosten fliegt (bei Gleichstand das früher eingefügte); ist es nicht teurer als das neue (`<=`), fliegt das neue: Rückgabe None."""
    worst = max(survivors, key=lambda x: labels[x][COST])
    return None if labels[worst][COST] <= new_cost else worst


def _route_of(labels, li) -> tuple:
    route = []
    x = li
    while x != -1:
        route.append(labels[x][NODE])
        x = labels[x][PARENT]
    return tuple(reversed(route))[1:]


def route_cost(inst: Instance, route) -> float:
    """Länge der Route Depot - Kunden - Depot (Entfernung = Kosten)."""
    seq = (0,) + tuple(route) + (0,)
    return sum(inst.d[a][b] for a, b in zip(seq, seq[1:]))


def price(inst: Instance, pi, k: int, limit=None, max_routes: int = 15, max_labels=None, trace: bool = False) -> PricingResult:
    """Label-Verfahren mit optionalem Etikettenlimit `limit` je Knoten (None = exakt).

    `pi[0] = 0`, `pi[j]` Dualpreis des Kunden j; `k` Größe des Gedächtnisses (k = n elementar). Gibt die `max_routes` besten Routen mit negativen reduzierten Kosten zurück.
    `max_labels`: Abbruch (aborted = True), sobald so viele Labels erzeugt sind. `trace`: je neues Label eine Entscheidung in `events` (Nummer, Knoten, Weg, Zeit, Kosten, Last,
    Entscheidung, bei Limit das verdrängte Label)."""
    n = inst.n
    ng = ng_masks(inst, k)
    d, svc, H, Q = inst.d, inst.service, inst.horizon, inst.capacity
    labels = [[0.0, 0.0, 0, 0, 0, -1, False, 0]]
    at_node = [[] for _ in range(n + 1)]
    heap = [(0.0, 0)]
    generated = 1
    dominated = limited = 0
    ended = []
    events = []
    paths = {0: ()}
    aborted = False
    while heap:
        _, li = heapq.heappop(heap)
        L = labels[li]
        if L[DEAD]:
            continue
        if max_labels is not None and generated > max_labels:
            aborted = True
            break
        t, c, q, mem, i = L[T], L[COST], L[LOAD], L[MEM], L[NODE]
        if i != 0 and t + svc + d[i][0] <= H:
            ended.append((c + d[i][0], li))
        for j in range(1, n + 1):
            if j == i or (mem >> j) & 1:
                continue
            q2 = q + inst.demand[j]
            if q2 > Q:
                continue
            arr = t + (svc if i != 0 else 0.0) + d[i][j]
            if arr > inst.due[j] + EPS:
                continue
            t2 = max(arr, inst.ready[j])
            c2 = c + d[i][j] - pi[j]
            m2 = (mem & ng[j]) | (1 << j)
            generated += 1
            lst = at_node[j]
            if trace:
                nr = generated - 1
                paths[nr] = paths[L[NR]] + (j,)
                ev = dict(nr=nr, node=j, path=paths[nr], parent=L[NR], time=t2, cost=c2, load=q2, live_before=[labels[oi][NR] for oi in lst], killer=None, killed=[], victim=None, status=None)
            killer = next((oi for oi in lst if dominates(labels[oi], c2, t2, q2, m2)), None)
            if killer is not None:
                dominated += 1
                if trace:
                    ev["status"], ev["killer"] = "dominiert", labels[killer][NR]
                    events.append(ev)
                continue
            survivors = []
            for oi in lst:
                O = labels[oi]
                if dominated_by(O, c2, t2, q2, m2):
                    O[DEAD] = True
                    dominated += 1
                    if trace:
                        ev["killed"].append(O[NR])
                else:
                    survivors.append(oi)
            at_node[j] = survivors
            if limit is not None and len(survivors) >= limit:
                limited += 1
                victim = limit_victim(labels, survivors, c2)
                if victim is None:
                    if trace:
                        ev["status"] = "limit-neu"
                        ev["worst"] = labels[max(survivors, key=lambda x: labels[x][COST])][NR]
                        events.append(ev)
                    continue
                labels[victim][DEAD] = True
                survivors.remove(victim)
                if trace:
                    ev["victim"] = labels[victim][NR]
            labels.append([t2, c2, q2, m2, j, li, False, generated - 1])
            idx = len(labels) - 1
            at_node[j].append(idx)
            heapq.heappush(heap, (t2, idx))
            if trace:
                ev["status"] = "behalten"
                events.append(ev)
    res = {}
    for rc, li in ended:
        route = _route_of(labels, li)
        if rc < -1e-7 and route not in res:
            res[route] = rc
    routes = sorted(((rc, r) for r, rc in res.items()))[:max_routes]
    live = tuple(sorted((L[NODE], L[T], L[COST], L[LOAD], L[MEM]) for L in labels if not L[DEAD]))
    return PricingResult(routes, generated, dominated, limited, aborted, live, events)


def check_route(inst: Instance, pi, route):
    """Unabhängige Prüfung einer Route (ohne Labels): Fenster, Last und Horizont eingehalten? Gibt die reduzierten Kosten zurück, sonst None."""
    seq = (0,) + tuple(route) + (0,)
    t = 0.0
    q = 0
    cost = 0.0
    for a, b in zip(seq, seq[1:]):
        t += (inst.service if a != 0 else 0.0) + inst.d[a][b]
        cost += inst.d[a][b]
        if b != 0:
            if t > inst.due[b] + 1e-7:
                return None
            t = max(t, inst.ready[b])
            q += inst.demand[b]
            cost -= pi[b]
    if q > inst.capacity or t > inst.horizon + 1e-7:
        return None
    return cost
