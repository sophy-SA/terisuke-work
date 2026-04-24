#!/usr/bin/env python3
"""detect_archetype.py

harness-profiler の一部。回答ベクトル (S1-S5 完了時点の部分 profile) から
各アーキタイプのスコア (0.0-1.0) を計算し、primary を推定する。

詳細ロジックは references/archetype-signals.md を参照。

Usage:
    # stdin から JSON を受け取る
    echo '{"project": {...}, "workflow": {...}, ...}' | python3 detect_archetype.py

    # または --input FILE
    python3 detect_archetype.py --input partial-profile.json

Output:
    stdout に以下形式の JSON:
        {
            "archetype_primary": "daily-utility",
            "archetype_scores": {
                "daily-utility": 0.72,
                "library-package": 0.08,
                "production-saas": 0.10,
                "mobile-app": 0.03,
                "ml-data": 0.04,
                "infra-iac": 0.03
            },
            "mixed_warning": false
        }
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


ARCHETYPES = [
    "daily-utility",
    "library-package",
    "production-saas",
    "mobile-app",
    "ml-data",
    "infra-iac",
]


def score_daily_utility(p: dict[str, Any]) -> float:
    score = 0.0
    project = p.get("project", {})
    workflow = p.get("workflow", {})
    qg = p.get("quality_gates", {})
    safety = p.get("safety", {})

    root_kind = project.get("root_kind", []) or []
    required = set(qg.get("required_checks", []) or [])

    if "cli" in root_kind:
        score += 0.40
    strictness = workflow.get("precommit_strictness", "")
    if strictness == "none":
        score += 0.20
    elif strictness == "lint-only":
        score += 0.15
    if not qg.get("ci_external", False) and required.issubset({"lint", "format"}):
        score += 0.20
    if not safety.get("handles_secrets", False):
        score += 0.10
    if workflow.get("plan_work_review") is False:
        score += 0.10
    # cli のみ (他の root_kind がない)
    if root_kind == ["cli"]:
        score += 0.20
    return score


def score_library_package(p: dict[str, Any]) -> float:
    score = 0.0
    project = p.get("project", {})
    qg = p.get("quality_gates", {})

    root_kind = project.get("root_kind", []) or []
    required = set(qg.get("required_checks", []) or [])

    if "library" in root_kind:
        score += 0.50
    if {"typecheck", "unit-test"}.issubset(required):
        score += 0.20
    if "api-compat" in required or "semver-check" in required:
        score += 0.20
    # CI は library には通常必要
    if not qg.get("ci_external", False):
        score += 0.05
    return score


def score_production_saas(p: dict[str, Any]) -> float:
    score = 0.0
    project = p.get("project", {})
    workflow = p.get("workflow", {})
    qg = p.get("quality_gates", {})
    safety = p.get("safety", {})

    root_kind = project.get("root_kind", []) or []
    required = set(qg.get("required_checks", []) or [])

    if "web" in root_kind:
        score += 0.40
    if {"typecheck", "unit-test"}.issubset(required):
        score += 0.25
    if "security-scan" in required:
        score += 0.15
    if safety.get("handles_secrets", False):
        score += 0.15
    if workflow.get("plan_work_review", False):
        score += 0.10
    if not qg.get("ci_external", False):
        score += 0.05
    return score


def score_mobile_app(p: dict[str, Any]) -> float:
    score = 0.0
    project = p.get("project", {})
    qg = p.get("quality_gates", {})

    root_kind = project.get("root_kind", []) or []
    languages = project.get("languages", []) or []
    required = set(qg.get("required_checks", []) or [])

    if "mobile" in root_kind:
        score += 0.50
    # Swift/Kotlin/JS/TS/Dart (Flutter だが Dart は enum に無いので approx)
    if any(l in ("swift", "kotlin") for l in languages):
        score += 0.20
    if "visual-regression" in required or "integration-test" in required:
        score += 0.15
    if "a11y" in required:
        score += 0.10
    return score


def score_ml_data(p: dict[str, Any]) -> float:
    score = 0.0
    project = p.get("project", {})
    workflow = p.get("workflow", {})
    qg = p.get("quality_gates", {})
    safety = p.get("safety", {})

    root_kind = project.get("root_kind", []) or []
    languages = project.get("languages", []) or []
    required = set(qg.get("required_checks", []) or [])

    if "notebook" in root_kind:
        score += 0.50
    if languages and languages[0] == "python":
        score += 0.20
    if "integration-test" in required:
        score += 0.10
    if workflow.get("plan_work_review", False):
        score += 0.10
    if safety.get("handles_secrets", False):
        score += 0.10
    return score


def score_infra_iac(p: dict[str, Any]) -> float:
    score = 0.0
    project = p.get("project", {})
    qg = p.get("quality_gates", {})
    safety = p.get("safety", {})
    workflow = p.get("workflow", {})

    root_kind = project.get("root_kind", []) or []
    required = set(qg.get("required_checks", []) or [])
    destructive = set(safety.get("destructive_ops", []) or [])

    if "infra" in root_kind:
        score += 0.50
    if "infra-plan-review" in required:
        score += 0.20
    if destructive & {"terraform-apply", "helm-upgrade", "k8s-apply", "deploy"}:
        score += 0.15
    if workflow.get("plan_work_review", False):
        score += 0.10
    # IaC では secret 扱いはほぼ必須
    if safety.get("handles_secrets", False):
        score += 0.05
    return score


# design-heavy は削除済み (project.design_focus フラグに統合)


def compute(partial_profile: dict[str, Any]) -> dict[str, Any]:
    raw_scores = {
        "daily-utility": score_daily_utility(partial_profile),
        "library-package": score_library_package(partial_profile),
        "production-saas": score_production_saas(partial_profile),
        "mobile-app": score_mobile_app(partial_profile),
        "ml-data": score_ml_data(partial_profile),
        "infra-iac": score_infra_iac(partial_profile),
    }
    total = sum(raw_scores.values())
    if total <= 0:
        scores = {a: 0.0 for a in ARCHETYPES}
        scores["daily-utility"] = 1.0
    else:
        scores = {a: round(v / total, 4) for a, v in raw_scores.items()}

    sorted_scores = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    primary = sorted_scores[0][0]
    top_diff = sorted_scores[0][1] - sorted_scores[1][1]
    mixed = top_diff < 0.15 and total > 0

    return {
        "archetype_primary": primary,
        "archetype_scores": scores,
        "mixed_warning": mixed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="partial profile JSON ファイル。省略時は stdin から読む",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = compute(data)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
