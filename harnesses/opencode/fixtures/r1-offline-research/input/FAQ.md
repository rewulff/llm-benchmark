# Kestrel — Frequently Asked Questions

Last reviewed: 2026-06-12.

**Where does the agent read its configuration from?**
`/etc/kestrel/agent.toml` on Linux, `%ProgramData%\Kestrel\agent.toml` on Windows.
The agent must be restarted after a change; there is no hot reload.

**How do I find out which version an agent runs?**
`kestrel --version`, or read the startup banner in the agent log. Since 2.5.0 the
version is printed on every start.

**Which document is authoritative for settings?**
The configuration reference that ships with your agent version. Tuning guides and
playbooks written before 2026-03 predate the upload scheduler change and can
recommend keys that no longer do anything. When two documents disagree, the newer
configuration reference wins.

**How do I collect logs for a support case?**
`kestrel support-bundle --since 48h`. Attach the bundle to the ticket, do not
paste single lines.

**Does the agent upload files in parallel?**
Chunks of one file are uploaded in parallel (`upload.max_concurrent`). Whole files
are processed one after another within a job.

**What do the error codes mean?**
`E_AUTH_EXPIRED` — session token expired, normally self-healing.
`E_CHUNK_TIMEOUT` — a multipart chunk made no progress and the upload was aborted.
`E_TARGET_UNREACHABLE` — the storage endpoint did not answer.
For open defects behind a code, check the known issues list.
