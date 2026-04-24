#!/usr/bin/env python3
"""check_claude_md.py

CLAUDE.md に対するチェック C01 / C02 / C03 を実行する。
run_all.py から呼ばれる。単独でも動く。

Usage:
    python3 check_claude_md.py --target /path/to/project [--claude-md-max-lines 50]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _approx_tokens(text: str) -> int:
    """CJK 混在テキスト向け: char / 3 を概算トークン"""
    return max(1, len(text) // 3)


def check_c01(path: Path, max_lines: int) -> dict[str, Any] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    n = len(lines)
    if n <= max_lines:
        return None
    return {
        "id": "C01",
        "severity": "WARNING",
        "message": f"CLAUDE.md が {n} 行 (budget: {max_lines})",
        "file": str(path),
        "line_start": max_lines + 1,
        "line_end": n,
        "why": "Bloated CLAUDE.md files cause Claude to ignore your actual instructions (Anthropic 公式)",
        "fix_hint": "超過セクションを docs/*.md に移して '@docs/...md' でインポート、または不要ルールを削除",
        "doc_ref": "https://code.claude.com/docs/en/best-practices",
    }


def check_c02(path: Path, max_tokens: int) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    t = _approx_tokens(text)
    if t <= max_tokens:
        return None
    return {
        "id": "C02",
        "severity": "WARNING",
        "message": f"CLAUDE.md が約 {t} tokens (budget: {max_tokens})",
        "file": str(path),
        "why": "primacy bias は 150-200 行超 (〜2000 tokens) で顕在化 (IFScale 研究)",
        "fix_hint": "不要な記述を刈る。コードから推測できる情報は削除 (Anthropic 公式 include/exclude リスト参照)",
        "doc_ref": "https://nyosegawa.com/en/posts/harness-engineering-best-practices-2026/",
    }


_LIST_RE = re.compile(r"^\s*(-|\*|\+|\d+\.)\s+")
_HEADING_RE = re.compile(r"^#{1,6}\s+")
_CODE_FENCE_RE = re.compile(r"^```")


def check_c03(path: Path, max_prose_block: int = 20) -> dict[str, Any] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    prose_start: int | None = None
    in_code = False
    longest_block_lines = 0
    longest_block_start = 0
    current_block_start = 0

    for i, line in enumerate(lines, start=1):
        if _CODE_FENCE_RE.match(line):
            in_code = not in_code
            # コードブロック境界で prose トラッキングリセット
            if prose_start is not None and i - prose_start > longest_block_lines:
                longest_block_lines = i - prose_start
                longest_block_start = prose_start
            prose_start = None
            continue
        if in_code:
            if prose_start is not None and i - prose_start > longest_block_lines:
                longest_block_lines = i - prose_start
                longest_block_start = prose_start
            prose_start = None
            continue
        stripped = line.strip()
        if not stripped or _HEADING_RE.match(line) or _LIST_RE.match(line):
            if prose_start is not None:
                length = i - prose_start
                if length > longest_block_lines:
                    longest_block_lines = length
                    longest_block_start = prose_start
            prose_start = None
        else:
            if prose_start is None:
                prose_start = i
    if prose_start is not None:
        length = len(lines) - prose_start + 1
        if length > longest_block_lines:
            longest_block_lines = length
            longest_block_start = prose_start

    if longest_block_lines > max_prose_block:
        return {
            "id": "C03",
            "severity": "INFO",
            "message": f"CLAUDE.md に {longest_block_lines} 行の散文ブロック",
            "file": str(path),
            "line_start": longest_block_start,
            "line_end": longest_block_start + longest_block_lines - 1,
            "why": "長い散文ブロックはポインタ主義から外れている兆候",
            "fix_hint": "該当ブロックを docs/*.md に切り出し、CLAUDE.md では @docs/...md で参照",
            "doc_ref": "https://code.claude.com/docs/en/best-practices",
        }
    return None


def run(target: Path, max_lines: int = 50, max_tokens: int = 2000) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    path = target / "CLAUDE.md"
    if not path.exists():
        issues.append(
            {
                "id": "C00",
                "severity": "INFO",
                "message": "CLAUDE.md が存在しない — C01/C02/C03 skip",
                "file": str(path),
                "why": "CLAUDE.md が無いとチェックできない",
                "fix_hint": "/harness-generator を実行するか、CLAUDE.md を手動配置",
            }
        )
        return issues
    for check in (check_c01(path, max_lines), check_c02(path, max_tokens), check_c03(path)):
        if check:
            issues.append(check)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=str)
    parser.add_argument("--claude-md-max-lines", type=int, default=50)
    parser.add_argument("--claude-md-max-tokens", type=int, default=2000)
    args = parser.parse_args()
    issues = run(
        Path(args.target).resolve(),
        max_lines=args.claude_md_max_lines,
        max_tokens=args.claude_md_max_tokens,
    )
    json.dump(issues, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
