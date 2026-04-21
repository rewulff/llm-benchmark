# OpenCode Benchmark — Code-Home

OpenCode als echter Agent-Harness fuer lokale LLM-Benchmarks. Statt smolagents-minimal
(stateless Single-Turn) laeuft hier ein echter Multi-Turn-Agent-Loop mit File-Zugriff,
Bash und selbstaendiger Fehlerkorrektur.

## Architektur: Zwei-Ebenen-Workspace

```
lib/local-llm/benchmark/opencode/   <-- Code-Home (Git-tracked)
  opencode.json                      Provider-Konfig (lokal, ueberschreibt ~/.config/opencode/)
  run_opencode_test.py               Wrapper: Fixture→Job→OpenCode→Parse→Result
  parse_opencode_run.py              Parser fuer opencode run --format json (bestehend)
  servers/                           Server-Start/-Stop-Scripts
    start-qwen36.sh
    start-knecht.sh
    stop-all.sh
  agents/                            Agent-Profile (Permission-Sets)
    builder.md
    restricted.md
  fixtures/                          Benchmark-Fixtures (Aufgabe + Oracle)
    a2-bugfix/
      prompt.md
      input/calculator.py
      oracle.sh
      README.md
  providers/                         Provider-Beispiele (nicht geladen, nur Referenz)
    minimax.example.json
  PROMPT-PATTERNS.md                 Empirisch validierte Prompt-Bausteine (Small-Diff etc.)
  models/                            Ergebnis-Output pro Modell (Git-untracked empfohlen)
    <model_short>/results/
      YYYY-MM-DD-opencode-<fixture>.json

~/opencode-jobs/                     <-- Job-Scratch (ausserhalb Git, OpenCode arbeitet hier)
  YYYY-MM-DD-<slug>/
    input/    Kopien der Fixture-Input-Dateien (read-only Referenz)
    work/     OpenCode arbeitet hier (liest, schreibt, führt Bash aus)
    output/   run.jsonl + geparste Results
```

### Warum zwei Ebenen?

OpenCode schreibt aktiv in sein Arbeitsverzeichnis. Damit Benchmark-Fixtures unveraendert
bleiben und mehrere Laeufe nicht interferieren, arbeitet OpenCode in `~/opencode-jobs/`
ausserhalb des Repos. Code-Home bleibt sauber versioniert.

## Multi-Provider-Setup

| Provider-ID      | Port | Modell                                    | Alias                |
|------------------|------|-------------------------------------------|----------------------|
| `local-qwen36`   | 1235 | Qwen3.6-35B-A3B-UD-Q5_K_XL               | qwen3.6-35b-a3b      |
| `local-knecht`   | 1235 | qwen3-coder-30b-a3b-instruct-q4_k_m      | qwen3-coder-30b      |
| `minimax`        | —    | MiniMax M2.7 Cloud (kommentierter Platzhalter) | MiniMax-M2.7    |

### RAM-Constraint: Option A (sequenziell)

Qwen3.6-35B (UD-Q5_K_XL) benoetigt ~25 GB VRAM/RAM.
Knecht (Q4_K_M, 30B MoE) benoetigt ~20 GB VRAM/RAM.
Zusammen ~45+ GB — auf 48 GB Gesamtsystem nicht parallel realisierbar.

Daher: **Option A — sequenziell**. Immer nur ein Server aktiv.

### Modell-Switch-Prozedur

```bash
# Von Qwen3.6 zu Knecht wechseln:
./servers/stop-all.sh
./servers/start-knecht.sh     # wartet auf /health, bis zu 300s
opencode run --model local-knecht/qwen3-coder-30b ...
```

### MiniMax (kuenftig)

Wenn MiniMax Coding-Plan aktiv ist: Provider-Block aus `providers/minimax.example.json`
in `opencode.json` unter `provider` mergen und `MINIMAX_API_KEY` in der Shell setzen.
Details siehe `providers/minimax.example.json`.

## Nutzung

### Server starten

```bash
# Qwen3.6 starten (wartet bis /health READY)
./servers/start-qwen36.sh

# Knecht starten
./servers/start-knecht.sh

# Laufenden Server stoppen
./servers/stop-all.sh
```

Logs: `/tmp/llama-qwen36.log` bzw. `/tmp/llama-knecht.log`

### Smoke-Test / Benchmark-Run

```bash
# Fixture a2-bugfix mit Qwen3.6
python3 run_opencode_test.py \
    --model local-qwen36/qwen3.6-35b-a3b \
    --fixture a2-bugfix \
    --job-slug a2-qwen36-$(date +%s)

# Gleiche Fixture mit Knecht (Server vorher wechseln!)
./servers/stop-all.sh && ./servers/start-knecht.sh
python3 run_opencode_test.py \
    --model local-knecht/qwen3-coder-30b \
    --fixture a2-bugfix \
    --job-slug a2-knecht-$(date +%s)
```

Ergebnisse landen in:
`lib/local-llm/benchmark/opencode/models/<model_short>/results/YYYY-MM-DD-opencode-<fixture>.json`

### Eigenen Prompt uebergeben

```bash
python3 run_opencode_test.py \
    --model local-qwen36/qwen3.6-35b-a3b \
    --fixture a2-bugfix \
    --job-slug custom-$(date +%s) \
    --prompt-file /path/to/custom-prompt.md
```

## Fixtures

| Name           | Beschreibung                                    | Oracle                            |
|----------------|-------------------------------------------------|-----------------------------------|
| `a2-bugfix`    | 3 Bugs in Python-Calculator fixen               | Bash grep-Check (3 Bedingungen)   |
| `a5-long-edit` | 8 Bugs in ~495-Zeilen-Modul fixen (Multi-Edit)  | Bash grep-Check (8 Bedingungen)   |

## Scope

- **V5-Benchmark:** Knecht vs Qwen3.6 auf identischen Fixtures, fair vergleichbar
- **Kuenftig:** MiniMax M2.7 Cloud-Vergleich sobald Coding-Plan aktiv
- **Basis fuer:** Mini-Runner-v2 Phase 2 (autonome Nacht-Runs mit `restricted`-Agent)

## Setup

Die globale Config `~/.config/opencode/opencode.json` wird vom Wrapper NICHT mehr
benoetigt. Der Wrapper symlinkt die projekt-lokale `opencode.json` ins Job-Scratch-
Verzeichnis (`~/opencode-jobs/<slug>/opencode.json`), sodass OpenCode sie via
CWD-Parent-Hierarchie findet. Die projekt-lokale Config ist damit immer autoritativ.

## DEV-Hinweise

- Nie Secrets in opencode.json committen (kein API-Key, kein Token)
- Job-Scratch `~/opencode-jobs/` ist ausserhalb des Repos — kein .gitignore noetig
- `models/` in diesem Verzeichnis enthaelt nur JSON-Ergebnisse — committbar, aber
  bei haeufigen Laeufen empfiehlt sich ein `.gitignore` fuer `models/*/results/*.json`
- OpenCode-Config-Prioritaet: Projekt-lokale `opencode.json` > `~/.config/opencode/opencode.json`
- Bash-Syntax-Check der Scripts: `bash -n servers/start-qwen36.sh`
- Python-Syntax-Check: `python3 -m py_compile run_opencode_test.py`
