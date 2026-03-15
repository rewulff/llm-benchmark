# LLM Benchmark Vergleich

**Generiert:** 2026-02-17 16:02

| Test | gemma-3-27b | gpt-oss-20b | qwen3-30b | qwen3-coder-30b |
|------|------|------|------|------|
| A1_file_write | **PASS** 45.6s | **PASS** 85.0s | **PASS** 38.5s | **PASS** 12.4s |
| A2_bug_fix | **PASS** 195.2s | **FAIL** 45.4s | **PASS** 34.9s | **PASS** 11.9s |
| A3_error_handling | **FAIL** 113.5s | **FAIL** 66.3s | **FAIL** 32.7s | **PASS** 30.8s |
| A4_large_read | **PASS** 17.6s | **FAIL** 33.3s | **FAIL** 35.4s | **PASS** 4.5s |
| A5_large_edit | **FAIL** 140.1s | **FAIL** 62.4s | **FAIL** 211.6s | **FAIL** 452.8s |
| B1_german_summary | **PASS** 11.6s | **PASS** 9.6s | **PASS** 7.0s | **PASS** 3.8s |
| B2_log_analysis | **PASS** 78.5s | **PASS** 26.0s | **PASS** 25.6s | **PASS** 17.5s |
| B3_statistics | **PASS** 67.7s | **PASS** 39.2s | **PASS** 36.0s | **PASS** 22.4s |
| B4_code_review | ERROR: timed out | **PASS** 45.6s | **PASS** 50.4s | **PASS** 13.7s |
| C1_config_diff | **PASS** 84.1s | **PASS** 20.9s | **PASS** 26.6s | **PASS** 9.8s |
| C2_decision_matrix | **PASS** 89.3s | **PASS** 18.6s | **PASS** 27.8s | **PASS** 11.2s |
| C3_root_cause | **PASS** 15.0s | **PASS** 10.2s | **PASS** 15.3s | **PASS** 3.7s |
| **GESAMT** | **9/12 (75%)** (858.2s) | **8/12 (66%)** (462.5s) | **9/12 (75%)** (541.8s) | **11/12 (91%)** (594.5s) |