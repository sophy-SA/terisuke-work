---
name: harness-validator
description: |
  harness-generator で scaffold された CLAUDE.md / subagents / hooks / settings.json
  を静的に検査し、衝突や不整合 (CLAUDE.md 肥大、hook matcher 重複、subagent 参照切れ、
  秘密情報漏洩等) を検出する read-only な skill。harness-report.md と
  harness-report.json を出力する。
  Use when the user says "harness を検証して", "CLAUDE.md サイズ確認", "hooks 監査",
  "validate my harness", "整合性チェック". harness-generator の直後、または手動編集後
  に実行する。
  Do NOT use as a general code linter (use ruff/eslint), for PR review
  (use code-reviewer skill), for security audit of application code
  (use security-review skill), or to auto-fix issues (validator は read-only).
allowed-tools: Read, Glob, Grep, Bash(python3:*), Bash(ls:*), Bash(cat:*), Bash(find:*)
---

# harness-validator

**役割**: scaffold 後の harness 一式を**読み取り専用**で検査し、以下を出力:
- `./harness-report.md` — 人間可読
- `./harness-report.json` — 機械可読 (report.schema.json 準拠)

## 起動時チェックリスト

```
- [ ] Step 1: cwd を確認 (harness が存在するディレクトリか)
- [ ] Step 2: profile.json が存在するか確認 (profile-driven check のため)
- [ ] Step 3: scripts/run_all.py を実行して全チェック走査
- [ ] Step 4: 結果サマリー + 重要な issue を提示
- [ ] Step 5: ユーザーに次アクション案内 (fix 後の再実行、または無視の判断)
```

## Step 1-2: 前提確認

対象ディレクトリに以下が存在するか:
- `CLAUDE.md` (推奨。無ければ C01 以降スキップ + 警告)
- `.claude/settings.json` (C04/C05/C12 対象)
- `.claude/subagents/*.md` (C07/C08 対象)
- `./profile.json` (C13 等の profile-driven チェック用、無ければ skip 扱い)

## Step 3: `run_all.py` 実行

```bash
python3 .../scripts/run_all.py \
  --target . \
  --output-json ./harness-report.json \
  --output-md ./harness-report.md \
  --schema <repo>/assets/knowledge/schema/report.schema.json
```

## Step 4: 結果提示

report の summary を表示:

```
Harness Validation Report
Target: /path/to/project
Archetype: daily-utility (v1.0)
Summary: 0 errors, 2 warnings, 1 info

WARNINGS:
  [C01] CLAUDE.md が 58 行 (budget: 50)
    WHY:   長い CLAUDE.md は「半分無視される」(Anthropic 公式)
    FIX:   Architecture セクション (lines 30-55) を docs/architecture.md に移す

  [C05] hook matcher "Edit|Write" が PostToolUse に 2 件重複
    WHY:   同一 matcher の重複は意図しないチェインを起こす
    FIX:   .claude/settings.json の PostToolUse entries を統合

INFO:
  [C03] CLAUDE.md lines 20-38 が 18 行の散文ブロック
    WHY:   ポインタ主義から外れている兆候
    FIX:   別ファイルに切り出して `@docs/...md` で参照
```

errors=0 なら ✓、warnings があれば ⚠️、errors があれば ✗ の見た目にする。

## Step 5: 次アクション

- errors=0 なら: `harness は健全です。開発を始めてください。`
- warnings / errors がある: `harness-report.md を確認し、修正後に再度 validator を実行してください。`
- `C13` (secret block hook 無し) など profile 要件由来の場合: `profile.json を更新するか、該当 hook を手動で追加してください。`

## Validator の原則

1. **Read-only**: いかなるファイルも編集しない
2. **Actionable**: 全ての issue に `WHY` と `FIX` を添える (WHY + FIX 原則 by Sakasegawa)
3. **機械可読**: `harness-report.json` を report.schema.json に準拠させる
4. **False positive 最小**: WARN は警告、ERROR は「間違いなく壊れている」状態のみ

## 禁止事項

- ファイルを編集・削除しない (auto-fix は将来の `--apply-fixes` フラグで分離)
- profile.json 無しでも動作する (profile-driven チェックは skip + INFO 表示)
- 全チェック失敗で例外終了しない (可能な限り全てのチェックを完走して report)
- report の severity を勝手に downgrade しない

## 参照ファイル

- [references/check-catalog.md](references/check-catalog.md) — 全チェック (C01-C99) 定義
- [references/severity-policy.md](references/severity-policy.md) — ERROR / WARNING / INFO 判定ルール
- `../../assets/knowledge/schema/report.schema.json` — 出力 report の JSON Schema
