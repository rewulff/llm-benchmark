# Fixture a5-long-edit

## Zweck

A5-Long-Edit-Pattern: grosse Python-Datei (~495 Zeilen), 8 markierte Bugs,
Multi-Edit-Task. Testet ob ein Modell eine lange Datei vollstaendig einlesen,
alle Bugs identifizieren und korrekt beheben kann.

## Erwartetes Verhalten

1. Modell liest `large_module.py` vollstaendig ein
2. Identifiziert alle 8 `# BUG:`-Kommentare
3. Fuhert Edit-Tool-Calls fuer jeden Bug aus (8 separate Edits oder Batch)
4. Speichert die Datei zurueck
5. Antwortet mit `DONE`

## Erwartung aus V4-Benchmark-Befunden

- **Knecht (qwen3-coder-30b):** Scheitert vermutlich — schwaches Context-Handling
  bei langen Dateien, verliert Bugs im mittleren Bereich
- **Qwen3.6 (35B-A3B):** Schafft es — besseres Reasoning, stabiles Context-Window

## Token-Schaetzung

- Input: ~10k Token (495-Zeilen-Datei im Kontext + Prompt)
- Output: ~8k Token (8 Edits mit erklaerenden Kommentaren)

## Oracle-Checks

| # | Funktion | Fehler | Pruefstrategie |
|---|----------|--------|---------------|
| 1 | `calculate_discount` | `price + percentage` statt Rabatt | grep `price * (1 - percentage` |
| 2 | `is_palindrome` | `s == s` statt `s == s[::-1]` | grep `s == s[::-1]` |
| 3 | `flatten_list` | `return nested` ohne Rekursion | `flatten_list` mind. 2x + kein `return nested` |
| 4 | `safe_divide` | kein Schutz gegen b=0 | grep `if b == 0` / `ZeroDivisionError` |
| 5 | `word_count` | `len(text)` statt `len(text.split())` | grep `len(text.split(` |
| 6 | `merge_dicts` | `return a` ohne b | grep `{**a, **b}` / `a.update(b)` / `a \| b` |
| 7 | `reverse_words` | `sentence[::-1]` statt Woerter umkehren | grep `sentence.split` ohne `sentence[::-1]` |
| 8 | `fibonacci` | `return n * n` statt Fibonacci | grep rekursiven Call oder `a, b = b, a + b` |

Oracle-Script: `oracle.sh` — Exit 0 bei allen 8 PASS, Exit 1 sonst.
