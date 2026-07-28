`logfilter.py` is a small CLI tool that filters a log file by severity level.
Extend it: it should support date filtering as well.

## Requirements

- Add `--since` and `--until` options that restrict the output to a date range.
- Either option may be given on its own, and both must combine with `--level`.
- `test_logfilter.py` is the existing baseline test suite. Do not edit it and do
  not edit `sample.log` — both must keep passing unchanged.

## Ambiguity rule (important)

If any requirement is ambiguous, ask exactly ONE clarifying question before you
write any code. Ask that single question and stop your turn — do not start editing
in the same turn you ask. If nothing is ambiguous, implement directly.

## Diff rule (critical!)

- `oldString` = 2-5 lines (only the directly affected ones)
- `newString` = as small as possible, at most ±30 lines vs `oldString`
- NEVER rewrite whole functions — only the changed lines
- Prefer a single `edit` operation per change

## Done

When the change is complete, respond with just: DONE
