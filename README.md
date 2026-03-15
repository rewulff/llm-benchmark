# LLM Benchmark Suite for Apple Silicon

A benchmark suite for local LLM models on Apple Silicon (M1/M4 Pro), designed to evaluate
models as autonomous coding assistants ("Knecht" — worker agents for Claude Code).

**Hardware:** M4 Pro 48GB, M1 Mac Mini 8GB
**Backends:** MLX via mlx-lm, llama.cpp via llama-server
**Goal:** Find the fastest, most reliable local model for agentic code tasks under macOS

---

## Methodology

### V1 — Feb 2026 (7 tests, PASS/FAIL only)

Tests B1–B4 (text analysis) and C1–C3 (reasoning) via direct API calls.
No quality scoring — binary PASS/FAIL.

### V2 — 15 Mar 2026 (14 tests, Quality-Scoring /25)

Adds two new categories:

- **D1–D5** (hard): Challenging agentic tasks requiring multi-step reasoning
- **E1–E2** (deep): Complex analysis requiring deep domain knowledge

Quality scoring: each passed test contributes to a `/25` total score, measuring not just
whether a model passes, but how well it performs.

---

## Test Categories

### B — Text Analysis (B1–B4)

| Test | What it checks |
|------|---------------|
| B1 | German summarization — language fidelity, conciseness |
| B2 | Log analysis — structured output, pattern recognition |
| B3 | Statistical anomaly detection — numerical reasoning |
| B4 | Code review — identifying bugs and quality issues |

### C — Reasoning (C1–C3)

| Test | What it checks |
|------|---------------|
| C1 | Config diff analysis — structured comparison |
| C2 | Decision matrix — multi-criteria evaluation |
| C3 | Root-cause analysis — causal reasoning from evidence |

### D — Hard (D1–D5, V2)

| Test | What it checks |
|------|---------------|
| D1–D5 | Complex agentic tasks requiring multi-step planning |

### E — Deep (E1–E2, V2)

| Test | What it checks |
|------|---------------|
| E1–E2 | Deep domain analysis, extended context reasoning |

---

## Results

### M4 Pro 48GB — Methodology V2 (15 Mar 2026)

| Model | Params | Backend | Pass | Quality /25 | Time | Role |
|-------|--------|---------|------|-------------|------|------|
| Qwen3-Coder-30B-A3B | 30B MoE | MLX 4bit | 14/14 | 21/22 | 67s | Fast-Knecht |
| Qwen3-Coder-Next 80B | 80B MoE | GGUF IQ3_XXS | 14/14 | 25/25 | 386s | Quality-Knecht |
| Devstral-2-24B | 24B | MLX 4bit | 14/14 | 25/25 | 483s | Reserve |
| Qwen3.5-2B | 2B | MLX 4bit | 14/14 | 25/25 | 150s | Mac-Mini-Champion |
| Qwen3.5-4B /no_think | 4B | MLX 4bit | 14/14 | 25/25 | 273s | Alternative |
| Qwen3.5-0.8B | 0.8B | MLX 4bit | 12/14 | 20/25 | 37s | Ultra-compact |
| Tongyi-DeepResearch-30B | 30B MoE | GGUF Q4_K_M | 12/14 | 13/25 | 495s | Research only |
| GLM-4.7-Flash | 9B | MLX 4bit | 10/14 | 12/25 | 642s | Too small |
| Qwen3.5-9B /no_think | 9B | MLX 4bit | 11/14 | 18/25 | 712s | Worse than 4B |
| Huihui-Qwen3.5-27B-Opus | 27B | MLX 4bit | 8/14 | 2/4 | 602s | Content-Loop |
| DeepSeek-Coder-V2-Lite | 16B MoE | GGUF Q8_0 | 5/7 | — | 88s | V1 only |
| GLM-4.5-REAP-82B | 82B MoE | GGUF IQ3_XS | 0/14 | — | — | Incompatible |

### M1 Mac Mini 8GB

| Model | Pass | Quality | Time |
|-------|------|---------|------|
| Qwen3.5-2B MLX 4bit | 12/14 | 21/25 | 563s |

### Methodology V1 Results — Feb 2026 (7 tests, B+C only)

| Model | Params | Backend | Pass B+C | Time | Notes |
|-------|--------|---------|----------|------|-------|
| qwen3-coder-30b | 30B MoE | GGUF Q4_K_M | 7/7 | 595s total | Primary model |
| qwen3-coder-30b | 30B MoE | MLX 4bit | 7/7 | 242s (B+C) | MLX faster on single-shot |
| qwen3.5-35b-a3b | 35B MoE | GGUF Q4_K_M | 6/7 | 991s | Best at large file edit |
| lfm2-24b-a2b | 24B MoE | GGUF Q5_K_M | 5/7 | 234s | Fast but unreliable |
| qwen3-30b | 30B MoE | GGUF Q4_K_M | 5/7 | 542s | No advantage over coder |
| gemma-3-27b | 27B Dense | GGUF Q4_K_M | 5/7 | 858s | Too slow |
| gpt-oss-20b | ~20B Dense | GGUF Q5_K_M | 5/7 | 463s | No agentic capability |
| DeepSeek-Coder-V2-Lite | 16B MoE | GGUF Q8_0 | 5/7 | 88s | V1 only |

---

## Key Findings

1. **Thinking mode is the biggest performance killer.** Qwen3.5 4B and 9B both use
   chain-of-thought by default. Disabling it via `/no_think` system prompt cuts time by
   ~60% and actually improves pass rates. The 4B with no_think beats the 9B.

2. **MLX vs llama.cpp: ~6% difference in English-only tasks.** Backend choice barely
   matters for quality. MLX is faster on single-shot text tasks; llama.cpp is significantly
   faster for multi-turn agent loops (KV-state caching in slots vs. full recomputation).

3. **2B models via knowledge distillation reach 25/25 quality.** Qwen3.5-2B achieves
   perfect quality scores on M4 Pro. Smaller distilled models inherit reasoning capabilities
   that were not possible in prior generations.

4. **70–122B models run on 48GB with MLX 4bit or GGUF IQ3.** Large models are viable for
   quality-critical tasks where time is not the bottleneck.

5. **Bigger != better.** Qwen3.5-2B beats Qwen3.5-9B due to thinking overhead. MoE
   architectures consistently outperform dense models of similar active parameter count.

6. **MoE >> Dense for 48GB RAM.** Dense 27B requires ~40GB at 40K context, forcing context
   to 16K. MoE equivalent (35B-A3B) runs at 65K context with the same RAM.

---

## Recommended Models

| Use Case | Model | Reason |
|----------|-------|--------|
| Fast agent on M4 Pro | Qwen3-Coder-30B-A3B (MLX) | Best speed/quality ratio, 67s |
| Quality-critical tasks | Qwen3-Coder-Next 80B (GGUF IQ3_XXS) | 25/25 quality, 386s |
| Mac Mini M1 8GB | Qwen3.5-2B (MLX 4bit) | Only viable option at 8GB |
| Offline reserve | Devstral-2-24B (MLX 4bit) | 25/25 quality, no internet needed |

---

## Usage

```bash
# Run benchmark for a specific model
cd benchmark/
./run.sh --config configs/qwen3-coder-30b.json

# Run only text+reasoning categories
./run.sh --config configs/qwen3-coder-30b.json --categories text,reasoning

# Compare all results
./run.sh --compare

# Add a new model
cp configs/qwen3-coder-30b.json configs/<new-model>.json
# Edit: gguf_path, name, inference settings
./run.sh --config configs/<new-model>.json
```

## Requirements

- macOS with Apple Silicon (M1/M4)
- For GGUF: `llama-server` from llama.cpp
- For MLX: `mlx-lm` (`pip install mlx-lm`)
- Python 3.11+

---

## File Structure

```
benchmark/
├── run_benchmark.py    # Main benchmark runner
├── run.sh              # Shell wrapper
├── configs/            # Model configurations (JSON)
├── results/            # JSON result files per model/run
└── fixtures/           # Test fixtures (auto-generated)
```

## Result Format

Each result file is a JSON with the following structure:

```json
{
  "model": "qwen3-coder-30b",
  "backend": "llama.cpp",
  "timestamp": "2026-03-15T...",
  "tests": {
    "B1": {"status": "PASS", "time": 4.2, "quality": 3},
    ...
  },
  "summary": {
    "passed": 14,
    "total": 14,
    "quality_score": 21,
    "quality_max": 22,
    "total_time": 67
  }
}
```
