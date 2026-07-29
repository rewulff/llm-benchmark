#!/usr/bin/env python3
"""Wrapper fuer gescriptete Multi-Turn-OpenCode-Runs.

Schwesterscript zu run_opencode_test.py: gleicher Job-Scratch, gleiches
Parsing, gleiches Result-JSON — nur fuehrt es statt eines Einzel-Prompts einen
vorgeschriebenen Dialog aus fixtures/<fixture>/turns.json.

Turn 1 laeuft als `opencode run --format json`, jeder Folge-Turn als
`opencode run -s <sessionID> --format json` in derselben Session. Die sessionID
wird aus den JSON-Events von Turn 1 gelesen.

Zusaetzlich zu den ueblichen Metriken schreibt der Driver Dialog-Metriken ins
Result-JSON: asked_clarifying (Heuristik, siehe looks_like_clarifying_question),
Turn-Anzahl, Steps gesamt und die Diff-Groesse pro Turn (Rewrite-Detektor).

Usage:
    python3 run_multiturn_test.py --fixture m1-multiturn-brief --dry-run

    python3 run_multiturn_test.py --model local-qwen36/qwen3.6-35b-a3b \\
        --fixture m1-multiturn-brief --job-slug m1-qwen36-$(date +%s)
"""

import argparse
import difflib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

# Dieses Script liegt in harnesses/opencode/ (Fixtures daneben unter fixtures/).
SCRIPT_DIR = Path(__file__).parent.resolve()
FIXTURES_DIR = SCRIPT_DIR / "fixtures"
MODELS_DIR = SCRIPT_DIR / "models"
OPENCODE_BIN = Path.home() / ".opencode" / "bin" / "opencode"
JOBS_BASE = Path.home() / "opencode-jobs"
LLAMA_HEALTH_URL = "http://127.0.0.1:1235/health"

# Code-Home von run_opencode_test.py — dort liegen parse_opencode_run.py und
# die autoritative opencode.json. Ueber --code-home ueberschreibbar.
DEFAULT_CODE_HOME = Path.home() / "Arbeitsverzeichnis" / "lib" / "local-llm" / "benchmark" / "opencode"

# Tools, die eine Datei veraendern. Ein Turn mit einem solchen Call gilt nicht
# mehr als reine Rueckfrage.
EDIT_TOOLS = {"edit", "write", "patch", "multiedit"}

# Dateiendungen, die fuer die Diff-Metrik verglichen werden.
DIFFABLE_SUFFIXES = {".py", ".md", ".json", ".txt", ".log", ".toml", ".yaml", ".yml", ".sh"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenCode Multi-Turn Wrapper — faehrt einen gescripteten Dialog aus turns.json."
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Provider/Model-String, z.B. local-qwen36/qwen3.6-35b-a3b (Pflicht ausser bei --dry-run)",
    )
    parser.add_argument(
        "--fixture",
        required=True,
        help="Name der Fixture (Unterordner unter fixtures/), z.B. m1-multiturn-brief",
    )
    parser.add_argument(
        "--job-slug",
        dest="job_slug",
        default=None,
        help="Eindeutiger Slug fuer diesen Run (Pflicht ausser bei --dry-run)",
    )
    parser.add_argument(
        "--code-home",
        dest="code_home",
        default=None,
        help=f"Verzeichnis mit parse_opencode_run.py und opencode.json (Standard: {DEFAULT_CODE_HOME})",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Nur turns.json pruefen und den Ablaufplan ausgeben. Kein Server, kein opencode.",
    )
    args = parser.parse_args()
    if not args.dry_run:
        missing = [name for name, value in (("--model", args.model), ("--job-slug", args.job_slug)) if not value]
        if missing:
            parser.error(f"{' und '.join(missing)} sind ohne --dry-run Pflicht")
    return args


# --------------------------------------------------------------------------
# Fixture / Turns
# --------------------------------------------------------------------------

def load_turns(fixture_dir: Path) -> list[dict]:
    """Liest turns.json und loest die Message-Dateien auf.

    Jeder Turn braucht entweder 'message' (inline) oder 'message_file'.
    Ein Turn mit 'condition' waehlt zwischen message_file (Bedingung erfuellt)
    und else_message_file.
    """
    turns_path = fixture_dir / "turns.json"
    if not turns_path.exists():
        print(f"FEHLER: turns.json nicht gefunden: {turns_path}", file=sys.stderr)
        sys.exit(1)
    try:
        spec = json.loads(turns_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"FEHLER: turns.json ist kein gueltiges JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    turns = spec.get("turns")
    if not isinstance(turns, list) or not turns:
        print("FEHLER: turns.json enthaelt keine nicht-leere 'turns'-Liste", file=sys.stderr)
        sys.exit(1)

    resolved = []
    for index, turn in enumerate(turns, start=1):
        entry = {
            "id": turn.get("id", index),
            "label": turn.get("label", f"turn {index}"),
            "condition": turn.get("condition"),
        }
        for key, target in (("message_file", "message"), ("else_message_file", "else_message")):
            if key in turn:
                path = fixture_dir / turn[key]
                if not path.exists():
                    print(f"FEHLER: Turn {entry['id']}: {key} nicht gefunden: {path}", file=sys.stderr)
                    sys.exit(1)
                entry[target] = path.read_text().strip()
                entry[f"{target}_source"] = turn[key]
        if "message" in turn:
            entry["message"] = turn["message"].strip()
            entry["message_source"] = "<inline>"
        if "else_message" in turn:
            entry["else_message"] = turn["else_message"].strip()
            entry["else_message_source"] = "<inline>"

        if "message" not in entry:
            print(f"FEHLER: Turn {entry['id']} hat weder 'message' noch 'message_file'", file=sys.stderr)
            sys.exit(1)
        if entry["condition"] and "else_message" not in entry:
            print(
                f"FEHLER: Turn {entry['id']} hat 'condition' aber kein 'else_message(_file)'",
                file=sys.stderr,
            )
            sys.exit(1)
        resolved.append(entry)
    return resolved


def select_message(turn: dict, flags: dict) -> tuple[str, str, str]:
    """Waehlt anhand der Bedingung die Message. Gibt (text, quelle, branch) zurueck."""
    condition = turn.get("condition")
    if not condition:
        return turn["message"], turn.get("message_source", "<inline>"), "default"
    if condition not in flags:
        print(
            f"FEHLER: Turn {turn['id']}: unbekannte Bedingung {condition!r} "
            f"(bekannt: {', '.join(sorted(flags)) or 'keine'})",
            file=sys.stderr,
        )
        sys.exit(1)
    if flags[condition]:
        return turn["message"], turn.get("message_source", "<inline>"), f"{condition}=true"
    return turn["else_message"], turn.get("else_message_source", "<inline>"), f"{condition}=false"


# --------------------------------------------------------------------------
# Job-Scratch (Konventionen aus run_opencode_test.py)
# --------------------------------------------------------------------------

def check_health() -> bool:
    """Prueft ob llama-server auf Port 1235 erreichbar ist."""
    try:
        with urlopen(LLAMA_HEALTH_URL, timeout=3) as resp:
            return resp.status == 200
    except (URLError, OSError):
        return False


def setup_job_dirs(job_slug: str) -> tuple[Path, Path, Path]:
    """Legt Job-Scratch-Verzeichnisse an. Gibt (job_dir, work_dir, output_dir) zurueck."""
    job_dir = JOBS_BASE / job_slug
    input_dir = job_dir / "input"
    work_dir = job_dir / "work"
    output_dir = job_dir / "output"
    for d in (input_dir, work_dir, output_dir):
        d.mkdir(parents=True, exist_ok=True)
    return job_dir, work_dir, output_dir


def copy_fixture_to_job(fixture_dir: Path, input_dir: Path, work_dir: Path) -> None:
    """Kopiert Fixture-Input-Dateien nach input/ (Referenz) und work/ (OpenCode-Workspace)."""
    src_input = fixture_dir / "input"
    if not src_input.exists():
        print(
            f"  Hinweis: Kein input/-Unterordner in {fixture_dir} — OpenCode startet in leerem work/",
            file=sys.stderr,
        )
        return
    for f in src_input.iterdir():
        if f.is_dir():
            print(f"  Hinweis: Unterordner {f.name}/ uebersprungen (Fixtures sind flach)", file=sys.stderr)
            continue
        shutil.copy2(f, input_dir / f.name)
        shutil.copy2(f, work_dir / f.name)


def link_opencode_config(job_dir: Path, code_home: Path) -> None:
    """Symlinkt die autoritative opencode.json ins Job-Scratch."""
    scratch_config = job_dir / "opencode.json"
    if scratch_config.exists():
        return
    for candidate in (SCRIPT_DIR / "opencode.json", code_home / "opencode.json"):
        if candidate.exists():
            scratch_config.symlink_to(candidate)
            print(f"  Config-Symlink: {scratch_config} -> {candidate}")
            return
    print(
        "FEHLER: keine opencode.json gefunden (gesucht in "
        f"{SCRIPT_DIR} und {code_home}). Mit --code-home das Code-Home angeben.",
        file=sys.stderr,
    )
    sys.exit(1)


# --------------------------------------------------------------------------
# Turn-Ausfuehrung und Auswertung
# --------------------------------------------------------------------------

def build_command(model: str, message: str, session_id: str | None, work_dir: Path | str = "<work>") -> list[str]:
    """Baut das opencode-Kommando fuer einen Turn."""
    cmd = [str(OPENCODE_BIN), "run", "--dir", str(work_dir)]
    if session_id:
        cmd += ["-s", session_id]
    cmd += ["--model", model, "--auto", "--format", "json", message]
    return cmd


def run_turn(model: str, message: str, session_id: str | None, work_dir: Path, jsonl_path: Path) -> None:
    """Fuehrt einen Turn aus und schreibt den Event-Stream nach jsonl_path."""
    cmd = build_command(model, message, session_id, work_dir)
    with open(jsonl_path, "w") as out_fh:
        result = subprocess.run(cmd, cwd=str(work_dir), stdout=out_fh, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"  WARNUNG: opencode exit {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(f"  stderr: {result.stderr[:500]}", file=sys.stderr)


def read_events(jsonl_path: Path) -> list[dict]:
    """Liest den JSONL-Event-Stream. Unparsbare Zeilen werden uebersprungen."""
    events = []
    if not jsonl_path.exists():
        return events
    for line in jsonl_path.read_text().splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def analyze_events(events: list[dict]) -> dict:
    """Metriken eines Turns. Feldnamen wie parse_opencode_run.parse(), plus
    ungekuerzter final_text und edit_tool_calls fuer die Dialog-Heuristik."""
    steps = [e for e in events if e.get("type") == "step_start"]
    step_finishes = [e for e in events if e.get("type") == "step_finish"]
    tool_uses = [e for e in events if e.get("type") == "tool_use"]
    texts = [e for e in events if e.get("type") == "text"]

    tool_counts: dict[str, int] = {}
    for t in tool_uses:
        name = t.get("part", {}).get("tool", "unknown")
        tool_counts[name] = tool_counts.get(name, 0) + 1

    if events:
        timestamps = [e["timestamp"] for e in events if "timestamp" in e]
        duration_s = round((max(timestamps) - min(timestamps)) / 1000.0, 2) if timestamps else 0
    else:
        duration_s = 0

    session_id = None
    for event in events:
        if event.get("sessionID"):
            session_id = event["sessionID"]
            break

    return {
        "duration_s": duration_s,
        "steps": len(steps),
        "tool_calls": len(tool_uses),
        "tools_breakdown": tool_counts,
        "final_text": texts[-1].get("part", {}).get("text", "") if texts else "",
        "stop_reason": step_finishes[-1].get("part", {}).get("reason", "unknown") if step_finishes else "unknown",
        "edit_tool_calls": sum(count for name, count in tool_counts.items() if name in EDIT_TOOLS),
        "session_id": session_id,
        "events": len(events),
    }


def looks_like_clarifying_question(analysis: dict) -> bool:
    """Heuristik fuer 'das Modell hat nachgefragt statt zu raten'.

    Wahr, wenn die letzte Assistant-Message ein Fragezeichen enthaelt UND im
    Turn kein datei-veraendernder Tool-Call vorkam. Bewusst simpel gehalten:
    beide Bestandteile stehen als question_mark / edit_tool_calls einzeln im
    Result-JSON, die Heuristik ist damit nachpruefbar und ohne Neulauf
    revidierbar.

    Bekannte Grenzen: eine rhetorische Frage im Abschlusstext ohne Edit zaehlt
    faelschlich als Rueckfrage; eine Rueckfrage, die das Modell nach einem
    bereits erfolgten Edit stellt, zaehlt faelschlich nicht.
    """
    return "?" in analysis.get("final_text", "") and analysis.get("edit_tool_calls", 0) == 0


# --------------------------------------------------------------------------
# Diff-Metrik (Rewrite-Detektor)
# --------------------------------------------------------------------------

def snapshot_work(work_dir: Path) -> dict[str, list[str]]:
    """Textzustand des Arbeitsverzeichnisses als {relativer Pfad: Zeilen}."""
    snapshot: dict[str, list[str]] = {}
    for path in sorted(work_dir.rglob("*")):
        if not path.is_file() or path.suffix not in DIFFABLE_SUFFIXES:
            continue
        if "__pycache__" in path.parts:
            continue
        try:
            snapshot[str(path.relative_to(work_dir))] = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
    return snapshot


def diff_stats(before: dict[str, list[str]], after: dict[str, list[str]]) -> dict:
    """Zaehlt geaenderte Dateien und +/- Zeilen zwischen zwei Snapshots."""
    added = removed = 0
    changed_files = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name, [])
        new = after.get(name, [])
        if old == new:
            continue
        changed_files.append(name)
        for line in difflib.unified_diff(old, new, lineterm="", n=0):
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
    return {
        "files_changed": len(changed_files),
        "files": changed_files,
        "lines_added": added,
        "lines_removed": removed,
        "lines_touched": added + removed,
    }


# --------------------------------------------------------------------------
# Nachlauf: Lint, Oracle, Ergebnis
# --------------------------------------------------------------------------

def run_python_lint(work_dir: Path) -> dict:
    """Ruff-Lint auf allen .py-Dateien im work-Dir. Gibt dict mit violations zurueck."""
    py_files = [p for p in work_dir.rglob("*.py") if "__pycache__" not in p.parts]
    if not py_files:
        return {"checked": 0, "violations": [], "passed": True}
    try:
        proc = subprocess.run(
            ["ruff", "check", "--select", "F", "--output-format", "json"] + [str(p) for p in py_files],
            capture_output=True, text=True, timeout=30,
        )
        try:
            findings = json.loads(proc.stdout) if proc.stdout.strip() else []
        except json.JSONDecodeError:
            findings = []
        return {
            "checked": len(py_files),
            "violations": findings,
            "passed": len(findings) == 0,
            "ruff_exit": proc.returncode,
        }
    except FileNotFoundError:
        return {"checked": len(py_files), "violations": [], "passed": True, "note": "ruff not installed, skipped"}
    except subprocess.TimeoutExpired:
        return {"checked": len(py_files), "violations": [], "passed": False, "note": "ruff timeout"}


def run_oracle(fixture_dir: Path, job_dir: Path) -> int | None:
    """Fuehrt oracle.sh aus (im job_dir, nicht in work/, da es work/ als Subpfad adressiert)."""
    oracle = fixture_dir / "oracle.sh"
    if not oracle.exists():
        return None
    return subprocess.run(["bash", str(oracle)], cwd=str(job_dir), text=True).returncode


def model_short(model_str: str) -> str:
    """Extrahiert den Modell-Kurznamen aus 'provider/model-name' -> 'model-name'."""
    parts = model_str.split("/", 1)
    return parts[1] if len(parts) == 2 else model_str


def save_result(result: dict, model: str, fixture: str, date_str: str) -> Path:
    """Speichert das Ergebnis-JSON unter models/<model_short>/results/."""
    out_dir = MODELS_DIR / model_short(model) / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{date_str}-multiturn-{fixture}.json"
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return out_file


# --------------------------------------------------------------------------
# Dry-Run
# --------------------------------------------------------------------------

def print_dry_run(fixture: str, fixture_dir: Path, turns: list[dict], model: str | None) -> None:
    """Gibt den Ablaufplan aus, ohne Server oder opencode zu beruehren."""
    shown_model = model or "<model>"
    print(f"[multiturn dry-run] fixture={fixture} ({fixture_dir})")
    print(f"  turns.json: {len(turns)} Turns")
    has_oracle = (fixture_dir / "oracle.sh").exists()
    input_files = sorted(p.name for p in (fixture_dir / "input").iterdir()) if (fixture_dir / "input").is_dir() else []
    print(f"  input/: {len(input_files)} Dateien: {', '.join(input_files) if input_files else '(leer)'}")
    print(f"  oracle.sh: {'vorhanden' if has_oracle else 'FEHLT'}")
    print("")

    for index, turn in enumerate(turns, start=1):
        session_ref = None if index == 1 else "<sessionID aus Turn 1>"
        print(f"  Turn {turn['id']} — {turn['label']}")
        if turn.get("condition"):
            print(f"    Bedingung : {turn['condition']}")
            print(f"      erfuellt      -> {turn.get('message_source')} ({len(turn['message'])} Zeichen)")
            print(f"      nicht erfuellt-> {turn.get('else_message_source')} ({len(turn['else_message'])} Zeichen)")
            preview_source = f"{turn.get('message_source')} | {turn.get('else_message_source')}"
        else:
            print(f"    Message   : {turn.get('message_source')} ({len(turn['message'])} Zeichen)")
            preview_source = turn.get("message_source")
        first_line = turn["message"].splitlines()[0] if turn["message"].splitlines() else ""
        print(f"    Beginnt mit: {first_line[:70]}")
        cmd = build_command(shown_model, "<message>", session_ref)
        print(f"    Kommando  : {' '.join(cmd[1:])}")
        print(f"    Quelle    : {preview_source}")
        print("")

    print("  Nach jedem Turn: Event-Parsing (steps/tool_calls/stop_reason), Diff-Snapshot des work/-Verzeichnisses.")
    print("  Heuristik asked_clarifying: '?' in der letzten Assistant-Message UND kein edit/write/patch-Tool-Call im Turn.")
    print("  Nach dem letzten Turn: ruff-Lint (optional), oracle.sh, Result-JSON unter models/<model>/results/.")
    print("")
    print("  Dry-Run: keine Server-Abfrage, kein opencode-Aufruf, kein Job-Verzeichnis angelegt.")


# --------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    fixture_dir = FIXTURES_DIR / args.fixture
    if not fixture_dir.exists():
        print(f"FEHLER: Fixture nicht gefunden: {fixture_dir}", file=sys.stderr)
        sys.exit(1)

    turns = load_turns(fixture_dir)

    if args.dry_run:
        print_dry_run(args.fixture, fixture_dir, turns, args.model)
        return

    code_home = Path(args.code_home).expanduser().resolve() if args.code_home else DEFAULT_CODE_HOME
    print(f"[multiturn] model={args.model} fixture={args.fixture} turns={len(turns)}")

    if not OPENCODE_BIN.exists():
        print(f"FEHLER: opencode nicht gefunden unter {OPENCODE_BIN}", file=sys.stderr)
        sys.exit(1)
    if not check_health():
        print(
            f"FEHLER: llama-server nicht erreichbar ({LLAMA_HEALTH_URL}).\n"
            "Bitte Server starten: ./servers/start-qwen36.sh oder ./servers/start-knecht.sh",
            file=sys.stderr,
        )
        sys.exit(1)
    print("  Health-Check: OK")

    job_dir, work_dir, output_dir = setup_job_dirs(args.job_slug)
    print(f"  Job-Scratch: {job_dir}")
    copy_fixture_to_job(fixture_dir, job_dir / "input", work_dir)
    link_opencode_config(job_dir, code_home)

    flags: dict[str, bool] = {}
    turn_results = []
    session_id = None

    for index, turn in enumerate(turns, start=1):
        message, source, branch = select_message(turn, flags)
        jsonl_path = output_dir / f"turn-{turn['id']}.jsonl"
        before = snapshot_work(work_dir)

        print(f"  Turn {turn['id']} ({turn['label']}, {branch}, {source}) ...")
        run_turn(args.model, message, session_id, work_dir, jsonl_path)

        analysis = analyze_events(read_events(jsonl_path))
        after = snapshot_work(work_dir)
        diff = diff_stats(before, after)

        if index == 1:
            session_id = analysis.get("session_id")
            if not session_id:
                print(
                    "FEHLER: keine sessionID in den Events von Turn 1 — Folge-Turns wuerden "
                    f"eine neue Session oeffnen. Stream pruefen: {jsonl_path}",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"    sessionID: {session_id}")
            flags["asked_clarifying"] = looks_like_clarifying_question(analysis)
            print(f"    asked_clarifying: {flags['asked_clarifying']}")

        print(
            f"    steps={analysis['steps']} tools={analysis['tool_calls']} "
            f"stop={analysis['stop_reason']} diff=+{diff['lines_added']}/-{diff['lines_removed']}"
        )

        turn_results.append({
            "id": turn["id"],
            "label": turn["label"],
            "branch": branch,
            "message_source": source,
            "message_chars": len(message),
            "steps": analysis["steps"],
            "tool_calls": analysis["tool_calls"],
            "tools_breakdown": analysis["tools_breakdown"],
            "edit_tool_calls": analysis["edit_tool_calls"],
            "stop_reason": analysis["stop_reason"],
            "duration_s": analysis["duration_s"],
            "question_mark": "?" in analysis["final_text"],
            "final_text": analysis["final_text"][:200],
            "diff": diff,
            "run_jsonl": str(jsonl_path),
        })

    lint_result = run_python_lint(work_dir)
    if lint_result.get("passed"):
        print(f"  Python-Lint: OK ({lint_result['checked']} Dateien)")
    else:
        print(f"  Python-Lint: {lint_result.get('note', str(len(lint_result.get('violations', []))) + ' violations')}")

    oracle_exit = run_oracle(fixture_dir, job_dir)
    status = "PASS" if oracle_exit == 0 else ("FAIL" if oracle_exit is not None else "ERROR")

    last_turn = turn_results[-1]
    result = {
        "model": args.model,
        "fixture": args.fixture,
        "job_slug": args.job_slug,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "harness": "opencode-multiturn",
        "multiturn": {
            "turns": len(turn_results),
            "asked_clarifying": flags.get("asked_clarifying"),
            "turn2_branch": turn_results[1]["branch"] if len(turn_results) > 1 else None,
            "steps_total": sum(t["steps"] for t in turn_results),
            "tool_calls_total": sum(t["tool_calls"] for t in turn_results),
            "final_turn_diff": last_turn["diff"],
            "session_id": session_id,
        },
        "turns": turn_results,
        "parser_output": {
            "duration_s": last_turn["duration_s"],
            "steps": last_turn["steps"],
            "tool_calls": last_turn["tool_calls"],
            "tools_breakdown": last_turn["tools_breakdown"],
            "final_text": last_turn["final_text"],
            "stop_reason": last_turn["stop_reason"],
            "session_id": session_id,
        },
        "python_lint": lint_result,
        "oracle_exit": oracle_exit,
        "scratch_path": str(job_dir),
    }

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    result_file = save_result(result, args.model, args.fixture, date_str)

    print(
        f"Turns: {len(turn_results)}, Steps gesamt: {result['multiturn']['steps_total']}, "
        f"asked_clarifying: {result['multiturn']['asked_clarifying']}"
    )
    print(f"Letzter Turn: +{last_turn['diff']['lines_added']}/-{last_turn['diff']['lines_removed']} Zeilen")
    print(f"Oracle: {'PASS' if oracle_exit == 0 else 'FAIL' if oracle_exit is not None else 'kein oracle.sh'}")
    print(f"Result: {result_file}")
    print(f"Status: {status}")


if __name__ == "__main__":
    main()
