# Fixture: C1 — Abhaengige Bug-Kette (Planungstiefe)

**Typ:** Multi-Step-Bugfix mit Reihenfolge-Zwang
**Schwierigkeit:** Mittel (3 kleine Fixes, aber nur sequenziell erreichbar)

## Zweck

Misst **Planungstiefe**, nicht Fix-Schwierigkeit. Die drei Bugs haengen voneinander ab:
Bug 2 wird erst sichtbar, wenn Bug 1 gefixt ist, Bug 3 erst nach Bug 2. Das Test-Script
bricht bei der **ersten** fehlschlagenden Stufe ab und zeigt nur diesen einen Fehler.

Damit trennt die Fixture zwei Verhaltensmuster:

- **Blindes Drauflos-Editieren:** Modell sieht `KeyError: 'limit'`, fixt, laeuft in den
  naechsten Fehler, fixt, laeuft in den naechsten — bei jedem Durchgang neuer Kontext,
  neue Datei, oft Rueckfall in Rewrites oder falsche Ursachen-Attribution ("die Daten
  sind kaputt" → `sample.json` editieren = Oracle-FAIL).
- **Planvolles Vorgehen:** Erst alle drei Module + `test_pipeline.py` lesen, die
  Datenfluss-Kette `config_loader → pipeline → report` verstehen, alle drei Defekte
  in einem Rutsch fixen, dann einmal verifizieren → linearer Durchlauf.

Der Datenvertrag steht komplett in `test_pipeline.py` (erwartete Werte, erwartetes
Report-Format). Ein Modell, das den Test liest, kann alle drei Bugs statisch finden —
genau das ist das gemessene Verhalten.

## Bug-Kette

| # | Datei | Defekt | Sichtbar ab | Fix |
|---|-------|--------|-------------|-----|
| 1 | `config_loader.py` | liest `source["limit"]`, der Key heisst `threshold` | sofort (`KeyError: 'limit'`) | 1 Zeile |
| 2 | `pipeline.py` | vergleicht das Reading-**Dict** mit dem Threshold statt `reading["value"]` | erst nach Fix 1 (`TypeError: '>=' not supported between 'dict' and 'int'`) | 1 Zeile |
| 3 | `report.py` | `enumerate(...)` ohne `start=1` → Rangliste beginnt bei 0 | erst nach Fix 2 (`report line is '0. 42', expected '1. 42'`) | 1 Zeile |

Keine `# BUG`-Marker, keine TODOs — die Defekte sind als realistische Fluechtigkeits-
fehler formuliert (umbenannter JSON-Key, geaendertes Datenformat, vergessener
`start`-Parameter).

## Dateien

```
input/config_loader.py    laedt sample.json → config-Dict           (Bug 1)
input/pipeline.py         filtert + aggregiert die Readings         (Bug 2)
input/report.py           formatiert den Report-Text                (Bug 3)
input/test_pipeline.py    End-to-End-Check, 3 Stufen, fail-fast     (read-only)
input/sample.json         8 Readings, threshold 20                  (read-only)
prompt.md                 Auftrag (englisch, Small-Diff-Regel)
oracle.sh                 deterministischer Check, kein LLM
```

**Layout-Hinweis:** Alle Input-Dateien liegen **flach** in `input/`, nicht in
`tests/` bzw. `data/`. Grund: `copy_fixture_to_job()` in
`lib/local-llm/benchmark/opencode/run_opencode_test.py` kopiert `input/` per
`shutil.copy2` Eintrag fuer Eintrag und wuerde an einem Unterordner mit
`IsADirectoryError` abbrechen. Alle bestehenden Fixtures sind ebenfalls flach.
Soll spaeter geschachtelt werden: `shutil.copy2` dort auf `shutil.copytree`
(bzw. Fallback pro Typ) umstellen — dann kann `input/` Unterordner enthalten.

Der Agent arbeitet in `work/` (Kopie von `input/`), `input/` bleibt als Referenz liegen.

## Oracle-Bedingungen (`oracle.sh`, Aufruf mit cwd = job_dir)

| # | Check | FAIL wenn |
|---|-------|-----------|
| 1 | alle 5 Dateien in `work/` vorhanden | eine geloescht/umbenannt |
| 2 | `test_pipeline.py` + `sample.json` md5-identisch zum Fixture-Stand | Test entschaerft oder Daten an den Code angepasst |
| 3 | `py_compile` auf den drei Modulen | Syntaxfehler |
| 4 | `cd work && python3 test_pipeline.py` → exit 0 | Kette nicht vollstaendig gefixt |

Jede Bedingung gibt eine eigene `PASS`/`FAIL`-Zeile aus, am Ende `ERGEBNIS: PASS|FAIL`.
Exit-Code 0 nur wenn alle vier Bedingungen halten. Bei FAIL wird der Test-Output
eingerueckt mitgeschrieben — daran ist ablesbar, **wie weit** die Kette kam
(`ok stage 1/3` … `FAILED at stage 2/3`), was als Teilfortschritts-Metrik taugt.

Die md5-Konstanten stehen oben in `oracle.sh`. Bei absichtlicher Aenderung der
Fixture-Dateien neu berechnen (`md5 -q input/test_pipeline.py input/sample.json`).

## Erwartete Differenzierung think vs. nothink

| Modus | erwartetes Muster |
|-------|-------------------|
| **think** | liest 3-5 Dateien bevor der erste Edit kommt, erkennt die Kette statisch, 3 kleine Edits, 1-2 Test-Laeufe, Oracle 4/4 |
| **nothink** | Edit direkt nach der ersten Fehlermeldung, pro Bug ein eigener Test-Lauf (≥3 Laeufe), deutlich mehr Steps; Risiko: Ursachen-Verwechslung (Fix in `sample.json` statt im Code) → Oracle-Check 2 FAIL |

Beobachtbare Metriken aus `run.jsonl` zusaetzlich zum Oracle:

- **Read-vor-Edit-Verhaeltnis:** Anzahl read-Tool-Calls vor dem ersten edit
- **Test-Laeufe:** Anzahl `python3 test_pipeline.py`-Bash-Calls (3+ = reaktiv, 1-2 = geplant)
- **Steps bis PASS** und Stop-Reason (`length` = Small-Diff-Regel ignoriert)
- **erreichte Stufe** bei FAIL (Teilfortschritt 1/3, 2/3)

## Reference solution (spoiler)

Drei Ein-Zeilen-Fixes, verifiziert (Oracle 4/4 PASS). Diese Fixes sind **nicht** im
`input/` enthalten:

```diff
--- config_loader.py
         "name": source["name"],
-        "threshold": source["limit"],
+        "threshold": source["threshold"],

--- pipeline.py
     threshold = config["threshold"]
-    return [reading for reading in config["readings"] if reading >= threshold]
+    return [reading["value"] for reading in config["readings"] if reading["value"] >= threshold]

--- report.py
-    for rank, value in enumerate(ranked[:TOP_N]):
+    for rank, value in enumerate(ranked[:TOP_N], start=1):
```

Erwarteter Endzustand:

```
ok   stage 1/3 (config)
ok   stage 2/3 (pipeline)
ok   stage 3/3 (report)
ALL 3 STAGES PASSED
```

Alternative gueltige Loesungen bestehen das Oracle ebenfalls (es prueft Verhalten,
nicht Fundstelle): Bug 2 laesst sich z.B. auch loesen, indem `select_readings` weiter
Dicts filtert und die Werte erst in `summarize` extrahiert — solange `summary["values"]`
die Zahlenliste `[25, 31, 42, 27, 35]` ergibt.

## Oracle-Grenzen

- Prueft **Verhalten**, nicht Fix-Ort oder Fix-Eleganz. Ein Modell, das alle drei
  Module umschreibt, besteht ebenfalls — die Small-Diff-Disziplin ist ueber
  `run.jsonl` (Output-Tokens, Stop-Reason) zu bewerten, nicht ueber das Oracle.
- Erkennt keine Hardcodes, die zufaellig zum Contract passen (z.B. `format_report`,
  das die erwarteten Zeilen konstant zurueckgibt). Solche Faelle sind im Diff sichtbar,
  aber nicht automatisch gefiltert.
- Prueft nicht, ob die Reihenfolge tatsaechlich erkannt wurde — die Reihenfolge-
  Erkennung ist an den Metriken oben abzulesen, nicht am Exit-Code.
