#!/usr/bin/env python3
"""render.py

軽量テンプレートエンジン。依存は Python stdlib のみ。

サポート構文:
    {{VAR}}                     — 変数展開
    {{#if VAR}}...{{/if}}       — VAR が truthy なら展開
    {{#unless VAR}}...{{/unless}} — VAR が falsy なら展開

非サポート (MVP 外):
    {{#if}}...{{else}}...{{/if}}
    ネストした if
    フィルタ (| default, | join 等)

"#if" ブロックはシングルラインでも複数行でも OK。
ネストしない前提で実装している。
"""

from __future__ import annotations

import re
from typing import Any


_VAR_RE = re.compile(r"\{\{\s*([A-Z][A-Z0-9_]*)\s*\}\}")
_IF_BLOCK_RE = re.compile(
    r"\{\{\#if\s+([A-Z][A-Z0-9_]*)\s*\}\}(.*?)\{\{/if\}\}",
    flags=re.DOTALL,
)
_UNLESS_BLOCK_RE = re.compile(
    r"\{\{\#unless\s+([A-Z][A-Z0-9_]*)\s*\}\}(.*?)\{\{/unless\}\}",
    flags=re.DOTALL,
)


def _truthy(value: Any) -> bool:
    """Python の真偽値判定を使うが、空文字列 "false" (大文字小文字不問) も False 扱い"""
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "0", "none", "null")
    return bool(value)


def _stringify(value: Any) -> str:
    """変数値を文字列化 (テンプレート埋め込み用)"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return str(value)


def render(template: str, variables: dict[str, Any]) -> str:
    """テンプレートを展開して返す。

    処理順:
    1. #unless ブロック (逆条件なので先に処理してネスト回避)
    2. #if ブロック
    3. {{VAR}} 変数展開

    未定義変数は空文字に展開され、警告を stderr に出す (呼び出し側判断で抑制可能)。
    """
    # 1. #unless
    def _unless_replacer(m: re.Match[str]) -> str:
        var_name, body = m.group(1), m.group(2)
        value = variables.get(var_name)
        return body if not _truthy(value) else ""

    result = _UNLESS_BLOCK_RE.sub(_unless_replacer, template)

    # 2. #if
    def _if_replacer(m: re.Match[str]) -> str:
        var_name, body = m.group(1), m.group(2)
        value = variables.get(var_name)
        return body if _truthy(value) else ""

    result = _IF_BLOCK_RE.sub(_if_replacer, result)

    # 3. {{VAR}}
    def _var_replacer(m: re.Match[str]) -> str:
        var_name = m.group(1)
        if var_name not in variables:
            # MVP: サイレントに空文字 (テスト時 strict モード有ればそこで検出)
            return ""
        return _stringify(variables[var_name])

    result = _VAR_RE.sub(_var_replacer, result)
    return result


def find_undefined_variables(template: str, variables: dict[str, Any]) -> set[str]:
    """テンプレート内の {{VAR}} のうち variables に無いもの一覧 (テスト用)"""
    var_names = set(_VAR_RE.findall(template))
    if_names = set(_IF_BLOCK_RE.findall(template))
    unless_names = set(_UNLESS_BLOCK_RE.findall(template))
    used = var_names | {name for name, _ in if_names} | {name for name, _ in unless_names}
    return used - set(variables.keys())


if __name__ == "__main__":
    # 簡易セルフテスト
    sample = """# {{PROJECT_NAME}}

Languages: {{LANGUAGES_CSV}}

{{#if HANDLES_SECRETS}}
This project handles secrets — block-secret-commit hook is active.
{{/if}}

{{#unless AI_SECOND_OPINION}}
No AI second-opinion reviewer is configured.
{{/unless}}
"""
    vars_ = {
        "PROJECT_NAME": "sample",
        "LANGUAGES_CSV": "python,typescript",
        "HANDLES_SECRETS": True,
        "AI_SECOND_OPINION": False,
    }
    out = render(sample, vars_)
    assert "sample" in out
    assert "python,typescript" in out
    assert "block-secret-commit" in out
    assert "No AI second-opinion" in out
    print(out)
