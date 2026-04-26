#!/usr/bin/env python3
"""apply_scaffold.py

harness-generator のメインエントリ。profile.json を読み、archetype YAML に基づいて
template を展開して実ファイルを scaffold する。

Usage:
    python3 apply_scaffold.py \
        --profile ./profile.json \
        --archetypes-dir /path/to/assets/archetypes \
        --templates-dir /path/to/assets/templates \
        --schema /path/to/profile.schema.json \
        [--force-overwrite PATH ...] \
        [--dry-run]

Exit:
    0  成功
    1  入力エラー / ファイル未存在
    2  スキーマ検証エラー
    3  archetype が stub (status: planned) で実装未了
    4  ユーザー編集検出、--force-overwrite 必要
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


def _resolve_assets_dir(explicit: str | None = None) -> Path:
    """assets ディレクトリを解決する (Phase 9 packaging 対応).

    優先順位:
    1. 引数で明示指定
    2. 環境変数 HARNESS_FORGE_ASSETS
    3. Script location からの相対パス (symlink は follow される)
    """
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("HARNESS_FORGE_ASSETS")
    if env:
        return Path(env).resolve()
    # scripts/ → skill/ → skills/ → repo_root/
    here = Path(__file__).resolve()
    candidate = here.parents[3] / "assets"
    if candidate.exists():
        return candidate
    raise SystemExit(
        "ERROR: assets dir を解決できません。--archetypes-dir/--templates-dir で指定するか、"
        "HARNESS_FORGE_ASSETS 環境変数を設定してください。"
    )

sys.path.insert(0, str(Path(__file__).parent))
try:
    from render import render  # type: ignore[import-not-found]
    from merge_settings import deep_merge  # type: ignore[import-not-found]
except ImportError as e:
    print(f"FATAL: render.py / merge_settings.py が sibling に無い: {e}", file=sys.stderr)
    sys.exit(1)


GENERATOR_VERSION = "0.1.0"
STATE_FILE = ".harness-forge.state.json"


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return _sha256(path.read_bytes())


# ============================================================================
# YAML ロード (PyYAML 必須)
# ============================================================================


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        print(
            "FATAL: PyYAML が必要。'pip install pyyaml' でインストールしてください。",
            file=sys.stderr,
        )
        sys.exit(1)
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ============================================================================
# Profile 検証とフラット化
# ============================================================================


def validate_profile(profile: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        errors = []
        for err in validator.iter_errors(profile):
            loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"[{loc}] {err.message}")
        return errors
    except ImportError:
        required = {"schema_version", "project", "archetype_primary", "workflow", "quality_gates", "meta"}
        missing = required - profile.keys()
        return [f"missing top-level keys: {sorted(missing)}"] if missing else []


def flatten_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """profile → テンプレート変数 flat dict (references/template-index.md 準拠)"""
    project = profile.get("project", {})
    workflow = profile.get("workflow", {})
    qg = profile.get("quality_gates", {})
    review = profile.get("review", {})
    safety = profile.get("safety", {})
    meta = profile.get("meta", {})

    languages = project.get("languages", []) or []
    root_kind = project.get("root_kind", []) or []
    mobile_platforms = project.get("mobile_platforms", []) or []
    required_checks = qg.get("required_checks", []) or []
    destructive_ops = safety.get("destructive_ops", []) or []
    intents = meta.get("intents", []) or []

    return {
        "PROJECT_NAME": project.get("name", ""),
        "PROJECT_SUMMARY": project.get("summary", ""),
        "LANGUAGES_CSV": ",".join(languages),
        "PRIMARY_LANGUAGE": languages[0] if languages else "",
        "ROOT_KIND_CSV": ",".join(root_kind),
        "ARCHETYPE_PRIMARY": profile.get("archetype_primary", ""),
        "DESIGN_FOCUS": bool(project.get("design_focus", False)),
        "MOBILE_PLATFORMS_CSV": ",".join(mobile_platforms),
        "MOBILE_PLATFORM_IOS": "ios" in mobile_platforms,
        "MOBILE_PLATFORM_ANDROID": "android" in mobile_platforms,
        "MOBILE_PLATFORM_RN": "react-native" in mobile_platforms,
        "MOBILE_PLATFORM_FLUTTER": "flutter" in mobile_platforms,
        "MOBILE_MULTI_PLATFORM": len(mobile_platforms) > 1,
        "LOCALE": meta.get("locale", "ja"),
        "PRECOMMIT_STRICTNESS": workflow.get("precommit_strictness", "lint-only"),
        "PLAN_WORK_REVIEW": bool(workflow.get("plan_work_review", False)),
        "LONG_RUNNING_AGENTS": bool(workflow.get("long_running_agents", False)),
        "CI_EXTERNAL": bool(qg.get("ci_external", False)),
        "CI_EXTERNAL_FALSE": not bool(qg.get("ci_external", False)),
        "HANDLES_SECRETS": bool(safety.get("handles_secrets", False)),
        "AI_SECOND_OPINION": bool(review.get("ai_second_opinion", False)),
        "REQUIRED_CHECKS_CSV": ",".join(required_checks),
        "REQUIRED_LINT": "lint" in required_checks,
        "REQUIRED_FORMAT": "format" in required_checks,
        "REQUIRED_TYPECHECK": "typecheck" in required_checks,
        "REQUIRED_UNIT_TEST": "unit-test" in required_checks,
        "REQUIRED_INTEGRATION_TEST": "integration-test" in required_checks,
        "REQUIRED_SECURITY_SCAN": "security-scan" in required_checks,
        "REQUIRED_A11Y": "a11y" in required_checks,
        "REQUIRED_VISUAL_REGRESSION": "visual-regression" in required_checks,
        "DESTRUCTIVE_OPS_CONTAINS_DEPLOY": "deploy" in destructive_ops,
        "DESTRUCTIVE_OPS_CONTAINS_DB_MIGRATE": "db-migrate" in destructive_ops,
        "DESTRUCTIVE_OPS_CONTAINS_FORCE_PUSH": "force-push" in destructive_ops,
        "DESTRUCTIVE_OPS_CONTAINS_RM_RF": "rm-rf" in destructive_ops,
        "DESTRUCTIVE_OPS_CONTAINS_DROP_TABLE": "drop-table" in destructive_ops,
        "INTENT_1": intents[0] if len(intents) > 0 else "",
        "INTENT_2": intents[1] if len(intents) > 1 else "",
        "INTENT_3": intents[2] if len(intents) > 2 else "",
        "GENERATED_AT": _iso_now(),
        "GENERATOR_VERSION": GENERATOR_VERSION,
    }


# ============================================================================
# Archetype ロード (extends チェーン解決)
# ============================================================================


def load_archetype_chain(archetypes_dir: Path, name: str) -> list[dict[str, Any]]:
    """extends を再帰的に解決。親が先頭、子が末尾の順にリストで返す。"""
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = name
    while current:
        if current in seen:
            raise ValueError(f"archetype extends に循環検出: {current}")
        seen.add(current)
        path = archetypes_dir / f"{current}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"archetype not found: {path}")
        data = load_yaml(path)
        chain.insert(0, data)  # 親を先頭に
        current = data.get("extends")
    return chain


def merge_archetype_chain(chain: list[dict[str, Any]]) -> dict[str, Any]:
    """親→子の順で templates / conditional_templates / hooks / subagents / variables をマージ.

    重要: 同一 dest の template は**子が親を上書き**する (extends の本来の意味)。
    dict の挿入順保持により、親の位置を保ったまま child の内容に差し替わる。
    subagents も同様に dedup する。
    """
    # dest → template entry
    templates_by_dest: dict[str, dict[str, Any]] = {}
    conditional_by_key: dict[str, dict[str, Any]] = {}
    subagents_seen: list[str] = []
    merged_hooks: dict[str, list[dict[str, Any]]] = {}
    merged_variables: dict[str, Any] = {}

    for a in chain:  # parent first, child last
        for t in a.get("templates") or []:
            dest = t.get("dest", "")
            templates_by_dest[dest] = t  # child wins
        for t in a.get("conditional_templates") or []:
            # condition + dest を key として dedup
            key = (t.get("condition", ""), t.get("dest", ""))
            conditional_by_key[str(key)] = t
        for s in a.get("subagents") or []:
            if s not in subagents_seen:
                subagents_seen.append(s)
        merged_variables.update(a.get("variables") or {})
        for event, hooks in (a.get("hooks") or {}).items():
            merged_hooks.setdefault(event, []).extend(hooks)

    return {
        "name": chain[-1].get("name", ""),
        "status": chain[-1].get("status", ""),
        "templates": list(templates_by_dest.values()),
        "conditional_templates": list(conditional_by_key.values()),
        "subagents": subagents_seen,
        "hooks": merged_hooks,
        "variables": merged_variables,
    }


# ============================================================================
# State ファイル管理
# ============================================================================


def load_state(cwd: Path) -> dict[str, Any]:
    path = cwd / STATE_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(cwd: Path, state: dict[str, Any]) -> None:
    path = cwd / STATE_FILE
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ============================================================================
# ファイル書き込み (merge モード対応)
# ============================================================================


def apply_template_entry(
    entry: dict[str, Any],
    templates_dir: Path,
    cwd: Path,
    variables: dict[str, Any],
    state: dict[str, Any],
    force_overwrite: set[str],
    dry_run: bool,
) -> tuple[str, str]:
    """1 つの template を適用。

    Returns:
        (action, message) — action は "created" / "overwritten" / "merged" / "skipped" / "blocked"
    """
    src = templates_dir / entry["src"]
    dest = cwd / entry["dest"]
    mode = entry.get("mode")
    merge_mode = entry.get("merge", "overwrite")

    if not src.exists():
        return ("blocked", f"template 源泉が無い: {src}")

    content = render(src.read_text(encoding="utf-8"), variables)

    existing_hash = _sha256_file(dest)
    previous_hash = state.get("file_hashes", {}).get(str(entry["dest"]))

    if dest.exists():
        if merge_mode == "skip_if_exists":
            return ("skipped", f"既存を尊重: {entry['dest']}")

        # ユーザー編集検出
        user_edited = previous_hash is not None and existing_hash != previous_hash
        if user_edited and entry["dest"] not in force_overwrite and "all" not in force_overwrite:
            return ("blocked", f"ユーザー編集検出 ({entry['dest']}) — --force-overwrite {entry['dest']} が必要")

    # merge
    if merge_mode == "json-deep":
        try:
            generated_json = json.loads(content)
        except json.JSONDecodeError as e:
            return ("blocked", f"生成 JSON が壊れている: {e}")
        if dest.exists():
            try:
                existing_json = json.loads(dest.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                return ("blocked", f"既存 JSON が壊れている ({entry['dest']}): {e}")
            merged = deep_merge(existing_json, generated_json)
        else:
            merged = generated_json
        new_content = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    else:
        new_content = content

    if dry_run:
        return ("would-write", f"{entry['dest']} ({len(new_content)} bytes)")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(new_content, encoding="utf-8")

    if mode:
        try:
            mode_int = int(mode, 8)
            os.chmod(dest, mode_int)
        except (ValueError, OSError) as e:
            return ("created", f"{entry['dest']} 書き込み成功、chmod 失敗: {e}")

    action = "merged" if merge_mode == "json-deep" and existing_hash else ("overwritten" if existing_hash else "created")
    state.setdefault("file_hashes", {})[str(entry["dest"])] = _sha256(new_content.encode("utf-8"))
    state.setdefault("files_written", []).append(
        {
            "path": entry["dest"],
            "merge": merge_mode,
            "action": action,
            "sha256_after": _sha256(new_content.encode("utf-8")),
        }
    )
    return (action, entry["dest"])


# ============================================================================
# 条件評価
# ============================================================================


def eval_condition(condition: str, variables: dict[str, Any]) -> bool:
    """単純な条件 (変数名) を評価。将来式にする場合はここを拡張"""
    if not condition:
        return True
    value = variables.get(condition.strip())
    if isinstance(value, str):
        return value.strip().lower() not in ("", "false", "0", "none", "null")
    return bool(value)


# ============================================================================
# メイン
# ============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="./profile.json", type=str, help="profile.json パス (既定: ./profile.json)")
    parser.add_argument("--archetypes-dir", default=None, type=str, help="assets/archetypes/ パス (省略時は自動解決)")
    parser.add_argument("--templates-dir", default=None, type=str, help="assets/templates/ パス (省略時は自動解決)")
    parser.add_argument("--schema", default=None, type=str, help="profile.schema.json パス (省略時は自動解決)")
    parser.add_argument("--assets-dir", default=None, type=str, help="assets/ のルート (archetypes/templates/schema をまとめて解決)")
    parser.add_argument(
        "--force-overwrite",
        action="append",
        default=[],
        help="ユーザー編集を無視して上書きするファイル。複数指定可、'all' で全部",
    )
    parser.add_argument("--dry-run", action="store_true", help="実ファイルを書かず動作確認のみ")
    args = parser.parse_args()

    profile_path = Path(args.profile).resolve()
    if not profile_path.exists():
        print(f"ERROR: profile.json が見つかりません: {profile_path}", file=sys.stderr)
        return 1

    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    # assets path 解決 (Phase 9 packaging 対応)
    if args.assets_dir:
        assets_root = Path(args.assets_dir).resolve()
    else:
        assets_root = _resolve_assets_dir()
    schema_path = Path(args.schema).resolve() if args.schema else (assets_root / "knowledge" / "schema" / "profile.schema.json")
    errs = validate_profile(profile, schema_path)
    if errs:
        print("ERROR: profile.json schema validation failed", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 2

    archetype_name = profile["archetype_primary"]
    archetypes_dir = Path(args.archetypes_dir).resolve() if args.archetypes_dir else (assets_root / "archetypes")
    templates_dir = Path(args.templates_dir).resolve() if args.templates_dir else (assets_root / "templates")

    chain = load_archetype_chain(archetypes_dir, archetype_name)
    status = chain[-1].get("status", "")
    if status == "planned":
        print(
            f"ERROR: archetype '{archetype_name}' は MVP 未実装 (status: planned)。",
            file=sys.stderr,
        )
        print(
            "  profile.archetype_primary を 'daily-utility' に変更して再実行してください。",
            file=sys.stderr,
        )
        return 3

    # deprecated archetype のハンドリング (design-heavy → project.design_focus flag)
    if status == "deprecated":
        print(
            f"ERROR: archetype '{archetype_name}' は廃止されました。",
            file=sys.stderr,
        )
        desc = chain[-1].get("description", "").strip()
        if desc:
            print(f"  {desc}", file=sys.stderr)
        return 3

    merged_archetype = merge_archetype_chain(chain)
    variables = flatten_profile(profile)

    cwd = Path.cwd()
    state = load_state(cwd)

    # profile_hash 判定
    profile_hash = _sha256(json.dumps(profile, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    if not args.force_overwrite and state.get("profile_hash") == profile_hash:
        print(
            f"INFO: profile.json に変化なし。前回と同一 scaffold 済み。"
            f" 強制再適用したい場合は --force-overwrite all を指定してください。",
            file=sys.stderr,
        )

    force_set = set(args.force_overwrite)

    # 通常 templates
    results: list[tuple[str, str]] = []
    for entry in merged_archetype.get("templates", []):
        action, msg = apply_template_entry(entry, templates_dir, cwd, variables, state, force_set, args.dry_run)
        results.append((action, msg))

    # conditional
    for entry in merged_archetype.get("conditional_templates", []):
        if not eval_condition(entry.get("condition", ""), variables):
            continue
        action, msg = apply_template_entry(entry, templates_dir, cwd, variables, state, force_set, args.dry_run)
        results.append((action, msg))

    # 失敗 (blocked) があれば報告して exit 4
    blocked = [msg for action, msg in results if action == "blocked"]
    if blocked:
        print("ERROR: scaffold 中断", file=sys.stderr)
        for m in blocked:
            print(f"  {m}", file=sys.stderr)
        return 4

    # state 保存
    state["schema_version"] = "1.0"
    state["generator_version"] = GENERATOR_VERSION
    state["last_run_at"] = _iso_now()
    state["profile_hash"] = profile_hash
    state["archetype_primary"] = archetype_name
    if not args.dry_run:
        save_state(cwd, state)

    # サマリー出力
    print(f"✓ harness 生成完了 (archetype: {archetype_name})")
    print()
    print("ファイル:")
    for action, msg in results:
        sign = {
            "created": "+",
            "overwritten": "~",
            "merged": "~",
            "skipped": "-",
            "would-write": "?",
        }.get(action, "?")
        print(f"  {sign} {msg}")
    print()
    print("次のステップ:")
    print("  1. /harness-validator で整合性確認")
    print("  2. 不足している linter / formatter をインストール (ruff, biome 等)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
