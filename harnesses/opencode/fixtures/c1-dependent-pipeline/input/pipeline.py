"""Readings pipeline: filter the raw readings and aggregate them.

Consumes the config dict from config_loader and produces the summary dict
that report.py formats.
"""

from config_loader import load_config


def select_readings(config):
    """Return the measured values of all readings that reach the threshold."""
    threshold = config["threshold"]
    return [reading for reading in config["readings"] if reading >= threshold]


def summarize(config):
    """Build the summary dict: name, unit, count, values, average."""
    values = select_readings(config)
    if not values:
        return {
            "name": config["name"],
            "unit": config["unit"],
            "count": 0,
            "values": [],
            "average": 0.0,
        }
    return {
        "name": config["name"],
        "unit": config["unit"],
        "count": len(values),
        "values": values,
        "average": sum(values) / len(values),
    }


def run(path=None):
    """Convenience entry point: load the config, then summarize it."""
    config = load_config(path) if path else load_config()
    return summarize(config)
