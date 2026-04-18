# OpenCode Agent Workflow — Session Summary

## Overview

This session established a skill-based agent workflow for OpenCode, centered around the jedi-analysis Python code analysis tool and a custom skill-cache persistence plugin.

## Final Architecture

```
User Request
     │
     ▼
Main Agent (AGENTS.md rules)
     │
     ├── Python analysis? → @jedi subagent (agents/jedi.md)
     │       │
     │       ├── skill_read("jedi:overview:...") → cache hit? → return
     │       ├── cache miss? → run jedi_tool.py → skill_save() → return
     │       └── file changed? → STALE → re-run → skill_save()
     │
     └── Other tasks → native tools (read, grep, bash, task)
```

## Components

### 1. skill-cache Plugin (`~/.config/opencode/plugins/skill-cache.ts`)

A custom OpenCode plugin providing 4 tools for caching expensive analysis results to disk.

| Tool | Purpose |
|------|---------|
| `skill_save(key, content, sourceFiles?)` | Cache result + track source file mtimes |
| `skill_read(key)` | Return cached content, STALE, or NOT_FOUND |
| `skill_list()` | List all cached entries with staleness status |
| `skill_invalidate(key)` | Delete a cached entry |

**Key design decisions:**
- Keys are normalized to forward slashes for cross-platform consistency
- Source file mtimes are tracked — cache auto-invalidates when files change
- Cache is per-project (hashed project root path)
- Stored at `~/.local/share/opencode/skill-cache/<project-hash>/<entry>.json`
- Zero external dependencies

### 2. @jedi Subagent (`~/.config/opencode/agents/jedi.md`)

A read-only subagent with bash access for running jedi_tool.py.

**Permissions:** edit=deny, write=deny, bash=allow

**Cache workflow built into prompt:**
1. Before running jedi_tool → call `skill_read("jedi:<command>:<filepath>")`
2. Cache hit → return immediately
3. Cache miss or STALE → run jedi_tool → `skill_save()` result

**Supported commands:**
- `overview <file>` — full file structure map
- `members <file> <ClassName>` — all methods with signatures
- `members <file> <methodName>` — specific method source
- `body <file> <line>` — source at line number
- `refs <file> <line> <col>` — find all references
- `search <dir> <name>` — project-wide definition search

### 3. AGENTS.md (`~/.config/opencode/AGENTS.md`)

Global rules loaded for all agents:
- Skill Cache usage instructions
- Task Agent Skill Delegation rules (tells main agent to delegate Python work to @jedi)
- Python Code Analysis MANDATORY rules (when to use jedi_tool vs read/grep)

### 4. jedi_tool.py (`~/.config/opencode/skills/jedi-analysis/jedi_tool.py`)

The underlying Python analysis tool using jedi + ast libraries. Called by @jedi agent via bash.

### 5. opencode.jsonc (`~/.config/opencode/opencode.jsonc`)

```json
{
  "plugin": ["skill-cache"],
  "provider": { ... }
}
```

## What Was Tried and Rejected

### opencode-agent-skills Plugin (rejected)

Attempted to use the opencode-agent-skills plugin for automatic skill discovery and injection. Rejected because:
- Only injected skill names/descriptions, not full content
- Semantic matching (embeddings) failed to match obvious cases like "find Bot class" → jedi-analysis
- Required agents to explicitly call `use_skill()` — they ignored it
- Full auto-injection approach bloated context with all skills for every session

### instructions Field (rejected)

Attempted `opencode.jsonc` `instructions` field to load jedi rules. Rejected because:
- Not universal — requires manual update per skill added
- Duplicate content with AGENTS.md

### opencode-background-agents Plugin (deferred)

Evaluated for async background delegation. Deferred because:
- Enforces read-only agents only (bash=deny) — incompatible with jedi_tool
- Over-engineered for current needs (600+ lines)
- The skill-cache plugin achieves the core benefit (persistence across compaction) without the complexity

## Lessons Learned

1. **Windows backslash hell** — Agent passes `E:\\AI\\...` (double backslash), JSON stores `E:\AI\...` (single), hashes differ. Fix: normalize all keys to forward slashes in the plugin.

2. **Plugin loading** — OpenCode plugins must be listed in `opencode.jsonc` under the `"plugin"` array. Local plugins go in `~/.config/opencode/plugins/`.

3. **Subagents get their own sessions** — Content injected into the main session does NOT propagate to Task subagent sessions. Each subagent needs rules baked into its agent definition (agents/*.md).

4. **Agent prompts > semantic matching** — The LLM is the best pattern matcher. Telling the agent via prompt "use @jedi for Python work" works better than embedding similarity matching.

## File Map

```
~/.config/opencode/
├── opencode.jsonc                    # Plugin + provider config
├── AGENTS.md                         # Global agent rules
├── agents/
│   └── jedi.md                       # @jedi subagent definition
├── plugins/
│   └── skill-cache.ts                # Cache persistence plugin
├── skills/
│   ├── jedi-analysis/
│   │   ├── SKILL.md                  # Skill metadata
│   │   └── jedi_tool.py              # Analysis tool
│   └── opencode-agent-skills/        # Rejected plugin (kept for reference)
```

## How to Add New Skills

1. Create skill tool (e.g. `skills/my-skill/tool.py`)
2. Create agent definition (`agents/my-skill.md`) with tool instructions + cache workflow
3. Update AGENTS.md with delegation rules for the new skill
4. No plugin changes needed — skill_cache is universal
