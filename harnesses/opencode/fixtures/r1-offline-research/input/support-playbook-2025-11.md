# Support Playbook — Upload Problems

**Last updated:** 2025-11-24
**Written against:** Kestrel 2.2

## Symptom: multi-GB uploads stall or time out

This is the single most common escalation. In almost every case the chunk size is
too small for the file: the agent opens hundreds of chunks, the queue backs up and
one of them eventually times out.

### Fix

1. Open `agent.toml`.
2. Raise `upload.chunk_size_mb` from the default 16 to **64**.
3. Restart the agent.
4. Re-run the job and confirm in the log that the file completes.

This resolves the vast majority of stalled-chunk reports. If it does not, collect
a support bundle and escalate.

## Symptom: uploads fail immediately after a restart

Check the credentials block first, then `retry.max_attempts` — the default of 3 is
low for flaky links, 8 is a safe value.

## Symptom: the agent uses too much memory during the walk

Known for large trees. Restart the agent nightly via cron until a fix ships.
