#!/usr/bin/env python3
"""evolve.py — harness drift 検出 + 選択的反映

3-way 比較:
    state_hash  : .harness-forge.state.json に記録された前回 scaffold 時の hash
    current_hash: disk 上の現在のファイル hash
    rendered_hash: 現 archetype + profile から再 render した期待 hash

カテゴリ:
    unchanged                  — state == current == rendered
    template_updated_safe      — state == current, state != rendered (template 更新, user 未編集)
    template_updated_conflict  — state != current, state != rendered (両方 drift)
    user_edited_only           — state != current, state == rendered (user のみ編集)
    user_deleted               — state にあり, current 不在
    new_template_file          — state に無し, archetype に存在
    removed_template_file      — state にあり, archetype から消えた

Usage:
    evolve.py --profile profile.json [--state .harness-forge.state.json] [--dry-run|--apply] [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# harness-generator/scripts を import path に追加
_THIS = Path(__file__).resolve()
_GEN_SCRIPTS = _THIS.parent.parent.parent / "harness-generator" / "scripts"
sys.path.insert(0, str(_GEN_SCRIPTS))

from apply_scaffold import (  # type: ignore
    _resolve_assets_dir,
    _sha256,
    _sha256_file,
    flatten_profile,
    load_archetype_chain,
    load_state,
    merge_archetype_chain,
    save_state,
    validate_profile,
)
from render import render  # type: ignore


# ---------- helpers ----------

def _render_template(
    src: Path, variables: dict[str, Any]
) -> bytes:
    """テンプレートファイルを読み込んで render → bytes"""
    text = src.read_text(encoding="utf-8")
    rendered = render(text, variables)
    return rendered.encode("utf-8")


def _eval_condition(condition: str, variables: dict[str, Any]) -> bool:
    """conditional_templates の condition 文字列を評価 (apply_scaffold と同じロジック)"""
    if not condition:
        return True
    val = variables.get(condition)
    if isinstance(val, str):
        return val.strip().lower() not in ("", "false", "0", "none", "null")
    return bool(val)


def _gather_template_entries(
    archetype: dict[str, Any], variables: dict[str, Any]
) -> list[dict[str, Any]]:
    """templates + 有効な conditional_templates をフラットな list で返す"""
    entries: list[dict[str, Any]] = list(archetype.get("templates", []))
    for ct in archetype.get("conditional_templates", []) or []:
        cond = ct.get("condition", "")
        if _eval_condition(cond, variables):
            entries.append({k: v for k, v in ct.items() if k != "condition"})
    return entries


def _categorize(
    state_hash: str | None,
    current_hash: str | None,
    rendered_hash: str | None,
) -> str:
    """3-way hash 比較からカテゴリ判定"""
    in_state = state_hash is not None
    in_disk = current_hash is not None
    in_archetype = rendered_hash is not None

    if not in_archetype:
        return "removed_template_file" if in_state else "unrelated"

    if not in_state:
        return "new_template_file"

    if not in_disk:
        return "user_deleted"

    # 全部存在 — 3-way 比較
    state_eq_current = state_hash == current_hash
    state_eq_rendered = state_hash == rendered_hash

    if state_eq_current and state_eq_rendered:
        return "unchanged"
    if state_eq_current and not state_eq_rendered:
        return "template_updated_safe"
    if not state_eq_current and state_eq_rendered:
        return "user_edited_only"
    return "template_updated_conflict"


# ---------- main analysis ----------

def analyze(
    profile: dict[str, Any],
    state: dict[str, Any],
    archetypes_dir: Path,
    templates_dir: Path,
    cwd: Path,
) -> dict[str, Any]:
    """drift 検出のコア処理"""
    archetype_name = profile["archetype_primary"]
    chain = load_archetype_chain(archetypes_dir, archetype_name)
    merged = merge_archetype_chain(chain)
    variables = flatten_profile(profile)

    # 現 archetype が宣言する template entries (skip skip_if_exists 含む)
    entries = _gather_template_entries(merged, variables)

    state_hashes: dict[str, str] = state.get("file_hashes", {}) or {}

    # 現 archetype の各 template について評価
    files_report: list[dict[str, Any]] = []
    seen_dests: set[str] = set()

    for entry in entries:
        src_rel = entry["src"]
        dest = entry["dest"]
        merge_mode = entry.get("merge", "overwrite")
        seen_dests.add(dest)

        src_path = templates_dir / src_rel
        if not src_path.exists():
            files_report.append({
                "path": dest,
                "category": "missing_template_source",
                "merge": merge_mode,
                "note": f"template source not found: {src_rel}",
            })
            continue

        rendered = _render_template(src_path, variables)
        rendered_hash = _sha256(rendered)

        disk_path = cwd / dest
        current_hash = _sha256_file(disk_path) if disk_path.exists() else None

        state_hash = state_hashes.get(dest)

        cat = _categorize(state_hash, current_hash, rendered_hash)

        # skip_if_exists の特殊処理: state にあって disk にあれば、これは「保護対象」なので
        # template_updated_* でも user 介入なしには触らない方針 (静かに unchanged 扱い)
        if merge_mode == "skip_if_exists" and state_hash and current_hash:
            if cat in ("template_updated_safe", "template_updated_conflict"):
                cat = "skip_protected"

        files_report.append({
            "path": dest,
            "category": cat,
            "merge": merge_mode,
            "src": src_rel,
            "state_hash": state_hash,
            "current_hash": current_hash,
            "rendered_hash": rendered_hash,
        })

    # state にあるが今回 archetype に存在しないファイル → removed
    for state_path in state_hashes:
        if state_path in seen_dests:
            continue
        disk_path = cwd / state_path
        current_hash = _sha256_file(disk_path) if disk_path.exists() else None
        files_report.append({
            "path": state_path,
            "category": "removed_template_file" if current_hash else "user_deleted",
            "merge": None,
            "src": None,
            "state_hash": state_hashes[state_path],
            "current_hash": current_hash,
            "rendered_hash": None,
        })

    # サマリー
    summary: dict[str, int] = {}
    for f in files_report:
        summary[f["category"]] = summary.get(f["category"], 0) + 1

    return {
        "archetype": archetype_name,
        "summary": summary,
        "files": files_report,
    }


# ---------- apply ----------

APPLIABLE_CATEGORIES = {"template_updated_safe", "new_template_file"}
FORCE_APPLIABLE_CATEGORIES = APPLIABLE_CATEGORIES | {"template_updated_conflict"}


def apply_changes(
    report: dict[str, Any],
    profile: dict[str, Any],
    archetypes_dir: Path,
    templates_dir: Path,
    cwd: Path,
    state: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    """report の category に基づき選択的反映、state 更新、conflict 出力"""
    chain = load_archetype_chain(archetypes_dir, profile["archetype_primary"])
    merged = merge_archetype_chain(chain)
    variables = flatten_profile(profile)

    targets = FORCE_APPLIABLE_CATEGORIES if force else APPLIABLE_CATEGORIES
    applied: list[str] = []
    skipped_conflicts: list[dict[str, str]] = []

    file_hashes: dict[str, str] = dict(state.get("file_hashes", {}) or {})

    # template entries を src で逆引きするための map
    src_by_dest: dict[str, dict[str, Any]] = {}
    for entry in _gather_template_entries(merged, variables):
        src_by_dest[entry["dest"]] = entry

    for f in report["files"]:
        cat = f["category"]
        path = f["path"]

        if cat == "template_updated_conflict" and not force:
            skipped_conflicts.append({
                "path": path,
                "state_hash": f.get("state_hash"),
                "current_hash": f.get("current_hash"),
                "rendered_hash": f.get("rendered_hash"),
            })
            continue

        if cat not in targets:
            continue

        entry = src_by_dest.get(path)
        if not entry:
            continue

        src_path = templates_dir / entry["src"]
        rendered = _render_template(src_path, variables)
        dest_path = cwd / path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(rendered)

        # 実行ビット
        if entry.get("mode"):
            try:
                mode_int = int(str(entry["mode"]), 8)
                os.chmod(dest_path, mode_int)
            except (ValueError, OSError):
                pass

        file_hashes[path] = _sha256(rendered)
        applied.append(f"{cat}: {path}")

    # state 更新
    state["file_hashes"] = file_hashes
    state["last_run_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state.setdefault("evolution_history", []).append({
        "at": state["last_run_at"],
        "applied_count": len(applied),
        "force": force,
    })
    save_state(cwd, state)

    # conflict 出力
    conflict_md = cwd / ".evolved-conflict.md"
    if skipped_conflicts:
        lines = [
            "# harness-evolver: 衝突したファイル",
            "",
            f"生成日時: {state['last_run_at']}",
            "",
            "以下のファイルは **template も user も両方更新済み** のため自動反映を skip しました。",
            "手動で 3-way merge してください。",
            "",
        ]
        for c in skipped_conflicts:
            lines += [
                f"## `{c['path']}`",
                "",
                f"- 前回 scaffold 時 hash: `{c['state_hash']}`",
                f"- 現在 disk hash:        `{c['current_hash']}`",
                f"- 期待 (新 template) hash: `{c['rendered_hash']}`",
                "",
                "次に試すこと:",
                "1. 現在の file をバックアップ",
                "2. `git diff` で user 編集内容を確認",
                "3. template の最新版を確認",
                "4. 手動マージ後 `git add <path>` → `evolve.py --apply` 再実行",
                "",
            ]
        conflict_md.write_text("\n".join(lines), encoding="utf-8")
    elif conflict_md.exists():
        conflict_md.unlink()

    # evolution log
    log_path = cwd / ".harness-forge.evolution.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{state['last_run_at']} applied={len(applied)} skipped_conflicts={len(skipped_conflicts)} force={force}\n")
        for a in applied:
            f.write(f"  + {a}\n")
        for c in skipped_conflicts:
            f.write(f"  ! conflict: {c['path']}\n")

    return {
        "applied": applied,
        "skipped_conflicts": skipped_conflicts,
    }


# ---------- output formatting ----------

CATEGORY_ICON = {
    "unchanged": "  ",
    "template_updated_safe": "↑ ",
    "template_updated_conflict": "⚠ ",
    "user_edited_only": "● ",
    "user_deleted": "✗ ",
    "new_template_file": "+ ",
    "removed_template_file": "- ",
    "skip_protected": "🔒",
    "missing_template_source": "? ",
    "unrelated": "  ",
}


def format_report_md(report: dict[str, Any], applied: dict[str, Any] | None = None) -> str:
    summary = report["summary"]
    lines = [
        f"# harness-evolver report",
        "",
        f"Archetype: `{report['archetype']}`",
        "",
        "## Summary",
        "",
    ]
    for cat, count in sorted(summary.items()):
        lines.append(f"- {cat}: {count}")
    lines += ["", "## Files", ""]

    for f in report["files"]:
        icon = CATEGORY_ICON.get(f["category"], "  ")
        lines.append(f"- {icon} `{f['path']}` — **{f['category']}**")

    lines.append("")
    lines.append("## Next steps")
    lines.append("")
    if applied is not None:
        lines.append(f"- Applied: {len(applied['applied'])} 件")
        if applied["skipped_conflicts"]:
            lines.append(f"- Skipped (conflict): {len(applied['skipped_conflicts'])} 件 → `.evolved-conflict.md` を確認")
        lines.append("- 反映後は `/harness-validator` で整合性を再確認してください")
    else:
        appliable = sum(summary.get(c, 0) for c in APPLIABLE_CATEGORIES)
        if appliable == 0:
            lines.append("- 反映可能な変更なし")
        else:
            lines.append(f"- `--apply` で {appliable} 件を反映できます")
            if summary.get("template_updated_conflict", 0):
                lines.append(f"- 衝突 {summary['template_updated_conflict']} 件は手動マージが必要")
    return "\n".join(lines)


# ---------- CLI ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="harness-evolver: drift 検出 + 選択的反映")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--state", default=".harness-forge.state.json")
    parser.add_argument("--archetypes-dir", default=None)
    parser.add_argument("--templates-dir", default=None)
    parser.add_argument("--schema", default=None)
    parser.add_argument("--apply", action="store_true", help="変更を反映する (default は dry-run)")
    parser.add_argument("--force", action="store_true", help="conflict も強制上書き (user 編集破棄)")
    parser.add_argument("--dry-run", action="store_true", help="明示 dry-run (default 動作)")
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-md", default=None)
    args = parser.parse_args()

    profile_path = Path(args.profile).resolve()
    if not profile_path.exists():
        print(f"ERROR: profile not found: {profile_path}", file=sys.stderr)
        return 2

    state_path = Path(args.state).resolve()
    if not state_path.exists():
        print(
            f"ERROR: state file not found: {state_path}\n"
            "       harness-generator で先に scaffold してください。",
            file=sys.stderr,
        )
        return 2

    cwd = state_path.parent

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))

    # asset 解決
    assets = _resolve_assets_dir()
    archetypes_dir = Path(args.archetypes_dir) if args.archetypes_dir else assets / "archetypes"
    templates_dir = Path(args.templates_dir) if args.templates_dir else assets / "templates"
    schema_path = Path(args.schema) if args.schema else assets / "knowledge" / "schema" / "profile.schema.json"

    if schema_path.exists():
        errors = validate_profile(profile, schema_path)
        if errors:
            print("profile validation failed:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 2

    report = analyze(profile, state, archetypes_dir, templates_dir, cwd)

    applied: dict[str, Any] | None = None
    if args.apply:
        applied = apply_changes(
            report, profile, archetypes_dir, templates_dir, cwd, state, force=args.force
        )

    md = format_report_md(report, applied)
    print(md)

    if args.output_md:
        Path(args.output_md).write_text(md, encoding="utf-8")
    if args.output_json:
        out = {"report": report}
        if applied is not None:
            out["applied"] = applied
        Path(args.output_json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
