# MTP-Tiefen-Sweep — ThinkingCap-Qwen3.8-27B-mlx-nvfp4

**Datum:** 2026-09-30 · **Host:** M4 Pro 48 GB · **omlx:** 0.7.0rc1
**Modell:** `ThinkingCap-Qwen3.8-27B-mlx-nvfp4` (dense 27B, nativer MTP-Head im Checkpoint:
`language_model.mtp.*`, 15 Tensoren bf16)
**Anlass:** rwu-Hypothese „mit Tiefe 3 müsste der Sweetspot sein" — bestätigt.

## Bedingungen

`enable_thinking: true` · `chat_template_kwargs: {reasoning_effort: medium}` ·
`max_tokens: 16384` · `max_context_window: 65536` · `temperature 0.6 / top_p 0.95 /
top_k 20` · `repetition_penalty: 1.0` (Pflicht — jeder andere Wert schaltet MTP in omlx
**still** ab) · `turboquant_kv_enabled: true, bits 3.0` (Einstellung rwu)

Messprotokoll: 250 max_tokens, `temperature 0.0`, Nonce im Prompt gegen Prefix-Cache-Treffer,
Modell-Unload zwischen den Stufen (MTP-Head wird beim Laden initialisiert), Netto-Zeit ohne
`model_load_duration`. Acceptance aus der Logzeile
`omlx.patches.mlx_lm_mtp.batch_generator - MTP[0] … accept=X/Y (Z%) depth[…]`.

## Ergebnis

| `mtp_fixed_depth` | tok/s | Faktor | Acceptance | tok/cycle | Tiefenverteilung |
|---|---|---|---|---|---|
| aus (Baseline) | 10,0 | 1,00× | — | — | — |
| 2 | 14,8 | 1,48× | 92,1 % | 2,79 | d1=42/47, d2=40/42 |
| **3** | **15,3** | **1,53×** | **94,9 %** | 3,79 | d1=32/34, d2=32/32, d3=29/32 |
| 4 | 14,3 | 1,43× | 92,4 % | 4,30 | d1=27/30 … d4=22/23 |
| 5 | 14,0 | 1,40× | 88,6 % | 4,53 | d1=32/38 … d5=21/24 |
| 6 | 12,1 | 1,21× | 85,5 % | 4,73 | d1=33/37 … d6=14/17 |
| adaptive (`None`) | 15,0 | 1,50× | 94,0 % | 3,91 | d1=28/30 … d4=17/18 |

**Sweetspot ist Tiefe 3.** Ab Tiefe 4 steigt zwar `tok/cycle` weiter, aber der Verify-Aufwand
pro Zyklus wächst schneller als der Gewinn und die Acceptance fällt — netto sinkt der Durchsatz.

## Bestätigung auf echten Agent-Fixtures

Der Mikrobenchmark unterschätzt den Effekt; auf Agent-Aufgaben trägt er teils stärker:

| Fixture | ohne MTP | mit MTP d3 | Faktor |
|---|---|---|---|
| `a2-bugfix` | 244 s | 147 s | **1,66×** |
| `v6-quick-nqueens` | 316 s | 230 s | 1,37× |
| `v6-debug-unmarked` | 205 s | 175 s | 1,17× |
| `c1-dependent-pipeline` | 340 s | 274 s | 1,24× |
| `v6-custom-constraint` | 196 s | 147 s | 1,33× |

Der Gewinn ist bei generierungslastigen Aufgaben groß und bei prefill-lastigen klein
(`v6-debug-unmarked` liest ein Log) — MTP beschleunigt nur die Generierung. Für den
Prefill-Anteil ist SpecPrefill der eigene Hebel (nur MoE-Targets).

## Abgrenzung zur Juli-Messung

Die Notiz vom 28.07. (`omlx 0.5.2rc2`) hielt fest: MTP am **35B-A3B MoE** 41–64 % Acceptance
und 0,77–1,00× (kein Gewinn), dense 27B mit frankensteintem Fremdkopf 71–84 % und 1,60–1,74 %.
Zwei Unterschiede heute:

1. **Nativer MTP-Head statt angeflanschtem** → Acceptance 94,9 % statt 71–84 %.
2. **Adaptive Depth kollabiert nicht mehr auf d1** (nutzt d1–d4, 94,0 %). Das war in 0.5.2rc2
   der Grund, warum Tiefensteuerung wirkungslos schien.

Unberührt bleibt die MoE-Aussage: Beim A3B-MoE multiplizieren sich die Experten-Reads im
Verify — das ist Bandbreiten-Mathematik und von der omlx-Version unabhängig.

## Betriebsempfehlung

Für `ThinkingCap-Qwen3.8-27B-mlx-nvfp4`: `mtp_enabled: true`, `mtp_fixed_depth: 3`,
`repetition_penalty: 1.0`. Prüfstein bei Abweichungen: die `MTP[0] … accept=` Logzeile —
fehlt sie, läuft MTP nicht (häufigste Ursache: Penalty ≠ 1.0).
