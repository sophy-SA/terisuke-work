#!/usr/bin/env python3
"""merge_settings.py

.claude/settings.json 用の JSON-deep merge。

戦略:
- dict: キーごとに再帰マージ
- list: union + dedup (要素が string なら完全一致 dedup, dict なら特定キーで照合)
- scalar: "hooks.*" 配下は生成側優先、その他は既存優先

Usage:
    # stdin に 2 つの JSON を区切って渡す (既存 + 生成) → 統合結果を stdout へ
    python3 merge_settings.py <existing.json> <generated.json>

    # 上書きモード: 既存を読み、生成を merge、既存パスに書き戻す
    python3 merge_settings.py --target .claude/settings.json --patch patch.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


# dict 要素として identify する際のキー (ユーザーが追記した同一 matcher hook を上書きしない)
LIST_DEDUP_KEYS_BY_PATH: dict[str, list[str]] = {
    "hooks.PreToolUse.hooks": ["command", "url"],
    "hooks.PostToolUse.hooks": ["command", "url"],
    "hooks.SessionStart.hooks": ["command", "url"],
    "hooks.Stop.hooks": ["command", "url"],
}


def _dedup_list(items: list[Any], path: str) -> list[Any]:
    """str なら set-like dedup、dict ならパス別 identify キーで dedup"""
    if not items:
        return items
    # 文字列 list (permissions.allow / deny 等)
    if all(isinstance(x, str) for x in items):
        seen: set[str] = set()
        out: list[str] = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return sorted(out)
    # dict list (hooks の matcher list 等)
    if all(isinstance(x, dict) for x in items):
        keys = LIST_DEDUP_KEYS_BY_PATH.get(path)
        if not keys:
            # dedup しない (merge 側が後で追加される順序を保持)
            return items
        seen_ids: set[tuple[Any, ...]] = set()
        out_dicts: list[dict[str, Any]] = []
        for d in items:
            ident = tuple(d.get(k) for k in keys)
            if ident in seen_ids:
                continue
            seen_ids.add(ident)
            out_dicts.append(d)
        return out_dicts
    return items


def deep_merge(existing: Any, generated: Any, path: str = "") -> Any:
    """既存と生成を再帰的に統合。path は "hooks.PostToolUse" のようなドット区切り。"""
    # scalar または None
    if not isinstance(existing, (dict, list)) or not isinstance(generated, (dict, list)):
        if path.startswith("hooks."):
            # hooks 配下は生成側優先
            return generated if generated is not None else existing
        # その他は既存優先
        return existing if existing is not None else generated

    # 型違い (既存が dict で生成が list 等): 生成側に置き換える (警告は呼び出し側で)
    if type(existing) is not type(generated):
        return copy.deepcopy(generated)

    # dict
    if isinstance(existing, dict):
        out: dict[str, Any] = dict(existing)
        for k, v_gen in generated.items():
            sub_path = f"{path}.{k}" if path else k
            if k in out:
                out[k] = deep_merge(out[k], v_gen, sub_path)
            else:
                out[k] = copy.deepcopy(v_gen)
        return out

    # list
    if isinstance(existing, list):
        # hooks の matcher 配列は ここで特別扱い: matcher が同一のエントリをマージ
        if path.endswith(".PreToolUse") or path.endswith(".PostToolUse"):
            return _merge_matcher_lists(existing, generated, path)
        # union + dedup
        combined = existing + generated
        return _dedup_list(combined, path)

    return existing


def _merge_matcher_lists(existing: list[dict[str, Any]], generated: list[dict[str, Any]], path: str) -> list[dict[str, Any]]:
    """hooks.PreToolUse / PostToolUse 用の特化マージ。

    各要素は {matcher: str, hooks: [...]} 形式。
    同じ matcher のエントリは hooks を union する。
    """
    by_matcher: dict[str, dict[str, Any]] = {}
    for entry in existing:
        m = entry.get("matcher", "")
        by_matcher.setdefault(m, {"matcher": m, "hooks": []})
        by_matcher[m]["hooks"].extend(entry.get("hooks", []))
    for entry in generated:
        m = entry.get("matcher", "")
        if m not in by_matcher:
            by_matcher[m] = {"matcher": m, "hooks": []}
        by_matcher[m]["hooks"].extend(entry.get("hooks", []))

    # hooks 内部の dedup
    out: list[dict[str, Any]] = []
    for m, entry in by_matcher.items():
        dedup_path = f"{path}.hooks"
        entry["hooks"] = _dedup_list(entry["hooks"], dedup_path)
        out.append(entry)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "existing",
        nargs="?",
        type=str,
        help="既存 JSON ファイルパス (または --target)",
    )
    parser.add_argument(
        "generated",
        nargs="?",
        type=str,
        help="生成 JSON ファイルパス (または --patch)",
    )
    parser.add_argument("--target", type=str, help="in-place merge する target JSON")
    parser.add_argument("--patch", type=str, help="--target に適用する patch JSON")
    args = parser.parse_args()

    if args.target and args.patch:
        target_path = Path(args.target)
        patch_path = Path(args.patch)
        existing = json.loads(target_path.read_text(encoding="utf-8")) if target_path.exists() else {}
        generated = json.loads(patch_path.read_text(encoding="utf-8"))
        merged = deep_merge(existing, generated)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Merged into {target_path}", file=sys.stderr)
        return 0

    if args.existing and args.generated:
        existing = json.loads(Path(args.existing).read_text(encoding="utf-8"))
        generated = json.loads(Path(args.generated).read_text(encoding="utf-8"))
        merged = deep_merge(existing, generated)
        json.dump(merged, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
