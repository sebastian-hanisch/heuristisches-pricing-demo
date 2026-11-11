"""Gemeinsame Fixtures: die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b).

Die Mini-Instanz ist das Handbeispiel: Depot bei (5, 5) und sechs Kunden auf einem Gitter, Entfernung = Fahrzeit = Kosten = Manhattan-Abstand, Bedienzeit 2, Horizont 40,
Kapazität 10, Zeitfenster [früh, spät]. Die Dualpreise der ersten Runde sind die Längen der Einzelrouten (2 mal der Abstand zum Depot). Die Zahlen stehen hier **noch einmal von Hand**
(nicht aus hpr_scenario); `test_algorithm.py` vergleicht beide Fassungen. Die Handrechnung steht als Rechnung in den Tests, nicht als abgeschriebenes Ergebnis."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from hpr_scenario import Instance  # noqa: E402

# Kunde: (Punkt, Last, früh, spät); Index 0 ist das Depot
HAND_TABLE = {
    0: ((5, 5), 0, 0, 40),
    1: ((6, 7), 2, 16, 34),
    2: ((1, 6), 3, 5, 19),
    3: ((8, 7), 4, 5, 12),
    4: ((6, 0), 2, 26, 32),
    5: ((10, 7), 2, 16, 31),
    6: ((9, 7), 3, 18, 32),
}
SERVICE, HORIZON, CAPACITY = 2, 40, 10


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def build_hand():
    pts = tuple(HAND_TABLE[i][0] for i in range(7))
    d = tuple(tuple(manhattan(a, b) for b in pts) for a in pts)
    inst = Instance(6, pts, d, tuple(HAND_TABLE[i][1] for i in range(7)), tuple(HAND_TABLE[i][2] for i in range(7)), tuple(HAND_TABLE[i][3] for i in range(7)), SERVICE, HORIZON, CAPACITY)
    pi = (0,) + tuple(2 * manhattan(HAND_TABLE[0][0], HAND_TABLE[i][0]) for i in range(1, 7))
    return inst, pi


@pytest.fixture
def hand():
    """(Instanz, Dualpreise der ersten Runde) des Handbeispiels aus der Tabelle oben."""
    return build_hand()
