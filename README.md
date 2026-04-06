# LLM Benchmark Suite for Apple Silicon

Practical benchmark suite for local LLM inference on Apple Silicon. Tests code agents, vision models, and agentic document synthesis — all running on consumer hardware.

**Hardware:** M4 Pro 48GB (primary) | M1 Mac Mini 8GB (edge validation)
**Current version:** V4 Multi-Harness (April 6, 2026) — 15 models, 12 tests, 3 harnesses

## 1. TL;DR — What Should I Run?

### Code Agent (Claude Code CLI backend)

All models run via llama-server. Speeds on M4 Pro 48GB. Expect 3-4x slower on M1/M2 8GB.

| Hardware | Model | RAM | t/s | Score | CC Duration | Notes |
|---|---|---|---|---|---|---|
| **M4 Pro 48GB** (quality) | Qwen3.5-35B-A3B think | ~20GB | ~45 | **6/7** | 241s | Perfect on all CC-Agent tests |
| **Any Mac 8GB+** (best value) | **Qwen3.5-4B think** | **2.5GB** | **~150** | **6/7** | **230s** | **Same score at 1/8 the RAM** |
| M4 Pro 48GB (all-rounder) | Qwen3-VL-4B F16 | 7.5GB | ~28 | **11/12** | 492s | Only model that passes ALL harnesses |
| M4 Pro 48GB (fast text) | Qwen3-Coder-30B-A3B | ~15GB | ~73 | **6/7** | 491s | No thinking support, reliable |

### Vision / Document Analysis

Vision models need `--mmproj` for llama-server. F16 is required for OCR text extraction.

| Hardware | Model | RAM | t/s | VLM Score | Agent Vision | Notes |
|---|---|---|---|---|---|---|
| **M4 Pro 48GB** (OCR) | **Qwen3-VL-4B F16** | **7.5GB** | **~28** | **3/3** | **7/7 CC + 2/2 Vision** | **F16 required for text extraction** |
| Any Mac 8GB+ (non-OCR) | Qwen3-VL-4B Q4 | 2.3GB | ~42 | 2/3 | 6/7 CC + 2/2 Vision | Fails vl2 (OCR), everything else perfect |
| Edge only | Qwen3-VL-2B | 1.0GB | ~120 | 1/3 | 1/7 CC | Too small for agent context |

### smolagents / Agentic Synthesis

HuggingFace `ToolCallingAgent` with custom Python tools. `sa1` = classify + check relevance.

| Hardware | Model | RAM | t/s | sa1 | sa1 Duration | Notes |
|---|---|---|---|---|---|---|
| M4 Pro 48GB | Qwen3-Coder-30B-A3B | ~15GB | ~73 | PASS | 36s | Fastest sa1 |
| Any Mac 8GB+ | Qwen3.5-4B think | 2.5GB | ~150 | PASS | 40s | Budget option |
| M4 Pro 48GB | Qwen3-VL-4B Q4 | 2.3GB | ~42 | PASS | 25s | Also handles vision |
| M4 Pro 48GB | Qwen3.5-35B-A3B think | ~20GB | ~45 | PASS | 50s | Overkill for sa1 |
| M4 Pro 48GB | Qwen3-VL-4B F16 | 7.5GB | ~28 | PASS | 45s | All-rounder champion |

14/15 models pass sa1. Only failure: Qwen3-VL-2B (too small for tool definitions).

### Text-Only Tasks (single-shot, llama-server)

From V3.1 benchmark (19 tests):

| Hardware | Model | RAM | t/s | Pass Rate | Quality | Time |
|---|---|---|---|---|---|---|
| **M4 Pro 48GB** (fast) | Qwen3-Coder-30B-A3B | ~15GB | ~73 | 100% (19/19) | **25/25** | **285s** |
| **M4 Pro 48GB** (quality) | Qwen3-Coder-Next 80B | ~30GB | ~15 | 100% (19/19) | **25/25** | 386s |
| **16-24GB Mac** | Devstral-2-24B | ~14GB | ~25 | 100% (19/19) | **25/25** | 483s |
| **M1/M2 8GB** | Qwen3.5-2B | ~1.5GB | ~200 | 100% (14/14) | **25/25** | 150s |

---

## 2. The Big Findings

### 1. Qwen3.5-4B is the Sleeper Hit

5/5 PASS on all CC-Agent text tasks (bugfix, debug, refactor, search, landing page) with just **2.5GB RAM**. Only 11 seconds slower than the 10x larger 35B model. The "budget workhorse" for trivial agent tasks.

### 2. Agentic Prompting Makes Small Vision Models Competitive

Qwen3-VL-4B (2.3GB) achieves **100% on document extraction and validation** — but only with agentic self-validation prompting:

| Prompt Style | E1 Score | Turns |
|---|---|---|
| Simple ("extract and write") | 3/5 (60%) | 3 |
| **Agentic (extract, self-validate, correct)** | **5/5 (100%)** | 6 |

The self-validation step catches date errors, amount confusion (kWh vs EUR), and document type misclassification.

### 3. Thinking Helps Agent Tasks (Opposite of Text Tasks)

In text benchmarks, thinking mode hurt small models. In agent benchmarks, **thinking helps**:

- Qwen3.5-4B: think 5/5, nothink 4/5
- Qwen3.5-35B: think 5/5, nothink 4/5
- Gemma E4B: think 4/5, nothink 3/5
- For smolagents sa1: thinking makes no difference (all pass either way)

**Why:** Agent tasks require multi-step planning. Thinking gives the model room to decide which tool to call next. Simple classification tasks (sa1) don't benefit.

### 4. Q4 is the Vision Sweet Spot — Except for Text Extraction (Use F16)

Q4 quantization handles most vision tasks perfectly, but **fails on dense text extraction** (vl2). This is a hard quantization boundary:

| Quant | vl1 (describe) | vl2 (extract text) | vl3 (receipt) | E1 (agent extract) | E2 (agent validate) |
|---|---|---|---|---|---|
| Q4_K_M | PASS | **FAIL** | PASS | PASS | PASS |
| **F16** | PASS | **PASS** | PASS | PASS | PASS |

**Rule of thumb:** If your pipeline does OCR or exact text extraction, use F16 (7.5GB). For everything else, Q4 (2.3GB) is sufficient.

### 5. 2B Models Can't Handle Agent Context

Claude Code injects ~30 tool definitions into every request. 2B models (Qwen3-VL-2B, Qwen3.5-2B for search) hallucinate random tool calls (`TaskStop`, `TodoWrite`) instead of working on the task. **4B is the minimum for agent tasks.**

### 6. smolagents Works Out of the Box

14/15 models pass `sa1` on the first attempt with zero prompt tuning. The `ToolCallingAgent` talks directly to llama-server via OpenAI-compatible endpoint with custom Python tools.

`sa2` (multi-document synthesis) fails for **all** models (0/15) — this is a fixture design issue, not a model limitation.

### 7. Gemma 4 — Great at Text, Weak at Vision Agent

| Task Type | Gemma 4 E4B (think) | Notes |
|---|---|---|
| Text (V3.1, 19 tests) | 18/19 PASS | Excellent |
| CC-Agent (think) | 4/5 | R1 refactor fails consistently |
| Vision-Agent (E1, E2) | PARTIAL / DQ | Weak OCR, false-positive corrections |
| VLM Oneshot | 2/3 | vl2 (text extract) fails |

Gemma hallucinates dates, produces English placeholders for German text, and over-corrects correct fields (DQ for false-positive on E2).

---

## 3. Benchmark Suites

### V4 Multi-Harness (April 6, 2026) — Current

3 harnesses, 12 tests, 15 models, all running in Docker against llama-server on the host.

| Harness | Tests | Description |
|---|---|---|
| **CC-Agent** (7) | b1, d1, lp1, r1, s1, e1, e2 | Claude Code CLI — bugfix, debug, refactor, search, generation, vision extraction/validation |
| **smolagents** (2) | sa1, sa2 | HuggingFace ToolCallingAgent — document classification (sa1), multi-doc synthesis (sa2, broken) |
| **VLM Oneshot** (3) | vl1, vl2, vl3 | Single-shot image-to-text — describe document, extract text fields, extract receipt line items |

**Scoring:** Sub-check quality score (0-100%). PASS >= 80%. Core-check mechanism: if pytest fails, verdict is capped at FAIL.

**Vision pipeline:** Image injected as base64 in initial user message via `--input-format stream-json` (llama-server ignores images in `tool_result` content blocks).

### V3.1 Text (April 3, 2026)

19 tests via llama-server. Text + code + reasoning. First Gemma 4 benchmarks after llama.cpp GGUF support.

### Screening V1 (April 4, 2026)

11 new models screened on 4 tests (B1/F1/G1/J1). Profile assignment: AGENT-READY, SINGLE-TASK, or ELIMINATED. No model passed G1 (Multi-Constraint Reasoning).

### V2 / V1 (Legacy)

V2: 14 tests, 5 categories, quality score /25 (March 2026). V1: 12 tests, code + text + reasoning (February 2026).

---

## 4. Full Results — V4 Matrix

### Complete Model Matrix

Latest run per model+test. Score = PASS / eligible (DQ excluded from both).

#### Text/Code Models (7 eligible tests: b1, d1, lp1, r1, s1, sa1, sa2)

| Model | b1 | d1 | lp1 | r1 | s1 | sa1 | sa2 | Score |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| glm-4.7-flash | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 4/7 |
| **Qwen3-Coder-30B-A3B** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** |
| qwen3.5-2b-nothink | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | 4/7 |
| qwen3.5-2b-think | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | 3/7 |
| qwen3.5-35b-nothink | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 5/7 |
| **qwen3.5-35b-think** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** |
| qwen3.5-4b-nothink | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 5/7 |
| **qwen3.5-4b-think** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** |

#### Vision-Language Models (12 eligible tests: all)

| Model | b1 | d1 | lp1 | r1 | s1 | e1 | e2 | sa1 | sa2 | vl1 | vl2 | vl3 | Score |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| gemma-4-e2b-nothink | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 3/12 |
| gemma-4-e2b-think | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 5/12 |
| gemma-4-e4b-q4-nothink | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | 6/12 |
| gemma-4-e4b-q4-think | ✅ | ✅ | ✅ | ❌ | ✅ | ⚠️ | DQ | ✅ | ❌ | ✅ | ❌ | ✅ | 7/11 |
| qwen3-vl-2b | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 2/12 |
| **qwen3-vl-4b-f16** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | **11/12** |
| qwen3-vl-4b-q4 | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | 9/12 |

Legend: ✅ PASS | ❌ FAIL | ⚠️ PARTIAL | DQ = Disqualified | -- = not applicable (no vision/VLM capability)

**sa2 note:** 0/15 models pass sa2 (multi-document synthesis). This is a fixture design issue — the task is too complex for the current tool architecture. Not a model limitation.

### Performance Table

Total duration per harness group (sum of all tests in group, latest run).

#### Text/Code Models

| Model | RAM | t/s | CC-Agent 5 (s) | sa1 (s) | Total (s) |
|---|---|---|---|---|---|
| glm-4.7-flash | 17GB | ~20 | 847 | 45 | 937 |
| **Qwen3-Coder-30B-A3B** | ~15GB | ~73 | 491 | 36 | 552 |
| qwen3.5-2b-nothink | 1.3GB | ~200 | 105 | 15 | 135 |
| qwen3.5-2b-think | 1.3GB | ~200 | 110 | 20 | 145 |
| qwen3.5-35b-nothink | ~20GB | ~45 | 190 | 30 | 255 |
| **qwen3.5-35b-think** | ~20GB | ~45 | 241 | 50 | 331 |
| qwen3.5-4b-nothink | 2.5GB | ~150 | 306 | 30 | 371 |
| **qwen3.5-4b-think** | 2.5GB | ~150 | **230** | 40 | 315 |

#### Vision-Language Models

| Model | RAM | t/s | CC-Agent 5 (s) | Vision 2 (s) | sa1 (s) | VLM 3 (s) | Total (s) |
|---|---|---|---|---|---|---|---|
| gemma-4-e2b-nothink | 4.6GB | ~67 | 256 | 366 | 186 | 15 | 1068 |
| gemma-4-e2b-think | 4.6GB | ~67 | 311 | 376 | 186 | 15 | 1133 |
| gemma-4-e4b-q4-nothink | 5.5GB | ~30 | 255 | 90 | 186 | 20 | 796 |
| gemma-4-e4b-q4-think | 5.5GB | ~30 | 546 | 185 | 50 | 35 | 862 |
| qwen3-vl-2b | 1.0GB | ~120 | 887 | 85 | 10 | 25 | 1017 |
| **qwen3-vl-4b-f16** | 7.5GB | ~28 | 492 | 200 | 45 | 45 | 812 |
| qwen3-vl-4b-q4 | 2.3GB | ~42 | 431 | 180 | 25 | 35 | 696 |

**CC-Agent 5** = b1 + d1 + lp1 + r1 + s1 (code tasks only). **Vision 2** = e1 + e2 (agent vision). **VLM 3** = vl1 + vl2 + vl3 (oneshot vision). Total includes sa2 durations not shown separately.

---

## 5. Key Lessons Learned

### Thinking Mode: Enable for Agents, Disable for Text

Qwen3.5 models have chain-of-thought enabled by default. For **text tasks**, this hurts (4B: 10/14 with thinking vs 14/14 without). For **agent tasks**, it helps (+1-2 tests). For smolagents sa1, it makes no difference.

```bash
# Disable thinking (text/VLM extraction):
--chat-template-kwargs '{"enable_thinking": false}'

# Enable thinking (agent tasks):
--reasoning on
```

### Vision Through Claude Code Requires Workarounds

llama-server's `/v1/messages` endpoint ignores image content blocks inside `tool_result` messages. Images must be injected into the **initial user message** via `--input-format stream-json`:

```bash
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

### Inline Context > File Reads for Small Models

4B models enter grep-loops when asked to read external JSON files for context. Embed context directly in the prompt instead.

### KV-Cache Quantization Works

`--cache-type-k q4_0 --cache-type-v q4_0` saves ~4GB KV-cache RAM with **no quality loss**. Essential for fitting vision models on 8GB hardware.

### MLX vs. llama.cpp — Backend Barely Matters

Same model, same tests: MLX ~80 t/s vs llama.cpp ~73 t/s (~6% difference). **Our choice:** llama.cpp for production (KV-cache reuse, vision via `--mmproj`, speculative decoding). MLX for quick single-shot benchmarks.

### Ollama — We Tried, We Left

60-75% GPU utilization, no `--mmproj`, no KV-cache quantization, no fine-grained control. Numbers are misleading compared to llama-server. Useful only for zero-config model testing.

---

## 6. Models That Don't Work

| Model | Why it Failed |
|---|---|
| Gemma 4 26B-A4B | Agent code-tag bug (`<code` not `<code>`), text-only tasks perfect |
| Gemma 4 31B (dense) | 10 t/s, 13.7GB swap on M4 Pro 48GB — impractical |
| GLM-4.5-REAP-82B | Architecture not supported in llama.cpp |
| NVFP4 models | NVIDIA TensorRT format, incompatible with MLX |
| Qwen3-VL-2B (as agent) | Too small for Claude Code tool definitions — hallucinates random tool calls |
| Opus-distilled models | Generate endlessly in Claude style, constant timeouts |

---

## 7. Hardware

| Machine | Chip | RAM | Use Case |
|---|---|---|---|
| MacBook Pro | Apple M4 Pro | 48GB Unified | Primary benchmark host |
| Mac Mini | Apple M1 | 8GB Unified | Edge/IoT validation |

## Quick Start

```bash
git clone https://github.com/rewulff/llm-benchmark.git
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
