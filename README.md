# Heuristisches Pricing: erst gelockert, exakt nur zum Beweis – Streamlit-Demo

<!-- Nach dem Deploy hier direkt den Live-Link einsetzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-heuristisches-pricing-demo.streamlit.app/)** -->

Demo der Linie „Ressourcenwege und Spaltenerzeugung“ in der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“. Die **Spaltenerzeugung** löst eine große Routenplanung in Runden: Ein **Master-Problem**
(ein lineares Programm) wählt aus den bekannten Routen die billigste Überdeckung der Kunden und liefert **Dualpreise**; das **Pricing** sucht eine neue Route mit negativen **reduzierten Kosten** (Weglänge minus die Dualpreise der besuchten Kunden), und zwar mit dem
**Label-Verfahren** (Teilwege heißen **Labels**, dominierte werden gestrichen). Diese Demo fragt nur eines: **Muss jedes Pricing beweisen, dass es die beste Route gefunden hat, oder genügt es, in den meisten Runden irgendeine gute neue Route zu finden, und der teure exakte
Aufruf kommt erst, wenn die Heuristik nichts mehr findet?** Die Heuristik ist ein **Etikettenlimit**: Jeder Kunde behält höchstens L lebende Labels. Gezählt werden Labels und Runden; Sekunden stehen nur zur Information da.

Die Anwendung in einem Fall zeigt [crew-pairing-demo](https://github.com/sebastian-hanisch/crew-pairing-demo) (Besatzungsplanung im Zugverkehr: Preisproblem als Label-Verfahren, immer exakt; nicht gemessen). Aus derselben Linie:
[pricing-dualpreise-demo](https://github.com/sebastian-hanisch/pricing-dualpreise-demo) (die Schleife Master–Pricing), [elementar-pricing-demo](https://github.com/sebastian-hanisch/elementar-pricing-demo) (was es kostet, jeden Kunden höchstens einmal zu besuchen) und
[eimer-labeling-demo](https://github.com/sebastian-hanisch/eimer-labeling-demo) (eine Sparmaßnahme im Pricing, die das Ergebnis nie ändert). **Abgrenzung:** [hub-labeling-demo](https://github.com/sebastian-hanisch/hub-labeling-demo) meint etwas anderes
(vorberechnete Listen für schnelle Abfragen kürzester Wege); hier sind Labels Teilwege im Preisproblem.

## Warum dieses Problem

Das Pricing ist der teure Teil der Spaltenerzeugung: In der Zeitmessung (30 Instanzen mit 30 Kunden, Fensterbreite 100, Gedächtnis 8, Überdeckungs-Master, Python; Rechner ausgelastet, also Größenordnung) macht das exakte Pricing 96,2 % der CPU-Zeit bei immer exaktem Pricing aus. Das Etikettenlimit
spart dort Labels, aber es liefert nur Routen, keinen Beweis; deshalb läuft das exakte Pricing am Ende trotzdem, und die Endschranke bleibt dieselbe. Die Demo zeigt den Mechanismus am Handbeispiel mit sechs Kunden, die Zahlen an einer Zufallsinstanz mit bis zu 30 Kunden
und in 46 festen Instanzen, und sie nennt, wann sich das nicht mehr lohnt.

**Kurz:** In allen 46 gemessenen Instanzen (30 Kunden, Gedächtnis 8, Überdeckungs-Master, eigene Instanzen, Python) ist die Endschranke mit Limit-Pricing und mit immer exaktem Pricing gleich. Bei Fensterbreite 100 braucht das Limit im Mittel der Verhältnisse 0,52 / 0,60 / 0,71 der Labels
(Limit 5 / 10 / 20; in allen 30 Instanzen weniger), aber +36 / +23 / +10 % Runden, also mehr Master-Aufgaben. Die Zeitmessung (Breite 100, 30 Instanzen, Rechner ausgelastet, also Größenordnung) zeigt für diesen Aufbau eine CPU-Zeit von 0,36 / 0,39 / 0,46 der CPU-Zeit bei immer exaktem Pricing,
weil dort das Pricing überwiegt und ein Master-LP nur etwa 380 Labels kostet; bei einem teureren Master wäre der Gewinn kleiner, im Modell kippt es bei etwa 16 300 / 22 000 / 40 500 Labels je Master-LP (nicht gemessen).

## Befunde und Korrekturen gegenüber dem Plan

- **Neu gerechnet statt übernommen (Zählungen):** Die 184 Läufe der Messreihen (46 Instanzen × 4 Varianten) sind mit dem Kern dieser Demo neu gerechnet (`tools/baender_bauen.py`), kein Lauf ist abgebrochen. Beim Bau wurde jede Zeile mit der Rohausgabe der früheren Messung verglichen: Runden, Spalten,
  Labels (gesamt, im Limit-Pricing, im exakten Pricing), Limit-Treffer und exakte Aufrufe stimmen in 184 von 184 Zeilen überein, die Endschranke bis auf die Rundung der Rohausgabe (größte Abweichung unter 10⁻⁶). Dieser Abgleich ist nicht Teil der Testsuite (die Rohausgaben liegen nicht im Repo);
  `data/vormessung_abgleich.json` hält ihn fest, ein Test prüft die Datei, und eine Stichprobe von 4 Instanzen (16 Läufe) wird in der Suite neu gerechnet.
- **Nicht neu gemessen (Zeit):** Die Zeitreihe (360 Läufe: 30 Instanzen × 4 Varianten × 3 Wiederholungen, ein Prozess, Rechner durch andere Sitzungen ausgelastet) stammt aus der Messdatei der früheren Messung (`data/zeit_vormessung.json`) und ist **nicht mit dem Kern dieser Demo neu gemessen.** Runden und Labels dieser 360 Läufe stimmen
  mit den neu gerechneten Läufen überein (Test). Zeiten werden nie festgeschrieben.
- **Korrektur: Die Gleichstandsregel des Limits ist nicht gleichgültig.** Der Plan nannte für gleiche größte Kosten „das später eingefügte Label fliegt“ („wie im Messcode“); der Messcode (und diese Demo) nimmt das früher eingefügte. Gleiche größte Kosten kommen vor: Im Handbeispiel mit Limit 2 braucht die Spaltenerzeugung mit der Regel dieser Demo 238 Labels,
  mit der anderen Regel 188 (so stand es in der Handrechnung des Plans); in der Zufallsinstanz mit Zufalls-Seed 1, Breite 100 und Limit 5 sind es 59 713 Labels gegen 59 711. Die Endschranke ist in allen Fällen gleich. Limit 1 und das exakte Pricing sind von der Regel im Handbeispiel nicht berührt (190 und 280 Labels wie in der Handrechnung).
- **Neu gegenüber dem Plan:** CPU-Zeit je Label im Limit-Pricing 3,40 / 4,15 / 5,10 µs (Limit 5 / 10 / 20) gegen 8,34 µs im exakten Pricing, also 0,41 / 0,50 / 0,61 (errechnet aus der Messdatei der Zeit und den neu gerechneten Label-Zählungen; Rechner ausgelastet). Das passt dazu, dass das Zeitverhältnis unter dem Label-Verhältnis liegt; setzt man die gemessenen Kosten je Limit-Label und die etwa 380 Labels je Master-LP in das Modell des Kipp-Rechners ein, liegt es bei 0,38 / 0,40 / 0,46 gegen gemessen 0,36 / 0,39 / 0,46.
  **Deutung (nicht eigens geprüft):** Im Limit-Pricing sehen die Dominanzprüfungen weniger lebende Labels an.
- **Das Handbeispiel hat mehr negative Routen, als das Verfahren liefert:** 58 der 65 zulässigen Routen haben bei den Dualpreisen der ersten Runde negative reduzierte Kosten, das exakte Label-Verfahren liefert 48 (Routen über dominierte Labels entstehen nicht); die beste Route ist dieselbe.
- **Kein Beleg für eine Quelle:** Für das Schema „heuristisches Pricing zuerst, exakt nur zum Beweis“ als Ganzes wurde keine eigene Quelle gefunden; die Demo stellt es als Messung dar.

## Modell

Ein Depot und Kunden mit Last, Zeitfenster und Dualpreis; Entfernung = Fahrzeit = Kosten; Warten vor einem Fenster ist kostenlos; Kapazität, Horizont (späteste Rückkehr) und Bedienzeit je Kunde. Ein Label am Kunden $i$ ist $(T, C, R, M)$: Zeit, reduzierte Kosten, verbrauchte Last, Gedächtnis (Menge). **Dominanz:** $O$ dominiert $N$, wenn
$C_O \le C_N$, $T_O \le T_N$, $R_O \le R_N$ und $M_O \subseteq M_N$; bei Gleichstand bleibt das ältere Label. Das Gedächtnis ist bei den Zufallsinstanzen die ng-Nachbarschaft mit $k = 8$ in den festen Messreihen (die acht nächsten Kunden; in der Live-Rechnung 4, 6 oder 8), beim Handbeispiel elementar (jeder Kunde höchstens einmal).

**Etikettenlimit:** Nach der Dominanzprüfung hält ein Kunde höchstens $L$ lebende Labels. Kommt ein weiteres, fliegt das Label mit den größten Kosten; bei gleichen größten Kosten das früher eingefügte; ist es nicht teurer als das neue, fliegt das neue. Das Limit sieht nur die Kosten, nicht Last und Zeit: Ein billigeres, aber volleres Label kann ein
Label verdrängen, das der beste Weg braucht (Handbeispiel, Limit 1). **Heuristisch zuerst:** Das Pricing läuft zuerst mit Limit; findet es mindestens eine neue Spalte, geht es damit weiter, sonst läuft das exakte Pricing; **die Rechnung endet erst, wenn das exakte Pricing keine neue Spalte findet.** Dann sind alle zulässigen Routen
geprüft, und der Zielwert des Masters ist das LP-Optimum über alle zulässigen Routen (bei Gedächtnis k < n über alle ng-Routen, nicht nur die elementaren): Die Endschranke hängt nicht vom Limit ab. Der Master ist ein Überdeckungs-Problem (jeder Kunde mindestens einmal), Anfangsspalten sind die Einzelfahrten, je Runde kommen höchstens 15 neue Spalten (im Handbeispiel 3) in den Master. Die Formeln stehen im Expander
**📐 Mathematische Formulierung** der App (`app.py`), mit Lesehilfe.

Zwei Arten von Instanzen: das **Handbeispiel** (6 Kunden, Manhattan-Abstand, alle Zahlen ganz, Bedienzeit 2, Horizont 40, Kapazität 10, Dualpreise der ersten Runde = Länge der Einzelroute) und **Zufallsinstanzen im Stil der Solomon-Instanzen** (Quadrat 100 × 100, Fahrzeit gleich Entfernung, Bedienzeit 10, Horizont 300,
Kapazität 70, Fensterbreite 40 oder 100 in der App und 100 oder 150 in den festen Messreihen, Kunden zufällig verteilt oder in fünf Gruppen; **nicht die Originalinstanzen**).

## Methodik

Der Kern (`hpr_algorithm.py`, `price`) verlängert Labels in Zeitreihenfolge um je einen Kunden; je Regel eine Funktion (`dominates`, `dominated_by`, `limit_victim`, `check_route`, `route_cost`); die Spaltenerzeugung (`hpr_colgen.py`, `colgen`) ruft sie der Reihe nach auf und zählt Labels, Runden, Limit-Treffer und exakte Aufrufe.
Das Master-LP löst HiGHS (SciPy); für das Handbeispiel gibt es einen Master mit exakten Brüchen (`master_exact`), weil HiGHS bei entarteten Master-Problemen andere gleichwertige Dualpreise wählt als die Handrechnung. Ein unabhängiger Routenprüfer bewertet gefundene Routen neu. Die **Experimente** der App: (1) das Limit Schritt für Schritt
am Handbeispiel (jede Verdrängung mit Begründung, dazu die Aufzählung aller Routen); (2) die ganze Schleife im Kleinen (Tabelle Runde × Variante, Regler für Limit und neue Spalten je Runde); (3) eine Zufallsinstanz live: immer exakt gegen Limit zuerst, Labels je Runde, Zeit nur zur Information; (4) ein Rechner für die Frage, wann das Limit
nicht mehr lohnt (Annahmen beschriftet); (5) die festen Messreihen mit Mittel, Median, Minimum und Maximum und die Zeitreihe.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen sind Zählungen (Labels, Runden) in Python an den genannten Instanzen; Zeiten sind nie ein Befund, sie stehen nur zur Information. Die feste Messreihe: 30 Kunden, Gedächtnis 8, Überdeckungs-Master, höchstens 15 neue Spalten je Runde, Fensterbreite 100 (15 zufällig verteilte und 15 gruppierte Instanzen, Zufalls-Seeds 0 bis 14)
und Fensterbreite 150 (je 8, Zufalls-Seeds 0 bis 7), vier Varianten (immer exakt, Limit 5, 10, 20): 184 Läufe, alle vollständig gerechnet. „Verhältnis“ heißt Labels der Variante geteilt durch Labels bei immer exaktem Pricing, in derselben Instanz; „Mittel der Verhältnisse“ ist nicht das Verhältnis der Mittel.
Die Spalte „Test“ nennt die Prüfung in `tests/` (Zahl-zu-Test-Tabelle).

| Frage | Befund (Voraussetzung im Satz) | Test |
|---|---|---|
| Handbeispiel (6 Kunden, elementar, Dualpreise der ersten Runde 6; 10; 10; 12; 14; 12): Labels des ersten Preisproblems? | Ohne Limit 66 Labels (48 gelieferte Routen mit negativen reduzierten Kosten), Limit 1: 23 (Limit 11-mal angewendet), Limit 2: 30 (13-mal), Limit 3: 36 (15-mal); die Aufzählung findet 65 zulässige elementare Routen, 58 davon mit negativen Kosten. | `test_algorithm.py::test_label_counts_of_the_first_pricing_call_as_in_the_hand_calculation`, `test_claims.py::test_hand_example_numbers_of_the_readme` |
| Handbeispiel: findet das Limit den besten Weg? | Die beste Route ist 3 → 5 → 6 mit reduzierten Kosten −22 (Länge 14 minus Dualpreise 36; die Aufzählung bestätigt sie). Limit 1 findet nur 3 → 1 → 5 mit −12 und **verfehlt den besten Weg**; Limit 2 und 3 finden ihn. | `test_algorithm.py::test_limit_1_misses_the_best_route_and_limit_2_finds_it`, `test_oracle_heuristisches_pricing.py` |
| Handbeispiel: warum scheitert Limit 1? | Das Label F14 (Weg 3 → 5, Kosten −17, Last 6) wird von F21 (Weg 3 → 1 → 5, Kosten −19, Last 8) verdrängt, weil F21 billiger ist und Kunde 5 nur ein Label behalten darf; von F21 aus ist Kunde 6 nicht mehr zu bedienen (Last 8 + 3 = 11 > 10), von F14 aus ging es (6 + 3 = 9 ≤ 10). | `test_algorithm.py::test_the_displacement_of_f14_by_f21_with_the_reason_from_the_hand_calculation` |
| Handbeispiel: die ganze Spaltenerzeugung (3 neue Spalten je Runde)? | Immer exakt: 5 Runden, 280 Labels. Limit 1: 6 Runden, 190 Labels (136 im Limit-Pricing, 54 im exakten; das Limit reichte in 5 von 6 Runden). Limit 2: 5 Runden, 238 Labels (2 exakte Aufrufe); Limit 3: 5 Runden, 211 Labels (1 exakter Aufruf). Endschranke in allen Varianten 38, gleich dem LP über alle 65 Routen (Dualpreise 3; 10; 5; 11; 5; 4). | `test_algorithm.py::test_exact_column_generation_of_the_hand_example_as_in_the_hand_calculation`, `test_limit_1_column_generation_of_the_hand_example_as_in_the_hand_calculation`, `test_limits_2_and_3_of_the_hand_example_differ_from_the_planning_log_by_the_tie_rule` |
| Ändert das Limit die Endschranke? | In allen 46 Instanzen (30 Kunden, Gedächtnis 8, Breite 100 und 150) ist die Endschranke bei allen vier Varianten gleich (Abweichung höchstens 10⁻⁶, die Datei rundet auf sechs Stellen); an kleinen Instanzen (6 Kunden, elementar) gleich dem LP über alle aufgezählten Routen, 40 Rechnungen. | `test_bands.py::test_the_end_bound_is_the_same_for_all_four_variants_in_all_46_instances`, `test_oracle_heuristisches_pricing.py::test_column_generation_ends_at_the_lp_optimum_over_all_routes_for_every_variant` |
| Wie viele Labels spart das Limit (Breite 100)? | Im Mittel der Verhältnisse 0,52 / 0,60 / 0,71 der Labels bei Limit 5 / 10 / 20 (kleinste und größte 0,25 bis 0,91 / 0,33 bis 0,88 / 0,38 bis 0,98), in 30 von 30 Instanzen weniger Labels; zufällig 0,57 / 0,67 / 0,79, gruppiert 0,47 / 0,53 / 0,64 (je 15 Instanzen); Summe der Labels gegen exakt 46,5 / 53,2 / 62,3 %. | `test_claims.py::test_label_ratios_of_the_readme` |
| … bei Breite 150? | Im Mittel 0,43 / 0,49 / 0,63; weniger Labels als exakt in 16, 16 und 15 von 16 Instanzen (bei Limit 20 einmal 1,02); Summe der Labels gegen exakt 37,7 / 40,6 / 50,3 %. | `test_claims.py::test_label_ratios_of_the_readme` |
| Was kostet das Limit? | Runden (Master-Aufgaben) bei Breite 100: 21,7 bei immer exakt gegen 29,5 / 26,7 / 23,9, also +36 / +23 / +10 %; bei Breite 150 25,1 gegen 32,5 / 31,6 / 29,4. | `test_claims.py::test_rounds_and_limit_hits_of_the_readme` |
| Wie oft reicht das Limit? | Das Limit-Pricing fand in 79,4 / 82,4 / 87,3 % der Runden eine neue Spalte (Breite 100); trotzdem entstehen 55,8 / 39,3 / 22,3 % der Labels im exakten Pricing, weil mindestens der Abschlussaufruf exakt sein muss; exakte Aufrufe im Mittel 6,1 / 4,7 / 3,0 gegen 21,7. | `test_claims.py::test_rounds_and_limit_hits_of_the_readme` |
| Zeit (Breite 100, 30 Instanzen, drei Wiederholungen, **aus der Messdatei der früheren Messung, nicht neu gemessen**; Rechner ausgelastet, also Größenordnung)? | CPU-Zeit der Summe über die 30 Instanzen gegen exakt 0,36 / 0,39 / 0,46; Mittel der Instanz-Verhältnisse 0,44 / 0,49 / 0,61, in 30 von 30 Instanzen schneller als exakt; Wanduhrzeit: Limit 20 in 28 von 30 schneller. Bei Limit 20 liegt das größte Instanz-Verhältnis bei 0,98 und damit innerhalb der Messunschärfe: „30 von 30 schneller“ ist dort nicht scharf. Aufteilung der CPU-Zeit bei immer exakt: Master-LP 2,07 s von 61,55 s, exaktes Pricing 59,19 s (96,2 %). | `test_claims.py::test_time_numbers_of_the_readme` |
| Was kostet ein Master-LP? | Bei immer exaktem Pricing im Mittel 3,18 ms (651 Aufrufe) gegen 8,34 µs je erzeugtem Label (7 096 412 Labels), also etwa 380 Labels je Master-LP (CPU-Zeit, Rechner ausgelastet). | `test_claims.py::test_time_numbers_of_the_readme` |
| Wann kippt es (Modell)? | Mit gleich teuren Labels im Limit- und im exakten Pricing ist das Limit im Modell billiger, solange ein Master-LP weniger als etwa 16 300 (Limit 5), 22 000 (Limit 10) und 40 500 Labels (Limit 20) kostet; bei 380 liegt der modellierte Aufwand bei 0,49 / 0,56 / 0,64 des Aufwands bei immer exakt (gemessen CPU-Summe 0,36 / 0,39 / 0,46: das Modell überschätzt), bei 20 000 bei 1,04 / 0,99 / 0,93. | `test_claims.py::test_kipp_numbers_of_the_readme` |
| Schnellstart-Szenarien (Zufallsinstanz, Kapazität 70, Gedächtnis 8) | Labels bei immer exakt → mit Limit: 20 Kunden, Breite 40, Zufalls-Seed 0, Limit 10: 17 998 → 10 537 (16 statt 23 Runden); Limit 5: 17 998 → 9 882 (21 statt 23 Runden); 30 Kunden, gruppiert, Breite 100, Limit 20: 254 029 → 179 293 (25 statt 23 Runden); **8 Kunden, Limit 20: 185 → 220 (das Limit braucht dort mehr Labels als immer exakt)**. | `test_presets.py::test_expected_verdict_lines_of_every_preset`, `test_claims.py::test_scenario_numbers_of_the_readme` |

**Breite 100, alle 30 Instanzen:**

| Variante | Instanzen | Labels (Mittel) | Labels / exakt (Mittel der Verhältnisse) | Median | Minimum | Maximum | Instanzen mit weniger Labels | Runden (Mittel) | Runden gegen exakt | Limit reichte (Anteil der Runden) | Exakte Aufrufe (Mittel) | Labels im exakten Pricing (Anteil) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exakt | 30 | 236 547 | 1,00 | 1,00 | 1,00 | 1,00 | – | 21,7 | – | – | 21,7 | 100,0 % |
| L5 | 30 | 109 931 | 0,52 | 0,49 | 0,25 | 0,91 | 30 von 30 | 29,5 | +36 % | 79,4 % | 6,1 | 55,8 % |
| L10 | 30 | 125 921 | 0,60 | 0,59 | 0,33 | 0,88 | 30 von 30 | 26,7 | +23 % | 82,4 % | 4,7 | 39,3 % |
| L20 | 30 | 147 375 | 0,71 | 0,71 | 0,38 | 0,98 | 30 von 30 | 23,9 | +10 % | 87,3 % | 3,0 | 22,3 % |

**Breite 100, 15 zufällig verteilte Instanzen:**

| Variante | Instanzen | Labels (Mittel) | Labels / exakt (Mittel der Verhältnisse) | Median | Minimum | Maximum | Instanzen mit weniger Labels | Runden (Mittel) | Runden gegen exakt | Limit reichte (Anteil der Runden) | Exakte Aufrufe (Mittel) | Labels im exakten Pricing (Anteil) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exakt | 15 | 131 307 | 1,00 | 1,00 | 1,00 | 1,00 | – | 20,3 | – | – | 20,3 | 100,0 % |
| L5 | 15 | 74 045 | 0,57 | 0,54 | 0,40 | 0,91 | 15 von 15 | 27,5 | +36 % | 79,9 % | 5,5 | 42,9 % |
| L10 | 15 | 87 768 | 0,67 | 0,64 | 0,44 | 0,88 | 15 von 15 | 25,1 | +24 % | 83,5 % | 4,1 | 27,4 % |
| L20 | 15 | 103 566 | 0,79 | 0,77 | 0,53 | 0,98 | 15 von 15 | 22,6 | +12 % | 89,7 % | 2,3 | 13,3 % |

**Breite 100, 15 gruppierte Instanzen:**

| Variante | Instanzen | Labels (Mittel) | Labels / exakt (Mittel der Verhältnisse) | Median | Minimum | Maximum | Instanzen mit weniger Labels | Runden (Mittel) | Runden gegen exakt | Limit reichte (Anteil der Runden) | Exakte Aufrufe (Mittel) | Labels im exakten Pricing (Anteil) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exakt | 15 | 341 787 | 1,00 | 1,00 | 1,00 | 1,00 | – | 23,1 | – | – | 23,1 | 100,0 % |
| L5 | 15 | 145 817 | 0,47 | 0,46 | 0,25 | 0,63 | 15 von 15 | 31,5 | +36 % | 79,0 % | 6,6 | 62,3 % |
| L10 | 15 | 164 074 | 0,53 | 0,55 | 0,33 | 0,66 | 15 von 15 | 28,4 | +23 % | 81,5 % | 5,3 | 45,6 % |
| L20 | 15 | 191 183 | 0,64 | 0,65 | 0,38 | 0,83 | 15 von 15 | 25,2 | +9 % | 85,2 % | 3,7 | 27,1 % |

**Breite 150, alle 16 Instanzen (8 zufällig, 8 gruppiert):**

| Variante | Instanzen | Labels (Mittel) | Labels / exakt (Mittel der Verhältnisse) | Median | Minimum | Maximum | Instanzen mit weniger Labels | Runden (Mittel) | Runden gegen exakt | Limit reichte (Anteil der Runden) | Exakte Aufrufe (Mittel) | Labels im exakten Pricing (Anteil) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exakt | 16 | 587 839 | 1,00 | 1,00 | 1,00 | 1,00 | – | 25,1 | – | – | 25,1 | 100,0 % |
| L5 | 16 | 221 450 | 0,43 | 0,42 | 0,23 | 0,59 | 16 von 16 | 32,5 | +30 % | 77,9 % | 7,2 | 70,4 % |
| L10 | 16 | 238 949 | 0,49 | 0,50 | 0,25 | 0,82 | 16 von 16 | 31,6 | +26 % | 82,2 % | 5,6 | 50,5 % |
| L20 | 16 | 295 753 | 0,63 | 0,58 | 0,33 | 1,02 | 15 von 16 | 29,4 | +17 % | 85,1 % | 4,4 | 32,5 % |

**Zeitreihe (Breite 100, 30 Instanzen, CPU-Zeit und Wanduhrzeit je Instanz als Median von drei Wiederholungen; aus der Messdatei der früheren Messung, nicht neu gemessen; Rechner ausgelastet, nur Größenordnung):**

| Variante | CPU-Zeit, Summe (s) | Summe / exakt | Median der Instanz-Verhältnisse (Minimum bis Maximum) | Mittel der Instanz-Verhältnisse | Schneller als exakt (CPU) | Wanduhr, Mittel der Instanz-Verhältnisse | Schneller als exakt (Wanduhr) |
|---|---|---|---|---|---|---|---|
| exakt | 61,55 | 1,00 | 1,00 (1,00 bis 1,00) | 1,00 | – | 1,00 | – |
| L5 | 22,39 | 0,36 | 0,42 (0,15 bis 0,68) | 0,44 | 30 von 30 | 0,43 | 30 von 30 |
| L10 | 23,84 | 0,39 | 0,49 (0,19 bis 0,72) | 0,49 | 30 von 30 | 0,49 | 30 von 30 |
| L20 | 28,09 | 0,46 | 0,61 (0,22 bis 0,98) | 0,61 | 30 von 30 | 0,62 | 28 von 30 |

**Wohin die CPU-Zeit geht (Summe über die 30 Instanzen):**

| Variante | gesamt (s) | Master-LP (s) | Pricing mit Limit (s) | Exaktes Pricing (s) | Rest (s) |
|---|---|---|---|---|---|
| exakt | 61,55 | 2,07 | – | 59,19 | 0,29 |
| L5 | 22,39 | 2,75 | 4,95 | 14,44 | 0,24 |
| L10 | 23,84 | 2,40 | 9,53 | 11,58 | 0,33 |
| L20 | 28,09 | 2,08 | 17,52 | 8,08 | 0,43 |

**Kipp-Rechner (Modell mit Annahmen: Aufwand = Labels im Limit-Pricing + Labels im exakten Pricing + Kosten eines Master-LPs × Runden, jedes Label gleich teuer; Summen über die 30 Instanzen der Breite 100):**

| Limit | Kipp-Stelle bei gleich teuren Labels (Labels je Master-LP) | Aufwand gegen exakt bei 380 | Aufwand gegen exakt bei 20 000 |
|---|---|---|---|
| L5 | 16 300 | 0,49 | 1,04 |
| L10 | 22 000 | 0,56 | 0,99 |
| L20 | 40 500 | 0,64 | 0,93 |

## Ehrliche Grenzen

- **Das Limit ist ein Limit nach Kosten.** Die gelockerte Dominanz, wie sie in der Literatur steht, ist weder gebaut noch gemessen; die Zahlen gelten nur für dieses Limit.
- **Die Aussage „heuristisches Pricing ist schneller“ steht hier nicht.** Gemessen ist, dass bei 30 Kunden, Gedächtnis 8, Überdeckungs-Master, Breite 100 und diesem Python-Aufbau (Pricing 96,2 % der CPU-Zeit bei immer exaktem Pricing, ein Master-LP etwa 380 Labels) die CPU-Zeit mit Limit 0,36 / 0,39 / 0,46 der Zeit bei immer exaktem Pricing betrug; die Zeitreihe ist aus der Messdatei der
  früheren Messung, bei ausgelastetem Rechner und nicht mit dem Kern dieser Demo neu gemessen; eine Wiederholung bei ruhigem Rechner und mit anderen Master-Größen (mehr Kunden, Schnitte) steht aus. Bei Fensterbreite 150 ist die Zeit nicht gemessen.
- **Der Gewinn hängt am Verhältnis von Master-Zeit zu Pricing-Zeit.** Im Modell kippt er bei etwa 16 300 / 22 000 / 40 500 Labels je Master-LP; das ist eine Rechnung mit Annahmen (jedes Label gleich teuer, die Master-Kosten angenommen), keine Messung. Bei einem Master mit viel mehr Zeilen und Spalten oder mit Schnitten nicht gemessen.
- **Nicht jede Instanz profitiert:** Bei Breite 150 braucht Limit 20 in 1 von 16 Instanzen mehr Labels als exakt (1,02), und bei der Live-Instanz mit 8 Kunden und Limit 20 braucht das Limit mehr Labels als immer exakt (220 gegen 185), weil der exakte Abschlussaufruf dazukommt.
- Je Typ stehen 15 (Breite 100) bzw. 8 (Breite 150) Instanzen; das Verhältnis streut stark (bei Breite 100 und Limit 5 von 0,25 bis 0,91). Gemessen sind nur 30 Kunden, Gedächtnis 8 und metrische Kosten; 50 und 100 Kunden, Fensterbreite 40 in den festen Messreihen, andere Master, Branch-and-Price und Kombinationen mit anderen Sparmaßnahmen im Pricing sind nicht gemessen.
- Die Live-Rechnung der App hat ein Rechenbudget (Abbruch bei mehr als 600 000 erzeugten Labels über alle Runden oder mehr als 300 000 in einem Aufruf); darüber zeigt die App den Abbruch als Warnung. Die festen Messreihen und das Handbeispiel sind davon unberührt.
- Das Handbeispiel (6 Kunden) ist zum Nachrechnen gebaut; seine Zahlen (zum Beispiel 190 statt 280 Labels mit Limit 1) sind ein einzelnes Beispiel und kein Beleg für die Größenordnung in den Messreihen.
- Ursachen („weil …“) sind Deutungen, wo es dasteht; gemessen sind die Zählungen.
- Literatur (Prüfstand): Salani, Basso (arXiv 2306.08622) und Basso, Salani (arXiv 2605.03760): Literaturteile gelesen; sie nennen Heuristiken im Pricing mit gelockerten Dominanzregeln und Etikettenlimits je Knoten. Die dort zitierten Originalarbeiten wurden nicht gesehen und sind deshalb nicht aufgeführt. Keine Zahl daraus übernommen.

Annahmen, Grenzen und bekannte Probleme, wie sie auch in der App stehen (ein Test prüft, dass beide Fassungen gleich sind):

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

## Verifikation

- **Kern** (`tests/conftest.py`, `tests/test_algorithm.py`): je Einheit gegen Handrechnung am Handbeispiel: Dominanzregel (jede Bedingung einzeln, Toleranz), Limitregel (Gleichstände), Routenprüfer, Gedächtnis, die Zähler des ersten Preisproblems für alle vier Limits, die Verdrängung F14 durch F21 mit Begründung, die ganze Spaltenerzeugung mit der Handrechnung der Planung
  (exakt und Limit 1), Master mit Brüchen gegen das LP über alle 65 Routen, Dualpreise jeder Runde zulässig und optimal, Gleichstandsregel (andere Regel: 188 statt 238 Labels, gleiche Endschranke), Labelbudget, Worst-Case am Regler-Maximum.
- **Orakel** (`tests/test_oracle_heuristisches_pricing.py`, `tests/ref_labeling.py`): ein anders geschriebenes Label-Verfahren (Mengen und Listen statt Bitmasken) liefert dieselben Zähler, dieselben lebenden Labels und dieselben Routen an 30 kleinen Instanzen (7 Kunden, Gedächtnis 1, 3 und 7, Limit 1, 2, 3, 5 und ohne); die Aufzählung aller Routen durch Tiefensuche bestätigt die beste Route
  und die Reduzierten Kosten jeder gelieferten Route; die Spaltenerzeugung endet bei dem LP-Optimum über alle aufgezählten Routen (40 Rechnungen mit 6 Kunden). Beim Bau lief außerdem eine große Fassung außerhalb des Repos (Messung dieser README, nicht im Test): 300 Zufallsinstanzen mit 4 bis 9 Kunden, 4 500 Vergleiche des Label-Verfahrens und 800 Spaltenerzeugungen gegen das LP, 0 Abweichungen.
- **Eigenschaften** (`tests/test_eigenschaften_heuristisches_pricing.py`): ein sehr großes Limit ändert nichts; die Endschranke hängt nicht vom Limit ab und die letzte Runde ist immer ein exaktes Pricing ohne neue Spalte; Umnummerieren der Kunden; jede gelieferte Route ist zulässig mit korrekt nachgerechneten Kosten; das Limit kann den besten Weg einer Runde verfehlen, nie die Endschranke ändern; gleiche Zähler in einem zweiten Prozess mit anderem Hash-Zufall.
- **Randfälle** (`tests/test_edge_cases.py`): ein und zwei Kunden, Limit 1 und Limit über alles, keine Route mit negativen Kosten (eine Runde, ein exakter Aufruf), Gleichstand, Kapazität unter jeder Last, Ankunft genau zum Fensterende und zum Horizont, Gedächtnis 1, Labelbudget 0.
- **Messreihen** (`tests/test_bands.py`): Aufbau, Quelle je Lauf, Zählungen innerhalb jedes Laufs stimmig, gleiche Endschranke in 46 Instanzen, eine Stichprobe von 4 Instanzen (16 Läufe) mit dem Kern neu gerechnet, der Abgleich mit der früheren Messung festgehalten, die Zeitreihe als Messdatei der früheren Messung mit übereinstimmenden Zählungen.
- **Zahlen der README** (`tests/test_claims.py`): jede Tabelle der README entsteht zeichengleich aus den Daten; die Handbeispiel-Zahlen, Spannen, Runden, Zeitverhältnisse und Kipp-Stellen werden aus den Daten berechnet; Zeiten werden nie festgeschrieben, die Zeitzahlen stammen aus der Messdatei.
- **Verdikte** (`tests/test_verdicts.py`) und **je Schnellstart-Szenario die erwarteten Verdikt-Zeilen** (`tests/test_presets.py`, `tests/test_app.py`).
- **Oberfläche:** AppTest-Rauchtest (jeder Knopf, jeder Regler am Minimum und Maximum, jede Option, Eckfälle, Worst-Case am Regler-Maximum, Permalink mit ungültigen Werten), Layout (fester Kopf, Schnellstart in der Seitenleiste, Hervorhebung, Tabellen im Telefon-Fenster), Footer, Laufzeit-Importe.
- **Testzahl:** 160 Tests (`pytest --collect-only -q tests`).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: Kopf, Ergebnis, Kernfrage, fünf Experimente, Grenzen, Formeln, Fußzeile |
| `hpr_algorithm.py` | Kern: Label-Verfahren mit Etikettenlimit, Dominanzregel, Limitregel, Routenprüfer |
| `hpr_colgen.py` | Spaltenerzeugung (exakt oder Limit zuerst), Master mit HiGHS und mit Brüchen |
| `hpr_constants.py` | Regler-Grenzen, Rechenbudget, Farben, Schnellstart-Szenarien, gemeinsamer Text der Annahmen |
| `hpr_evaluation.py` | Handbeispiel-Auswertung, Live-Läufe, Kipp-Rechner, Auswertung der Messreihen, Zahlenformate, Verdikte (reine Funktionen) |
| `hpr_layout.py` | Fester Kopf (Stylesheet, breite Tabellen scrollen im Telefon-Fenster) |
| `hpr_presets.py` | Permalink (Begrenzen), Schnellstart in der Seitenleiste, aktives Szenario hervorgehoben, Zufalls-Seed-Knopf |
| `hpr_scenario.py` | Handbeispiel, Zufallsinstanzen im Solomon-Stil, Nachbarschaft des Gedächtnisses |
| `hpr_visualization.py` | Plotly-Abbildungen (Achsen gesperrt und fest) |
| `data/laeufe_v13.json`, `data/zeit_vormessung.json`, `data/vormessung_abgleich.json` | feste Messreihen (neu gerechnete Läufe mit Quelle je Lauf), Zeitreihe der früheren Messung (nicht neu gemessen), Ergebnis des Abgleichs mit den Rohausgaben der früheren Messung |
| `tools/baender_bauen.py` | rechnet die 184 Läufe mit dem Kern der Demo (`messen`) und baut `data/*.json` samt Abgleich (`bauen`) |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `tests/` | siehe Verifikation; `tests/ref_labeling.py` ist der unabhängige Rechenweg, `tests/readme_tables.py` erzeugt die Tabellen der README aus den Daten |

## Bewusst nicht umgesetzt

- **Die gelockerte Dominanz der Literatur** ist nicht gebaut und nicht gemessen; die Demo zeigt nur das Etikettenlimit nach Kosten.
- Keine Zeitmessung in der App über die Live-Wanduhr hinaus und keine neue Zeitmessung der Messreihen; die Zeitreihe ist die Messdatei der früheren Messung.
- Keine Instanzen mit mehr als 30 Kunden, keine Originalinstanzen, kein Gedächtnis über k = 8, kein anderer Master als die Überdeckung, kein Branch-and-Price, keine Kombination mit Eimern, Kantenstreichung oder beidseitigem Labeling.
- Kein PDF-Export.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Python 3.12 oder neuer (die CI läuft mit 3.12). Die in der Streamlit Cloud eingestellte Python-Version ist beim ersten Deploy einzutragen. <!-- lint-ok: dezimalpunkt -->

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, pandas, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html).
