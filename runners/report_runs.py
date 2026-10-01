#!/usr/bin/env python3
"""Baut eine Markdown-Tabelle aus den summary.json-Dateien mehrerer Lauf-Labels.

Liest fuer jedes Label die Datei <results-dir>/<label>/summary.json und gibt
eine Tabelle aus: eine Zeile je Fixture, eine Spalte je Label
("PASS 26s" bzw. "FAIL 48s"), darunter eine Summenzeile je Label
("PASS x/n" und Gesamtzeit in Minuten).

Nebenwirkungen: Das Skript liest nur Dateien aus dem Results-Verzeichnis und
schreibt nichts. Mit --json wird statt der Tabelle die geladene Datenstruktur
als JSON auf stdout ausgegeben.
"""
import argparse
import json
import sys
from pathlib import Path


def load_label(path):
    """Liest eine summary.json und gibt (label, runs) zurueck.

    Wirft SystemExit(2) mit klarer Fehlermeldung, wenn die Datei fehlt oder
    nicht geparst werden kann.
    """
    if not path.is_file():
        print(f"Fehler: summary.json nicht gefunden: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"Fehler: {path} ist kein gueltiges JSON: {e}", file=sys.stderr)
        sys.exit(2)
    runs = data.get("runs")
    if not isinstance(runs, list):
        print(f"Fehler: {path} hat kein 'runs'-Array", file=sys.stderr)
        sys.exit(2)
    return data.get("label", path.parent.name), runs


def build_table(labels_data):
    """Gibt die Markdown-Tabelle als String zurueck."""
    # Fixtures in der Reihenfolge ihres ersten Auftretens sammeln.
    fixtures = []
    seen = set()
    for _, runs in labels_data:
        for r in runs:
            fx = r.get("fixture")
            if fx is not None and fx not in seen:
                seen.add(fx)
                fixtures.append(fx)

    def cell(r):
        if r is None:
            return "-"
        status = r.get("status", "")
        dur = r.get("duration_s", 0) or 0
        return f"{status} {int(round(dur))}s"

    # Pro Label eine Mapping fixture->run aufbauen.
    by_fixture = []
    for _, runs in labels_data:
        by_fixture.append({r.get("fixture"): r for r in runs if r.get("fixture") is not None})

    header = "| Fixture | " + " | ".join(label for label, _ in labels_data) + " |"
    sep = "|---|" + "---|" * len(labels_data)
    rows = [header, sep]
    for fx in fixtures:
        cells = [cell(by_fixture[i].get(fx)) for i in range(len(labels_data))]
        rows.append(f"| {fx} | " + " | ".join(cells) + " |")

    # Summenzeile je Label: PASS x/n und Gesamtzeit in Minuten.
    totals = []
    for label, runs in labels_data:
        present = [r for r in runs if r.get("fixture") is not None]
        passed = sum(1 for r in present if r.get("status") == "PASS")
        total = sum(r.get("duration_s", 0) or 0 for r in present)
        totals.append(f"PASS {passed}/{len(present)} · {total / 60:.1f} min")
    rows.append(f"| **Summe** | " + " | ".join(totals) + " |")

    return "\n".join(rows)


def build_json_output(labels_data):
    """Gibt die geladene Datenstruktur als JSON zurueck."""
    payload = {}
    for label, runs in labels_data:
        payload[label] = {"runs": runs}
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Baut eine Markdown-Tabelle aus summary.json mehrerer Lauf-Labels.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Nebenwirkungen: Das Skript liest nur die summary.json-Dateien im "
            "Results-Verzeichnis und schreibt sonst nichts. --json gibt statt "
            "der Tabelle die geladene Datenstruktur als JSON aus."
        ),
    )
    parser.add_argument("labels", nargs="+", help="Lauf-Labels, deren summary.json gelesen wird")
    parser.add_argument(
        "--results-dir",
        default="results/king-eval-2026-09-30",
        help="Verzeichnis, das die einzelnen Label-Ordner enthaelt (Default: results/king-eval-2026-09-30)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Ganze statt der Markdown-Tabelle als JSON ausgeben",
    )
    args = parser.parse_args(argv)

    results_dir = Path(args.results_dir)
    labels_data = []
    for label in args.labels:
        path = results_dir / label / "summary.json"
        labels_data.append(load_label(path))

    if args.json:
        print(build_json_output(labels_data))
    else:
        print(build_table(labels_data))


if __name__ == "__main__":
    main()
