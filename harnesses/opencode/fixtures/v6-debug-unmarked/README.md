# v6-debug-unmarked — Off-by-one Bug ohne Marker

## Zweck

Testet ob ein Modell einen subtilen Bug **ohne explizite Hinweise im Code** finden kann.
Der Bug steckt in `get_top_n()` in `server.py`: `sorted_items[:n-1]` liefert stets `n-1`
statt `n` Elemente. Es gibt keinerlei `# BUG`-Kommentar, kein TODO, keinen auffaelligen
Variablennamen — nur die Log-Ausgabe und die User-Meldung.

## Erwarteter Modell-Prozess

1. `test_run.log` lesen und die Diskrepanz identifizieren:
   `Calling get_top_n(items, 10)` → `Returned 9 items` (erwartet: 10)
2. In `server.py` nach einer Funktion suchen, die die Anzahl der zurueckgegebenen
   Elemente bestimmt — `get_top_n` ist der einzige Kandidat.
3. Den Off-by-one erkennen: `sorted_items[:n-1]` ist der Bug.
4. Fix anwenden: `sorted_items[:n]`.
5. Datei speichern und mit `DONE` antworten.

## Reasoning-Anforderung

Kein Pattern-Matching genuegt. Das Modell muss:
- Log-Output interpretieren (Quantitaets-Diskrepanz)
- Ursache-Wirkung vom Log auf den Code zurueckverfolgen
- Einen Off-by-one in einem unkommentierten Slicing-Ausdruck erkennen

## Oracle-Logik

1. `work/server.py` muss existieren.
2. Der Bug-Ausdruck `sorted_items[:n-1]` darf nicht mehr vorhanden sein.
3. Der Fix-Ausdruck `sorted_items[:n]` muss vorhanden sein —
   oder `get_top_n` wurde vollstaendig neu geschrieben (ohne den alten Bug).

## Oracle-Grenzen

- Ein Modell das die Datei unveraendert zurueckgibt + `DONE` antwortet: FAIL (Bug noch da).
- Ein Modell das `n-1` durch `max(0, n-1)` ersetzt: FAIL (Bug semantisch unveraendert).
- Ein Modell das `get_top_n` durch eine korrekte Alternative ersetzt (z.B. `heapq.nlargest`):
  PASS — der dritte Check akzeptiert das.
- Das Oracle prueft nicht ob das restliche Pipeline-Verhalten korrekt ist (nur der Bug-Fix).
- Keine Laufzeit-Verifikation: Die Funktion wird nicht ausgefuehrt, nur der Quelltext geprueft.
