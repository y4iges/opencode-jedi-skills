# Add this section to your opencode AGENTS.md file
# 
# Copy the content below and paste it at the end of your ~/.config/opencode/AGENTS.md
#
# ─────────────────────────────────────────────────────────────────────────────

## Skill Cache — Persistence Layer

Tools: `skill_save`, `skill_read`, `skill_list`, `skill_invalidate`

Cache expensive analysis results to disk. Survives context compaction and session restarts.
Source file mtimes are tracked — cached results auto-invalidate when files change.

Workflow for any expensive analysis:
1. `skill_read("key")` → if cached, use it
2. If STALE or NOT_FOUND → run analysis
3. `skill_save("key", result, sourceFiles="path/to/file.py")` → cache for reuse

## Python Code Analysis — MANDATORY `jedi_tool.py`

### Execution model — PREFER INLINE, delegate only when parallel

**Inline (default):** Run jedi_tool directly via bash during chain of thought. Check cache first.

```
1. skill_read("jedi:overview:") → hit? → use result, done
2. Miss? → bash: python jedi_tool.py overview <file> → skill_save()
3. Continue working — full context, zero duplicate tokens
```

**Delegated (only for parallel work):** Summon `@jedi` when you need analysis to run while you do other things. Results are cached and shared.

### Cache key format (shared between main agent and @jedi)

- `jedi:overview:`
- `jedi:members::<name>`
- `jedi:body::<line>`
- `jedi:refs::<line>:<col>`
- `jedi:search:<dir>:<name>`

Always include `sourceFiles` param when saving so staleness is tracked.

### jedi_tool.py location

Tool: `python "C:/Users/<USER>/.config/opencode/skills/jedi-analysis/jedi_tool.py"`

### When to use jedi_tool instead of `read`

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