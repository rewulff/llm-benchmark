# LLM Benchmark Suite for Apple Silicon

Practical benchmark suite for local LLM inference on Apple Silicon. Tested on M4 Pro (48GB) and M1 Mac Mini (8GB).

After testing **30+ models** across text, reasoning, code, agent, and vision tasks — here's what actually works.

## TL;DR — What Should I Run?

### Text + Code Agent (Claude Code CLI backend)

| Your Hardware | Model | RAM | t/s | Pass Rate | Speed | Notes |
|---|---|---|---|---|---|---|
| **M4 Pro 48GB** (max quality) | Qwen3.5-35B-A3B think | ~20GB | ~45 | **5/5 (100%)** | 251s | Agent-Matrix Champion |
| **Any Mac 8GB+** (best value) | **Qwen3.5-4B think** | **2.5GB** | **~150** | **5/5 (100%)** | **266s** | **Same quality at 1/8 the RAM** |
| **Embedded / Edge** | Qwen3.5-2B think | 1.3GB | ~200 | 3/5 | 391s | Fast on simple tasks, weak on search |

### Vision / Document Analysis (Paperless-ngx style)

| Your Hardware | Model | RAM | VRAM (w/ KV-Q4) | t/s | Extraction | Validation |
|---|---|---|---|---|---|---|
| **Any Mac 8GB+** | **Qwen3-VL-4B Q4** | **2.3GB** | **~6GB** | **~42** | **5/5 (100%)** | **6/6 (100%)** |
| | Gemma 4 E4B Q4 | 5.5GB | ~8GB | ~30 | 2/5 | DQ |
| | Qwen3-VL-2B | 1.6GB | ~3GB | ~120 | 0/5 (agent) | 0/6 |

### Text-Only Tasks (smolagents / single-shot)

| Your Hardware | Model | RAM | t/s | Quality | Speed | How to Run |
|---|---|---|---|---|---|---|
| **M4 Pro 48GB** (fast) | Qwen3-Coder-30B-A3B | ~15GB | ~73 | 25/25 | **285s** | llama-server, GGUF Q4_K_M |
| **M4 Pro 48GB** (quality) | Qwen3-Coder-Next 80B | ~30GB | ~15 | **25/25** | 386s | GGUF IQ3_XXS |
| **16-24GB Mac** | Devstral-2-24B | ~14GB | ~25 | **25/25** | 483s | MLX 4bit |
| **M1/M2 8GB** | Qwen3.5-2B | ~1.5GB | ~200 | 25/25 | 150s | MLX 4bit |

## The Big Findings (April 2026)

### 1. Qwen3.5-4B is the Sleeper Hit

5/5 PASS on all agent tasks (bugfix, debug, refactor, search, landing page) with just **2.5GB RAM**. Only 15 seconds slower than the 10x larger 35B model. This is the new "budget workhorse" — the model you run when you don't want to waste API calls on trivial tasks.

### 2. Agentic Prompting Makes Small Vision Models Competitive

Qwen3-VL-4B (2.3GB!) achieves **100% on document extraction and validation** — but only with agentic self-validation prompting:

| Prompt Style | E1 Score | Turns |
|---|---|---|
| Simple ("extract and write") | 3/5 (60%) | 3 |
| **Agentic (extract → self-validate → correct)** | **5/5 (100%)** | 6 |

The self-validation step catches date errors, amount confusion (kWh vs EUR), and document type misclassification. The model corrects its own mistakes.

### 3. Thinking Helps Agent Tasks (Opposite of Text Tasks!)

In V2 text benchmarks (March), thinking mode hurt small models. In agent benchmarks (April), **thinking helps**:

| Model | Without Thinking | With Thinking |
|---|---|---|
| Qwen3.5-2B (text V2) | 14/14 | 10/14 — thinking hurts |
| Qwen3.5-4B (agent V2) | — | **5/5 — thinking helps** |
| Gemma E4B (agent V2) | 1/2 | **2/2 — thinking helps** |

**Hypothesis:** Agent tasks require multi-step planning. Thinking gives the model room to decide which tool to call next.

### 4. Q4 is the Sweet Spot for Vision

We tested Qwen3-VL-4B at four quantization levels:

| Quant | Size | E1 Score | Speed | Verdict |
|---|---|---|---|---|
| Q2_K | 1.6GB | TIMEOUT | — | Broken |
| **Q4_K_M** | **2.3GB** | **5/5** | **91s** | **Best** |
| Q8_0 | 4.0GB | 5/5 | 95s | Same quality, slightly slower |
| F16 | 7.5GB | 5/5 | 134s | 47% slower, no quality gain |

Higher quantization adds nothing for vision tasks. Q4 gives you 100% quality at minimum RAM.

### 5. 2B Models Can't Handle Agent Context

Claude Code injects ~30 tool definitions into every request. 2B models (Qwen3-VL-2B, Qwen3.5-2B for search) can't parse this and hallucinate random tool calls:

```
Turn 1: TaskStop(task_id="task_stop_123")     ← invented
Turn 2: TodoWrite("Check if task exists")     ← loop
Turn 3-15: TaskOutput → TodoWrite → repeat    ← stuck
```

The model never even tries to read the image or write the output. **4B is the minimum for Claude Code agent tasks.**

### 6. Gemma 4 — Great at Text, Bad at Vision Agent

| Task Type | Gemma 4 E4B | Verdict |
|---|---|---|
| Text (B1-B4, C1-C3) | 14/14 PASS | Excellent |
| Agent (D1, R1) | 3/5 | OK |
| **Vision (E1, E2)** | **2/5, DQ** | **Weak OCR, false positives** |

Gemma hallucinates dates ("2026-04-05" = today's date instead of reading the document), produces English placeholders for German text ("Utility Company" instead of the actual German company name), and over-corrects correct fields (disqualified for false-positive).

## Benchmark Versions

### Agent-Benchmark V2 (April 6, 2026) — NEW

7 test fixtures run in Docker (Claude Code CLI → llama-server on host):

| Test | Type | Sub-Checks | Vision? | What it Tests |
|---|---|---|---|---|
| B1 | Bugfix | 1 | No | Fix off-by-one, pytest must pass |
| LP1 | Generation | 1 | No | Create HTML landing page |
| D1 | Debug | 5 | No | Fix bug from pytest traceback |
| R1 | Refactor | 7 | No | Rename function across 3 files |
| S1 | Search | 5 | No | Find function usage (read-only, DQ on write) |
| E1 | Extraction | 5 + 3 vision-verify | **Yes** | Extract metadata from document image |
| E2 | Validation | 6 | **Yes** | Validate + correct AI-extracted metadata |

**Scoring:** Sub-check quality score (0-100%). PASS >= 80%. Core-check mechanism: if pytest fails, verdict is capped at FAIL regardless of score.

**Vision pipeline:** Image injected as base64 in initial user message via `--input-format stream-json`. Required because llama-server ignores images in tool_result content blocks.

**Full results + evaluation contract:** See `AGENT_BENCHMARKS.md` and `EVALUATION_CONTRACT_V2.md` in the benchmark directory.

### Screening V1 (April 4, 2026)

11 new models screened on 4 tests (B1/F1/G1/J1). Profile assignment:

| Model | Size | Profile | Recommendation |
|---|---|---|---|
| GLM-4.7-Flash | 17GB | AGENT-READY | Full test recommended |
| Nemotron-3-Nano 30B | 23GB | AGENT-READY | Full test recommended |
| GPT-OSS 20B | 11GB | AGENT-READY | Full test recommended |
| DeepSeek-R1-Qwen3-8B | 4.7GB | AGENT-READY | Full test recommended |
| Magistral Small 24B | 13GB | SINGLE-TASK | Only J1 pipelines |
| Meta Llama 3 8B | 4.6GB | SINGLE-TASK | Only simple pipelines |
| LFM2-24B-A2B | 16GB | SINGLE-TASK | Fast but F1 FAIL |
| Qwen3-14B Opus Distill | 8.4GB | AGENT-READY | With reservation |

**No model passed G1 (Multi-Constraint Reasoning)** — even with thinking mode enabled.

### Benchmark V3.1 (April 3, 2026)

19 tests via llama-server. First Gemma 4 benchmarks after llama.cpp GGUF support landed.

| Model | Architecture | t/s | Pass Rate | Quality | Time | Key Finding |
|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B** | 3B MoE | ~73 | **100% (19/19)** | **25/25** | **285s** | Undefeated champion |
| **Gemma 4 E4B** | 4.5B dense | ~30 | 94% (18/19) | **25/25** | 560s | Best Gemma, VLM-capable |
| Gemma 4 E2B (think) | 2.3B dense | ~67 | 94% (18/19) | 24/25 | 857s | Thinking +1 test, 3.7x slower |
| Gemma 4 E2B (no-think) | 2.3B dense | ~67 | 89% (17/19) | 23/25 | 234s | Fastest model overall |
| Qwen3.5-2B | 2B dense | ~200 | 84% (16/19) | 21/25 | 244s | Mac Mini champion |
| Gemma 4 26B-A4B | 4B MoE | ~30 | 73% (14/19) | **25/25** | 461s | Perfect text, broken agent (code-tag bug) |

**Gemma 4 31B (dense) was eliminated** — ~10 t/s generation speed, 13.7GB swap, impractical on M4 Pro 48GB.

### Benchmark V2 (March 15-16, 2026)

14 tests, 5 categories, quality score /25. See "Full Results" tables below.

### Benchmark V1 (February 27, 2026)

12 tests (code + text + reasoning). Legacy, English prompts.

## Full Results — V2 (14 Tests, M4 Pro 48GB)

### Large Models

| Model | Params | Backend | t/s | Pass /14 | Quality /25 | Time | Role |
|---|---|---|---|---|---|---|---|
| **Qwen3-Coder-30B** | 30B MoE (3B active) | MLX 4bit | ~73 | 14/14 | 21/22 | **67s** | Fast workhorse |
| **Qwen3-Coder-Next 80B** | 80B MoE (10B active) | GGUF IQ3_XXS | ~15 | 14/14 | **25/25** | 386s | Quality workhorse |
| Devstral-2-24B | 24B dense | MLX 4bit | ~25 | 14/14 | 25/25 | 483s | Reserve |

### Small Models

| Model | Params | Backend | t/s | Pass /14 | Quality /25 | Time | Notes |
|---|---|---|---|---|---|---|---|
| **Qwen3.5-2B** | 2B | MLX 4bit | ~200 | **14/14** | **25/25** | 150s | Mac Mini Champion |
| **Qwen3.5-4B /no_think** | 4B | MLX 4bit | ~150 | 14/14 | 25/25 | 273s | Must disable thinking |
| Gemma-3-4B | 4B | MLX 4bit | ~120 | 14/14 | 21/25 | 158s | Strongest alternative |

### Vision-Language Models (Document Analysis Benchmark)

| Model | Params | Size | t/s | VRAM (KV-Q4) | Extraction | Validation | Use Case |
|---|---|---|---|---|---|---|---|
| **Qwen3-VL-4B Q4** | 4B | 2.3GB | ~42 | ~6GB | **5/5 (100%)** | **6/6 (100%)** | **Document analysis agent** |
| Qwen3-VL-2B Q4 | 2B | 1.0GB | ~120 | ~3GB | 10/10 (one-shot) | — | Simple one-shot VLM extraction |
| Gemma 4 E4B Q4 | 4.5B | 3.8GB | ~30 | ~8GB | 2/5 | DQ | Not recommended for vision-agent |

**Key distinction:** Qwen3-VL-2B excels at **one-shot VLM extraction** (the current one-shot VLM pipeline). Qwen3-VL-4B excels at **agentic multi-turn vision** (v2 pipeline with self-validation). Different use cases, different winners.

## Key Lessons Learned

### 1. Disable Thinking Mode on Qwen3.5 (for text tasks)

Qwen3.5 models 4B+ have chain-of-thought enabled by default. For **text tasks**, this hurts:

| Model | With Thinking | Without Thinking |
|---|---|---|
| Qwen3.5-4B | 10/14 pass, 424s | **14/14 pass, 273s** |

**But enable it for agent tasks** — thinking helps with multi-step tool planning.

**Fix for llama.cpp:**
```bash
# Disable thinking (text/VLM extraction):
--chat-template-kwargs '{"enable_thinking": false}'

# Enable thinking (agent tasks):
--reasoning on
```

### 2. Bigger is NOT Better

| Model | Params | Agent Score | RAM |
|---|---|---|---|
| **Qwen3.5-4B think** | **4B** | **5/5 (100%)** | **2.5GB** |
| Qwen3.5-35B think | 35B | 5/5 (100%) | 20GB |
| Gemma 4 E4B think | 4.5B | 3/5 (60%) | 5.5GB |

The 4B model matches the 35B on every test. Knowledge distillation + MoE architecture makes parameter count irrelevant for practical tasks.

### 3. Vision Through Claude Code Requires Workarounds

llama-server's `/v1/messages` endpoint ignores image content blocks inside `tool_result` messages. Images must be injected into the **initial user message** via `--input-format stream-json`:

```bash
# Build JSON with base64 image in initial message
python3 -c "
import base64, json
with open('document.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
msg = {'type': 'user', 'message': {'role': 'user', 'content': [
    {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': b64}},
    {'type': 'text', 'text': 'Analyze this document...'}
]}}
print(json.dumps(msg))
" | claude -p --input-format stream-json --output-format stream-json --verbose
```

### 4. Inline Context > File Reads for Small Models

4B models get confused when they need to Read external JSON files for context. They enter grep-loops or confuse input/output files. **Embed context directly in the prompt:**

```
Bad:  "Read ppl_document_types.json for available types"  → model loops
Good: "Available types: Rechnung, Vertrag, Brief, ..."     → model uses it
```

### 5. Q4 Quantization is the Sweet Spot

Tested on Qwen3-VL-4B across Q2/Q4/Q8/F16:
- Q2: broken (timeouts)
- **Q4: 100% quality, fastest**
- Q8: same quality, 4% slower
- F16: same quality, 47% slower

Higher precision wastes RAM and time without quality improvement.

### 6. KV-Cache Quantization Works

`--cache-type-k q4_0 --cache-type-v q4_0` saves ~4GB KV-cache RAM with **no quality loss**. Essential for fitting models on 8GB hardware or increasing context window.

### 7. MLX vs. llama.cpp — Backend Barely Matters

Same model (Qwen3-Coder-30B-A3B), same tests, different backends:

| Backend | Pass | Quality | Time | t/s |
|---|---|---|---|---|
| MLX 4bit | 7/7 | — | 44.5s | ~80 |
| llama.cpp Q4_K_M | 7/7 | — | 47.6s | ~73 |

**~6% difference.** Pick whichever is easier to set up.

**MLX advantages:** 20-35% faster single-shot (Apple Metal native, unified memory optimized), better quantization options (TurboQuant, 3.5-bit KV).

**llama.cpp advantages:** KV-cache reuse across turns (critical for agent loops), N-gram speculative decoding, `--mmproj` for vision models, broader hardware support (CUDA, Vulkan, CPU).

**Our choice:** llama.cpp for production (agent loops, vision, cross-platform). MLX for quick single-shot benchmarks.

### 8. Ollama — We Tried, We Left

We used Ollama briefly (March-April 2026) as a workaround when llama.cpp GGUF support for Gemma 4 was broken (PR #21309 pending).

**Why we stopped:**
- **60-75% GPU utilization** — Ollama's Metal backend underperforms vs. llama-server (2-3x slower on same model)
- **No `--mmproj` support** — can't run vision models with separate projector
- **No KV-cache quantization** — wastes RAM
- **No fine-grained control** — can't set `--ubatch-size`, `--cache-type-k`, flash attention, etc.
- **Model storage bloat** — duplicates models in its own blob store

**When Ollama is still useful:** Quick model testing, zero-config setup, pulling models with one command. Just don't benchmark with it — the numbers are misleading.

**V3 Ollama results (for reference, April 3, 2026):**

| Model | Backend | Pass Rate | Avg/Test | Note |
|---|---|---|---|---|
| Gemma 4 E4B | Ollama | 91% (11/12) | 52s | Same model via llama-server: 94%, 29s |
| Gemma 4 E2B | Ollama | 91% (11/12) | 35s | Same model via llama-server: 89%, 12s |
| Nemotron Cascade 2 | Ollama | 83% (10/12) | 58s | Too slow for practical use |
| Gemma 4 26B-A4B | Ollama | 66% (8/12) | 70s | Agent code-tag bug persists |

These numbers are **not comparable** with llama-server results due to Ollama's GPU underutilization.

## Models That Don't Work

| Model | Why it Failed |
|---|---|
| Gemma 4 26B-A4B | Agent code-tag bug (`<code` not `<code>`), text-only tasks perfect |
| Gemma 4 31B (dense) | 10 t/s, 13.7GB swap on M4 Pro 48GB — impractical |
| GLM-4.5-REAP-82B | Architecture not supported in llama.cpp |
| NVFP4 models | NVIDIA TensorRT format, incompatible with MLX |
| Qwen3-VL-2B (as agent) | Too small for Claude Code tool definitions — hallucinates random tool calls |
| Opus-distilled models | Generate endlessly in Claude style, constant timeouts |

## Hardware

| Machine | Chip | RAM | Use Case |
|---|---|---|---|
| MacBook Pro | Apple M4 Pro | 48GB Unified | Primary benchmark host |
| Mac Mini | Apple M1 | 8GB Unified | Edge/IoT validation |

## Quick Start

```bash
git clone https://github.com/YOUR-USER/llm-benchmark.git
cd llm-benchmark

# Start a model
llama-server \
  --model ~/models/Qwen3.5-4B-Q4_K_M.gguf \
  --port 1235 --host 127.0.0.1 \
  --ctx-size 32768 --flash-attn on --jinja \
  --chat-template-kwargs '{"enable_thinking": false}'

# Run benchmark
./run.sh --config configs/qwen3.5-4b.json --external-server
```

## License

MIT. Benchmark code and results are freely available. Model weights are subject to their respective licenses.
