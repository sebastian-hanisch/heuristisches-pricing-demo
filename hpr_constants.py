"""Konstanten: Regler-Grenzen, feste Annahmen, Farben, Schnellstart-Szenarien und Texte, die App und README gemeinsam haben."""

# --- Regler ---------------------------------------------------------------------------------------------------------------------------------
# Komplexität am Regler-Maximum (n = 30, Fensterbreite 100, gruppiert, k = 8): Die exakte Spaltenerzeugung erzeugt über alle Runden einige Hunderttausend Labels (bei den 15 gemessenen
# gruppierten Instanzen 128 327 bis 1 101 093), und das Verfahren prüft je neues Label alle lebenden Labels seines Kunden. MAX_LABELS_CALL und MAX_LABELS_COLGEN fangen das ab: Die Rechnung
# bricht nach so vielen erzeugten Labels ab (einige Sekunden in Python) und die App zeigt den Abbruch als Befund; die festen Messreihen (Experiment 5) bleiben davon unberührt.
N_MIN, N_MAX, DEFAULT_N = 8, 30, 20
WIDTH_OPTIONS, DEFAULT_WIDTH = (40, 100), 40
TYP_OPTIONS, DEFAULT_TYP = ("zufall", "cluster"), "zufall"
K_OPTIONS, DEFAULT_K = (4, 6, 8), 8                          # Gedächtnis (ng-Nachbarschaft) der Live-Instanz; die festen Messreihen rechnen mit k = 8
LIMIT_OPTIONS, DEFAULT_LIMIT = (5, 10, 20), 10               # Etikettenlimit der Live-Instanz
SEED_MAX, DEFAULT_SEED = 999999, 0
MAX_LABELS_CALL = 300_000                                    # Abbruch eines einzelnen Preisproblems der Live-Instanz bei so vielen erzeugten Labels
MAX_LABELS_COLGEN = 600_000                                  # Abbruch einer Spaltenerzeugung der Live-Instanz bei so vielen erzeugten Labels über alle Runden zusammen
HAND_LIMIT_OPTIONS, DEFAULT_HAND_LIMIT = (1, 2, 3), 1        # Etikettenlimit im Handbeispiel
HAND_NEW_OPTIONS, DEFAULT_HAND_NEW = (1, 2, 3, 5), 3         # neue Spalten je Runde im Handbeispiel
HAND_K = 6                                                   # Gedächtnis im Handbeispiel: elementar (k = Zahl der Kunden)
HAND_MAX_NEW_FREE = 15                                       # neue Spalten je Runde der Live-Instanz und der Messreihen
MEMORY_K_BANDS = 8                                           # Gedächtnis der festen Messreihen
HORIZON, SERVICE, CAPACITY = 300, 10, 70
# Kipp-Rechner (Experiment 4)
MASTER_COST_OPTIONS = (10, 30, 100, 380, 1000, 3000, 10000, 20000, 40000, 100000)   # Kosten eines Master-LPs in „Labels des exakten Preisproblems“
DEFAULT_MASTER_COST = 380                                    # gemessen am Rechner der Zeitmessung (3,18 ms je Master-LP gegen 8,34 µs je exaktem Label); eine ANNAHME für jeden anderen Aufbau
LABEL_COST_MIN, LABEL_COST_MAX, DEFAULT_LABEL_COST, LABEL_COST_STEP = 0.2, 1.0, 1.0, 0.05   # Kosten eines Labels im Limit-Pricing im Verhältnis zu einem im exakten: eine ANNAHME

# Messreihen (data/laeufe_v13.json): 30 Instanzen mit Breite 100 (15 zufällig, 15 gruppiert, Zufalls-Seeds 0 bis 14) und 16 mit Breite 150 (je 8, Seeds 0 bis 7), je vier Varianten
BAND_VARIANTS = ("exakt", "L5", "L10", "L20")
BAND_WIDTHS = (100, 150)
BAND_SEEDS = {100: tuple(range(15)), 150: tuple(range(8))}

# --- Farben ---------------------------------------------------------------------------------------------------------------------------------
COLOR_OK = "#2F6B65"
COLOR_BAD = "#C0392B"
COLOR_OTHER = "rgba(150,150,150,0.55)"
COLOR_LINE = "#4c78a8"
COLOR_LINE2 = "#e08a2c"
COLOR_LINE3 = "#7a5195"
COLOR_LINE4 = "#2F6B65"

# --- Schnellstart-Szenarien -----------------------------------------------------------------------------------------------------------------
# Jedes Szenario setzt alle Regler: Handbeispiel (Limit, neue Spalten je Runde), Live-Instanz (Größe, Fensterbreite, Typ, Gedächtnis, Limit, Zufalls-Seed) und Kipp-Rechner.


def _scenario(hand_limit, hand_new, n, width, typ, k, limit, seed, master_cost, label_cost):
    return {"hand_limit": hand_limit, "hand_new": hand_new, "n": n, "width": width, "typ": typ, "k": k, "limit": limit, "seed": seed, "master_cost": master_cost, "label_cost": label_cost}


def _s(**kw):
    base = dict(hand_limit=DEFAULT_HAND_LIMIT, hand_new=DEFAULT_HAND_NEW, n=DEFAULT_N, width=DEFAULT_WIDTH, typ=DEFAULT_TYP, k=DEFAULT_K, limit=DEFAULT_LIMIT, seed=DEFAULT_SEED,
                master_cost=DEFAULT_MASTER_COST, label_cost=DEFAULT_LABEL_COST)
    base.update(kw)
    return _scenario(**base)


PRESETS = {
    "Limit 1 verfehlt den besten Weg (Voreinstellung)": _s(),
    "Limit 2 im Handbeispiel": _s(hand_limit=2),
    "Kleines Limit 5 auf einer Zufallsinstanz": _s(limit=5),
    "Gruppierte Kunden, Breite 100, Limit 20": _s(n=30, width=100, typ="cluster", limit=20),
    "Teurer Master: 20 000 Labels je Master-LP": _s(master_cost=20000),
    "Kleine Instanz: das Limit spart nichts": _s(n=8, limit=20),
}
PRESET_HELP = {
    "Limit 1 verfehlt den besten Weg (Voreinstellung)": "Handbeispiel mit Etikettenlimit 1 und 3 neuen Spalten je Runde (Experimente 1 und 2); Zufallsinstanz mit 20 Kunden, Fensterbreite 40, Gedächtnis 8, Limit 10, Zufalls-Seed 0.",
    "Limit 2 im Handbeispiel": "Handbeispiel mit Etikettenlimit 2: Das Limit findet im ersten Preisproblem den besten Weg (Experiment 1).",
    "Kleines Limit 5 auf einer Zufallsinstanz": "Zufallsinstanz mit 20 Kunden und Etikettenlimit 5 statt 10: kleinere Limits sparen im Mittel mehr Labels (Experiment 3).",
    "Gruppierte Kunden, Breite 100, Limit 20": "Gruppiert verteilte Kunden, 30 Kunden, Fensterbreite 100, Limit 20: eine größere Rechnung als die Voreinstellung (Experiment 3).",
    "Teurer Master: 20 000 Labels je Master-LP": "Kipp-Rechner mit 20 000 Labels je Master-LP statt 380: Das Limit 5 lohnt sich dann nicht mehr, Limit 10 und 20 noch (Experiment 4; die Kosten des Masters sind hier eine Annahme).",
    "Kleine Instanz: das Limit spart nichts": "Zufallsinstanz mit 8 Kunden und Limit 20: Das Limit greift nur wenige Male, und weil am Ende ein exakter Aufruf kommt, braucht die Rechnung mehr Labels als immer exakt (Experiment 3).",
}

# --- Text, den App und README gleich führen -------------------------------------------------------------------------------------------------
ASSUMPTIONS_MARKDOWN = """\
**Annahmen**
- Eigene Instanzen im Stil der Solomon-Instanzen (Quadrat 100 × 100, Fahrzeit gleich Entfernung, Bedienzeit 10, Horizont 300, Kapazität 70), **nicht die Originalinstanzen**; das Handbeispiel rechnet mit dem Manhattan-Abstand auf einem Gitter.
- Die Spaltenerzeugung hat einen Überdeckungs-Master (jeder Kunde mindestens einmal überdeckt), Gedächtnis k = 8 in den festen Messreihen und höchstens 15 neue Spalten je Runde; die Dualpreise kommen aus HiGHS (SciPy).
- Das **Etikettenlimit** ist ein Limit nach Kosten: Ein Knoten behält höchstens L lebende Labels, bei Überschreitung fliegt das Label mit den größten Kosten. **Die gelockerte Dominanz der Literatur ist weder gebaut noch gemessen.**
- Gezählt werden Labels, nicht Sekunden. Sekunden sind nur Information (Python, HiGHS als Master-Löser, Rechner durch andere Läufe ausgelastet, also Größenordnung).

**Grenzen**
- Gemessen ist nur n = 30, Fensterbreite 100 (30 Instanzen) und 150 (16 Instanzen), Gedächtnis k = 8, Überdeckungs-Master, metrische Kosten; für größere Instanzen, Fensterbreite 40 in den festen Messreihen, andere Master und Branch-and-Price ist nichts gemessen.
- Die Zeit ist nur für Fensterbreite 100 und die 30 genannten Instanzen gemessen, mit der Messdatei der Planung (nicht mit dem Kern dieser Demo neu gemessen). Wie viel das Limit an Zeit spart, hängt am Verhältnis von Master-Zeit zu Pricing-Zeit; bei einem teureren Master wäre der Gewinn kleiner.
- Je Typ stehen nur 15 (Breite 100) bzw. 8 (Breite 150) Instanzen; das Verhältnis der Labels zu „exakt“ streut stark.
- Für das Schema „heuristisches Pricing zuerst, exakt nur zum Beweis“ als Ganzes wurde keine eigene Quelle gefunden; die Demo stellt es als Messung dar, nicht als Nachbau eines Verfahrens aus der Literatur.

**Bekannte Probleme und Unsicherheiten**
- Ursachen („weil …“) sind Deutungen, wo es dasteht; gemessen sind die Zählungen.
- Die Dualpreise hängen vom Löser des Master-Problems ab und können mit einer anderen Version der Bibliothek abweichen; die Zahlen der festen Messreihen sind mit dem Löser dieser Demo neu gerechnet und mit der Messung der Planung abgeglichen, bei einer anderen Version kann sich der Weg der Spaltenerzeugung ändern, nicht die Endschranke.
- Die Darstellung der Tabellen und Diagramme ist im Browser am Computer und in einem 375 Pixel breiten Fenster durchgesehen, nicht auf anderen Geräten oder in anderen Browsern. Die Diagramme haben keine Auswahl per Mausklick.
"""
