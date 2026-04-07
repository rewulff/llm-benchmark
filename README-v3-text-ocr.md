# LLM Benchmark — Apple Silicon

Practical benchmark for local LLM inference on Apple Silicon.
14 tests, 23 runs across 22 model variants, all on consumer hardware.

**Hardware:** M4 Pro 48GB (primary) | M1 Mac Mini 8GB (edge)
**Suite:** V3.1 Text/Code/Reasoning (14 tests)
**Stand:** March 2026

## TL;DR

Qwen3.5-2B (MLX, 4bit, think mode) achieves a perfect 14/14 pass rate with a 25/25 quality score in just 150s — the best value model in this suite. Qwen3.5-4B no-think (MLX) also hits 14/14 at 25/25. For larger models, Devstral-2-24B and Qwen3-Coder-Next-80B both score 25/25. Thinking mode is a double-edged sword: it helps Qwen3.5-4B (think fails 4 tests; no-think passes all 14), but adds significant latency on 9B without a quality gain. Sub-2B models (0.8B, 1B) are surprisingly capable but struggle with nuanced reasoning (D5) and complex multi-step tasks.

## Test Suite

| Test | Category | Description |
|------|----------|-------------|
| B1 | Text | Summarize a technical article about Proxmox maintenance |
| B2 | Text | Analyze a structured maintenance log and identify issues |
| B3 | Text | Statistical analysis of monthly sales data (12 months, 3 products) |
| B4 | Text | Code review of a Python script with multiple bugs |
| C1 | Reasoning | Diff two config files and list semantic changes |
| C2 | Reasoning | Evaluate a decision matrix and recommend an option |
| C3 | Reasoning | Root-cause analysis from a series of system events |
| D1 | Hard | Identify a subtle off-by-one bug in a data-processing function |
| D2 | Hard | Follow multi-step instructions with conditional branching |
| D3 | Hard | Multi-step calculation with intermediate results |
| D4 | Hard | Answer a question using information buried deep in a long context |
| D5 | Hard | Nuanced code review requiring domain knowledge (hardest test) |
| E1 | Expert | Correlate events across multiple log sources to find root cause |
| E2 | Expert | Analyze DMARC report XML and explain deliverability issues |

## Results

### Complete Table

Sorted by pass rate (descending), then quality score, then time.
`Think` column: `yes` = Qwen3.5 think mode active, `no` = no-think / `nothink` variant, `n/a` = not a Qwen3.5 model.
`Run` column disambiguates models with multiple runs.

| # | Model | Params | Quant | RAM | Engine | Score | Rate | QS | Time(s) | Think | HW |
|---|-------|--------|-------|-----|--------|-------|------|----|---------|-------|----|
| 1 | devstral-2-24b-opt | 24B | 4bit | ~14GB | MLX | 14/14 | 100% | 25/25 | 640 | n/a | M4 |
| 2 | devstral-2-24b | 24B | 4bit | ~14GB | MLX | 14/14 | 100% | 25/25 | 483 | n/a | M4 |
| 3 | qwen3-coder-next-80b-opt | 80B/10B | IQ3_XXS | ~30GB | llama | 14/14 | 100% | 25/25 | 386 | n/a | M4 |
| 4 | qwen3.5-2b (Mar 15) | 2B | 4bit | ~1.5GB | MLX | 14/14 | 100% | 25/25 | 150 | yes | M4 |
| 5 | qwen3.5-4b-nothink | 4B | 4bit | ~2.5GB | MLX | 14/14 | 100% | 25/25 | 273 | no | M4 |
| 6 | qwen3-coder-30b-mlx | 30B/3B | 4bit | ~15GB | MLX | 14/14 | 100% | 24/25 | 106 | n/a | M4 |
| 7 | qwen3-coder-next-80b | 80B/10B | IQ3_XXS | ~30GB | llama | 14/14 | 100% | 24/25 | 371 | n/a | M4 |
| 8 | qwen3.5-2b (Mar 16) | 2B | 4bit | ~1.5GB | MLX | 14/14 | 100% | 23/25 | 119 | yes | M4 |
| 9 | gemma-3-4b | 4B | 4bit | ~2.5GB | MLX | 14/14 | 100% | 21/25 | 158 | n/a | M4 |
| 10 | phi-4-mini | ~4B | 4bit | ~2.5GB | MLX | 14/14 | 100% | 21/25 | 406 | n/a | M4 |
| 11 | qwen3.5-4b-gguf-nothink | 4B | Q4_K_M | ~2.5GB | llama | 13/14 | 93% | 25/25 | 267 | no | M4 |
| 12 | qwen3.5-2b-gguf-nothink | 2B | Q4_K_M | ~1.5GB | llama | 13/14 | 93% | 21/25 | 125 | no | M4 |
| 13 | llama-3.2-3b | 3B | 4bit | ~2GB | MLX | 13/14 | 93% | 19/25 | 78 | n/a | M4 |
| 14 | tongyi-deepresearch-30b-opt | 30B/3B | Q4_K_M | ~17GB | llama | 12/14 | 86% | 13/25 | 494 | n/a | M4 |
| 15 | qwen3.5-0.8b | 0.8B | 4bit | ~0.5GB | MLX | 12/14 | 86% | 20/25 | 37 | yes | M4 |
| 16 | qwen3.5-2b-macmini-m1 | 2B | 4bit | ~1.5GB | MLX | 12/14 | 86% | 21/25 | 562 | yes | M1 |
| 17 | qwen3.5-27b-opus-distilled | 27B | 4bit | ~17GB | MLX | 11/14 | 79% | 15/15* | 811 | yes | M4 |
| 18 | qwen3.5-9b-nothink | 9B | 4bit | ~6GB | MLX | 11/14 | 79% | 18/25 | 712 | no | M4 |
| 19 | llama-3.2-1b | 1B | 4bit | ~0.7GB | MLX | 11/14 | 79% | 16/25 | 37 | n/a | M4 |
| 20 | glm-4.7-flash | ? | 4bit | ? | MLX | 10/14 | 71% | 12/25 | 642 | n/a | M4 |
| 21 | qwen3.5-4b (think) | 4B | 4bit | ~2.5GB | MLX | 10/14 | 71% | 22/25 | 424 | yes | M4 |
| 22 | qwen3.5-9b (think) | 9B | 4bit | ~6GB | MLX | 9/14 | 64% | 17/25 | 852 | yes | M4 |
| 23 | huihui-qwen35-27b-opus | 27B | 4bit | ~17GB | MLX | 8/14 | 57% | 2/4* | 602 | yes | M4 |

*\* quality_score denominator is lower because timed-out tests were excluded from scoring*

### Per-Test Pass Rate (sorted by difficulty)

| # | Test | Pass Rate | Difficulty |
|---|------|-----------|------------|
| 1 | D5_nuanced_review | 16/23 (70%) | Hardest |
| 2 | B1_summary | 19/23 (83%) | Hard |
| 3 | C3_root_cause | 19/23 (83%) | Hard |
| 4 | E1_correlated_log | 19/23 (83%) | Hard |
| 5 | E2_dmarc_analysis | 19/23 (83%) | Hard |
| 6 | C2_decision_matrix | 20/23 (87%) | Medium |
| 7 | D2_instruction_following | 20/23 (87%) | Medium |
| 8 | B3_statistics | 21/23 (91%) | Medium |
| 9 | B4_code_review | 21/23 (91%) | Medium |
| 10 | B2_log_analysis | 22/23 (96%) | Easy |
| 11 | C1_config_diff | 22/23 (96%) | Easy |
| 12 | D1_subtle_bug | 22/23 (96%) | Easy |
| 13 | D3_multi_step_calc | 22/23 (96%) | Easy |
| 14 | D4_long_context | 23/23 (100%) | Easiest |

`D4_long_context` (100%) is the only test every model passes. `D5_nuanced_review` (70%) is the hardest — only models with 14/14 pass it reliably.

### Think vs. No-Think

Direct comparison for models where both variants were tested.

| Model | Think Score | Think QS | Think Time | No-Think Score | No-Think QS | No-Think Time | Winner |
|-------|-------------|----------|------------|----------------|-------------|---------------|--------|
| Qwen3.5-2B MLX | 14/14 | 25/25 | 150s | 13/14 | 21/25 | 125s | **Think** |
| Qwen3.5-4B MLX | 10/14 | 22/25 | 424s | 14/14 | 25/25 | 273s | **No-Think** |
| Qwen3.5-9B MLX | 9/14 | 17/25 | 852s | 11/14 | 18/25 | 712s | **No-Think** |

For 2B: thinking mode improves both pass rate and quality at a modest time cost (+25s). For 4B and 9B: no-think mode wins on all metrics — think mode adds substantial latency and actually hurts accuracy on this benchmark.

## Key Findings

1. **Thinking mode hurts at 4B and above (on this suite).** Qwen3.5-4B with think active fails 4 tests (71%); with no-think it passes all 14 (100%) in 35% less time. Same pattern at 9B. Only at 2B does thinking help.

2. **2B is the efficiency champion.** Qwen3.5-2B (MLX, 4bit, think) hits 14/14 with 25/25 quality in 150s using ~1.5GB RAM. That is the same score as Devstral-2-24B (14x larger) at 1/3 the time.

3. **qwen3-coder-30b-mlx is fastest at 100%.** 106 seconds for 14/14 — 3-4x faster than any other model at that score level. MoE architecture (3B active) explains the speed.

4. **D5_nuanced_review separates the models.** This single test fails 30% of all runs. Models that pass D5 are 4B+ or architecturally strong (Devstral, Qwen3-Coder, Llama-3.2-3B squeaks through).

5. **Size alone does not predict quality.** Tongyi-DeepResearch-30B-opt (30B MoE) scores 13/25 quality while Qwen3.5-2B scores 25/25. GLM-4.7-Flash (unknown param count) scores only 10/14 despite presumably being a large model.

6. **M1 Mac Mini penalty is real but manageable.** Qwen3.5-2B on M1 8GB: 562s vs 150s on M4 Pro — 3.7x slower. Pass rate drops from 14/14 to 12/14 (B2_log_analysis and D5 fail). For text tasks without time pressure, M1 is viable.

7. **Distilled reasoning models timed out on this suite.** Both `qwen3.5-27b-opus-distilled` and `huihui-qwen35-27b-opus` timed out on 3-5 tests (B3, B4, D5, E1, E2). These models were trained for deep single-question reasoning, not batch text-analysis tasks.

8. **Optimized configs matter for Qwen3-Coder-Next-80B.** The `-opt` variant (temp=1.0 official settings) scores 25/25 vs 24/25 with standard params — same pass rate (14/14), one point better quality.

## OCR Benchmark — German Documents (April 2026)

Separate benchmark: 14 VLM/OCR models on 5 German document fixtures (49 ground-truth keywords). Keyword matching, not semantic evaluation. All on M4 Pro 48GB via llama-server.

**Fixtures:** Receipt scan (12 kw), Handwritten notes (12 kw), Digital text (10 kw), Mixed layout (11 kw), Product manual (4 kw)

**Scoring:** `>=90%` RECOMMENDED | `>=70%` SUITABLE | `<70%` NOT SUITABLE

### Results

| # | Model | Quant | Score | Keywords | PASS | Avg Speed | Image Size |
|---|-------|-------|------:|----------|------|----------:|-----------:|
| 1 | **Qwen3-VL-2B** | Q4_K_M | **93.9%** | 46/49 | 2/5 | 5.0s | 768 |
| 2 | GLM-OCR | Q8_0 | 91.8% | 45/49 | 1/5 | 5.1s | 336 |
| 3 | Qwen3-VL-4B | F16 | 91.8% | 45/49 | 1/5 | 13.8s | 768 |
| 4 | Qwen3-VL-8B | Q4_K_M | 91.8% | 45/49 | 1/5 | 14.1s | 768 |
| 5 | Qwen3-VL-4B | Q4_K_M | 89.8% | 44/49 | 1/5 | 8.4s | 768 |
| 6 | PaddleOCR-VL-1.5 | default | 77.6% | 38/49 | 1/5 | 3.5s | 1001 |
| 7 | Qwen2.5-VL-3B | Q4_K_M | 67.3% | 33/49 | 1/5 | 9.5s | 560 |
| 8 | InternVL3-2B | Q4_K_M | 53.1% | 26/49 | 1/5 | 5.4s | 448 |
| 9 | InternVL3-1B | Q8_0 | 51.0% | 25/49 | 1/5 | 3.1s | 448 |
| 10 | InternVL2.5-4B | Q4_K_M | 34.7% | 17/49 | 1/5 | 5.3s | 448 |
| 11 | Qianfan-OCR | Q4_K_M | 30.6% | 15/49 | 0/5 | 12.0s | 448 |
| 12 | Gemma 4 E4B | Q4_K_M | 24.5% | 12/49 | 0/5 | 14.6s | 224 |
| 13 | Moondream2 | F16 | 0.0% | 0/49 | 0/5 | — | 378 |
| 14 | SmolVLM2-2.2B | Q4_K_M | 0.0% | 0/49 | 0/5 | — | 384 |

### Config-Tuning Re-Runs

5 re-runs with adjusted ctx_size and image_max_tokens. None improved — most got worse.

| Model | Original | Changed Config | Re-Run | Delta |
|-------|:--------:|----------------|:------:|:-----:|
| PaddleOCR ctx 8k | 77.6% | ctx 4096→8192 | 59.2% | **-18%** |
| PaddleOCR ctx 16k | 77.6% | ctx 4096→16384 | 71.4% | -6% |
| Qianfan-OCR imt2048 | 30.6% | image_max_tokens 2048 | 18.4% | **-12%** |
| InternVL3-2B imt4096 | 53.1% | image_max_tokens 4096 | 53.1% | ±0 |
| Gemma 4 E4B imt512 | 24.5% | image_max_tokens 512 | 22.4% | -2% |

### OCR Key Findings

1. **Smallest generalist wins on German.** Qwen3-VL-2B (2 GB, Q4) beats all larger models and all OCR specialists at 93.9%.
2. **Bigger ≠ better for OCR.** 2B = 4B = 8B quality within the Qwen3-VL family (93.9% vs 91.8% vs 91.8%). The 2B is 3x faster.
3. **Chinese-trained specialists fail on German.** PaddleOCR-VL leads OmniDocBench (English/Chinese) but drops to 77.6% on German. Qianfan-OCR: 30.6%.
4. **Config tuning doesn't help.** 5 re-runs with adjusted context and image tokens — all equal or worse. The problem is training data, not configuration.

Raw OCR results: `lib/local-llm/benchmark/agent-results/ocr-*/results.json`

## Archive

Older benchmark generations (V1 code-agent tests, V2 fixture suite, V4 multi-harness CC/smolagents/VLM) are in `results/archive/`.

## Quick Start

```bash
# Create venv and run benchmark for a model
./run.sh --config configs/qwen3.5-2b.json

# Run specific categories only
./run.sh --config configs/qwen3.5-4b-nothink.json

# Results are saved to results/<model>_<date>.json
```

**Requirements:** Python 3.10+, llama-server or mlx-lm server running on port 1235.

For GGUF models (llama-server):
```bash
llama-server -m <model.gguf> --port 1235 --ctx-size 32768 --gpu-layers 99 --flash-attn --jinja
```

For MLX models (mlx-lm):
```bash
mlx_lm.server --model mlx-community/<model> --port 1235
```

## License

MIT
