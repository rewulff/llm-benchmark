"""Configuration loader for the readings pipeline.

Reads the JSON data file and flattens it into the config dict that
pipeline.py consumes.
"""

import json
import os

DEFAULT_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.json")


class ConfigError(Exception):
    """Raised when the data file is structurally unusable."""


def load_config(path=DEFAULT_DATA):
    """Load the data file and return a flat config dict.

    Keys: name, threshold, unit, readings.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    source = raw.get("source")
    if source is None:
        raise ConfigError(f"missing 'source' section in {path}")

    return {
        "name": source["name"],
        "threshold": source["limit"],
        "unit": source.get("unit", "celsius"),
        "readings": raw.get("readings", []),
    }
