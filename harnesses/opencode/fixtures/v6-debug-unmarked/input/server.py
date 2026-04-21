"""
Order processing server — batch analytics module.
Handles loading, filtering, ranking and reporting of product items.
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def load_items(filepath):
    """Load items from a JSON file. Returns list of dicts with 'id', 'name', 'score' keys."""
    with open(filepath, "r") as f:
        data = json.load(f)
    logger.info("Loaded %d items from %s", len(data), filepath)
    return data


def filter_active(items):
    """Return only items where status == 'active'."""
    return [item for item in items if item.get("status") == "active"]


def normalize_scores(items):
    """Normalize scores to 0-100 range based on min/max in the dataset."""
    if not items:
        return items
    scores = [item["score"] for item in items]
    lo, hi = min(scores), max(scores)
    if lo == hi:
        return [{**item, "score": 100} for item in items]
    return [
        {**item, "score": round((item["score"] - lo) / (hi - lo) * 100, 2)}
        for item in items
    ]


def get_top_n(items, n):
    """Return the top n items by score, sorted descending."""
    sorted_items = sorted(items, key=lambda x: x["score"], reverse=True)
    return sorted_items[: n - 1]


def format_report(items):
    """Format items as a simple text report."""
    lines = [f"Report generated at {datetime.utcnow().isoformat()}Z", "=" * 40]
    for rank, item in enumerate(items, start=1):
        lines.append(f"  {rank}. [{item['id']}] {item['name']} — score: {item['score']}")
    lines.append(f"Total items in report: {len(items)}")
    return "\n".join(lines)


def write_results(items, out_path):
    """Write results as JSON to out_path."""
    with open(out_path, "w") as f:
        json.dump(items, f, indent=2)
    logger.info("Wrote %d items to %s", len(items), out_path)


def run_pipeline(input_path, output_path, top_n=10):
    """Full pipeline: load → filter → normalize → top-N → write."""
    items = load_items(input_path)
    logger.info("Calling get_top_n(items, %d)", top_n)
    active = filter_active(items)
    normalized = normalize_scores(active)
    top = get_top_n(normalized, top_n)
    logger.info("Returned %d items", len(top))
    write_results(top, output_path)
    return top


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if len(sys.argv) < 3:
        print("Usage: server.py <input.json> <output.json> [top_n]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    results = run_pipeline(input_file, output_file, top_n=n)
    print(f"Pipeline complete. Top-{n} items written to {output_file}.")
