# Fixture: A2 — 3 Bugs in Python-Calculator

**Typ:** Bugfix  
**Schwierigkeit:** Einfach (Lesen + gezieltes Schreiben)

## Aufgabe

Der Agent liest `calculator.py` und fixt drei absichtliche Bugs:

1. `multiply()` addiert statt zu multiplizieren (`a + b` statt `a * b`)
2. `divide()` hat keine Zero-Division-Absicherung
3. `average()` fehlt das `return`-Statement (Ergebnis wird berechnet aber nicht zurueckgegeben)

## Erwartetes Verhalten

- Agent liest die Datei (mind. 1 read-Tool-Call)
- Agent schreibt die korrigierte Datei zurueck (mind. 1 write/edit-Tool-Call)
- Agent antwortet final mit `DONE`

## Oracle-Checks (oracle.sh)

| Check | Grep-Pattern | Bedeutung |
|-------|-------------|-----------|
| 1 | `a \* b` oder `a*b` | multiply gefixt |
| 2 | `ZeroDivisionError\|ValueError\|raise\|if b == 0` | zero-check vorhanden |
| 3 | `return sum(` oder `return total` | return-Statement vorhanden |

## Dateien

- `input/calculator.py` — Ausgangsdatei mit 3 Bugs (wird nach work/ kopiert)
- `prompt.md` — Aufgabenbeschreibung fuer den Agenten
- `oracle.sh` — Automatischer Pruefskript (exit 0 = PASS)
