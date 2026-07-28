# Kestrel — Known Issues

Maintained by Support Engineering. Last update: 2026-06-18.
Entries are removed once the fix ships in a stable release.

## KES-914 — large uploads abort with E_CHUNK_TIMEOUT

**Status:** open

Uploads of a single file above roughly 5 GB can abort with `E_CHUNK_TIMEOUT`
after the chunk queue stalls. The root cause is the multipart upload scheduler
rewrite, not the customer network and not the storage backend — see the changelog
entry for the release that shipped that rewrite.

Agents older than that rewrite are not affected; the issue cannot be reproduced
on them.

**Workaround:** pin `upload.chunk_strategy` to the legacy value documented in the
current config reference, then restart the agent. Raising chunk sizes has no
effect while the adaptive scheduler is active.

## KES-877 — auth token refresh loops on expired refresh tokens

**Status:** closed in 2.5.0

The agent retried the refresh endpoint indefinitely when the refresh token itself
had expired. Symptom in the logs: repeated `E_AUTH_EXPIRED` at a fixed interval.

## KES-902 — file walker skips symlinked directories on Windows

**Status:** open, low priority

Workaround: use `sync.follow_symlinks = true`.
