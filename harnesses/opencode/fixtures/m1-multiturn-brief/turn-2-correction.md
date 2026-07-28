You went ahead without asking, so here is the specification you were missing:

- Dates are ISO-8601 calendar dates in the form `YYYY-MM-DD`, matched against the
  date part of the log timestamp.
- Both bounds are inclusive. `--until 2026-06-05` must still return the entries
  of June 5th, and `--since 2026-06-01` includes June 1st.

Adjust your implementation minimally so it matches this. Do not rewrite the file,
change only what is actually wrong, and leave `test_logfilter.py` untouched.
When you are done, respond with just: DONE
