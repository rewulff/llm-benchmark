# Sprint planning notes

**Date:** 2026-04-08
**Present:** Platform, Support

## Topics

- 2.5.0 scope confirmed: retry defaults, token refresh fix (KES-877), packaging.
- Two customers mentioned that large uploads "feel slower than last year".
  Nothing reproducible so far, no error codes attached to either report.
  **Working hypothesis (unconfirmed):** the checksum switch in the 2.3 line adds
  CPU time on big files. Someone should measure this before we act on it.
- Windows symlink walker (KES-902) parked, low priority.

## Notes

- We still have no synthetic test for files above 5 GB in the nightly pipeline.
  Everything we test is below 2 GB. Action item without an owner since February.
- Support asked whether the old 2025 troubleshooting playbook is still valid.
  Nobody in the room knew. Parked.
