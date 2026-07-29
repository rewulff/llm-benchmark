# Kestrel Configuration Reference

**Applies to:** Kestrel 2.2.x
**Generated:** 2025-11-20
**Note:** kept for customers on the 2.2 maintenance line. Newer agents ship their
own reference — do not mix the two.

## upload

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `upload.chunk_size_mb` | int | 16 | Size of a single multipart chunk. Raise this for large files: bigger chunks mean fewer round trips and noticeably better throughput on archives above 1 GB. |
| `upload.max_concurrent` | int | 4 | Chunks uploaded in parallel per file. |
| `upload.verify_after` | bool | true | Re-read the object after upload and compare the checksum. |

## retry

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `retry.max_attempts` | int | 3 | Attempts per chunk before the file is marked failed. |
| `retry.backoff_seconds` | int | 5 | Base delay for the exponential backoff. |

## sync

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sync.interval_minutes` | int | 60 | Interval between scheduled runs. |
| `sync.exclude_globs` | list | `[]` | Patterns excluded from the walk. |
| `sync.follow_symlinks` | bool | false | Follow symlinked directories. |
