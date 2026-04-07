# LLM Benchmark Suite for Apple Silicon

Practical benchmark suite for local LLM inference on Apple Silicon. Tests code agents, vision models, and agentic document synthesis — all running on consumer hardware.

**Hardware:** M4 Pro 48GB (primary) | M1 Mac Mini 8GB (edge validation)
**Current version:** V4 Multi-Harness (April 7, 2026) — 32 models, 12 tests, 3 harnesses

## 1. TL;DR — What Should I Run?

### Code Agent (Claude Code CLI backend)

All models run via llama-server. Speeds on M4 Pro 48GB. Expect 3-4x slower on M1/M2 8GB.

| Hardware | Model | RAM | t/s | Score | CC Duration | Notes |
|---|---|---|---|---|---|---|
| **M4 Pro 48GB** (quality) | Qwen3.5-35B-A3B think | ~20GB | ~45 | **6/7** | 241s | Perfect on all CC-Agent tests |
| **M4 Pro 48GB** (best value mid-range) | **Qwen3.5-9B think** | **6GB** | **~60** | **6/7** | **~60s avg** | **New sweet spot — same score, more headroom** |
| **Any Mac 8GB+** (best value) | **Qwen3.5-4B think** | **2.5GB** | **~150** | **6/7** | **230s** | **Same score at 1/8 the RAM** |
| M4 Pro 48GB (all-rounder) | Qwen3-VL-4B F16 | 7.5GB | ~28 | **11/12** | 492s | Only model that passes ALL harnesses |
| M4 Pro 48GB (fast text) | Qwen3-Coder-30B-A3B | ~15GB | ~73 | **6/7** | 491s | No thinking support, reliable |

### Vision / Document Analysis

Vision models need `--mmproj` for llama-server. Text extraction capability depends on model architecture (see Finding 4).

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
| M4 Pro 48GB | Carnice-9B | ~6GB | ~50 | PASS | ~40s | Agentic specialist, 6/7 CC |
| M4 Pro 48GB | Nemotron-3-Nano-30B | ~23GB | ~30 | PASS | ~45s | Mamba architecture, 6/7 CC |
| M4 Pro 48GB | Qwen3.5-35B-A3B think | ~20GB | ~45 | PASS | 50s | Overkill for sa1 |
| M4 Pro 48GB | Qwen3-VL-4B F16 | 7.5GB | ~28 | PASS | 45s | All-rounder champion |

27/32 models pass sa1. Failures: Qwen3-VL-2B (too small), DeepSeek-R1-Qwen3-8B, granite-3.3-8b, Bonsai-8B (server fail), Qwen3.5-27B-think.

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

### 4. Text Extraction Depends on Model Architecture, Not Quantization

~~Previously reported as "F16 required for text extraction."~~ The April 7 night run (17 new models) corrected this: **text extraction (vl2) is architecture-dependent, not quantization-dependent.**

| Model | Quant | vl2 (extract text) | Notes |
|---|---|---|---|
| InternVL3-2B | Q4 | **PASS** | Architecture handles OCR at Q4 |
| SmolVLM2-2.2B | Q4 | **PASS** | Architecture handles OCR at Q4 |
| Qianfan-OCR | Q4 | **PASS** | OCR specialist, passes at Q4 |
| Qwen3-VL-4B F16 | F16 | **PASS** | F16 helps Qwen-VL specifically |
| Qwen3-VL-4B Q4 | Q4 | **FAIL** | Qwen-VL needs F16 for OCR |
| Gemma 4 E4B | Q4 | **FAIL** | Architecture limitation |

**Rule of thumb:** Text extraction depends on model architecture (InternVL, OCR specialists pass at Q4; Gemma/Qwen-VL fail even at Q4). F16 helps Qwen-VL specifically but is not a universal rule.

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

3 harnesses, 12 tests, 32 models, all running in Docker against llama-server on the host.

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

### 4.1 Model Specs

Central reference for all 32 models tested. All run via llama-server on M4 Pro 48GB.

| Model | Params | Arch | Quant | RAM | t/s | ctx | Thinking | Vision | Base |
|---|---|---|---|---|---|---|---|---|---|
| Bonsai-8B | 8B | dense | Q1_0 | 2 GB | -- | 32k | -- | -- | Qwen3 |
| Carnice-9B | 9B | dense | Q4_K_M | 6 GB | ~50 | 32k | nothink | -- | Qwen3.5-9B |
| DeepSeek-R1-Qwen3-8B | 8B | dense | Q4_K_M | 5 GB | ~40 | 64k | reason | -- | Qwen3 |
| gemma-4-e2b-nothink | 2.3B | dense | Q8_0 | 4.6 GB | ~67 | 32k | nothink | mmproj | Gemma 4 |
| gemma-4-e2b-think | 2.3B | dense | Q8_0 | 4.6 GB | ~67 | 32k | think | mmproj | Gemma 4 |
| gemma-4-e4b-q4-nothink | 4.5B | dense | Q4_K_M | 5.5 GB | ~30 | 32k | nothink | mmproj | Gemma 4 |
| gemma-4-e4b-q4-think | 4.5B | dense | Q4_K_M | 5.5 GB | ~30 | 32k | think | mmproj | Gemma 4 |
| GLM-4.7-Flash | 30B | dense | Q4_K | 17 GB | ~20 | 32k | -- | -- | GLM |
| GLM-OCR | ~4B | dense | Q8_0 | 9 GB | ~60 | 8k | -- | mmproj | GLM |
| GPT-OSS-20B | 20B | dense | Q4_K_M | 12 GB | ~25 | 128k | reason | -- | GPT-OSS |
| granite-3.3-8b | 8B | dense | Q4_K_M | 5 GB | ~45 | 128k | reason | -- | Granite |
| InternVL3-2B | 2B | dense | Q4_K_M | 3 GB | ~50 | 8k | -- | mmproj | InternVL3 |
| Nemotron-3-Nano-30B | 30B | MoE (3B) | Q4_K_M | 18 GB | ~30 | 32k | reason | -- | Mamba-SSM |
| Nemotron-Cascade-2-30B | 30B | MoE (3B) | Q4_K_M | 25 GB | ~20 | 32k | reason | -- | Mamba-SSM |
| phi-4-mini | 3.8B | dense | Q4_K_M | 3 GB | ~80 | 128k | -- | -- | Phi-4 |
| Qianfan-OCR | ~4B | dense | Q4_K_M | 5 GB | ~50 | 8k | reason | mmproj | InternVL |
| Qwen3-8B | 8B | dense | Q5_K_M | 7 GB | ~40 | 32k | nothink | -- | Qwen3 |
| Qwen3-Coder-30B-A3B | 30B | MoE (3B) | Q4_K_M | 20 GB | ~73 | 32k | -- | -- | Qwen3 |
| Qwen3-VL-2B | 2B | dense | Q4_K_M | 3.5 GB | ~120 | 32k | -- | mmproj | Qwen3-VL |
| Qwen3-VL-4B F16 | 4B | dense | F16 | 9 GB | ~28 | 32k | -- | mmproj | Qwen3-VL |
| Qwen3-VL-4B Q4 | 4B | dense | Q4_K_M | 5.5 GB | ~42 | 32k | -- | mmproj | Qwen3-VL |
| Qwen3.5-2B nothink | 2B | dense | Q4_K_M | 1.3 GB | ~200 | 32k | nothink | -- | Qwen3.5 |
| Qwen3.5-2B think | 2B | dense | Q4_K_M | 1.3 GB | ~200 | 32k | reason | -- | Qwen3.5 |
| Qwen3.5-4B nothink | 4B | dense | Q4_K_M | 2.5 GB | ~150 | 32k | nothink | -- | Qwen3.5 |
| Qwen3.5-4B think | 4B | dense | Q4_K_M | 2.5 GB | ~150 | 32k | reason | -- | Qwen3.5 |
| Qwen3.5-9B nothink | 9B | dense | Q4_K_M | 6 GB | ~60 | 32k | nothink | -- | Qwen3.5 |
| Qwen3.5-9B think | 9B | dense | Q4_K_M | 6 GB | ~60 | 32k | reason | -- | Qwen3.5 |
| Qwen3.5-27B nothink | 27B | dense | Q5_K_M | 19 GB | ~25 | 32k | nothink | -- | Qwen3.5 |
| Qwen3.5-27B think | 27B | dense | Q5_K_M | 19 GB | ~25 | 32k | reason | -- | Qwen3.5 |
| Qwen3.5-35B-A3B nothink | 35B | MoE (3B) | Q4_K_M | 20 GB | ~45 | 32k | nothink | -- | Qwen3.5 |
| Qwen3.5-35B-A3B think | 35B | MoE (3B) | Q4_K_M | 20 GB | ~45 | 32k | reason | -- | Qwen3.5 |
| SmolVLM2-2.2B | 2.2B | dense | Q4_K_M | 3 GB | ~55 | 16k | -- | mmproj | SmolVLM2 |

**Legend:** t/s = tokens/second (generation). ctx = max context window. Thinking: `reason` = chain-of-thought enabled, `nothink` = explicitly disabled, `think` = thinking variant. Vision: `mmproj` = multimodal projector required for llama-server. Arch: `MoE (3B)` = Mixture-of-Experts with 3B active parameters.

### 4.2 Test Results Matrix

Latest run per model+test. Score = PASS / eligible (DQ excluded from both).

#### Text/Code Models (7 eligible tests: b1, d1, lp1, r1, s1, sa1, sa2)

| Model | RAM | b1 | d1 | lp1 | r1 | s1 | sa1 | sa2 | Score | Total (s) | Avg (s/test) |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---:|---:|
| Bonsai-8B | 2 GB | -- | -- | -- | -- | -- | -- | -- | 0/7 | -- | -- |
| **Carnice-9B** | 6 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** | 340 | 49 |
| DeepSeek-R1-Qwen3-8B | 5 GB | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 0/7 | 1437 | 205 |
| GLM-4.7-Flash | 17 GB | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 4/7 | 937 | 134 |
| GPT-OSS-20B | 12 GB | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 4/7 | 426 | 61 |
| granite-3.3-8b | 5 GB | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 0/7 | 857 | 122 |
| **Nemotron-3-Nano-30B** | 18 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** | 916 | 131 |
| Nemotron-Cascade-2-30B | 25 GB | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 4/7 | 847 | 121 |
| phi-4-mini | 3 GB | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | 1/7 | 116 | 17 |
| **Qwen3-Coder-30B-A3B** | 20 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** | 552 | 79 |
| Qwen3-8B | 7 GB | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | 3/7 | 706 | 101 |
| Qwen3.5-2B nothink | 1.3 GB | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | 4/7 | 135 | 19 |
| Qwen3.5-2B think | 1.3 GB | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | 3/7 | 145 | 21 |
| **Qwen3.5-4B nothink** | 2.5 GB | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 5/7 | 371 | 53 |
| **Qwen3.5-4B think** | 2.5 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** | 315 | 45 |
| **Qwen3.5-9B nothink** | 6 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** | 396 | 57 |
| **Qwen3.5-9B think** | 6 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** | 471 | 67 |
| Qwen3.5-27B nothink | 19 GB | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | 5/7 | 1172 | 167 |
| Qwen3.5-27B think | 19 GB | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 4/7 | 1323 | 189 |
| Qwen3.5-35B-A3B nothink | 20 GB | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | 5/7 | 255 | 36 |
| **Qwen3.5-35B-A3B think** | 20 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | **6/7** | 331 | 47 |

#### Vision-Language Models (12 eligible tests: b1, d1, lp1, r1, s1, e1, e2, sa1, sa2, vl1, vl2, vl3)

| Model | RAM | b1 | d1 | lp1 | r1 | s1 | e1 | e2 | sa1 | sa2 | vl1 | vl2 | vl3 | Score | Total (s) | Avg (s/test) |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---:|---:|
| gemma-4-e2b-nothink | 4.6 GB | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 3/12 | 1068 | 89 |
| gemma-4-e2b-think | 4.6 GB | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 5/12 | 1133 | 94 |
| gemma-4-e4b-q4-nothink | 5.5 GB | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | 6/12 | 796 | 66 |
| gemma-4-e4b-q4-think | 5.5 GB | ✅ | ✅ | ✅ | ❌ | ✅ | ⚠️ | DQ | ✅ | ❌ | ✅ | ❌ | ✅ | 7/11 | 862 | 78 |
| GLM-OCR | 9 GB | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | 1/12 | 401 | 33 |
| InternVL3-2B | 3 GB | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | 2/12 | 251 | 21 |
| Qianfan-OCR | 5 GB | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | 2/12 | 876 | 73 |
| Qwen3-VL-2B | 3.5 GB | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 2/12 | 1017 | 85 |
| **Qwen3-VL-4B F16** | 9 GB | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | **11/12** | 812 | 68 |
| Qwen3-VL-4B Q4 | 5.5 GB | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | 9/12 | 696 | 58 |
| SmolVLM2-2.2B | 3 GB | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | 2/12 | 121 | 10 |

**Legend:** ✅ PASS | ❌ FAIL | ⚠️ PARTIAL | DQ = Disqualified (excluded from eligible count) | -- = server failure, no data

**sa2 note:** 0/32 models pass sa2 (multi-document synthesis). This is a fixture design issue -- the task is too complex for the current tool architecture. Not a model limitation.

**Avg (s/test)** = Total duration / 7 (text) or / 12 (VLM). Includes time spent on failed tests.

### 4.3 Performance Ranking

Sorted by **Efficiency Score** = PASS count / RAM (GB). Higher is better -- more passes per gigabyte of memory.

#### Text/Code Models

| Rank | Model | RAM | Score | Total (s) | Efficiency (PASS/GB) |
|---:|---|---|:--:|---:|---:|
| 1 | Qwen3.5-2B nothink | 1.3 GB | 4/7 | 135 | 3.08 |
| 2 | **Qwen3.5-4B think** | 2.5 GB | **6/7** | 315 | **2.40** |
| 3 | Qwen3.5-2B think | 1.3 GB | 3/7 | 145 | 2.31 |
| 4 | Qwen3.5-4B nothink | 2.5 GB | 5/7 | 371 | 2.00 |
| 5 | **Qwen3.5-9B nothink** | 6 GB | **6/7** | 396 | **1.00** |
| 6 | **Qwen3.5-9B think** | 6 GB | **6/7** | 471 | **1.00** |
| 7 | **Carnice-9B** | 6 GB | **6/7** | 340 | **1.00** |
| 8 | Qwen3-8B | 7 GB | 3/7 | 706 | 0.43 |
| 9 | phi-4-mini | 3 GB | 1/7 | 116 | 0.33 |
| 10 | **Nemotron-3-Nano-30B** | 18 GB | **6/7** | 916 | 0.33 |
| 11 | GPT-OSS-20B | 12 GB | 4/7 | 426 | 0.33 |
| 12 | **Qwen3-Coder-30B-A3B** | 20 GB | **6/7** | 552 | 0.30 |
| 13 | **Qwen3.5-35B-A3B think** | 20 GB | **6/7** | 331 | 0.30 |
| 14 | Qwen3.5-27B nothink | 19 GB | 5/7 | 1172 | 0.26 |
| 15 | Qwen3.5-35B-A3B nothink | 20 GB | 5/7 | 255 | 0.25 |
| 16 | GLM-4.7-Flash | 17 GB | 4/7 | 937 | 0.24 |
| 17 | Qwen3.5-27B think | 19 GB | 4/7 | 1323 | 0.21 |
| 18 | Nemotron-Cascade-2-30B | 25 GB | 4/7 | 847 | 0.16 |
| 19 | Bonsai-8B | 2 GB | 0/7 | -- | 0.00 |
| 20 | DeepSeek-R1-Qwen3-8B | 5 GB | 0/7 | 1437 | 0.00 |
| 21 | granite-3.3-8b | 5 GB | 0/7 | 857 | 0.00 |

#### Vision-Language Models

| Rank | Model | RAM | Score | Total (s) | Efficiency (PASS/GB) |
|---:|---|---|:--:|---:|---:|
| 1 | **Qwen3-VL-4B Q4** | 5.5 GB | 9/12 | 696 | **1.64** |
| 2 | gemma-4-e4b-q4-think | 5.5 GB | 7/11 | 862 | 1.27 |
| 3 | **Qwen3-VL-4B F16** | 9 GB | **11/12** | 812 | **1.22** |
| 4 | gemma-4-e4b-q4-nothink | 5.5 GB | 6/12 | 796 | 1.09 |
| 5 | gemma-4-e2b-think | 4.6 GB | 5/12 | 1133 | 1.09 |
| 6 | SmolVLM2-2.2B | 3 GB | 2/12 | 121 | 0.67 |
| 7 | InternVL3-2B | 3 GB | 2/12 | 251 | 0.67 |
| 8 | gemma-4-e2b-nothink | 4.6 GB | 3/12 | 1068 | 0.65 |
| 9 | Qwen3-VL-2B | 3.5 GB | 2/12 | 1017 | 0.57 |
| 10 | Qianfan-OCR | 5 GB | 2/12 | 876 | 0.40 |
| 11 | GLM-OCR | 9 GB | 1/12 | 401 | 0.11 |

**Key takeaway:** Qwen3.5-4B think (2.40 PASS/GB) dominates text efficiency -- 6/7 score at just 2.5 GB. For VLM, Qwen3-VL-4B Q4 (1.64 PASS/GB) leads on efficiency, but F16 (1.22 PASS/GB) is the better choice when OCR accuracy matters (11/12 vs 9/12).

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
| Bonsai-8B | 1-bit quantization — llama-server returns HTTP 500, cannot load model |
| DeepSeek-R1-Qwen3-8B | 0/7 total failure — fails all CC-Agent and smolagents tests |
| Gemma 4 26B-A4B | Agent code-tag bug (`<code` not `<code>`), text-only tasks perfect |
| Gemma 4 31B (dense) | 10 t/s, 13.7GB swap on M4 Pro 48GB — impractical |
| GLM-4.5-REAP-82B | Architecture not supported in llama.cpp |
| granite-3.3-8b | 0/7 — not capable as Claude Code backend |
| NVFP4 models | NVIDIA TensorRT format, incompatible with MLX |
| phi-4-mini | 1/7 — only passes sa1, fails all CC-Agent tests |
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
