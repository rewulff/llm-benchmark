# Kestrel Configuration Reference

**Applies to:** Kestrel 2.4.x — 2.6.x
**Generated:** 2026-06-10

Deprecated keys are marked inline. A deprecated key is still accepted by the
parser, it simply has no effect in the situations noted below.

## upload

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `upload.chunk_strategy` | enum | `adaptive` | `adaptive` sizes chunks at runtime from the observed throughput. `fixed` restores the pre-2.4 scheduler: chunks of a constant size, taken from `upload.chunk_size_mb`. |
| `upload.chunk_size_mb` | int | 16 | **Deprecated.** Ignored unless `upload.chunk_strategy` is set to `fixed`. |
| `upload.max_concurrent` | int | 4 | Chunks uploaded in parallel per file. |
| `upload.verify_after` | bool | true | Re-read the object after upload and compare the checksum. |

## retry

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `retry.max_attempts` | int | 5 | Attempts per chunk before the file is marked failed. Default raised in 2.5.0; agents upgraded in place keep whatever the config file states. |
| `retry.backoff_seconds` | int | 5 | Base delay for the exponential backoff. |

## sync

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sync.interval_minutes` | int | 60 | Interval between scheduled runs. |
| `sync.parallel_streams` | int | 2 | Targets served in parallel. New in 2.6.0. |
| `sync.exclude_globs` | list | `[]` | Patterns excluded from the walk. |
| `sync.follow_symlinks` | bool | false | Follow symlinked directories. |
