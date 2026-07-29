# Fixture: R1 — Offline-Recherche mit Decoy-Fallen

**Typ:** Multi-Hop-Recherche ueber einen Dokumentensatz
**Schwierigkeit:** Mittel-schwer (kein Code, aber 13 Dokumente mit Widersprüchen)

## Zweck

Misst die **Recherche-Dimension**: Kann ein Modell Fakten aus mehreren Dokumenten
kombinieren, Datierungen auswerten und veraltete Aussagen als solche erkennen?
Vollstaendig offline und deterministisch — kein Netz, kein Code-Lauf, kein
LLM-Judge im Oracle.

Die vier Fragen sind so gebaut, dass **keine** von ihnen aus einem einzelnen
Dokument beantwortbar ist. Gleichzeitig liegen zwei plausible, aber falsche
Faehrten aus, die genau dann uebernommen werden, wenn nur nach Stichworten
gesucht statt datiert gelesen wird.

## Szenario

Fiktiver "Kestrel Sync Agent", Releases 2.1 bis 2.6. Der Scheduler-Rewrite in
**2.4.0** bricht Uploads einzelner Dateien ueber ~5 GB (`E_CHUNK_TIMEOUT`,
Ticket KES-914). Drei Kunden-Logs zeigen drei Zustaende: betroffen (Northwind,
2.5.1), durch Workaround geschuetzt (ACME, 2.6.0 mit `chunk_strategy=fixed`),
zu alt zum Betroffensein (Brightwave, 2.3.2).

## Die vier Fragen und ihre Hop-Ketten

| Frage | Antwort | benoetigte Dokumente |
|-------|---------|----------------------|
| Q1 Welches Release fuehrte den Defekt ein? | **2.4.0** | Log Northwind (Fehlercode) → `known-issues.md` (Code ↔ "scheduler rewrite", nennt bewusst KEINE Version) → `CHANGELOG.md` (Rewrite = 2.4.0) |
| Q2 Workaround (Key + Wert)? | **`upload.chunk_strategy` = `fixed`** | `known-issues.md` (nennt den Key, aber nicht den Wert) → `config-reference-2.6.md` (Wert `fixed` = Pre-2.4-Verhalten) |
| Q3 Wer kann nicht betroffen sein? | **Brightwave Media, 2.3.2** | Q1-Ergebnis (2.4 als Schwelle) → `log-brightwave-*` (Version) |
| Q4 Ist es gefixt? | **nein — 2.7.0, KES-914** | `known-issues.md` (Status open, Ticket) → `meeting-notes-2026-06-16.md` (Ziel-Release 2.7.0, kein Backport) |

Jede Kette hat mindestens zwei Glieder, Q1 sogar drei. `known-issues.md` verweist
bewusst nur auf "the release that shipped that rewrite" statt auf eine Nummer.

## Die Decoys

| Dokument | Datum | falsche Faehrte | warum verlockend |
|----------|-------|------------------|------------------|
| `wiki-tuning-guide-2026-01.md` | 2026-01-20, gilt fuer 2.3, Owner vakant | "Large-file uploads sind seit **2.3.0** langsamer (BLAKE3)" + "`retry.max_attempts` default ist 3" | beantwortet Q1 scheinbar direkt, mit technisch klingender Begruendung |
| `support-playbook-2025-11.md` | 2025-11-24, gilt fuer 2.2 | "`upload.chunk_size_mb` auf **64** erhoehen loest fast alle Stalled-Chunk-Faelle" | beantwortet Q2 scheinbar direkt, als Schritt-fuer-Schritt-Anleitung |

Beide sind zeitlich konsistent — sie waren zu ihrem Zeitpunkt richtig. Entwertet
werden sie nur ueber Datum/Version-Vergleich, ueber `config-reference-2.6.md`
(`chunk_size_mb` ist seit 2.4 wirkungslos) und ueber die Juni-Meeting-Notes
("Do not tell customers to raise chunk sizes"). Zusaetzlich enthaelt
`meeting-notes-2026-04-08.md` eine explizit als unbestaetigt markierte
Hypothese, die in dieselbe 2.3-Richtung zeigt.

Weiteres Rauschen ohne eigene Frage: der Retry-Default (3 in 2.2, 5 ab 2.5) und
das geschlossene Ticket KES-877 als Fehlgriff-Kandidat fuer Q4.

## Dateien

```
input/README-project.md              Uebersicht: wer hat was wann geschrieben
input/CHANGELOG.md                   Releases 2.1 - 2.6 (2.4 = Scheduler-Rewrite)
input/known-issues.md                KES-914 offen, KES-877 geschlossen
input/config-reference-2.2.md        alte Fassung (chunk_size_mb als Hebel)
input/config-reference-2.6.md        neue Fassung (chunk_strategy, deprecations)
input/FAQ.md                         u.a. Fehlercodes + "neuere Referenz gewinnt"
input/meeting-notes-2026-06-16.md    Incident-Review (2.7.0, kein Backport)
input/meeting-notes-2026-04-08.md    aeltere Sprint-Notes (unbestaetigte 2.3-These)
input/support-playbook-2025-11.md    DECOY 1
input/wiki-tuning-guide-2026-01.md   DECOY 2
input/log-northwind-2026-06-14.txt   betroffen, 2.5.1, E_CHUNK_TIMEOUT
input/log-acme-2026-06-11.txt        Workaround aktiv, 2.6.0
input/log-brightwave-2026-06-09.txt  zu alt, 2.3.2
prompt.md                            4 Fragen + striktes answers.md-Format
oracle.sh                            grep-basiert, 3 Check-Gruppen
```

**Layout-Hinweis:** Die Dokumente liegen **flach** in `input/`, nicht in
`input/docs/`. Grund: `copy_fixture_to_job()` in
`lib/local-llm/benchmark/opencode/run_opencode_test.py` kopiert `input/` per
`shutil.copy2` Eintrag fuer Eintrag und bricht an einem Unterordner mit
`IsADirectoryError` ab. Gleiche Einschraenkung wie bei `c1-dependent-pipeline`.

## Antwortformat

Der Prompt schreibt pro Frage einen Block vor — das Oracle liest genau diese
zwei Zeilen, alles andere im Block ist Freitext und wird ignoriert:

```markdown
## Q1
Answer: <eine einzige Zeile, keine Alternativen>
Sources: <Dateinamen, die die Antwort stuetzen>
```

## Oracle-Bedingungen (`oracle.sh`, Aufruf mit cwd = job_dir)

| Gruppe | Checks | Inhalt |
|--------|--------|--------|
| pre | 2 | `work/answers.md` existiert; Dokumentensammlung md5-unveraendert |
| **A Kernfakten** | 7 | Q1 `2.4` · Q2 `chunk_strategy` + `fixed` · Q3 `Brightwave` + `2.3.2` · Q4 `2.7` + `KES-914` |
| **B Zitate** | 4 | Q1 → `CHANGELOG` · Q2 → `config-reference-2.6` · Q3 → `log-brightwave` · Q4 → `meeting-notes-2026-06-16` |
| **C Decoy-Negativ** | 5 | Q1 ohne `2.3` · Q2 ohne `chunk_size_mb`+`64` · Q3 ohne `Northwind`/`ACME` · Q4 ohne `KES-877` · keine Sources-Zeile nennt ein Decoy-Dokument |

PASS nur wenn alle 18 Checks halten. Positiv- und Negativchecks laufen ueber die
`Answer:`-Zeile, Zitat-Checks ueber die `Sources:`-Zeile — dadurch bleibt eine
Erlaeuterung im Fliesstext ("nicht 2.3, wie das Wiki behauptet") folgenlos.

## Reference solution (spoiler)

Verifiziert gegen das Oracle (18/18 PASS). Diese Datei liegt **nicht** im Fixture:

```markdown
## Q1
Answer: Release 2.4.0 introduced the defect, the release that shipped the multipart upload scheduler rewrite.
Sources: log-northwind-2026-06-14.txt, known-issues.md, CHANGELOG.md

## Q2
Answer: Set upload.chunk_strategy to the legacy value fixed and restart the agent.
Sources: known-issues.md, config-reference-2.6.md

## Q3
Answer: Brightwave Media, running agent version 2.3.2, which predates the scheduler rewrite.
Sources: log-brightwave-2026-06-09.txt, CHANGELOG.md, known-issues.md

## Q4
Answer: Not fixed yet — the permanent fix is targeted for 2.7.0 and is tracked as KES-914.
Sources: meeting-notes-2026-06-16.md, known-issues.md
```

## Erwartete Differenzierung

| Muster | erwartetes Ergebnis |
|--------|---------------------|
| liest breit (10+ Dokumente), vergleicht Daten | A+B+C PASS |
| greppt nach Stichworten ("large upload", "chunk") | faellt auf Playbook/Wiki herein → C1/C2 FAIL |
| liest nur die neuesten Dokumente | Q1 unbeantwortbar (Version nur im CHANGELOG) → A1 FAIL |
| antwortet ohne Quellen oder mit pauschalen Quellenlisten | B-Gruppe FAIL, C5 wenn Decoys pauschal mitzitiert werden |

Ergaenzende Metriken aus `run.jsonl`: Anzahl gelesener Dateien (read-Tool-Calls),
Verhaeltnis gelesene zu zitierten Dokumenten, Steps bis `answers.md` geschrieben ist.

## Oracle-Grenzen

- Prueft Stichworte, nicht Semantik: eine Antwort, die die richtigen Tokens in
  falschem Sinnzusammenhang nennt ("2.4 ist nicht betroffen"), wuerde bestehen.
  Bei Grenzfaellen die `answers.md` im Job-Scratch mitlesen.
- `C1` verbietet `2.3` in der Q1-Antwortzeile. Eine korrekte Antwort, die die
  falsche Faehrte in derselben Zeile widerlegt, faellt dadurch durch — der Prompt
  fordert deshalb explizit eine Antwortzeile ohne Alternativen.
- Formatabweichungen (fehlendes `Answer:`/`Sources:`-Praefix) zaehlen als FAIL.
  Das ist beabsichtigt: Instruction-Following ist Teil der Messung.
