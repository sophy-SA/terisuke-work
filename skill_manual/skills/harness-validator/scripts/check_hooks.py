#!/usr/bin/env python3
"""check_hooks.py

.claude/settings.json の hooks 登録に対するチェック C04 / C05 / C12 を実行する。

Usage:
    python3 check_hooks.py --target /path/to/project
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def check_c12_and_parse(settings_path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """C12: settings.json が有効 JSON か。パースできたら (data, []) を返す。

    Returns:
        (parsed_data | None, issues_list)
    """
    issues: list[dict[str, Any]] = []
    if not settings_path.exists():
        return None, []
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        return data, issues
    except json.JSONDecodeError as e:
        issues.append(
            {
                "id": "C12",
                "severity": "ERROR",
                "message": f"settings.json が有効な JSON でない: {e.msg}",
                "file": str(settings_path),
                "line_start": e.lineno,
                "line_end": e.lineno,
                "why": "JSON パース失敗時 Claude Code は警告出力して設定を無視、harness 全体が動かない",
                "fix_hint": "python3 -m json.tool .claude/settings.json でエラー箇所を確認し、引用符/カンマ/括弧を修正",
            }
        )
        return None, issues


def check_c04(settings_data: dict[str, Any], target: Path) -> list[dict[str, Any]]:
    """C04: settings.json で参照される hook script が実在するか"""
    issues: list[dict[str, Any]] = []
    hooks = settings_data.get("hooks", {})
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            continue
        for entry_idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            for handler in entry.get("hooks", []):
                if not isinstance(handler, dict):
                    continue
                if handler.get("type") != "command":
                    continue
                cmd = handler.get("command", "")
                # $CLAUDE_PROJECT_DIR を target に展開
                resolved = cmd.replace('"$CLAUDE_PROJECT_DIR"', str(target))
                resolved = resolved.replace("$CLAUDE_PROJECT_DIR", str(target))
                # クオート除去
                resolved = resolved.strip('"').strip("'")
                # 最初のトークン (コマンド本体) を取得
                first = resolved.split()[0] if resolved.split() else ""
                if not first:
                    continue
                script_path = Path(first)
                if not script_path.is_absolute():
                    script_path = (target / script_path).resolve()
                if not script_path.exists():
                    issues.append(
                        {
                            "id": "C04",
                            "severity": "ERROR",
                            "message": f"hook script が存在しない: {cmd}",
                            "file": f".claude/settings.json (hooks.{event}[{entry_idx}])",
                            "why": "参照先が無いと hook 発火時にエラー、harness 全体が動かない",
                            "fix_hint": f"'{script_path}' を配置するか、settings.json の該当 entry を削除",
                        }
                    )
    return issues


def check_c05(settings_data: dict[str, Any]) -> list[dict[str, Any]]:
    """C05: hook matcher の重複"""
    issues: list[dict[str, Any]] = []
    hooks = settings_data.get("hooks", {})
    for event, entries in hooks.items():
        if not isinstance(entries, list):
            continue
        matcher_counts: defaultdict[str, int] = defaultdict(int)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            m = entry.get("matcher", "")
            matcher_counts[m] += 1
        for m, count in matcher_counts.items():
            if count > 1:
                issues.append(
                    {
                        "id": "C05",
                        "severity": "WARNING",
                        "message": f"hook matcher '{m}' が {event} に {count} 件重複",
                        "file": f".claude/settings.json (hooks.{event})",
                        "why": "同 matcher の複数 entry は実行順序が保証されず意図しないチェインを起こす",
                        "fix_hint": f"{event} の '{m}' entry を 1 つに統合し、複数 handler を hooks 配列で並べる",
                    }
                )
    return issues


def run(target: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    settings_path = target / ".claude" / "settings.json"
    data, c12_issues = check_c12_and_parse(settings_path)
    issues.extend(c12_issues)
    if data is None:
        return issues
    issues.extend(check_c04(data, target))
    issues.extend(check_c05(data))
    return issues


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
