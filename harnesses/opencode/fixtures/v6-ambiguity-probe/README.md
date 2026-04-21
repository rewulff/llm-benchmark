# v6-ambiguity-probe — Bewusst unklarer Optimierungs-Auftrag

## Zweck

Testet wie ein Modell mit einem absichtlich vagen Prompt umgeht. Der Auftrag "Optimize
slow.py" gibt keinerlei Anhaltspunkte:
- Welche Funktion soll optimiert werden?
- Was ist das Ziel (Laufzeit? Speicher? Lesbarkeit)?
- Wie viel Speedup wird erwartet?
- Darf der Algorithmus geaendert werden, oder nur Micro-Optimierungen?

Das Modell hat zwei valide Strategien:
- **(a) Nachfragen:** Klaerungsfragen stellen, bevor es losarbeitet
- **(b) Beste Interpretation:** Alle drei Funktionen optimieren und die Entscheidungen dokumentieren

Beide sind akzeptabel — der Stub-Oracle bewertet das (noch) nicht.

## Input: slow.py

Drei absichtlich langsame Funktionen, jede mit einem anderen Problem:

| Funktion | Komplexitaet | Optimierung |
|----------|-------------|-------------|
| `fibonacci(n)` | O(2^n) — naive Rekursion | Memoization oder iterativ → O(n) |
| `find_duplicates(items)` | O(n²) mit List-Lookup O(n) = O(n³) | Set-basiert → O(n) |
| `sort_and_rank(records)` | Bubble Sort O(n²) | `sorted()` / `list.sort()` → O(n log n) |

## Erwarteter Modell-Prozess (valide Pfade)

**Pfad A — Nachfragen:**
Modell fragt: "Welche Funktion? Welches Ziel? Constraints?" — valide Reaktion auf
Ambiguitaet, zeigt dass das Modell Anforderungen klaert statt blind loszulegen.

**Pfad B — Optimieren + Dokumentieren:**
Modell optimiert alle drei Funktionen und erklaert kurz die Entscheidungen.
Beispiel-Output in `slow.py` mit Kommentaren wie `# O(n) via memoization`.

**Pfad C — Partial:**
Modell optimiert nur die offensichtlichste Funktion (z.B. fibonacci via lru_cache).
Stub: PASS. Vollstaendiger Oracle: niedriger Score.

## Oracle-Status: STUB

Aktuell geprueft: Datei-Hash unterscheidet sich von Original.

## TODO — Vollausbau (Performance-Oracle)

- [ ] Benchmark-Skript schreiben: Zeitmessung fuer alle drei Funktionen (original vs. optimiert)
- [ ] Mindest-Speedup-Schwellen definieren:
  - fibonacci(35): original ~3s, optimiert < 0.001s (Faktor > 1000x)
  - find_duplicates mit 10000 Elementen: original ~10s, optimiert < 0.1s
  - sort_and_rank mit 5000 Records: original ~2s, optimiert < 0.05s
- [ ] Oracle prueft ob JEDE der drei Funktionen den Speedup-Threshold erreicht
- [ ] Partial-Credit: 1/3, 2/3, 3/3 Funktionen optimiert → Score
- [ ] Bonus: Prueft ob Korrektheit erhalten bleibt (gleicher Output wie Original)
- [ ] Ambiguitaets-Probe-Anteil: Wenn Modell eine `questions.md` oder `CLARIFY.md` ablegt,
  soll Oracle das als "Pfad A" erkennen und separat bewerten

## Oracle-Grenzen (Stub)

- Eine triviale Aenderung (Kommentar hinzufuegen, Leerzeile) gilt als PASS — das ist falsch.
- Im Vollausbau muss Laufzeit tatsaechlich gemessen werden.
- Der Ambiguitaets-Aspekt (nachfragen vs. assumieren) wird im Stub gar nicht bewertet.
