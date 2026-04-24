#!/usr/bin/env python3
"""check_subagents.py

.claude/subagents/*.md と CLAUDE.md 参照に対するチェック C07 / C08。

Usage:
    python3 check_subagents.py --target /path/to/project
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


KNOWN_TOOLS = {
    "Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebSearch", "WebFetch",
    "TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet",
    "NotebookEdit", "Agent", "AskUserQuestion", "ExitPlanMode",
    "SendMessage", "LSP", "Monitor", "ScheduleWakeup",
}


def _parse_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = parts[1]
    # 簡易 YAML パース (PyYAML があれば使う)
    try:
        import yaml
        return yaml.safe_load(fm) or {}
    except ImportError:
        # 最低限: tools: の1行抽出
        result: dict[str, Any] = {}
        for line in fm.splitlines():
            m = re.match(r"^\s*(\w[\w-]*)\s*:\s*(.*)$", line)
            if m:
                result[m.group(1)] = m.group(2).strip()
        return result


def check_c07(target: Path) -> list[dict[str, Any]]:
    """subagent の tools allowlist に未知ツール名"""
    issues: list[dict[str, Any]] = []
    subagents_dir = target / ".claude" / "subagents"
    if not subagents_dir.exists():
        return issues
    for md in subagents_dir.glob("*.md"):
        fm = _parse_frontmatter(md)
        if not fm or "tools" not in fm:
            continue
        tools_raw = fm["tools"]
        # 文字列または list を扱う
        if isinstance(tools_raw, str):
            tools_list = [t.strip() for t in tools_raw.split(",") if t.strip()]
        elif isinstance(tools_raw, list):
            tools_list = [str(t).strip() for t in tools_raw]
        else:
            continue
        unknown = []
        for t in tools_list:
            # Bash(...) / MCP サーバー形式は base name で判定
            base = t.split("(")[0].strip()
            if base.startswith("mcp__"):
                continue
            if base not in KNOWN_TOOLS:
                unknown.append(t)
        if unknown:
            issues.append(
                {
                    "id": "C07",
                    "severity": "ERROR",
                    "message": f"subagent {md.name} の tools に未知のツール名: {unknown}",
                    "file": str(md),
                    "why": "未知ツール名は silently ignored され、subagent が想定通りに動かない",
                    "fix_hint": f"既知ツール {sorted(KNOWN_TOOLS)[:10]}... から選ぶ or タイポ修正",
                }
            )
    return issues


def check_c08(target: Path) -> list[dict[str, Any]]:
    """CLAUDE.md 参照の subagent が実在するか"""
    issues: list[dict[str, Any]] = []
    claude_md = target / "CLAUDE.md"
    if not claude_md.exists():
        return issues
    text = claude_md.read_text(encoding="utf-8")
    # パターン: .claude/subagents/NAME.md or @NAME (agent)
    refs_path = set(re.findall(r"\.claude/subagents/([a-zA-Z0-9_-]+)\.md", text))
    refs_mention = set(re.findall(r"@([a-zA-Z0-9_-]+)\s+\(agent\)", text))
    subagents_dir = target / ".claude" / "subagents"
    existing = set()
    if subagents_dir.exists():
        existing = {p.stem for p in subagents_dir.glob("*.md")}
    for ref in (refs_path | refs_mention):
        if ref not in existing:
            issues.append(
                {
                    "id": "C08",
                    "severity": "ERROR",
                    "message": f"CLAUDE.md 参照の subagent '{ref}' が .claude/subagents/ に存在しない",
                    "file": str(claude_md),
                    "why": "ユーザー呼び出し時にエラー、混乱の原因",
                    "fix_hint": f"'{ref}.md' を .claude/subagents/ に配置するか、CLAUDE.md の参照を削除",
                }
            )
    return issues


def run(target: Path) -> list[dict[str, Any]]:
    return check_c07(target) + check_c08(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=str)
    args = parser.parse_args()
    issues = run(Path(args.target).resolve())
    json.dump(issues, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
