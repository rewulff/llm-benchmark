# Fixture: M1 — Gescripteter Multi-Turn-Brief (Nachfrage-Dimension)

**Typ:** Multi-Turn-Dialog mit Bedingungs-Verzweigung
**Schwierigkeit:** Einfach in der Sache, schwer im Verhalten
**Driver:** `../../run_multiturn_test.py` (NICHT `run_opencode_test.py`)

## Zweck

Misst die **Nachfrage-Dimension**: Erkennt ein Modell eine unterspezifizierte
Anforderung und stellt genau EINE Rueckfrage — oder raet es drauflos? Und wie
verhaelt es sich, wenn mitten im Task die Anforderung nachgeschoben wird?

Der Auftrag in Turn 1 ist absichtlich unvollstaendig: `--since`/`--until` sollen
"nach Datum filtern", aber weder Format noch Inklusivitaet der Grenzen sind
genannt. Wer raet, trifft den Randfall mit ~50% Wahrscheinlichkeit nicht — und
das Oracle prueft genau diesen Randfall.

## Dialog-Ablauf (`turns.json`)

| Turn | Inhalt | Verzweigung |
|------|--------|-------------|
| 1 | `turn-1.md` — mehrdeutiger Auftrag + Regel "bei Mehrdeutigkeit genau EINE Rueckfrage, dann Turn beenden" | — |
| 2 | Spezifikation nachreichen | `asked_clarifying=true` → `turn-2-answer.md` ("Good question…") · `false` → `turn-2-correction.md` ("You went ahead without asking…") |
| 3 | `turn-3.md` — Anforderungsaenderung: zusaetzlich `--skip-weekends`, minimaler Diff | — |

Beide Turn-2-Varianten enthalten **dieselbe** Spezifikation (ISO-8601
`YYYY-MM-DD`, beide Grenzen inklusiv). Der Unterschied liegt nur im Rahmen:
Antwort auf eine Frage vs. Korrektur einer Annahme. Damit ist der Endzustand
fuer beide Pfade erreichbar und das Oracle bleibt fair — die Rueckfrage selbst
ist eine eigene Metrik, kein Oracle-Kriterium.

### Heuristik `asked_clarifying`

Der Driver wertet Turn 1 aus:

```
asked_clarifying = ("?" in letzter Assistant-Message) UND (edit_tool_calls == 0)
```

`edit_tool_calls` zaehlt Tool-Calls aus `{edit, write, patch, multiedit}`.
Beide Bestandteile stehen einzeln im Result-JSON (`question_mark`,
`edit_tool_calls`), die Einstufung ist also ohne Neulauf nachpruefbar.

Bekannte Fehlklassifikationen:
- Rhetorische Frage im Abschlusstext ohne Edit → faelschlich `true`.
- Rueckfrage, die nach einem bereits erfolgten Edit gestellt wird → `false`
  (bewusst so: die Regel verlangt Fragen **vor** dem Coden).

## Dateien

```
input/logfilter.py          CLI-Tool, filtert nach Level (Ausgangszustand)
input/test_logfilter.py     Baseline-Suite, 4 Tests (read-only)
input/sample.log            15 Zeilen, 2026-06-01 bis 2026-06-14 (read-only)
turns.json                  Dialog-Definition
turn-1.md                   Turn 1 — mehrdeutiger Auftrag
turn-2-answer.md            Turn 2a — Antwort auf die Rueckfrage
turn-2-correction.md        Turn 2b — Korrektur, wenn nicht gefragt wurde
turn-3.md                   Turn 3 — Anforderungsaenderung
oracle.sh                   Endzustands-Checks
oracle_check.py             Feature-Verifikation, wird vom Oracle nach work/
                            kopiert und danach wieder entfernt — liegt bewusst
                            NICHT in input/, damit der Agent die Faelle nicht sieht
```

Die Testdaten sind kalendarisch abgestimmt: 2026-06-01 ist ein Montag,
06./07. und 13./14. Juni sind Wochenenden. `--skip-weekends` muss genau
4 der 15 Zeilen entfernen.

## Oracle-Bedingungen (`oracle.sh`, Aufruf mit cwd = job_dir)

| # | Check | Inhalt |
|---|-------|--------|
| 1 | Dateien + Kompilierbarkeit | `logfilter.py`, `test_logfilter.py`, `sample.log` vorhanden, `py_compile` sauber |
| 2 | Contract-Dateien unveraendert | md5 von `test_logfilter.py` und `sample.log` |
| 3 | Keine Regression | Baseline-Suite `test_logfilter.py` exit 0 |
| 4 | Features | `oracle_check.py`: 7 CLI-Faelle |

Die 7 Feature-Faelle: inklusiver Datumsbereich (`--since 2026-06-01 --until
2026-06-05` → 6 Zeilen), offener Anfang, offenes Ende, `--skip-weekends` allein
(11 Zeilen), Datumsbereich + Wochenende kombiniert, Level-Filter unveraendert,
Level + Wochenende kombiniert.

**Der Randfall ist der Kern:** eine exklusive `--until`-Interpretation faellt in
3 der 7 Faelle durch. Genau diesen Randfall klaert Turn 2 — entweder als Antwort
auf eine Rueckfrage oder als nachtraegliche Korrektur.

## Driver-Metriken (Result-JSON)

`run_multiturn_test.py` schreibt zusaetzlich zu den ueblichen Feldern:

```json
"multiturn": {
  "turns": 3,
  "asked_clarifying": true,
  "turn2_branch": "asked_clarifying=true",
  "steps_total": 14,
  "tool_calls_total": 9,
  "final_turn_diff": {"files_changed": 1, "lines_added": 6, "lines_removed": 2, "lines_touched": 8},
  "session_id": "ses_..."
}
```

Pro Turn zusaetzlich: `steps`, `tool_calls`, `tools_breakdown`, `edit_tool_calls`,
`stop_reason`, `duration_s`, `question_mark`, `final_text` (200 Zeichen), `diff`
und der Pfad zum Event-Stream.

**Rewrite-Detektor:** `turns[2].diff.lines_touched` — die Referenzloesung fuer
Turn 3 braucht rund 8 beruehrte Zeilen (Parameter, Filterbedingung, argparse-
Option, Aufruf). Deutlich dreistellige Werte bedeuten, dass die Datei trotz
"minimal diff, do not rewrite" neu geschrieben wurde.

## Nutzung

```bash
# Ablaufplan pruefen, ohne Server und ohne opencode
python3 ../../run_multiturn_test.py --fixture m1-multiturn-brief --dry-run

# Echter Lauf
python3 ../../run_multiturn_test.py \
    --model local-qwen36/qwen3.6-35b-a3b \
    --fixture m1-multiturn-brief \
    --job-slug m1-qwen36-$(date +%s)
```

Der Driver braucht eine `opencode.json`. Er sucht sie neben sich in
`harnesses/opencode/` und dann im Code-Home (`--code-home`, Standard
`~/Arbeitsverzeichnis/lib/local-llm/benchmark/opencode`). In diesem Repo liegt
nur `opencode.json.template` — also entweder eine `opencode.json` daneben legen
oder `--code-home` setzen.

## Reference solution (spoiler)

Verifiziert gegen das Oracle (4/4 Bedingungen, 7/7 Feature-Checks). Vier
Aenderungen an `logfilter.py`, insgesamt ~10 Zeilen:

```diff
+import datetime

-def filter_lines(lines, level=None):
+def filter_lines(lines, level=None, since=None, until=None, skip_weekends=False):
     ...
         if level is not None and entry["level"] != level:
             continue
+        if since is not None and entry["date"] < since:
+            continue
+        if until is not None and entry["date"] > until:
+            continue
+        if skip_weekends and datetime.date.fromisoformat(entry["date"]).weekday() >= 5:
+            continue

+    parser.add_argument("--since", default=None, help="earliest date, YYYY-MM-DD, inclusive")
+    parser.add_argument("--until", default=None, help="latest date, YYYY-MM-DD, inclusive")
+    parser.add_argument("--skip-weekends", action="store_true", help="drop Saturday and Sunday entries")
```

Der lexikographische Vergleich der ISO-Datumsstrings ist hier korrekt und
beidseitig inklusiv — `datetime`-Parsing der Grenzen ginge genauso.

## Erwartete Differenzierung

| Muster | Signatur im Result |
|--------|--------------------|
| fragt nach, implementiert dann sauber | `asked_clarifying: true`, Turn 1 ohne Edits, Oracle PASS |
| raet und trifft den Randfall | `asked_clarifying: false`, Oracle PASS, aber Turn-2-Branch `correction` |
| raet und trifft ihn nicht | `false` + Oracle-Check 4 FAIL, falls die Korrektur in Turn 2 nicht sauber umgesetzt wird |
| ignoriert "minimal diff" | grosses `final_turn_diff.lines_touched`, oft zusammen mit `stop_reason: length` |
| bricht die Baseline | Oracle-Check 3 FAIL (Regression) |
| editiert die Testdatei | Oracle-Check 2 FAIL |

## Oracle-Grenzen

- Prueft nur den **Endzustand nach Turn 3**. Ob die Loesung in Turn 1 oder erst
  nach der Korrektur entstanden ist, steht ausschliesslich in den Driver-Metriken.
- `oracle_check.py` fixiert die Flag-Namen (`--since`, `--until`,
  `--skip-weekends`) — die gibt der Auftrag woertlich vor. Ein Modell, das eigene
  Namen waehlt, faellt durch; das ist als Instruction-Following gewollt.
- Kein Schutz gegen Sonderfall-Hardcoding auf die Testdaten: eine Implementierung,
  die die erwarteten Zeilen fest verdrahtet, wuerde bestehen. Im Zweifel den Diff
  im Job-Scratch ansehen.
