#!/usr/bin/env python3
"""Filter a log file by severity level.

Usage:
    python3 logfilter.py sample.log
    python3 logfilter.py sample.log --level ERROR
"""

import argparse
import sys

LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")


def parse_line(line):
    """Split one log line into its parts.

    Returns a dict with date, timestamp, level and message, or None if the line
    does not look like a log entry.
    """
    parts = line.split(None, 2)
    if len(parts) < 3:
        return None
    timestamp, level, message = parts[0], parts[1], parts[2]
    if level not in LEVELS:
        return None
    return {
        "date": timestamp[:10],
        "timestamp": timestamp,
        "level": level,
        "message": message,
    }


def read_lines(path):
    """Read the log file and return its non-empty lines."""
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def filter_lines(lines, level=None):
    """Return the lines that match the given filters."""
    selected = []
    for line in lines:
        entry = parse_line(line)
        if entry is None:
            continue
        if level is not None and entry["level"] != level:
            continue
        selected.append(line)
    return selected


def main(argv=None):
    parser = argparse.ArgumentParser(description="Filter a log file by level.")
    parser.add_argument("path", help="path to the log file")
    parser.add_argument(
        "--level",
        choices=LEVELS,
        default=None,
        help="only show entries of this level",
    )
    args = parser.parse_args(argv)

    for line in filter_lines(read_lines(args.path), level=args.level):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
