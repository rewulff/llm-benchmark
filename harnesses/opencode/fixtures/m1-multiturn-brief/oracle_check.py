#!/usr/bin/env python3
"""Feature verification for m1-multiturn-brief.

Not part of input/ — oracle.sh copies this file into work/ for the run and
removes it afterwards, so the agent never sees these cases while working.

Drives the CLI as a black box and checks the two features the dialogue asked
for: an inclusive ISO-8601 date range and the weekend exclusion, both combined
with the pre-existing level filter.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "logfilter.py")
LOG = os.path.join(HERE, "sample.log")

# label, CLI args, expected line count, substrings that must appear, substrings that must not
CASES = [
    (
        "date range, both bounds inclusive",
        ["--since", "2026-06-01", "--until", "2026-06-05"],
        6,
        ["2026-06-05T22:18:03Z", "2026-06-01T08:15:00Z"],
        ["2026-06-06", "2026-06-07"],
    ),
    (
        "open start, --until inclusive",
        ["--until", "2026-06-02"],
        3,
        ["2026-06-02T03:12:44Z"],
        ["2026-06-03"],
    ),
    (
        "open end, --since inclusive",
        ["--since", "2026-06-13"],
        2,
        ["2026-06-13T04:15:00Z", "2026-06-14T05:02:48Z"],
        ["2026-06-12"],
    ),
    (
        "weekend exclusion",
        ["--skip-weekends"],
        11,
        ["2026-06-01T08:15:00Z", "2026-06-08T08:01:55Z"],
        ["2026-06-06", "2026-06-07", "2026-06-13", "2026-06-14"],
    ),
    (
        "date range combined with weekend exclusion",
        ["--since", "2026-06-05", "--until", "2026-06-08", "--skip-weekends"],
        2,
        ["2026-06-05T22:18:03Z", "2026-06-08T08:01:55Z"],
        ["2026-06-06", "2026-06-07"],
    ),
    (
        "level filter still intact",
        ["--level", "ERROR"],
        3,
        ["2026-06-07T02:30:17Z"],
        [" INFO ", " WARN "],
    ),
    (
        "level filter combined with weekend exclusion",
        ["--level", "ERROR", "--skip-weekends"],
        2,
        ["2026-06-03T14:02:09Z", "2026-06-10T16:44:02Z"],
        ["2026-06-07"],
    ),
]


def run_cli(args):
    return subprocess.run(
        [sys.executable, TOOL, LOG, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def main():
    failures = 0
    for label, args, expected_count, must_have, must_not_have in CASES:
        rendered = " ".join(args)
        try:
            proc = run_cli(args)
        except subprocess.TimeoutExpired:
            print(f"FAIL {label} [{rendered}]: timeout")
            failures += 1
            continue

        if proc.returncode != 0:
            print(f"FAIL {label} [{rendered}]: exit {proc.returncode}: {proc.stderr.strip()[:200]}")
            failures += 1
            continue

        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        problems = []
        if len(lines) != expected_count:
            problems.append(f"{len(lines)} lines, expected {expected_count}")
        body = "\n".join(lines)
        for needle in must_have:
            if needle not in body:
                problems.append(f"missing {needle!r}")
        for needle in must_not_have:
            if needle in body:
                problems.append(f"unexpected {needle!r}")

        if problems:
            print(f"FAIL {label} [{rendered}]: " + "; ".join(problems))
            failures += 1
        else:
            print(f"ok   {label}")

    if failures:
        print(f"{failures} of {len(CASES)} feature checks failed")
        return 1
    print(f"all {len(CASES)} feature checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
