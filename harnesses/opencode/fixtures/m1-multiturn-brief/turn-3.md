Requirement change: the tool additionally needs `--skip-weekends`, a flag that
drops every entry falling on a Saturday or Sunday.

- It combines with `--since`, `--until` and `--level`.
- Without the flag the behaviour stays exactly as it is now.

Minimal diff: do not rewrite existing functions, do not reorganise the file, and
do not touch `test_logfilter.py` or `sample.log`.

When you are done, respond with just: DONE
