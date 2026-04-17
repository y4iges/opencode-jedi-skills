# opencode-jedi-skills

Static analysis tool for Python code, integrated as an [opencode](https://github.com/anomalyco/opencode) skill.

Uses **ast** for structure extraction and **[jedi](https://github.com/davidhalter/jedi)** for references — no need to read entire files.

## What it does

| Command | What you get |
|----------|--------------|
| `overview <file>` | File map: classes, methods, imports, line numbers (~30 lines instead of 2000+) |
| `members <file> <name>` | If class → all methods with signatures. If method → full source code + docstring |
| `body <file> <line>` | Source of the function/class at given line number |
| `refs <file> <line> <col>` | All references to a variable/function (definitions + usages) |
| `search <dir> <name>` | Find where a name is defined across the whole project |

## Requirements

- Python 3.8+
- `jedi` library: `pip install jedi`

## Installation

```bash
python install.py
```

This copies `SKILL.md` and `jedi_tool.py` to `~/.config/opencode/skills/jedi-analysis/`.

After installation, add the rules to your opencode `AGENTS.md`:

```bash
# Copy the rules from agents-template.md to your AGENTS.md
cat agents-template.md >> ~/.config/opencode/AGENTS.md
```

Or manually add the content from `agents-template.md` to `~/.config/opencode/AGENTS.md`.

## Quick example

```bash
# Get structure of a large file
python jedi_tool.py overview /path/to/large_module.py

# Get full source of a specific method
python jedi_tool.py members /path/to/module.py MyClass.my_method

# Find where a function is used
python jedi_tool.py refs /path/to/module.py 123 5
```

## Example output

```
=== Bot (class, L25, 52 methods) ===

  L  26  __init__(config=None)
  L 414  process_candle(candle, timestamp, ...)
  L 818  _check_volume_impulse_long(indicators, timestamp)
```

## Why?

Most language model code analysis tools require reading entire files. For a 2000-line file, that's 2000+ tokens just for structure.

`jedi_tool.py` uses Python's `ast` module to extract structure — it's fast, reliable, and returns only what you need.

## Using with opencode

When configured as a skill, opencode agents automatically use it for Python files >300 lines. See `SKILL.md` for detailed usage rules and `agents-template.md` for opencode configuration.
