# King-Eval 2026-09-30/10-01 — lokaler Default-Coding-Agent ("neuer Knecht")

> **Nachtrag 01.10.2026 — alle Zahlen in diesem Report sind auf omlx 0.7.0rc1 gemessen.**
> Die Nachmessung auf 0.7.0 mit dem omlx-eigenen Quantformat oQ4e liegt unter
> `results/omlx-070-throughput/REPORT.md`. Kurz: Ornith 46,9 -> **78,9 tok/s**,
> ThinkingCap 15,3 -> **22,6 tok/s**. Die Durchsatzzahlen hier sind damit ueberholt;
> die Qualitaetsaussagen (Fixtures) stehen weiter, weil sie auf oQ4e noch nicht
> nachgefahren sind.

**Anlass:** Wechsel Max → Team Premium. Ziel ist ein lokales Modell, das Sonnet-/Opus-
Coding-Aufgaben übernimmt, damit Abo-Kontingent für die Arbeit bleibt, die es wirklich braucht.

**Hardware:** MacBook Pro M4 Pro, 48 GB (~273 GB/s) · **Inferenz:** omlx 0.7.0rc1 (MLX)
**Harness lokal:** opencode · **Harness Cloud:** Claude-Code-CLI
**Läufe:** 16 Matrizen à 10 Fixtures, ~160 Einzelläufe, 30.09. 19:20 – 01.10. 09:28

---

## 1. Ergebnis

**Knecht: `ornith-ai/Ornith-1.5-35B-A3B-MLX-6bit`, nothink, TurboQuant-KV 4-bit, ctx 262144.**

| Lauf | PASS | Zeit | Kosten | gescheitert an |
|---|---|---|---|---|
| **Ornith 6-bit nothink (temp 0)** | **10/10** | **7,6 min** | 0 | — |
| **Ornith 6-bit nothink (temp 0.6)** | **10/10** | 8,1 min | 0 | — |
| **Ornith 6-bit + TQ-KV 4-bit** | **10/10** | 8,6 min | 0 | — |
| ThinkingCap-Qwen3.8 ohne MTP | 10/10 | 74,2 min | 0 | — |
| Sonnet 5 (Cloud) | 9/10 | 3,1 min | 1,08 $ | v6-produktiv-fqdn-bug |
| Opus 5 (Cloud) | 9/10 | 7,8 min | 2,90 $ | v6-produktiv-fqdn-bug |
| Ornith 6-bit nothink (temp 0, Lauf 2) | 9/10 | 7,8 min | 0 | r1-offline-research |
| JetBrains-Blend + MTP-Drafter | 9/10 | 41,5 min | 0 | a5-long-edit |
| ThinkingCap MTP + Budget 2048 | 9/10 | 50,3 min | 0 | a5-long-edit |
| ThinkingCap MTP + effort low | 9/10 | 51,6 min | 0 | a5-long-edit |
| ThinkingCap MTP d3 (medium) | 9/10 | 64,5 min | 0 | a5-long-edit |
| JetBrains-Blend ohne Drafter | 9/10 | 65,5 min | 0 | a5-long-edit |
| Ornith 4-bit nothink | 8/10 | 5,2 min | 0 | a5, v6-custom-constraint |
| Ornith uncensored MXFP4 nothink | 8/10 | 8,6 min | 0 | r1, v6-quick-nqueens |
| Ornith 6-bit + TQ-KV **3-bit** | **5/10** | 10,6 min | 0 | r1, a5, nqueens, custom-constraint, architecture |

Über vier Läufe löst Ornith-6-bit **39 von 40 Fixtures**. Es schlägt beide Cloud-Modelle in der
Trefferquote und liegt zeitlich auf Opus-Niveau — bei null Grenzkosten.

---

## 2. Die fünf Befunde, die zählen

### 2.1 Der uncensored-Finetune war das Problem, nicht Ornith

Die junafinity-MXFP4-Fassung scheiterte dreimal an `r1-offline-research` (14/18, 14/18, 11/18),
immer mit identischem Fehlerbild: nennt „ACME Industries" statt Brightwave, zitiert die falschen
Logs. Die **offiziellen** Fassungen lösen dieselbe Fixture mit 18/18 — in 4-bit, in 6-bit und
bei Temperatur 0. Abliteration/Uncensoring beschädigt die Fähigkeit, in einem Dokumentenhaufen
die richtige Entität zu greifen.

**Einschränkung:** Auch die offizielle Fassung traf den Fehler in 1 von 5 Läufen. Die
Anfälligkeit steckt im Modell, der Finetune verschlimmert sie massiv.

### 2.2 MoE schlägt dense um Faktor 3,5–4 — unabhängig von allen Beschleunigern

omlx-Telemetrie über alle Läufe (Output tok/s):

| Modell | tok/s | Typ |
|---|---|---|
| Ornith-1.5 6-bit | **46,9** | MoE, 3B aktiv |
| ThinkingCap-Qwen3.8 nvfp4 | 13,5 | dense 27B |
| JetBrains-Blend 4-bit | 11,5 | dense 27B |

Ein dense-Modell liest pro Token alle Gewichte; bei 15–23 GB und 273 GB/s Bandbreite sind
10–15 tok/s die physikalische Decke. Der MoE liest nur die aktiven Experten. Keine
Spekulationstechnik schließt diese Lücke.

### 2.3 TurboQuant-KV: 4-bit gratis, 3-bit zerstörerisch

| | PASS | Zeit |
|---|---|---|
| ohne TurboQuant | 10/10 | 7,6 min |
| **TQ 4-bit** | **10/10** | 8,6 min |
| TQ 3-bit | **5/10** | 10,6 min |

3-bit verliert die Hälfte der Fixtures — und zwar die anspruchsvollen (`r1`, `a5`,
`architecture-choice`, `nqueens`, `custom-constraint`) — und ist dabei *langsamer*.
4-bit kostet 13 % Zeit und keine einzige Aufgabe.

**KV-Bedarf (empirisch bestätigt):** omlx meldet
`TurboQuant: converted 9/40 cache layers` — nur 10 der 40 Layer haben volle Attention
(2 KV-Heads, head_dim 256), der Rest ist linear attention mit konstantem Speicher.
Das ergibt ~20 KB/Token, also 1,3 GB bei 64k und 5,2 GB bei vollen 262k.

### 2.4 Lokal löst Aufgaben, an denen die Cloud scheitert

`v6-produktiv-fqdn-bug` (echter Bug aus `lib/forgejo-git/main.py`): **Sonnet und Opus
scheitern beide** am selben Sub-Check (Token-Injection-Pattern, je 6/7). **Alle** lokalen
Fassungen lösen ihn mit 7/7 — die uncensored, beide offiziellen, ThinkingCap und JetBrains.

Umgekehrt trennt `a5-long-edit` (8 Bugs in 495 Zeilen) die Architekturen: beide dense-27B
scheitern in **allen** Varianten, Ornith als MoE löst sie.

### 2.5 Denkaufwand ist bei ThinkingCap weitgehend Verschwendung

| Variante | PASS | Zeit |
|---|---|---|
| medium | 9/10 | 64,5 min |
| effort low | 9/10 | 51,6 min |
| Budget 2048 Token (hart) | 9/10 | 50,3 min |

Beide Bremsen sparen 20–40 % ohne Qualitätsverlust. Der harte Deckel wirkt vor allem auf
Ausreißer (`fqdn` 1158 → 701 s), die Prompt-Bremse gleichmäßiger. Die alte Notiz
„thinkingcap über-reasont irreparabel" gilt mit Budget nicht mehr.

Bei Ornith ist der Toggle binär (`enable_thinking`, keine Stufen) — und nothink ist dort
ohnehin schneller **und** gleich gut.

---

## 3. Was von den „experimentellen Features" übrig bleibt

| Technik | Ergebnis | Grund |
|---|---|---|
| **Lightning MTP** (ThinkingCap, nativer Head) | **1,2–1,66×**, Acceptance 94,9 % | wirkt, nur dense |
| **Externer MTP-Drafter** (JetBrains) | **1,58×**, Acceptance 58–62 % | wirkt, Paar offiziell geliefert |
| **TurboQuant-KV 4-bit** | Speicher −75 %, Qualität unverändert | wirkt |
| SpecPrefill | greift **nie** | Prefix-Cache fängt die Prompts ab |
| ANE / INT8 Prefill | stiller No-op | keine native Extension in der brew-Installation |
| DFlash | nicht anwendbar | kein Speculator-Checkpoint für unsere Geometrien |
| MTP bei MoE | strukturell tot | Experten-Reads im Verify |

**MTP-Sweetspot:** `mtp_fixed_depth: 3` (15,3 tok/s; d2 14,8 · d4 14,3 · d6 12,1 · adaptive 15,0).
Details in `MTP-SWEEP-thinkingcap-qwen38.md`.

**Acceptance sagt wenig:** JetBrains' Drafter bringt mit 58–62 % mehr (1,58×) als
ThinkingCaps nativer Head mit 94,9 % (1,2–1,66×). Entscheidend ist, wie viele Token pro
Verify-Zyklus durchkommen.

---

## 4. Empfohlene Konfiguration

```
Modell : ornith-ai--Ornith-1.5-35B-A3B-MLX-6bit      (27,55 GB)
enable_thinking      : false
turboquant_kv_enabled: true      turboquant_kv_bits: 4.0
max_context_window   : 262144    max_tokens: 16384
temperature 0.6 · top_p 0.95 · top_k 20 · repetition_penalty 1.0
specprefill_enabled  : false     mtp_enabled: false
```
Verifiziert: lädt mit 262144 Kontext in 13,8 s, kein Guard-Fehler.
Speicher mit TTS-Modell (1,79 GB) daneben: ~30,7 GB + Prefill — unter dem Ceiling von 38,33 GB.

**Zweitmodell für dense-Aufgaben:** `JetBrains/Qwen3.8-3.6-27B-blend-MLX-4bit` mit externem
MTP-Drafter (`vlm_mtp_enabled` + `vlm_mtp_draft_model`). 41,5 min, Apache-2.0, 15 GB —
löst ThinkingCap ab (50–74 min, PolyForm Small Business).

---

## 5. Grenzen des Knechts (Gate-Pflicht)

**Geeignet** (mechanischer Prüfstein vorhanden): Bugfix über mehrere Dateien, Refactor mit
Tests, Testgerüste, Code nach exakter Spezifikation, Formatierung, Commit-Messages.
Belegt: `c1-dependent-pipeline` (4 Dateien, verkettete Bugs) und `a5-long-edit` (8 Bugs,
495 Zeilen) werden zuverlässig gelöst — die alte trainee-Grenze „nicht für Multi-File" ist
damit überholt.

**Nicht geeignet:** Recherche mit widersprüchlichen Quellen (`r1` fiel in 1 von 5 Läufen,
bei der uncensored-Fassung in 3 von 3) und Aufgaben mit reinem Ermessensspielraum.
Faustregel: **Wo kein Test, Linter oder Oracle „richtig/falsch" sagen kann, darf der trainee
nicht entscheiden.**

---

## 6. Methodische Einschränkungen

- **Streuung ±1–2 Fixtures** bei `temperature 0.6` (zwei identische nothink-Läufe: 8/10 und
  7/10, gegenläufig bei `nqueens` und `custom-constraint`). Ein-Test-Unterschiede sind kein Befund.
- **Temperatur 0 macht den Agent-Loop nicht deterministisch** — zwei Läufe ergaben 10/10 und
  9/10, und die Step-Zahlen wichen ab (MLX-Reduktionen sind nicht bitgleich).
- **Prefix-Cache verfälscht Zeitvergleiche** zwischen Läufen (bis 3×: 86 s → 29 s bei
  identischen Settings). Seit 30.09. leert der Runner Hot- und SSD-Cache vor jedem Batch;
  Läufe davor sind zeitlich nur intern vergleichbar.
- **Zwei Harnesses**: lokal opencode, Cloud die Claude-Code-CLI. Ein Teil der Zeit- und
  Step-Unterschiede geht darauf zurück, nicht auf das Modell.
- **Ein Lauf durch Akku-Entleerung verfälscht**: `ornith15-6bit-lowthink-tq3`,
  `v6-architecture-choice` 15726 s statt ~80 s, danach `a5` nach 39 s abgebrochen.
  Zeiten dieses Laufs unbrauchbar; Wiederholung lief in den Thinking-Prüfstein (s. u.).
- **Die Suite misst Python-Coding-Agentik.** Java, TypeScript, PHP sind ungedeckt — ebenso
  die Klassifikations-/Anti-Halluzinations-Klasse, in der ThinkingCap im August führte.
- **Sub-Check-Auflösung uneinheitlich**: vier Fixtures haben binäre Oracles.

---

## 7. Offen

- [ ] Ornith **think mit Denkbremse** — nicht messbar: `reasoning_tokens: 0`, kein
      `reasoning_content`, obwohl `enable_thinking: true` und Template gepatcht. Ein
      Prüfstein vor dem Batch verhinderte eine Stunde Blindmessung. Ursache ungeklärt.
- [ ] **Java-/TypeScript-Fixtures** — die Suite misst nur Python
- [ ] **Jev/Laya** als typed-decision-Schicht für Klassifikation (Laya: Apache-2.0,
      ~700 MB, lokal; Drittmessung 57 % gegen Jev-API 78 %, aber 7,6 ms gegen 588 ms;
      mit Konfidenz-Gate 0,60: 75 % bei 45 % lokal gelösten Fällen)
- [ ] **omlx mit `--with-custom-kernel`** bauen — ANE-Prefill ist sonst ein No-op
- [ ] **trainee-Definition und PM-Routing** via skill-forge anpassen
- [ ] **N-Klasse (Crawler-Klassifikation)** mit Ornith-6-bit gegenprüfen — dort führte
      ThinkingCap im August

---

## 8. Reproduktion

```bash
set -a; . ~/.config/omlx/.env; set +a
python3 runners/run_king_matrix.py --model <omlx-id> --label <label>   # lokal
python3 runners/run_cc_matrix.py   --model sonnet    --label cc-sonnet5 # Cloud
python3 runners/fix_status_and_lint_baseline.py   # Status oracle-only + Lint-Delta
python3 runners/subchecks.py                      # Sub-Check-Quoten, V2-Verdict
python3 runners/verify_specprefill.py             # belegt, OB SpecPrefill griff
python3 runners/report.py                         # Matrix-Tabellen
```

Der Runner bricht ab, wenn das Modell nicht im omlx-Provider der `opencode.json` steht,
leert vor jedem Batch den Prefix-Cache, wiederholt Läufe mit `steps=0` einmal und markiert
sie danach als `INVALID` statt als Modellfehler.
