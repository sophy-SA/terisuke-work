#!/usr/bin/env python3
"""run_all.py

harness-validator のメインエントリ。全チェックを実行し、report.schema.json 準拠の
JSON と人間可読 Markdown の両方を出力する。

Usage:
    python3 run_all.py \
        --target . \
        --output-json ./harness-report.json \
        --output-md ./harness-report.md

Exit:
    0  全チェック完走 (errors==0)
    1  チェック実行エラー (スクリプト起動失敗等)
    2  errors > 0 の検出あり
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any


def _resolve_assets_dir(explicit: str | None = None) -> Path:
    """assets ディレクトリを解決する (Phase 9 packaging 対応).

    優先順位: 明示 > HARNESS_FORGE_ASSETS 環境変数 > script location 相対
    """
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("HARNESS_FORGE_ASSETS")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    candidate = here.parents[3] / "assets"
    if candidate.exists():
        return candidate
    # Validator は assets が無くても動く (check_*.py は独立)。None を返さず raise はせず、
    # report schema だけ使えなくてもよい
    return here.parents[3] / "assets"  # 存在しなくてもパスとして返す (後続で check)

sys.path.insert(0, str(Path(__file__).parent))
try:
    from check_claude_md import run as run_claude_md  # type: ignore[import-not-found]
    from check_hooks import run as run_hooks  # type: ignore[import-not-found]
    from check_permissions import run as run_permissions  # type: ignore[import-not-found]
    from check_subagents import run as run_subagents  # type: ignore[import-not-found]
except ImportError as e:
    print(f"FATAL: check_*.py が sibling に無い: {e}", file=sys.stderr)
    sys.exit(1)


VALIDATOR_VERSION = "0.1.0"


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_report(target: Path, profile_path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {"errors": 0, "warnings": 0, "info": 0}
    for issue in issues:
        sev = issue.get("severity", "INFO")
        if sev == "ERROR":
            summary["errors"] += 1
        elif sev == "WARNING":
            summary["warnings"] += 1
        else:
            summary["info"] += 1

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "target": str(target),
        "generated_at": _iso_now(),
        "validator_version": VALIDATOR_VERSION,
        "summary": summary,
        "issues": issues,
    }
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            report["profile"] = {
                "archetype_primary": profile.get("archetype_primary", ""),
                "schema_version": profile.get("schema_version", ""),
            }
        except json.JSONDecodeError:
            pass
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Harness Validation Report")
    lines.append("")
    lines.append(f"- Target: `{report['target']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    prof = report.get("profile")
    if prof:
        lines.append(
            f"- Profile: archetype={prof.get('archetype_primary', 'unknown')} (schema v{prof.get('schema_version', '?')})"
        )
    lines.append(f"- Validator: v{report['validator_version']}")
    s = report["summary"]
    lines.append("")
    lines.append(f"**Summary**: {s['errors']} errors, {s['warnings']} warnings, {s['info']} info")
    lines.append("")

    by_severity: dict[str, list[dict[str, Any]]] = {"ERROR": [], "WARNING": [], "INFO": []}
    for issue in report["issues"]:
        by_severity.setdefault(issue.get("severity", "INFO"), []).append(issue)

    for sev in ("ERROR", "WARNING", "INFO"):
        items = by_severity.get(sev, [])
        if not items:
            continue
        lines.append(f"## {sev}S")
        lines.append("")
        for issue in items:
            file = issue.get("file", "")
            line_start = issue.get("line_start")
            loc = f"{file}:{line_start}" if line_start else file
            lines.append(f"### [{issue['id']}] {issue['message']}")
            if loc:
                lines.append(f"- **File**: `{loc}`")
            if issue.get("why"):
                lines.append(f"- **WHY**: {issue['why']}")
            if issue.get("fix_hint"):
                lines.append(f"- **FIX**: {issue['fix_hint']}")
            if issue.get("doc_ref"):
                lines.append(f"- **Ref**: {issue['doc_ref']}")
            lines.append("")
    if not report["issues"]:
        lines.append("_No issues found._")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=".", type=str)
    parser.add_argument("--output-json", default="./harness-report.json", type=str)
    parser.add_argument("--output-md", default="./harness-report.md", type=str)
    parser.add_argument("--profile", default=None, type=str)
    parser.add_argument("--claude-md-max-lines", type=int, default=50)
    parser.add_argument("--claude-md-max-tokens", type=int, default=2000)
    args = parser.parse_args()

    target = Path(args.target).resolve()
    profile_path = Path(args.profile).resolve() if args.profile else target / "profile.json"

    all_issues: list[dict[str, Any]] = []
    all_issues.extend(
        run_claude_md(target, max_lines=args.claude_md_max_lines, max_tokens=args.claude_md_max_tokens)
    )
    all_issues.extend(run_hooks(target))
    all_issues.extend(run_subagents(target))
    all_issues.extend(run_permissions(target, profile_path))

    report = build_report(target, profile_path, all_issues)

    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.output_md).write_text(render_markdown(report), encoding="utf-8")

    # stdout にサマリーを出す
    s = report["summary"]
    print(f"Harness Validation: {s['errors']} errors, {s['warnings']} warnings, {s['info']} info")
    print(f"  JSON: {args.output_json}")
    print(f"  MD:   {args.output_md}")
    if s["errors"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
