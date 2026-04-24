#!/usr/bin/env python3
"""check_permissions.py

.claude/settings.json + hooks + subagents に対する秘密情報スキャン (C10) と
profile-driven な C13 (handles_secrets → secret block hook 必須) を実行する。

Usage:
    python3 check_permissions.py --target /path/to/project [--profile ./profile.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("GitHub token (new)", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub token (old)", re.compile(r"gho_[A-Za-z0-9]{36}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Private key (PEM)", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Generic key=value", re.compile(r'(?i)(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*["\'][^"\'\s]{12,}["\']')),
]


def scan_file_for_secrets(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    issues: list[dict[str, Any]] = []
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            # 行番号を計算
            line_no = text[: match.start()].count("\n") + 1
            snippet = match.group(0)[:60] + ("..." if len(match.group(0)) > 60 else "")
            issues.append(
                {
                    "id": "C10",
                    "severity": "ERROR",
                    "message": f"秘密情報の疑い ({name}): {snippet}",
                    "file": str(path),
                    "line_start": line_no,
                    "line_end": line_no,
                    "why": "秘密情報を .claude/ や repo に含めると commit で漏洩、rotation が必要になる",
                    "fix_hint": "該当値を環境変数 or Secret Manager に移し、スクリプトからは $VAR_NAME で参照",
                }
            )
    return issues


def check_c10(target: Path) -> list[dict[str, Any]]:
    """C10: 全 .claude/ 配下と settings.json を秘密情報スキャン"""
    issues: list[dict[str, Any]] = []
    claude_dir = target / ".claude"
    if not claude_dir.exists():
        return issues
    for path in claude_dir.rglob("*"):
        if path.is_file() and path.suffix in (".json", ".sh", ".md", ".yaml", ".yml"):
            issues.extend(scan_file_for_secrets(path))
    return issues


def check_c13(target: Path, profile_path: Path) -> list[dict[str, Any]]:
    """C13: handles_secrets=true なら block-secret-commit hook が必須"""
    if not profile_path.exists():
        return []
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    handles_secrets = (profile.get("safety") or {}).get("handles_secrets", False)
    if not handles_secrets:
        return []
    # hook script の存在確認
    hook_script = target / ".claude" / "hooks" / "block-secret-commit.sh"
    settings_path = target / ".claude" / "settings.json"
    script_exists = hook_script.exists()
    # settings.json で参照されているか
    registered = False
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            for entries in (settings.get("hooks") or {}).values():
                for entry in entries:
                    for h in entry.get("hooks", []):
                        cmd = h.get("command", "")
                        if "block-secret-commit" in cmd:
                            registered = True
        except json.JSONDecodeError:
            pass
    if script_exists and registered:
        return []
    return [
        {
            "id": "C13",
            "severity": "WARNING",
            "message": (
                "profile.safety.handles_secrets=true なのに block-secret-commit hook が "
                + ("未配置" if not script_exists else "未登録 (settings.json で参照されていない)")
            ),
            "file": str(target),
            "why": "秘密情報を扱う宣言がある harness に秘密漏洩ガードが無い = リスク",
            "fix_hint": "'/harness-generator --force-overwrite .claude/hooks/block-secret-commit.sh' で再生成、または手動配置 + settings.json 登録",
        }
    ]


def run(target: Path, profile_path: Path) -> list[dict[str, Any]]:
    return check_c10(target) + check_c13(target, profile_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=str)
    parser.add_argument("--profile", type=str, default=None)
    args = parser.parse_args()
    target = Path(args.target).resolve()
    profile_path = Path(args.profile).resolve() if args.profile else target / "profile.json"
    issues = run(target, profile_path)
    json.dump(issues, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
