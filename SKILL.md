---
name: jedi-analysis
description: Python code analysis via jedi_tool.py CLI — file overview, class members, method source, find references, project-wide search. Structure via ast, references via jedi.
version: 4.0.0
author: opencode-skill
tags: [python, static-analysis, code-structure, find-references]
compatibility: opencode
---

# Python Code Analysis Tool

## Tool Location

`C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py`

## Commands

### `overview <file>` — Map of file structure

Replaces reading files >500 lines. Returns: classes with all methods, imports, functions, variables.

```bash
python "C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py" overview path/to/file.py
```

**Output example (2362-line file → 60 lines):**
```
=== bot_deep_buy.py (2362 lines) ===

IMPORTS:
  import pandas as pd
  ...

class Bot (L25, 52 methods):
  __init__(config=None)                                 L26
  process_candle(candle, timestamp, ...)                L414
  _check_volume_impulse_long(indicators, timestamp)     L818
  ...
```

### `members <file> <name|line>` — Class API or single method source

**If name matches a class:** shows all methods with signatures and docstrings.

**If name matches a method:** shows signature, docstring, and full source code of that method.
This is the most efficient path — one call gives you everything about a method.

```bash
python "C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py" members path/to/file.py ClassName
python "C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py" members path/to/file.py _check_volume_impulse_long
```

**Output for method:**
```
=== _check_volume_impulse_long (method of Bot, L818, 101 lines) ===
  _check_volume_impulse_long(indicators, timestamp)
  doc: Вход в лонг по объемному импульсу в ап‑тренде.

    def _check_volume_impulse_long(self, indicators, timestamp):
        """..."""
        ... full source code ...
```

### `body <file> <line>` — Source code at line number

Returns the full source of the function/method/class at the given line.
Useful after `overview` when you know the line number but not the method name.

```bash
python "C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py" body path/to/file.py 818
```

**Output:**
```
=== _check_volume_impulse_long (function, L818-L918, 101 lines) ===

    def _check_volume_impulse_long(self, indicators, timestamp):
        """..."""
        ... full source code ...
```

### `refs <file> <line> <col>` — Find all references to a name

Shows DEFINITION + all REFERENCE locations. **Column must point to the identifier name, not `def` keyword.**

```bash
python "C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py" refs path/to/file.py 1612 8
python "C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py" refs path/to/file.py 1612 8 --scope file
```

**Important:** `line` is 1-based, `col` is 0-based. Position on the name itself (e.g. `_create_buy_event` starts at col 8 in `    def _create_buy_event(...)`).

### `search <dir> <name>` — Project-wide name search

Finds where a class/function/variable is defined across all Python files in a project.

```bash
python "C:/Users/y4igb/.config/opencode/skills/jedi-analysis/jedi_tool.py" search /path/to/project ClassName
```

All commands accept `--json` for machine-readable output.

---

## Decision Guide

### USE jedi_tool when:
- **File >500 lines** → `overview` shows structure in ~30 lines instead of reading everything
- **Need a specific method's code** → `members file.py methodName` returns signature + docstring + full source in one call
- **Multi-file project** → `search` finds definitions without reading all files
- **Before refactoring** → `refs` shows exactly where a function/variable is used
- **Unfamiliar class** → `members file.py ClassName` gives full API with signatures and docstrings
- **Know line number from overview** → `body file.py <line>` returns enclosing function's source

### DON'T use when:
- **File <300 lines** → just `read` the file, it's faster
- **Simple text search** → `grep` is faster and more reliable for string patterns
- **Need to understand LOGIC** → the tool shows structure, not meaning
- **Dynamic code** (`getattr`, `__getattr__`, monkey-patching) → invisible to static analysis

### Known Limitations

1. **Dynamic code:** `getattr`, `__getattr__`, monkey-patching → invisible to both ast and jedi
2. **`refs` column positioning:** must point to the identifier name, not the `def`/`class` keyword
3. **`search` performance:** first call on large project takes 1-5 seconds
4. **`search` scope:** jedi searches for Python names, not arbitrary text — use grep for text patterns
5. **Broken syntax:** `overview`/`members` fail on files with syntax errors (uses ast.parse)
6. **Inherited methods:** `members` only shows methods defined in the class itself, not inherited

### When to prefer grep/read over jedi_tool

| Task | Use |
|------|-----|
| Find text pattern (`TODO`, `config.get`) | `grep` |
| Read specific lines | `read` with offset |
| File <300 lines | `read` the whole thing |
| Understand algorithm logic | `read` the code |
| Find class definition in project | `jedi_tool.py search` |
| Map a 1000+ line file | `jedi_tool.py overview` |
| Get a method's signature + source | `jedi_tool.py members file.py methodName` |
| Get source at known line number | `jedi_tool.py body file.py <line>` |
| Find all usages of a function | `jedi_tool.py refs` |

---

## Experience Log

This section tracks real-world usage results. Update as you use the tool.

- **overview**: Works perfectly. ast-based, fast, reliable. Tested on 2362-line file → 52 methods listed correctly.
- **members (class)**: Works. Shows signatures + docstrings. Unicode handled.
- **members (method)**: Works. Returns signature, docstring, class context, and full source code. Tested on `_check_volume_impulse_long` (101 lines) — correct output. Falls back to method search after class/function lookup fails.
- **body**: Works. Returns full source of function/method/class at given line. Handles inner line numbers (e.g. line 825 inside method starting at 818) — finds the enclosing function. Tested on line 818 and 825.
- **refs**: Works. Found 7 references to `_create_buy_event` across a 2362-line file. Column must be on the identifier, not `def`.
- **search**: Works for proper Python packages. May fail for ad-hoc directories. Tested: found `Script` in jedi package.
