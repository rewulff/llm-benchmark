This directory contains a small pipeline that reads sensor data from `sample.json`,
filters it and prints a report. Running `python3 test_pipeline.py` currently fails.

Your task: make the test suite pass by fixing the root causes in the source files.

## Files

- `config_loader.py` — reads `sample.json`, builds the config dict
- `pipeline.py` — filters the readings and aggregates them
- `report.py` — formats the final report text
- `test_pipeline.py` — end-to-end check, read-only
- `sample.json` — input data, read-only

## Rules (strict!)

- Fix the root causes in `config_loader.py`, `pipeline.py` and `report.py` only.
- Do NOT modify `test_pipeline.py` or `sample.json` — they define the expected contract.
- Do NOT weaken or skip assertions and do NOT wrap failures in try/except to hide them.
- There is more than one defect and they depend on each other: the test stops at the
  FIRST failing stage. Run `python3 test_pipeline.py` again after every fix to see the
  next one. Read all three source files before you start editing.
- No refactoring, no style changes, no reorganised imports.

## Diff rule (critical!)

- `oldString` = 2-5 lines (only the directly affected ones)
- `newString` = as small as possible, at most ±30 lines vs `oldString`
- NEVER rewrite whole functions — only the changed lines
- Prefer a single `edit` operation per fix

## Done

Run `python3 test_pipeline.py` one last time. Once it prints `ALL 3 STAGES PASSED`,
respond with just: DONE
Do not ask follow-up questions.
