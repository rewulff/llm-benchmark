# v6-custom-constraint — Kombiniertes Constraint-Puzzle

## Zweck

Testet ob ein Modell eine neuartige Constraint-Kombination korrekt implementieren kann,
die nicht als Wikipedia-Klassiker existiert. Das Modell muss die Logik selbst ableiten —
drei simultane Constraints (exact-n, target-sum, max-gap) auf Kombinationen ueber einem
begrenzten Wertebereich.

## Erwartungs-Wert

`find_sequences(4, 30, 5)` muss `32` zurueckgeben.
Berechnet via Referenz-Implementation (`/tmp/ref-solve.py`): erschoepfende Enumeration
aller C(50, 4)-Kombinationen mit allen drei Filter-Kriterien.

Der Wert ist NICHT im Prompt enthalten — das Modell muss selbst zur richtigen Antwort rechnen.

## Erwarteter Modell-Prozess

1. Die drei Constraints verstehen:
   - Genau `n` verschiedene Elemente aus [1, 50]
   - Summe == `target_sum`
   - Max. Luecke zwischen aufeinanderfolgenden sortierten Werten <= `max_gap`
2. Eine korrekte Implementierung schreiben (z.B. via `itertools.combinations`
   oder rekursivem Backtracking)
3. Den `__main__`-Block mit `print(len(find_sequences(4, 30, 5)))` korrekt befuellen
4. Datei speichern und `DONE` antworten

## Reasoning-Anforderung

- Kein bekanntes Puzzle — keine gespeicherte Antwort abrufbar
- Modell muss alle drei Constraints gleichzeitig korrekt umsetzen
- `max_gap` ist der subtilste Constraint: prueft CONSECUTIVE-Paare in sortierten Listen,
  nicht alle Paare oder den Gesamtbereich

## Oracle-Logik

1. `work/solve.py` muss existieren
2. `find_sequences` muss definiert sein
3. `__main__`-Block muss vorhanden sein
4. Ausfuehren mit Timeout 15s
5. Letzte Stdout-Zeile muss exakt `32` sein

## Oracle-Grenzen

- Timeout 15s: brute-force O(C(50,4)) ist ~230.000 Kombinationen, laeuft in < 1s.
  Pathologisch langsame Implementierungen (z.B. Permutationen statt Kombinationen) koennen
  den Timeout triggern — das ist ein legitimes FAIL-Signal.
- Das Oracle prueft nur den Zahlenwert, nicht den Algorithmus. Eine Implementierung die
  zunaechst Permutationen generiert und dann dedupliziert gibt dennoch 32 zurueck → PASS.
- Falsche Constraints-Implementierung (z.B. max_gap prueft alle Paare statt nur consecutive)
  fuehrt zur falschen Zahl → FAIL.
