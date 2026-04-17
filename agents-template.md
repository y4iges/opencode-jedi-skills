# Add this section to your opencode AGENTS.md file
# 
# Copy the content below and paste it at the end of your ~/.config/opencode/AGENTS.md
#
# ─────────────────────────────────────────────────────────────────────────────

## Python Code Analysis — MANDATORY `jedi_tool.py`

Tool: `python "C:/Users/<USER>/.config/opencode/skills/jedi-analysis/jedi_tool.py"`

### MANDATORY — always use jedi_tool instead of `read` when:

| Situation | Command | Why not `read` |
|-----------|---------|----------------|
| Python file **>500 lines** and you need its structure | `overview path/file.py` | `read` wastes tokens on full file; overview gives map in ~30 lines |
| Need a **specific method's** signature + source | `members path/file.py methodName` | Returns signature + docstring + full source in 1 call; `read` requires knowing line range first |
| Need **all methods** of a class | `members path/file.py ClassName` | Lists all signatures + docstrings; `read` would need the whole file |
| Need source at a **known line number** | `body path/file.py <line>` | Returns enclosing function's full source; `read` needs offset/limit guessing |
| Need to find **where** a function/variable is used | `refs path/file.py <line> <col>` | `grep` finds text; refs finds actual Python references (definitions, calls, imports) |
| Need to find a **definition** across project | `search /project/dir <name>` | Finds classes/functions across all .py files; no need to glob+grep |

### DO NOT use jedi_tool when:

- **File <300 lines** — just `read` it, overhead of tool call isn't worth it
- **Text search** (`TODO`, `config.get`, string literals) — use `grep`
- **Need to understand logic/flow** — jedi shows structure, not meaning

### Decision flowchart

```
Is the file a Python file?
  NO  → use read/grep normally
  YES → Is it <300 lines?
        YES → just read it
        NO  → Do you need the whole file's structure?
              YES → overview
              NO  → Do you need a specific method/class?
                    YES → members <name>
                    NO  → Do you need source at a known line?
                          YES → body <line>
                          NO  → Do you need to find usages?
                                YES → refs <line> <col>
                                NO  → Do you need to find a definition in the project?
                                      YES → search <dir> <name>
                                      NO  → use read/grep
```
