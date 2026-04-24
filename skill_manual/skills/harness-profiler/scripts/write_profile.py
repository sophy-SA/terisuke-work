#!/usr/bin/env python3
"""write_profile.py

harness-profiler の最終ステップ。回答 dict を profile.json スキーマ (v1.0)
に整形して書き出し、JSON Schema で検証する。

Usage:
    # 標準: 会話内で Claude が組み立てた answers dict を stdin から受ける
    echo '{"answers": {...}, "archetype": {...}}' | python3 write_profile.py --output ./profile.json

    # バッチモード: answers.yaml を直接読み込み
    python3 write_profile.py --batch answers.yaml --output ./profile.json

    # 検証のみ (ファイルを書かずに)
    python3 write_profile.py --dry-run --input existing-profile.json

Input format (stdin / --batch):
    answers dict は interview-script.md の S1-S6 の回答をキーとする。
    詳細は references/interview-script.md の answers.yaml フォーマット参照。

Exit:
    0  成功
    1  入力エラー
    2  スキーマ検証エラー
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


def _iso_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_profile(answers: dict[str, Any], archetype_info: dict[str, Any]) -> dict[str, Any]:
    """回答 dict を profile.json 形式に整形する。

    answers の想定構造 (references/interview-script.md の S1-S6):
        S1: {project_summary, languages, root_kind}
        S2: {plan_work_review, precommit_strictness, long_running_agents}
        S3: {required_checks, ci_external}
        S4: {ai_second_opinion, specialized_reviewers}
        S5: {handles_secrets, destructive_ops}
        S6: {project_name, locale, existing_claude_dir, intents}

    archetype_info: detect_archetype.py の出力
        {archetype_primary, archetype_scores, mixed_warning}
    """
    s1 = answers.get("S1", {}) or {}
    s2 = answers.get("S2", {}) or {}
    s3 = answers.get("S3", {}) or {}
    s4 = answers.get("S4", {}) or {}
    s5 = answers.get("S5", {}) or {}
    s6 = answers.get("S6", {}) or {}

    # MVP: locale は ja 強制
    locale = s6.get("locale", "ja")
    if locale != "ja":
        print(
            f"WARNING: MVP は locale=ja のみサポート。"
            f"{locale!r} は ja に置き換えます。",
            file=sys.stderr,
        )
        locale = "ja"

    project_name = s6.get("project_name") or s1.get("project_name") or "unnamed-project"

    profile = {
        "schema_version": "1.0",
        "generated_at": _iso_now(),
        "project": {
            "name": project_name,
            "summary": s1.get("project_summary", ""),
            "languages": s1.get("languages", []),
            "root_kind": s1.get("root_kind", []),
        },
        "archetype_primary": archetype_info.get("archetype_primary", "daily-utility"),
        "archetype_scores": archetype_info.get("archetype_scores", {}),
        "workflow": {
            "plan_work_review": bool(s2.get("plan_work_review", False)),
            "precommit_strictness": s2.get("precommit_strictness", "lint-only"),
            "long_running_agents": bool(s2.get("long_running_agents", False)),
        },
        "quality_gates": {
            "required_checks": s3.get("required_checks", ["lint", "format"]),
            "ci_external": bool(s3.get("ci_external", False)),
        },
        "review": {
            "ai_second_opinion": bool(s4.get("ai_second_opinion", False)),
            "specialized_reviewers": s4.get("specialized_reviewers", []),
        },
        "safety": {
            "handles_secrets": bool(s5.get("handles_secrets", False)),
            "destructive_ops": s5.get("destructive_ops", []),
        },
        "meta": {
            "locale": locale,
            "existing_claude_dir": bool(s6.get("existing_claude_dir", False)),
            "intents": s6.get("intents", []),
        },
        "overrides": {
            "exclude_subagents": [],
            "force_include_hooks": [],
        },
    }
    return profile


def load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open(encoding="utf-8") as f:
        return json.load(f)


def validate(profile: dict[str, Any], schema_path: Path) -> list[str]:
    """検証エラーのリストを返す (空なら OK)。

    jsonschema が利用可能ならそれを使い、無ければ簡易チェック。
    """
    errors: list[str] = []
    try:
        import jsonschema

        schema = load_schema(schema_path)
        validator = jsonschema.Draft7Validator(schema)
        for err in validator.iter_errors(profile):
            loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"[{loc}] {err.message}")
    except ImportError:
        # jsonschema 未インストール時は最低限のチェック
        required = {"schema_version", "project", "archetype_primary", "workflow", "quality_gates", "meta"}
        missing = required - profile.keys()
        if missing:
            errors.append(f"missing top-level keys: {sorted(missing)}")
    return errors


def load_answers_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        print(
            "ERROR: PyYAML が必要。'pip install pyyaml' でインストールしてください。",
            file=sys.stderr,
        )
        raise
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_schema_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    # このスクリプトからの相対: ../../../assets/knowledge/schema/profile.schema.json
    here = Path(__file__).resolve()
    return (here.parents[3] / "assets" / "knowledge" / "schema" / "profile.schema.json").resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="answers + archetype_info の JSON ファイル。省略時は stdin",
    )
    parser.add_argument(
        "--batch",
        "-b",
        type=str,
        default=None,
        help="answers.yaml を直接読む (detect_archetype.py を内部呼び出し)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="./profile.json",
        help="出力先 (既定: ./profile.json)",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="profile.schema.json のパス (既定: リポジトリ相対)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイル書き込みをせずスキーマ検証のみ",
    )
    args = parser.parse_args()

    schema_path = resolve_schema_path(args.schema)

    # 入力取得
    if args.batch:
        answers = load_answers_yaml(Path(args.batch))
        # detect_archetype.py を呼ぶ代わりに、answers を仮 profile に変換して
        # 同じロジックを使う (ここでは detect_archetype 関数を import する)
        sys.path.insert(0, str(Path(__file__).parent))
        try:
            from detect_archetype import compute as compute_archetype  # noqa: E402
        except ImportError as e:
            print(f"ERROR: detect_archetype.py が見つからない: {e}", file=sys.stderr)
            return 1
        s1 = answers.get("S1", {}) or {}
        s2 = answers.get("S2", {}) or {}
        s3 = answers.get("S3", {}) or {}
        s4 = answers.get("S4", {}) or {}
        s5 = answers.get("S5", {}) or {}
        partial = {
            "project": {
                "languages": s1.get("languages", []),
                "root_kind": s1.get("root_kind", []),
            },
            "workflow": {
                "plan_work_review": s2.get("plan_work_review", False),
                "precommit_strictness": s2.get("precommit_strictness", "lint-only"),
            },
            "quality_gates": {
                "required_checks": s3.get("required_checks", []),
                "ci_external": s3.get("ci_external", False),
            },
            "review": {
                "specialized_reviewers": s4.get("specialized_reviewers", []),
            },
            "safety": {
                "handles_secrets": s5.get("handles_secrets", False),
            },
        }
        archetype_info = compute_archetype(partial)
    else:
        raw = sys.stdin.read() if args.input is None else Path(args.input).read_text(encoding="utf-8")
        data = json.loads(raw)
        if args.dry_run and "schema_version" in data:
            # --dry-run + 既存 profile の検証モード
            errs = validate(data, schema_path)
            if errs:
                for e in errs:
                    print(f"SCHEMA ERROR: {e}", file=sys.stderr)
                return 2
            print("OK", file=sys.stderr)
            return 0
        answers = data.get("answers", {})
        archetype_info = data.get("archetype", {})

    profile = build_profile(answers, archetype_info)

    errs = validate(profile, schema_path)
    if errs:
        print("ERROR: profile schema validation failed", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        json.dump(profile, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    out_path = Path(args.output)
    out_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path.resolve()}", file=sys.stderr)
    print(f"  archetype_primary: {profile['archetype_primary']}", file=sys.stderr)
    print(
        f"  archetype_scores: {json.dumps(profile.get('archetype_scores', {}), ensure_ascii=False)}",
        file=sys.stderr,
    )
    if archetype_info.get("mixed_warning"):
        print(
            "  WARNING: top2 archetypes within 0.15 — consider overriding archetype_primary",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
