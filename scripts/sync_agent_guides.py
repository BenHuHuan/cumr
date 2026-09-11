#!/usr/bin/env python3
"""Generate model/compatibility guides from the single canonical AGENTS.md."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ("AGENT.md", "GLM.md", "KIMI.md", "CLAUDE.md", "CODEX.md", "GROK.md")
HEADER = "<!-- Generated from AGENTS.md by scripts/sync_agent_guides.py; do not edit this copy. -->\n\n"


def expected_guide(root=ROOT):
    return HEADER + (root / "AGENTS.md").read_text()


def check_guides(root=ROOT):
    expected = expected_guide(root)
    return [f"{name} differs from AGENTS.md; run make agents"
            for name in GUIDES
            if not (root / name).is_file() or (root / name).read_text() != expected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate; default only checks consistency")
    args = parser.parse_args()
    if args.write:
        content = expected_guide()
        for name in GUIDES:
            (ROOT / name).write_text(content)
        print("Generated " + ", ".join(GUIDES))
    else:
        errors = check_guides()
        if errors:
            raise SystemExit("\n".join(errors))
        print("All model/compatibility guides match AGENTS.md")


if __name__ == "__main__":
    main()
