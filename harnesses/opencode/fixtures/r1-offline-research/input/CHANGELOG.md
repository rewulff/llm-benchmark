# Kestrel Sync Agent — Changelog

All dates are release dates of the tagged build.

## 2.6.0 — 2026-06-10

- Added `sync.parallel_streams` (default 2) for multi-target deployments.
- Config reference rewritten; deprecated keys are now marked inline.
- Support: documented the large-upload workaround for KES-914.
- Fixed: agent no longer re-uploads unchanged files after a clock skew of < 5s.

## 2.5.0 — 2026-04-28

- Raised the default of `retry.max_attempts` from 3 to 5.
- Closed KES-877 (auth token refresh looped on expired refresh tokens).
- Log lines now carry the agent version in the startup banner.
- Packaging: Debian 13 builds.

## 2.4.0 — 2026-03-05

- Rewrote the multipart upload scheduler. The new key `upload.chunk_strategy`
  is introduced and defaults to `adaptive`.
- `upload.chunk_size_mb` is deprecated: it is ignored while the adaptive
  scheduler is active.
- Reduced memory footprint of the file walker by ~40%.
- Removed the legacy `--slow-mode` command line flag.

## 2.3.0 — 2026-01-15

- Switched checksums from MD5 to BLAKE3.
- Added `sync.exclude_globs`.
- Startup no longer blocks on unreachable secondary targets.

## 2.2.0 — 2025-11-20

- Added `retry.backoff_seconds`.
- Windows service wrapper.

## 2.1.0 — 2025-09-12

- First supported release of the 2.x line.
- `upload.chunk_size_mb` introduced (default 16).
