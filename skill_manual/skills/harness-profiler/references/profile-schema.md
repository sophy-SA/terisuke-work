# profile.json スキーマ (人間可読版)

**正式スキーマ**: `assets/knowledge/schema/profile.schema.json` (JSON Schema draft-07)

この文書はユーザーが profile.json を手動編集する際の参考用。

---

## 最小必須サンプル (MVP)

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "my-cli-tool",
    "languages": ["python"],
    "root_kind": ["cli"]
  },
  "archetype_primary": "daily-utility",
  "workflow": {
    "precommit_strictness": "lint-only"
  },
  "quality_gates": {
    "required_checks": ["lint", "format"]
  },
  "meta": {
    "locale": "ja",
    "existing_claude_dir": false
  }
}
```

## 完全サンプル

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-24T12:00:00Z",
  "project": {
    "name": "sample-project",
    "summary": "日常的なファイル整理を自動化する CLI ツール",
    "languages": ["python"],
    "root_kind": ["cli"]
  },
  "archetype_primary": "daily-utility",
  "archetype_scores": {
    "daily-utility": 0.72,
    "production-saas": 0.15,
    "ml-data": 0.08,
    "design-heavy": 0.05
  },
  "workflow": {
    "plan_work_review": false,
    "precommit_strictness": "lint-only",
    "long_running_agents": false
  },
  "quality_gates": {
    "required_checks": ["lint", "format"],
    "ci_external": false
  },
  "review": {
    "ai_second_opinion": false,
    "specialized_reviewers": []
  },
  "safety": {
    "handles_secrets": false,
    "destructive_ops": []
  },
  "meta": {
    "locale": "ja",
    "existing_claude_dir": false,
    "intents": [
      "一度に1機能だけ実装する",
      "commit 前に必ず lint を通す",
      "ファイル移動前に dry-run で対象を確認"
    ]
  },
  "overrides": {
    "exclude_subagents": [],
    "force_include_hooks": []
  }
}
```

---

## フィールドの意味と選択肢

### `schema_version` (required, "1.0")

互換性のないメジャー変更時に bump する。

### `project.name` (required, string)

プロジェクト名。`CLAUDE.md` の一番上に埋め込まれる。

### `project.languages[]` (required, array)

許可値: `python`, `typescript`, `javascript`, `go`, `rust`, `swift`, `kotlin`, `ruby`, `java`, `csharp`, `php`, `shell`, `other`

最低1つ必要。最初の要素が "primary language" として扱われ、linter / formatter 選択に使用。

### `project.root_kind[]` (required, array)

許可値: `cli`, `web`, `notebook`, `design`, `mixed`

アーキタイプ判定の主要信号。複数選択可。

### `archetype_primary` (required, enum)

許可値: `daily-utility`, `production-saas`, `ml-data`, `design-heavy`

Generator がこの値で template set を決定。手動編集可能。

### `workflow.precommit_strictness` (default: "lint-only")

- `none` — pre-commit hook を配置しない
- `lint-only` — lint のみ (MVP daily-utility デフォルト)
- `lint-test` — lint + 差分テスト
- `full` — lint + typecheck + test + security (production-saas 推奨)

### `quality_gates.required_checks[]`

許可値: `lint`, `format`, `typecheck`, `unit-test`, `integration-test`, `security-scan`, `a11y`, `visual-regression`

各項目に対し、対応する hook または CI job が生成される (archetype が対応する範囲で)。

### `safety.handles_secrets` (boolean)

true なら `.claude/hooks/block-secret-commit.sh` が必須配置される (Validator C13)。

### `safety.destructive_ops[]`

許可値: `deploy`, `db-migrate`, `force-push`, `rm-rf`, `drop-table`

各項目に対し、PreToolUse hook でブロックするスクリプトが生成される。

### `meta.locale` (required)

MVP では `ja` のみ。将来 `en` など追加予定。

### `meta.intents[]` (optional, max 5)

CLAUDE.md の「プロジェクト固有」セクションに埋め込まれる。3つまでが推奨。

### `overrides.exclude_subagents[]`

archetype がデフォルト生成する subagent のうち、生成しないものを列挙。
例: daily-utility で reviewer すら要らない場合は `["reviewer"]`。

### `overrides.force_include_hooks[]`

archetype の標準セットに追加で含めたい hook の ID (hook-catalog.md 参照)。

---

## 手動編集の注意点

1. `schema_version` は勝手に上げない。Generator が非互換バージョンを拒否する。
2. `archetype_primary` を変更すると、生成される template set が全く変わる。再生成時は既存 scaffold が上書き対象になる (merge mode 動作)。
3. `archetype_scores` は監査ログ。手動編集しても Generator は無視する (`archetype_primary` のみ参照)。
4. JSON Schema 違反があると Generator が起動時にエラー出力する。修正後再実行。

## スキーマ検証コマンド

```bash
python3 -c "
import json, jsonschema
schema = json.load(open('assets/knowledge/schema/profile.schema.json'))
data = json.load(open('./profile.json'))
jsonschema.validate(data, schema)
print('OK')
"
```

失敗時はエラーメッセージに不整合フィールドが示される。
