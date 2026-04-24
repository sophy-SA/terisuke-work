# Hook Catalog

harness-generator が配置可能な hook テンプレート一覧。

## 自動配置 hook (archetype デフォルト)

### daily-utility

| hook ID | イベント | matcher | 目的 |
|---|---|---|---|
| `post-edit-format` | PostToolUse | `Edit|Write` | 編集後に対象ファイルを言語別 formatter で整形 |
| `pre-commit-lint` | (git hook) | - | `.git/hooks/pre-commit` から呼ばれる lint ゲート |

## 条件付き hook (profile に応じて)

### safety 系

| hook ID | 条件 | イベント | matcher |
|---|---|---|---|
| `block-secret-commit` | `safety.handles_secrets == true` | PreToolUse | `Bash` |
| `block-rm-rf` | `"rm-rf" in safety.destructive_ops` | PreToolUse | `Bash` |
| `block-force-push` | `"force-push" in safety.destructive_ops` | PreToolUse | `Bash` (計画中) |
| `block-db-migrate` | `"db-migrate" in safety.destructive_ops` | PreToolUse | `Bash` (計画中) |
| `block-deploy` | `"deploy" in safety.destructive_ops` | PreToolUse | `Bash` (計画中) |

### production-saas 系 (Phase 8)

| hook ID | 条件 | イベント | matcher |
|---|---|---|---|
| `protect-linter-config` | 常時 (production-saas) | PreToolUse | `Edit|Write` |
| `pre-pr-gate` | `archetype=production-saas` | PreToolUse | `Bash(gh pr create:*)` |

### ml-data 系 (Phase 8)

| hook ID | 条件 | イベント | matcher |
|---|---|---|---|
| `block-large-artifact` | `archetype=ml-data` | PreToolUse | `Write` |

### design-heavy 系 (Phase 8)

| hook ID | 条件 | イベント | matcher |
|---|---|---|---|
| `post-edit-screenshot` | `archetype=design-heavy` AND gstack 利用可 | PostToolUse | `Edit|Write` |

---

## hook script の共通契約 (harness-forge 生成品)

すべての hook script は以下の共通フォーマット:

1. `#!/usr/bin/env bash` + `set -euo pipefail` 冒頭
2. `INPUT_JSON=$(cat)` で stdin から Claude Code の JSON を受け取る
3. `python3 -c` で `tool_name`, `tool_input` を抽出
4. 判定ロジック
5. **成功時は exit 0, 無言** (back-pressure 原則)
6. **失敗 (ブロック) 時は exit 2, stderr に以下フォーマット**:
   ```
   ERROR: [何が違反だったか]
   WHY:   [なぜこれがブロック対象か, 参考 URL あれば]
   FIX:   [具体的な修正手順]
   ```

詳細は `assets/templates/_shared/hooks/` 以下のテンプレートを参照。

## `force_include_hooks` オーバーライド

profile.json の `overrides.force_include_hooks` に hook ID を列挙すると、archetype の
デフォルトに関係なく配置される:

```json
{
  "overrides": {
    "force_include_hooks": ["block-force-push", "block-db-migrate"]
  }
}
```

存在しない ID を指定するとエラー。

## `exclude_subagents` オーバーライド

同様に `overrides.exclude_subagents` で subagent を除外できるが、対応する hook も
自動削除される (subagent を参照する hook がある場合)。
