# King-Eval 2026-09-30 — lokaler Default-Coding-Agent vs. Sonnet/Opus

**Anlass:** Wechsel Max → Team Premium. Ziel ist ein lokaler Default-Coding-Agent, der
Sonnet-/Opus-Aufgaben übernehmen kann. Kandidaten kommen aus der laufenden Modell-Voreval.

**Hardware:** MacBook Pro M4 Pro, 48 GB · **Inferenz:** omlx 0.7.0rc1 (MLX)
**Agent-Harness lokal:** opencode (`lib/local-llm/benchmark/opencode/run_opencode_test.py`)
**Agent-Harness Cloud:** Claude-Code-CLI (`runners/run_cc_matrix.py`)
**Stand:** laufend — nothink-Durchgang unvollständig, ThinkingCap-Qwen3.8 noch im Download.

---

## 1. Methodik

10 agentische Fixtures mit mechanischem Oracle, identisch für alle Kandidaten:

| Fixture | Was sie misst |
|---|---|
| `a2-bugfix` | 3 offensichtliche Bugs fixen |
| `v6-quick-nqueens` | Algorithmus aus Spezifikation erzeugen |
| `v6-debug-unmarked` | Bug ohne Marker finden, nur über Log |
| `c1-dependent-pipeline` | verkettete Bugs — Planungstiefe |
| `v6-custom-constraint` | exakte Signatur + Randbedingungen einhalten |
| `v6-ambiguity-probe` | unterspezifizierte Aufgabe — Rückfrage vs. Raten |
| `v6-produktiv-fqdn-bug` | echter Bug aus `lib/forgejo-git/main.py` |
| `r1-offline-research` | Multi-Hop-Recherche mit Decoy-Dokumenten |
| `v6-architecture-choice` | Trade-off-Urteil unter harten Randbedingungen |
| `a5-long-edit` | 8 Bugs in ~495 Zeilen — Multi-Edit-Ausdauer |

**Statuskriterium:** ausschließlich der Oracle-Exit — genau wie der opencode-Runner
(`run_opencode_test.py:290-295`). Das Lint-Gate wird protokolliert, aber **nicht** gewertet:
mehrere Fixtures liefern ruff-Verstöße bereits im Input mit (`a5-long-edit` 7,
`v6-produktiv-fqdn-bug` 7, `c1-dependent-pipeline` 2, `v6-debug-unmarked` 1). Gewertet wird
nur das Delta („neue Verstöße gegenüber Fixture-Baseline", Spalte ⚠lint).

**Zusätzliche Auflösung:** Die Oracles sind all-or-nothing, drucken aber Sub-Check-Quoten.
Diese werden nachträglich geparst (`runners/subchecks.py`) und nach
`EVALUATION_CONTRACT_V2.md` bewertet (PASS ≥ 80 %, PARTIAL ≥ 50 %). Deshalb können
Oracle-FAIL und V2-PASS gleichzeitig auftreten — z. B. 6/7 = 86 %.

**Sampling identisch über think/nothink:** `max_tokens 16384`, `temperature 0.6`,
`top_p 0.95`, `top_k 20`, `repetition_penalty 1.0`. Nur `enable_thinking` unterscheidet sich.
Gesetzt über die omlx-Admin-API (Runtime-Store ist SSOT; Dateiedits an
`~/.omlx/model_settings.json` werden beim Shutdown überschrieben). Wirksamkeit des Toggles
wurde belegt: mit `enable_thinking: false` bleibt `reasoning_content` leer (2 Completion-Tokens
für „17*3"), nicht nur die Settings-Antwort geprüft.

---

## 2. Ergebnisse

| Fixture | Opus 5 | Sonnet 5 | Ornith-1.5 nothink | Ornith-1.5 think |
|---|---|---|---|---|
| `a2-bugfix` | PASS · 17s · 4st/3tc | PASS · 9s · 3st/2tc | PASS · 34s · 3st/2tc | PASS · 38s · 4st/3tc |
| `v6-quick-nqueens` | PASS · 10s | PASS · 9s | **FAIL** · 42s | PASS · 94s |
| `v6-debug-unmarked` | PASS · 10s | PASS · 7s | PASS · 86s | PASS · 49s |
| `c1-dependent-pipeline` | PASS 4/4 · 15s | PASS 4/4 · 13s | INVALID (507) | PASS 4/4 · 151s |
| `v6-custom-constraint` | PASS · 19s | PASS · 10s | INVALID (507) | PASS · 50s |
| `v6-ambiguity-probe` | PASS 1/1 · 29s | PASS 1/1 · 17s | offen | PASS 1/1 · 65s |
| `v6-produktiv-fqdn-bug` | **FAIL 6/7** · 72s ⚠lint | **FAIL 6/7** · 28s ⚠lint | offen | **PASS 7/7** · 146s ⚠lint |
| `r1-offline-research` | PASS 18/18 · 13s | PASS 18/18 · 9s | offen | **FAIL 14/18** · 181s |
| `v6-architecture-choice` | PASS 1/1 · 252s | PASS 1/1 · 62s | offen | PASS 1/1 · 215s |
| `a5-long-edit` | PASS · 29s · 13st/10tc | PASS · 20s · 13st/10tc | offen | PASS · 147s · 7st/13tc |

| Lauf | Oracle-PASS | V2-Verdict PASS | Gesamtzeit | Kosten (CLI-Angabe) |
|---|---|---|---|---|
| Opus 5 (cc-cli) | 9/10 | 10/10 | 7,8 min | 2,90 USD |
| Sonnet 5 (cc-cli) | 9/10 | 10/10 | 3,1 min | 1,08 USD |
| **Ornith-1.5 think** (lokal) | **9/10** | 9/10 | 18,9 min | **0** |
| Ornith-1.5 nothink (lokal) | 2/3 | 2/3 | 2,7 min | 0 · 2 Läufe ungültig |

---

## 3. Befunde

**1. Lokal ist auf 9 von 10 Aufgaben gleichwertig — der Preis ist Zeit, nicht Qualität.**
Ornith-1.5 think erreicht dieselbe Oracle-Quote wie Sonnet und Opus (9/10). Der Aufwand ist
Faktor 6 gegenüber Sonnet (18,9 vs. 3,1 min) und Faktor 2,4 gegenüber Opus.

**2. Bei der Aufgabe aus unserem Produktivcode liegt lokal vorn.**
`v6-produktiv-fqdn-bug`: Ornith 7/7, Sonnet und Opus je 6/7 — beide reißen denselben Check 4
(Token-Injection-Pattern im neuen URL-Format). Nach V2-Contract sind alle drei PASS (86 %),
aber die Aufgabe ist nur lokal vollständig gelöst worden.

**3. Thinking ist aufgabenabhängig, nicht global.** Zwei belegte Gegenrichtungen:
- `v6-quick-nqueens`: think PASS, **nothink FAIL** — der nothink-Solver liefert 0 statt 18
  Lösungen, also inhaltlich falsch, nicht bloß unsauber. Algorithmen brauchen die Denkphase.
- `r1-offline-research`: think **FAIL** (14/18). Alle vier gerissenen Checks betreffen Q3:
  Ornith antwortet „ACME Industries, agent version 2.6.0" statt Brightwave/Northwind, zitiert
  die falschen Logs — es läuft in die Decoy-Falle. Dieselbe Fixture hat qwen36 im Juli
  think-seitig gerissen und nothink bestanden (`results/agentic-matrix-2026-07-29`).
  Der nothink-Gegenbeleg für Ornith fehlt noch (507-Abbruch, s. Einschränkungen).

**4. Der Zeitvorteil der Cloud verschwindet bei Urteilsaufgaben.**
`v6-architecture-choice`: Opus 252 s (24.755 Output-Tokens, 0,85 USD), Ornith lokal 215 s.
Opus schreibt sich lange aus; lokal ist hier nicht langsamer.

**5. Kosten der Messlatte:** 10 Fixtures kosten laut CLI 1,08 USD (Sonnet) bzw. 2,90 USD
(Opus). Über das Abo ist das Kontingent, nicht Rechnung — aber es ist die Größenordnung,
die bei jeder abgegebenen Aufgabe gespart wird.

---

## 4. Einschränkungen (gegen Überinterpretation)

- **Zwei Harnesses.** Lokal läuft opencode, Cloud die Claude-Code-CLI. Tool-Sets und
  System-Prompts unterscheiden sich; ein Teil der Zeit- und Step-Unterschiede geht darauf
  zurück, nicht auf das Modell. Ein Anthropic-Key für opencode existiert nicht, OpenRouter
  hat 0,00 USD Guthaben — deshalb dieser Weg (Entscheid rwu).
- **Kandidat ist ein Dritt-Finetune.** Getestet wurde
  `junafinity/Ornith-1.5-35B-A3B-uncensored-MLX-MXFP4` (18 GB), nicht die offizielle
  `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit`. Aussagen über „Ornith 1.5" sind damit vorläufig.
- **Zwei nothink-Läufe ungültig.** `c1-dependent-pipeline` und `v6-custom-constraint` brachen
  mit `507: projected memory 45.63GB would exceed the memory ceiling 37.44GB` ab — paralleler
  22-GB-Download plus gepinntes `gemma-4-E2B` ließen keinen Modell-Reload zu. steps=0,
  tool_calls=0: kein Modellergebnis. Als INVALID markiert, Wiederholung offen.
- **Timings unter Last.** Alle lokalen Läufe liefen bei parallelem Modell-Download.
  Fremdanfragen an omlx (23 × `401 Invalid API key` von einem alten opencode-Prozess ohne
  gesetzten `OMLX_API_KEY`, sowie `507`-Ablehnungen) verbrauchten **keine** GPU-Zeit — sie
  werden vor der Generierung abgewiesen. Die Zeiten sind also nicht durch Parallel-Inferenz
  verfälscht.
- **Juli-Baseline deckt nur 4 der 10 Fixtures** (a2, a5, c1, r1); die sechs v6-Fixtures kamen
  später dazu.
- **Sub-Check-Auflösung ist uneinheitlich.** Vier Fixtures haben binäre Oracles ohne
  Sub-Check-Ausgabe; dort fehlt die Feinauflösung.

---

## 5. Offen

- [ ] nothink-Durchgang für die sieben fehlenden Fixtures (nach Download-Ende)
- [ ] ThinkingCap-Qwen3.8-27B (`airagrp/…-mlx-nvfp4`, 22,3 GB) — gleiche Matrix.
      Lizenz PolyForm Small Business: vor Kundeneinsatz zu klären.
- [ ] offizielle `ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit` als Quant-/Finetune-Vergleich
- [ ] `apiKey: {env:OMLX_API_KEY}` in `lib/local-llm/benchmark/opencode/opencode.json`
      nachtragen — fehlt, dadurch laufen Suite-Starts ohne gesetzte Env in stille 401er
- [ ] Sweep-Kandidat `Kwaipilot/KAT-Coder-V2.5-Dev` (Apache-2.0, SWE-bench Verified 69,4,
      Architektur identisch zu Ornith 1.5) — von rwu zunächst zurückgestellt

## 6. Reproduktion

```bash
# lokal (omlx), pro Modell ein Batch über alle Fixtures
set -a; . ~/.config/omlx/.env; set +a
python3 runners/run_king_matrix.py --model <omlx-id> --label <label>

# Cloud-Messlatte über die Claude-Code-CLI
python3 runners/run_cc_matrix.py --model sonnet --label cc-sonnet5

# Nachbereitung + Report
python3 runners/fix_status_and_lint_baseline.py   # Status oracle-only + Lint-Delta
python3 runners/subchecks.py                     # Sub-Check-Quoten, V2-Verdict
python3 runners/report.py                         # Matrix-Tabellen
```
