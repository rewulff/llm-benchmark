#!/usr/bin/env python3
"""Tests fuer runners/report_runs.py (unittest, Standardbibliothek).

Getestet wird das Verhalten ueber die Kommandozeile: Tabelle, JSON-Modus und
der Fehlerfall bei fehlender summary.json.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "report_runs.py"


def write_summary(root, label, runs, model="m", label_field=None):
    d = root / label
    d.mkdir(parents=True, exist_ok=True)
    rec = {"label": label_field or label, "model": model, "runs": runs}
    (d / "summary.json").write_text(json.dumps(rec))


class ReportRunsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, args, **kw):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, **kw
        )

    def test_table_output(self):
        write_summary(self.root, "label-a", [
            {"fixture": "fx1", "status": "PASS", "duration_s": 26.0, "steps": 1, "tool_calls": 1},
            {"fixture": "fx2", "status": "FAIL", "duration_s": 48.0, "steps": 1, "tool_calls": 1},
        ])
        write_summary(self.root, "label-b", [
            {"fixture": "fx1", "status": "FAIL", "duration_s": 10.0, "steps": 1, "tool_calls": 1},
            {"fixture": "fx2", "status": "PASS", "duration_s": 5.0, "steps": 1, "tool_calls": 1},
            {"fixture": "fx3", "status": "PASS", "duration_s": 3.0, "steps": 1, "tool_calls": 1},
        ])

        r = self.run_script(["label-a", "label-b", "--results-dir", str(self.root)])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout

        # Header und Spaltenreihenfolge.
        self.assertIn("| Fixture | label-a | label-b |", out)
        # Fixturespalte und Zeilenreihenfolge.
        self.assertIn("| fx1 |", out)
        self.assertIn("| fx2 |", out)
        self.assertIn("| fx3 |", out)
        self.assertLess(out.index("fx1"), out.index("fx2"))
        self.assertLess(out.index("fx2"), out.index("fx3"))

        # Zelleninhalt: "PASS 26s" / "FAIL 48s".
        self.assertIn("PASS 26s", out)
        self.assertIn("FAIL 48s", out)

        # fx3 existiert nur in label-b -> "-" in label-a.
        fx3_line = [ln for ln in out.splitlines() if ln.startswith("| fx3 |")][0]
        self.assertIn("| fx3 | - |", fx3_line)

        # Summenzeile: PASS x/n und Gesamtzeit in Minuten (1 Kommastelle).
        sum_lines = [ln for ln in out.splitlines() if ln.startswith("| **")]
        self.assertEqual(len(sum_lines), 1)
        self.assertIn("PASS 1/2", sum_lines[0])   # label-a: nur fx1 PASS
        self.assertIn("PASS 2/3", sum_lines[0])   # label-b: fx1 FAIL, fx2/fx3 PASS
        # Erste Zelle der Summenzeile ist "Summe", nie ein Label-Name.
        self.assertTrue(sum_lines[0].startswith("| **Summe** |"), sum_lines[0])

    def test_json_mode(self):
        write_summary(self.root, "label-a", [
            {"fixture": "fx1", "status": "PASS", "duration_s": 26.0, "steps": 1, "tool_calls": 1},
        ])
        r = self.run_script(["label-a", "--json", "--results-dir", str(self.root)])
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = json.loads(r.stdout)
        self.assertIn("label-a", payload)
        self.assertEqual(payload["label-a"]["runs"][0]["fixture"], "fx1")
        # Im JSON-Modus keine Markdown-Tabelle.
        self.assertNotIn("| Fixture |", r.stdout)

    def test_missing_summary_json(self):
        # Kein summary.json angelegt -> klarer Fehler, kein Traceback.
        r = self.run_script(["label-a", "--results-dir", str(self.root)])
        self.assertEqual(r.returncode, 2)
        self.assertIn("summary.json", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
