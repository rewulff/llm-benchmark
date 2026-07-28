"""Report formatting for the readings pipeline.

Renders the summary dict as plain text: header, top-N ranking, footer.
"""

from pipeline import run

TOP_N = 3


def format_report(summary):
    """Return the report text for a summary dict."""
    ranked = sorted(summary["values"], reverse=True)
    lines = [f"Report: {summary['name']} ({summary['unit']})"]
    for rank, value in enumerate(ranked[:TOP_N]):
        lines.append(f"{rank}. {value}")
    lines.append(f"selected={summary['count']} average={summary['average']:.1f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report(run()))
