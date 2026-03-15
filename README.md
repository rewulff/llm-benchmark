# LLM Benchmark Suite for Apple Silicon

Practical benchmark suite for local LLM inference on Apple Silicon. Tested on M4 Pro (48GB) and M1 Mac Mini (8GB).

If you're trying to figure out which model to run locally — this repo has the answers we found after testing 15+ models in a single weekend.

## TL;DR — What Should I Run?

| Your Hardware | Model | RAM | Quality | Speed | How to Run |
|---|---|---|---|---|---|
| **M4 Pro 48GB** (fast) | Qwen3-Coder-30B-A3B | ~15GB | 21/25 | **67s** | MLX 4bit |
| **M4 Pro 48GB** (quality) | Qwen3-Coder-Next 80B | ~30GB | **25/25** | 386s | GGUF IQ3_XXS, `temp=1.0 top_p=0.95 top_k=40` |
| **16-24GB Mac** | Devstral-2-24B | ~14GB | **25/25** | 483s | MLX 4bit |
| **M1/M2 8GB** | Qwen3.5-2B | ~1.5GB | **25/25** | 150s | MLX 4bit |
| **Any Mac** (ultra-fast) | Qwen3.5-0.8B | ~0.5GB | 20/25 | **37s** | MLX 4bit |

## The Surprising Finding

**Qwen3.5-2B achieves the same quality score (25/25) as 80B models.** This 2-billion parameter model, running in 1.5GB RAM, matches our 30GB quality champion on every test. The secret: Alibaba's knowledge distillation from larger Qwen3.5 models (122B, 397B) into the small ones.

But there's a catch: **Thinking mode ruins everything.** Qwen3.5-4B and 9B have chain-of-thought enabled by default. They waste their token budget "thinking" and then timeout before answering. Disabling it (`/no_think` system prompt or `--chat-template-kwargs '{"enable_thinking": false}'`) fixes this completely:

| Model | With Thinking | Without Thinking |
|---|---|---|
| Qwen3.5-4B | 10/14 pass, 424s | **14/14 pass, 273s** |
| Qwen3.5-9B | 9/14 pass, 852s | 11/14 pass, 712s |

The 2B model has thinking disabled by default — which is why it "beats" the larger models out of the box.

## What We Tested

15+ models across MLX and llama.cpp backends. All tests in English, all on Apple Silicon.

### Full Results — M4 Pro 48GB

| Model | Params | Backend | Pass /14 | Quality /25 | Time | Notes |
|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B-A3B** | 30B MoE (3B active) | MLX 4bit | 14/14 | 21/22 | **67s** | Best speed/quality ratio |
| **Qwen3-Coder-Next 80B** | 80B MoE (10/512 experts) | GGUF IQ3_XXS | 14/14 | **25/25** | 386s | Perfect quality, official settings critical |
| **Devstral-2-24B** | 24B dense | MLX 4bit | 14/14 | **25/25** | 483s | Mistral's coding model, excellent |
| **Qwen3.5-2B** | 2B dense | MLX 4bit | 14/14 | **25/25** | 150s | Distillation miracle |
| **Qwen3.5-2B** | 2B dense | GGUF Q4_K_M | 13/14 | 21/25 | **125s** | GGUF faster! Needs `enable_thinking: false` |
| Qwen3.5-4B `/no_think` | 4B dense | MLX 4bit | 14/14 | 25/25 | 273s | Must disable thinking |
| Qwen3.5-0.8B | 0.8B dense | MLX 4bit | 12/14 | 20/25 | 37s | Impressive for 500MB |
| Qwen3.5-122B-A10B | 122B MoE (10B active) | MLX 4bit | 7/7* | — | 69s | *V1 tests only, runs on 48GB with 4GB swap |
| Tongyi-DeepResearch-30B | 30B MoE | GGUF Q4_K_M | 12/14 | 13/25 | 495s | Good at log correlation, bad at code/security |
| Qwen3.5-9B `/no_think` | 9B dense | MLX 4bit | 11/14 | 18/25 | 712s | Paradoxically worse than 4B |
| GLM-4.7-Flash | 9B dense | MLX 4bit | 10/14 | 12/25 | 642s | Reddit hype doesn't hold up in deep tests |
| Huihui-Qwen3.5-27B-Opus | 27B dense | MLX 4bit | 8/14 | 2/4 | 602s | Claude-style verbosity causes timeouts |
| DeepSeek-Coder-V2-Lite | 16B MoE | GGUF Q8_0 | 5/7* | — | 88s | *V1 tests only |
| GLM-4.5-REAP-82B | 82B MoE (12B active) | GGUF IQ3_XS | 0/14 | — | — | llama.cpp incompatible with glm4_moe |

### Mac Mini M1 8GB

| Model | Pass /14 | Quality /25 | Time |
|---|---|---|---|
| Qwen3.5-2B MLX 4bit | 12/14 | 21/25 | 563s |

3.8x slower than M4 Pro, but fully functional. DMARC security analysis (E2) passes perfectly.

### MLX vs. llama.cpp — Same Model Comparison

Qwen3-Coder-30B-A3B, English text+reasoning tests:

| Backend | Pass | Quality | Time |
|---|---|---|---|
| MLX 4bit | 7/7 | — | 44.5s |
| llama.cpp Q4_K_M | 7/7 | — | 47.6s |

**~6% difference.** Backend choice barely matters for quality. Pick whichever is easier to set up.

## Key Lessons Learned

### 1. Disable Thinking Mode on Qwen3.5

Qwen3.5 models 4B+ have chain-of-thought enabled by default. This causes:
- 3-10x slower responses (tokens wasted on `<think>...</think>` blocks)
- Timeouts on complex prompts
- Lower pass rates despite theoretically higher capability

**Fix for llama.cpp:**
```bash
llama-server --jinja --chat-template-kwargs '{"enable_thinking": false}' --model qwen3.5-XB.gguf
```

**Fix for MLX:** Use `/no_think` system prompt:
```json
{"role": "system", "content": "/no_think"}
```

**Fix for Ollama:**
```python
ollama.chat(model='qwen3.5:2b', messages=[...], think=False)
```

Qwen3.5-2B has thinking disabled by default — no fix needed.

### 2. Official Settings Matter

Qwen3-Coder-Next 80B scored 24/25 with default settings but **25/25 with official settings**:

| Setting | Source | Quality |
|---|---|---|
| `temp=0.7, top_p=0.8` | Our default | 24/25 |
| `temp=1.0, top_p=0.95, top_k=40` | Official `generation_config.json` | **25/25** |

Always check `generation_config.json` on HuggingFace before benchmarking.

### 3. Bigger is NOT Better

| Model | Params | Quality | Time |
|---|---|---|---|
| Qwen3.5-2B | 2B | **25/25** | **150s** |
| Qwen3.5-4B `/no_think` | 4B | 25/25 | 273s |
| Qwen3.5-9B `/no_think` | 9B | 18/25 | 712s |

The 2B model is the best small model we tested. Knowledge distillation from 122B/397B teachers gives it capabilities far beyond its parameter count.

### 4. MoE Wins on Limited RAM

With 48GB unified memory:
- Dense 27B at Q4 = ~17GB model + limited context
- MoE 35B-A3B at Q4 = ~20GB model but only 3B active = faster inference + longer context
- MoE 80B at IQ3 = ~30GB model but only 10B active = great quality with headroom

### 5. Models That Don't Work

| Model | Why it Failed |
|---|---|
| GLM-4.5-REAP-82B (GGUF) | `glm4_moe` architecture not supported in llama.cpp 8350 |
| NVFP4 quantized models | NVIDIA TensorRT format, incompatible with MLX despite llmfit listing them |
| Moonlight-16B-A3B | Broken tokenizer (removed `bytes_to_unicode` in newer transformers) |
| Opus-distilled models (Huihui) | Generate endlessly in Claude style, 5/14 timeouts |

### 6. RAM Pressure is Real

Running a 122B model while downloading other models simultaneously caused **36GB swap** and nearly crashed macOS. Always:
- Run one model at a time
- `purge` between model switches
- Monitor with Activity Monitor — green memory pressure = safe

## Benchmark Methodology

### V2 — 14 Tests, Quality Scoring /25 (current)

All prompts in English. Each test measures specific capabilities:

| Category | Test | What it Measures | Quality Points |
|---|---|---|---|
| **Text** | B1 Summary | Concise summarization | PASS/FAIL |
| | B2 Log Analysis | Structured report from Proxmox logs | PASS/FAIL |
| | B3 Statistics | Anomaly detection in sales data | PASS/FAIL |
| | B4 Code Review | Finding SQL injection, eval(), bare except | 3 checks |
| **Reasoning** | C1 Config Diff | YAML comparison (8 differences) | PASS/FAIL |
| | C2 Decision Matrix | Structured evaluation of 3 options | PASS/FAIL |
| | C3 Root Cause | Causal chain from symptoms to fix | PASS/FAIL |
| **Hard** | D1 Subtle Bug | Race condition in threading code | 2 checks |
| | D2 Instruction Following | Exact format constraints (5 items, no "lightweight", end phrase) | 4 checks |
| | D3 Multi-Step Calc | RAM calculation with 50% rule | PASS/FAIL |
| | D4 Long Context | Find hidden detail in ~3K token config | PASS/FAIL |
| | D5 Nuanced Review | 5 code issues ranked by severity | 5 checks |
| **Deep** | E1 Correlated Logs | Causal chains across PVE maintenance phases | 6 checks |
| | E2 DMARC Analysis | Email security: spoofing, SPF, DKIM, policy | 7 checks |

Total quality points: 25 (from D4, D5, D2 checks + E1 + E2 scores).

### V1 — 7 Tests (legacy, Feb 2026)

Tests B1-B4 + C1-C3 only. PASS/FAIL, no quality scoring. German prompts (switched to English in V2).

## Quick Start

```bash
# Clone this repo
git clone https://github.com/your-user/llm-benchmark.git
cd llm-benchmark

# Install MLX (Apple Silicon only)
python3 -m venv .venv && .venv/bin/pip install mlx-lm

# Start a model server
.venv/bin/python3 -m mlx_lm.server \
  --model mlx-community/Qwen3.5-2B-4bit \
  --port 1235 --host 127.0.0.1

# Run benchmark against it
./run.sh --config configs/qwen3.5-2b.json --external-server --categories text,reasoning,hard,deep

# Or with llama.cpp (GGUF models)
./run.sh --config configs/qwen3-coder-30b.json --categories text,reasoning,hard,deep
```

### Adding Your Own Model

1. Create a config in `configs/your-model.json`:
```json
{
  "name": "your-model",
  "model_id": "mlx-community/Your-Model-4bit",
  "gguf_path": "path/to/model.gguf",
  "ctx_size": 32768,
  "no_think": true,
  "inference": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 4096}
}
```

2. For MLX: set `model_id` and use `--external-server`
3. For GGUF: set `gguf_path` (server starts automatically)
4. For thinking models: add `"no_think": true` and `"jinja": true, "chat_template_kwargs": "{\"enable_thinking\": false}"`

## Hardware Used

| Machine | Chip | RAM | Use Case |
|---|---|---|---|
| MacBook Pro | Apple M4 Pro | 48GB Unified | Primary benchmark host |
| Mac Mini | Apple M1 | 8GB Unified | Edge/IoT validation |

## License

MIT. Benchmark code and results are freely available. Model weights are subject to their respective licenses.
