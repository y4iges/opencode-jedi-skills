#!/usr/bin/env python3
"""
Install script for opencode-jedi-skills.

Copies SKILL.md and jedi_tool.py to ~/.config/opencode/skills/jedi-analysis/
"""

import sys
from pathlib import Path


def get_skill_dir() -> Path:
    base = Path.home() / ".config" / "opencode" / "skills" / "jedi-analysis"
    return base


def install():
    skill_dir = get_skill_dir()
    script_dir = Path(__file__).parent

    print(f"Installing opencode-jedi-skills to {skill_dir}")

    skill_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("SKILL.md", "jedi_tool.py"):
        src = script_dir / filename
        dst = skill_dir / filename
        if src.exists():
            dst.write_bytes(src.read_bytes())
            print(f"  Copied {filename}")
        else:
            print(f"  WARNING: {filename} not found in script directory")

    print()
    print("Installation complete!")
    print(f"  Skill directory: {skill_dir}")
    print()
    print("Next steps:")
    print("  1. Add rules to your opencode AGENTS.md:")
    print("     cat agents-template.md >> ~/.config/opencode/AGENTS.md")
    print("  2. Restart opencode to load the skill.")
    print()
    print("Requirements: pip install jedi")


if __name__ == "__main__":
    install()
