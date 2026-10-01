# Durchsatz auf omlx 0.7.0 — warum unsere Zahlen von den Release-Benchmarks abwichen

**Gemessen:** 01.10.2026 · **Hardware:** MacBook Pro M4 Pro, 48 GB, ~273 GB/s
**Server:** omlx 0.7.0 (von 0.7.0rc1 aktualisiert) · **Rohdaten:** `throughput.json`, `throughput-E.json`
**Runner:** `runners/run_070_throughput.py`

## Anlass

Die Release-Benchmarks zu omlx 0.7.0 melden gegenüber 0.7.0rc1 bis **+46 % Prompt Processing
und +50 % Token Generation**. Unsere komplette King-Eval vom 30.09. lag weit darunter
(ThinkingCap-27B: 10,0 tok/s). Die Frage war, ob bei uns etwas falsch konfiguriert ist.

**Antwort: ja, zwei Dinge — und ein dritter Teil ist Hardware.** Wir maßen auf der alten
Version *und* mit einem anderen Quantformat als die Referenz. Beide Faktoren waren
gleichzeitig anders, dazu die Hardware. Diese Matrix dreht sie einzeln.

## Ergebnis

| Zelle | Modell | Quant | MTP | tok/s | gegen rc1 |
|---|---|---|---|---|---|
| A | ThinkingCap-27B (dense) | nvfp4, 22,3 GiB | aus | 11,1 | 10,0 → **+11 %** |
| B | ThinkingCap-27B | nvfp4 | d3 | 14,0 | 15,3 → **−8,5 %** |
| C | ThinkingCap-27B | **oQ4e**, 15,8 GiB | aus | 14,6 | — |
| D | ThinkingCap-27B | **oQ4e** | d3 | **22,6** | 15,3 → **+48 %** |
| E | Ornith-1.5-35B-A3B (MoE) | MLX-6bit, 26 GiB | aus | 65,9 | 46,9 → **+41 %** |
| F | Ornith-1.5-35B-A3B | **oQ4e**, 20,2 GiB | aus | **78,9** | 46,9 → **+68 %** |
| G | Ornith-1.5-35B-A3B | **oQ4e** | d3 | 51,2 | — |

Je Zelle drei Läufe, Median; Streuung durchweg unter 1 tok/s. Vor jedem Lauf Hot- und
SSD-Cache geleert. Messgröße ist `generation_tokens_per_second` aus der omlx-Antwort —
Prefill und Ladezeit sind herausgerechnet.

## Die drei Faktoren, getrennt

### 1. Serverversion: wirkt bei MoE stark, bei dense kaum

| | rc1 → 0.7.0 |
|---|---|
| dense (A gegen rc1-Basis) | **+11 %** |
| MoE (E gegen rc1-Basis) | **+41 %** |

Das deckt sich mit den Release Notes, wenn man genau liest: Die dense-Beschleuniger sind
dort ausdrücklich an M5 gebunden — *„QSA attention on the M5 tensor units"*, *„exact fused
decode and MTP verify kernels on M5 GPUs"*. Der M4 Pro hat diese Einheiten nicht. Der
einzige Decode-Punkt **ohne** M5-Einschränkung ist *„fused MoE, DeltaNet and attention
kernels for one-token decode"* — und genau dort messen wir die +41 %.

**Die Balken im Release-Chart stammen von M5 Max und M3 Ultra.** Für dense auf M4 Pro sind
sie nicht erreichbar; für MoE schon.

### 2. Quantformat: wirkt überall, ungefähr nach Gewicht

| | Gewichtsverhältnis | gemessener Gewinn |
|---|---|---|
| dense: nvfp4 → oQ4e (C gegen A) | 22,3 → 15,8 GiB = 1,41× | **+32 %** |
| MoE: 6bit → oQ4e (F gegen E) | 26 → 20,2 GiB = 1,29× | **+20 %** |

Der Gewinn bleibt etwas hinter dem Gewichtsverhältnis zurück, folgt ihm aber. Das ist die
erwartete Bandbreitenlogik: Decode liest pro Token die Gewichte, kleinere Gewichte sind
schneller. **oQ4e ist das Format, in dem omlx selbst misst und optimiert** — wir hatten
nvfp4 bzw. affine-6bit verwendet.

### 3. MTP: bei dense ja, bei MoE nur adaptiv und nur bei Code — Befund am Abend korrigiert

| | ohne MTP | mit MTP d3 | Acceptance |
|---|---|---|---|
| dense, nvfp4 (A→B) | 11,1 | 14,0 | **63,9 %** |
| dense, oQ4e (C→D) | 14,6 | **22,6** (+55 %) | **64,2 %** |
| MoE, oQ4e (F→G) | 78,9 | 51,2 (**−35 %**) | **15,7 %** |

Die Acceptance stammt aus den `accept=`-Zeilen des Serverlogs, nicht aus einem Settings-Feld.
Zellen ohne Beleg wären als MTP-inaktiv markiert worden; alle drei MTP-Zellen sind belegt.

> **Korrektur 18:05 Uhr — die folgende Schlussfolgerung war zu eng.** Alle drei „Beine" liefen
> mit **fester Tiefe 3** und **Prosa-Prompt**. rwu beobachtete live 87 tok/s auf Ornith
> (adaptiv ≤ 4, Thinking, HTML-Shop-Prompt, 10 089 Token, Acceptance 93 %). Die Nachmessung
> (Zellen C0–C4, echte Request-Temperatur 0) trennt die Faktoren:
>
> | Zelle | Prompt | MTP | Thinking | tok/s | Acceptance Stufe 1 |
> |---|---|---|---|---|---|
> | C2 | Code | aus | aus | 77,8 | – |
> | **C1** | **Code** | **adaptiv ≤ 4** | aus | **103,1 (+33 %)** | **88 %** |
> | C4 | Code | aus | an | 78,2 | – |
> | C3 | Code | adaptiv ≤ 4 | an | 101,0 | 89 % |
> | X | Prosa | aus | aus | 77,2 | – |
> | C0 | Prosa | adaptiv ≤ 4 | aus | 77,5 | 21 % (Regler parkt) |
> | Y | Prosa | fest 1 | aus | 62,8 | 19 % |
> | G | Prosa | fest 3 | aus | 51,2 | 16 % |
>
> Der A3B-Head trifft nur die **erste** Draft-Stufe (`d2=18/72`), und das nur bei
> vorhersagbarem Output (HTML/CSS, Code). Bei Prosa liegt Stufe 1 bei ~20 %; feste Tiefe
> verschwendet dann jeden Zyklus, der adaptive Regler **parkt** MTP nach 128 Token und
> probiert periodisch neu — Ergebnis ±0 statt −35 %. Thinking ändert am Durchsatz nichts
> (C3/C4 ≈ C1/C2); rwus 93 % kamen vom Prompt-Typ. Die Basis ist prompt-unabhängig
> (77,2 / 77,8). **Knecht-Konsequenz:** Ornith mit `mtp_fixed_depth: null`,
> `mtp_adaptive_max_depth: 4` — bei Code +33 %, bei Prosa kein Verlust; die 9/10 der
> Fixtures sind damit noch nicht nachgewiesen (Lightning MTP ist als „exact" gebaut, der
> Beleg steht aus). Daten: `throughput-C0C1C2C3C4.json`, `throughput-VWXY.json`,
> `throughput-ZZ2.json` (V–Z2 liefen wegen eines Runner-Fehlers bei Request-Temperatur
> 0,6 statt 0 — untereinander vergleichbar, die Temperatur-Trennung leistet erst C0).
>
> Methodisch: Ein Durchsatz-Benchmark mit Prosa-Prompt unterschätzt MTP für Code-Arbeit
> systematisch (auch Solstice: Code 27–29 vs. Prosa 24,6). Der Runner führt deshalb seit
> 18:00 Uhr einen Code-Prompt (`_prompt: "code"`) als zweite Standardzelle.

**MoE profitiert nicht von Spekulation** (ursprünglicher Text, gilt nur für feste Tiefe ≥ 3 und
Prosa). Das stand auf drei Beinen:
llama.cpp mit nativem GGUF-Head (34,9 gegen 48,2 tok/s, Acceptance 38,2 %), omlx 0.7.0 mit
nativem oQ4e-Head (51,2 gegen 78,9, Acceptance 15,7 %), und in beiden Fällen dieselbe
Richtung. Die Sorge, der Befund sei ein Artefakt der rc1-Implementierung, ist ausgeräumt —
0.7.0 hat „Exact Lightning MTP" und residenten MTP-Head bei Expert Offload gebaut, und es
ändert nichts.

**Nebenbefund:** Die dense-Acceptance liegt hier bei ~64 %, im rc1-Sweep waren es 94,9 %.
Das ist kein Versionseffekt, sondern der Prompt: Der rc1-Sweep lief auf Code-Fixtures,
diese Matrix auf Fließtext (Wärmetauscher-Erklärung). Code ist repetitiv und gut
vorhersagbar, Prosa nicht — Zelle B mit demselben Head wie rc1 zeigt dieselben 64 %.
Für Agent-Arbeit (Code) ist die höhere Acceptance die realistischere.

## Was das praktisch heißt

| Rolle | bisher | neu | Gewinn |
|---|---|---|---|
| Knecht (Allrounder, schnell) | Ornith MLX-6bit, 46,9 tok/s | **Ornith oQ4e-mtp, MTP aus, 78,9 tok/s** | **1,68×** |
| dense-Kandidat (Qualität) | ThinkingCap nvfp4+MTP, 15,3 | **ThinkingCap oQ4e-mtp + MTP d3, 22,6** | **1,48×** |

Beide Empfehlungen wechseln das Quantformat. Für Ornith bleibt MTP **aus**, für ThinkingCap
**an** — gegenläufig, und beides gemessen.

Dazu kommt ein Nebeneffekt: Die oQ4e-Fassungen sind kleiner (20,2 statt 26 GiB, 15,8 statt
22,3 GiB). Das entschärft das Speicherproblem, siehe unten.

## Zwei Betriebsfallen aus diesem Lauf

**1. Der Memory Guard in 0.7.0 blockiert Ornith 6-bit.** Zelle E scheiterte zunächst mit
`prefill_memory_exceeded`: *„would require ~27,31 GB peak but dynamic ceiling is 27,31 GB …
only 2,90 GB is reclaimable right now"*. `memory_guard_tier` stand dabei bereits auf
`balanced`. Ursache war ein parallel laufender `llama-server`, der 24 GB in Metal-Buffern
hielt — die tauchen **nicht** im RSS auf, nur in `Pages wired`. Nach dessen Stopp lud das
Modell sofort.
→ **Nie zwei große Modelle in zwei Servern gleichzeitig halten.** Der Guard meldet das als
Speicherfehler, nicht als Konflikt.

**2. `loaded_count` fällt nie auf 0.** omlx hält sein Default-Modell und lädt es nach. Wer
nach einem Unload darauf wartet, wartet vergeblich. Das Entladen läuft zudem asynchron
weiter: Setzt der nächste Schritt sofort neue Settings, kollidiert der Reload und der
Request stirbt mit **HTTP 409**. Fester Puffer plus Retry ist die Lösung, nicht Warten auf
den Zähler.

## Qualität auf oQ4e — Fixture-Matrix (Nachtrag, 14:16–14:33 Uhr)

Je Kandidat nur die schnellste Konfiguration, jeder gegen seine eigene Referenz vom 30.09.
mit deren Sampling. Ornith voll (10 Fixtures, temp 0), ThinkingCap minimal (3 Fixtures:
zwei schnelle Typen plus der einzige Referenz-FAIL).

| Lauf | PASS | Agent-Zeit | Ausfall | Fehlerbild |
|---|---|---|---|---|
| Ornith MLX-6bit, temp 0, run1 (Ref.) | 10/10 | 7,9 min | — | — |
| Ornith MLX-6bit, temp 0, run2 (Ref.) | 9/10 | 8,1 min | r1 | ACME statt Brightwave |
| **Ornith oQ4e, MTP aus, temp 0** | **9/10** | **6,1 min** | r1 | **ACME statt Brightwave, 14/18 — identisch** |
| ThinkingCap nvfp4 + MTP d3 (Ref., 10 Fix.) | 9/10 | 64,8 min | a5 | 7/8 gefixt, calculate_discount |
| **ThinkingCap oQ4e + MTP d3 (3 Fix.)** | **2/3** | 139–259 s/Fix. | a5 | **7/8 gefixt, calculate_discount — identisch** |

**Beide Ausfälle sind Modellschwächen, keine Quant-Schäden** — das Fehlerbild ist jeweils
bis in die Sub-Checks identisch mit der Referenz, und beim offiziellen Ornith-6bit tritt r1
ebenso auf. Qualität liegt innerhalb der Referenz-Streuung.

**Die Agent-Zeit ist die Zahl, die zählt:** Ornith oQ4e erledigt dieselben zehn Fixtures
in 6,1 statt 7,9–8,1 Minuten (−23 %) bei gleicher Tool-Call-Zahl (55 gegen 54/51). Das ist
weniger als die +20 % Decode, weil Prefill und Tool-Overhead dominieren — und es ist der
Wert, der für den Knecht gilt. ThinkingCap-Fixtures laufen 5–10 % schneller als die Referenz
(a2 nicht wertbar: ein TTS-Load fiel genau hinein).

**Knecht-Umstellung auf `scottlowry/Ornith-1.5-35B-A3B-oQ4e-mtp`, MTP aus, ist damit belegt**
— Tempo, Qualität und Speicher (20,2 statt 26 GiB).

## Grenzen dieser Messung

- **Ein Prompt, 2048 Token, kurzer Kontext.** Langkontext-Verhalten ist nicht erfasst; der
  dort gemessene Einbruch (M3 Ultra: 70,3 bei 64K gegen 74,6 bei 4K) ist nicht nachgefahren.
- **Die dense-Acceptance-Differenz zu rc1 ist kein sauberer A/B** (anderer Prompt).
- Prefill wurde nicht gemessen, obwohl die Release-Notes dort die größten Gewinne melden —
  und zwar ebenfalls überwiegend M5-gebunden.

- **Die Hochrechnung „23,6 erwartet, 22,6 gemessen"** vergleicht die M3-Ultra-Zahl von
  `Qwen3.8-27B-oQ4e` mit unserem `ThinkingCap-Qwen3.8-27B-oQ4e` — ein Finetune auf derselben
  Basis, nicht dasselbe Modell. Für die Größenordnung tragfähig, nicht für die Nachkommastelle.
- **Concurrent > 1 ist in keinem Stack gemessen.** llama.cpp lief mit vier Slots, omlx hat
  einen Engine-Pool — beide wurden nur mit einem Request belastet. Für Worker-Parallelität
  ist das die offene Frage. Draft-Modell-Spekulation bei llama.cpp (`-md`) ebenfalls nicht.
- **Speicherdruck während aller Messungen:** Swap 82 % voll, Memory-Guard-Ceiling über den
  Tag von 30,2 auf 26,2 GiB gefallen (dynamisch, folgt dem Systemdruck). Decode-Durchsatz
  ist davon kaum betroffen (Modell liegt wired), die 507/400-Ausfälle schon.

## Weitere Betriebsfalle: TTS-Wrapper weicht unter Last still aus

`tools/tts-macbook` (Port 8084, Bifrost-Ziel) nutzt omlx als Primary und prüft `/health`
mit **1,5 s Timeout, 30 s gecacht**. Antwortet omlx unter Benchmark-Last langsamer, schaltet
der Wrapper für 30 s auf seinen `subprocess`-Pfad — ohne Logzeile in omlx. Null TTS-Requests
im omlx-Log sind also kein Beleg für „kein TTS", sondern können „TTS lief am omlx vorbei"
heißen. TTS-Smoke nach dem Upgrade: PASS (HTTP 200, 161 KB WAV, omlx-Load belegt). Das
TTS-Modell ist seit 01.10. omlx-Default (`is_default`), damit nach jedem Unload 3 GB statt
22 GB nachgeladen werden; real belegt es 3,16 GB, omlx schätzt 1,0.

## Nachtrag Solstice Qwen3.8-27B-TURBO (16:00–17:13 Uhr): Modellkarte, Modus, MTP-Tiefe

Kandidat für den Mac mini M6 (rwu): `Solstice-AI/Qwen3.8-27B-TURBO-Fable-Cold-Fusion-…-oQ4e-1M`.
Die Modellkarte verspricht 58–72 tok/s und empfiehlt TurboQuant-KV, kein MTP, kein Thinking.

**Was davon stimmt, geprüft:**
- oQ4e ist echt (`mode: affine, bits 4, g64` + Overrides, identisch mit scottlowry/chriswessels).
- Die Benchmark-Tabelle der Karte ist aus der Alibaba-Qwen3.8-Karte kopiert, die tok/s-Zahlen
  stammen aus „Anvil" (Solstice-Labs) — ein llama.cpp-Build (770× ggml, 0× mlx), der MLX gar
  nicht laden kann; 1 Contributor, 8 Stars. Für unseren Stack sind die Zahlen ohne Aussage.
- „kein MTP" ist falsch: der safetensors-Index enthält 29 `language_model.mtp.*`-Tensoren.
  (Unser erster Check suchte Dateinamen statt Tensoren und meldete „kein Head" — Fehler,
  rwu fand ihn per WebUI: „ich sehe sofort mehr t/s".)
- Das Chat-Template setzt `enable_thinking` **an** mit `reasoning_effort` Default `xhigh` und
  kennt zehn Profile per In-Chat-Tag (`{REASON:apollo}` … `{REASON:oracle}`); die
  Profil-Instruktion wird auch bei Thinking aus injiziert (Prompt 54 Token off, 257 low,
  306 xhigh). omlx kennt kein `reasoning_effort`-Setting, nur `chat_template_kwargs` im
  Request; opencode sendet keines und zählt omlx' `reasoning_content`-Delta nicht
  (`reasoning: 0` ist blind, nicht „denkt nicht").

**Durchsatz (nothink, 2048 Token, Prosa-Prompt, Ceiling ≥ 25,6 GiB, keine Drosselung):**

| Zelle | Modus | tok/s | Acceptance |
|---|---|---|---|
| H | ohne MTP, TQ-KV 4-bit (Karte) | 12,7 | – |
| I | ohne MTP, TQ aus | 13,8 | – |
| N | MTP fest 3 | 24,6 | 67,6 % |
| O | **MTP fest 4** | **27,1** | 66,0 % |
| P | MTP fest 5 | 24,6 | 63,5 % |
| Q | MTP fest 6 | 23,4 | 62,1 % |
| R | MTP fest 8 | 13,2 | 61,7 % |
| S | adaptiv, omlx-Default (27B ⇒ Ceiling 4) | 25,4 | 66,4 % |
| T | adaptiv ≤ 6 | 26,3 | 67,2 % |
| U | adaptiv ≤ 8 | 26,2 | 68,2 % |

Referenz ThinkingCap (gleiche Basis): Zelle D 22,6 mit MTP fest 3. Daten:
`throughput-HIJ.json`, `throughput-N.json`, `throughput-OPQRSTU.json`.

**Befund MTP-Tiefe — das übersehene Setting.** Fest d3 stammte aus dem rc1-Sweep vom 30.09.
und war auf 0.7.0 eine Altlast: omlx wählt die Tiefe standardmäßig **adaptiv** je Sequenz aus
der laufenden Acceptance und erzwingt für Qwen 27B (hidden 5120, 64 Layer) einen Ceiling von
mindestens 4 (`utils/model_loading.py`, „Qwen 27B keeps an adaptive ceiling of at least
four"); `mtp_fixed_depth` schaltet diesen Regler ab. Maximum ist 8. Die 27,7 tok/s aus rwus
WebUI-Lauf („adaptiv ≤ 3", intern auf 4 gehoben) sind damit vollständig erklärt. TQ-KV kostet
8 % und konvertiert nur 15/64 Layer — für Tempo kontraproduktiv, in der Karte für 16/24-GB-
Geräte gedacht.

Tiefer als 4 lohnt bei Prosa nicht: die Stufen-Acceptance fällt auf 50–65 %
(`d4=50/90, d5=19/38`), d8 verschenkt sechs Drafts pro Zyklus. Beim **Code-Fixture** lag sie
bei 82–90 % (`d3=116/142`, tok/cycle 3,4 von max 4; 26,5–28,9 tok/s je Request) — dort ist
die Tiefe der Deckel. Der adaptive Regler löst das: bei ≤ 8 nutzte er auf Prosa von selbst
nie d6–d8 (`d6=0/0`). Vorschlag Betriebsmodus: `mtp_enabled`, `mtp_fixed_depth: null`,
`mtp_adaptive_max_depth: 8`; der Code-Beleg (Fixtures mit adaptiv) steht noch aus.

**Fixtures „jedes Modell in seinem Modus"** (Thinking an, Profile per Tag, Drift-Check nach
jeder Fixture, `run_mode_fixtures.sh`):

| Lauf | Modus | a2-bugfix | v6-custom | a5-long-edit |
|---|---|---|---|---|
| solstice-think-profiles-min | Thinking, ohne MTP | PASS 203 s | PASS 324 s | FAIL 370 s |
| solstice-think-profiles-mtp-min | Thinking, MTP d3 | PASS 179 s | PASS 235 s | FAIL 246 s |
| thinkingcap-think-xhigh-mtp-min | Thinking xhigh, MTP d3 | PASS 214 s | PASS 170 s | FAIL 321 s |
| thinkingcap-oq4e-mtp-d3-min | nothink, MTP d3 | PASS 195 s | PASS 137 s | FAIL 257 s |

`solstice-oq4e-tq4-min` ist ungültig (Runner-Abbruch, NO_RESULT). a5-long-edit fällt in
allen fünf Läufen identisch (7/8, `calculate_discount`) — bevor das als Modellschwäche
gilt, ist die Fixture selbst zu prüfen. Thinking kostet Solstice bei a2/v6 nichts Messbares
gegenüber ThinkingCap; MTP spart 12–28 % Laufzeit.

## Offen

- Prefill-Durchsatz messen (unser bekannter Schwachpunkt: ~121 tok/s auf M4 Pro; die
  Release-Notes melden gerade dort +46 %, überwiegend M5-gebunden)
- Concurrent > 1 auf beiden Stacks — beantwortet zugleich, ob llama.cpp noch einen Vorteil hat
- ThinkingCap-Vollmatrix auf oQ4e, falls der dense-Kandidat je produktiv werden soll
- Solstice/ThinkingCap-Fixtures mit adaptivem MTP (≤ 8) statt fest d3 — Code-Beleg für die
  Tiefenwahl; ThinkingCap-Gegenprobe adaptiv
- Ornith-Fixtures (10) mit adaptivem MTP ≤ 4 — Qualitätsnachweis vor Umstellung des Knechts
- a5-long-edit-Fixture prüfen (identischer FAIL in fünf Läufen)
