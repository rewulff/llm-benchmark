# Internal Wiki — Kestrel Performance Tuning

**Last edited:** 2026-01-20
**Applies to:** 2.3
**Owner:** vacant (former owner left the team)

## Large files

Large-file uploads have been noticeably slower since **2.3.0**. This is expected:
the release replaced MD5 with BLAKE3 and the extra hashing shows up on multi-GB
archives. If a customer complains about big archives, this is where to look first.

There is no configuration switch for the checksum algorithm. If throughput matters
more than integrity, disable `upload.verify_after` — that saves a full re-read of
the object.

## Retries

`retry.max_attempts` defaults to **3**. Raising it only hides network problems and
makes incidents harder to read in the logs. Leave it alone.

## Chunking

`upload.chunk_size_mb` is the main throughput lever. 32 is a good compromise for
mixed workloads, 64 for archive-only jobs.

## Parallelism

`upload.max_concurrent` above 8 saturates most uplinks and starts to hurt.
