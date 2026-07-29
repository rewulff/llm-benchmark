# Incident review — stalled large uploads

**Date:** 2026-06-16
**Present:** Support Engineering, Platform, Product
**Ticket:** KES-914

## What we know

- Northwind reported failing nightly archives two nights in a row. Their agent
  logs show the abort on the single large file; the two smaller files go through.
- Reproduced in staging with a synthetic 6 GB file. The customer network is not
  involved — the same file fails against our own test bucket.
- The trigger is the multipart scheduler rewrite, confirmed by bisecting our own
  builds. It is not the checksum change from the 2.3 line, which is what the
  wiki tuning guide still suggests. That guide is stale and needs an owner.
- ACME is not affected. They pinned the legacy scheduler value during the
  rollout and never moved off it.
- Brightwave has not upgraded yet, so they cannot hit this at all.

## Decisions

- Support keeps handing out the config workaround from the current reference.
  Do not tell customers to raise chunk sizes — that key is inert with the
  adaptive scheduler and we have wasted two calls on it already.
- The permanent fix is targeted for **2.7.0**. No backport to 2.6.x: the
  scheduler change is too invasive for a patch release.
- KES-914 stays open until 2.7.0 ships.

## Follow-ups

- Platform: rework the chunk stall detection, target 2.7.0.
- Support: retire the 2025 playbook section on large uploads.
- Product: decide whether `chunk_strategy` should flip its default back.
